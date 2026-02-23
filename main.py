import os
import configparser
from pathlib import Path
from io import BytesIO

import requests
import discord
from discord import option
from discord.ext import commands
from escpos.printer import Network
from PIL import Image
from PIL import ImageEnhance

from multitone import main as multitoneImage

print("[escpos-printer-bot] hello welcome to bot, it is initializing")

class ConfigManager:
    def __init__(self, config_file='escpos-printer-bot.ini'):
        self.config = configparser.ConfigParser(allow_no_value=True)

        if not Path(config_file).exists():
            print("[ConfigManager] The config file was not found, creating one now")
            try:
                self.write_config(config_file)
            except Exception as e:
                print(f"[ConfigManager] Error while writing config: {repr(e)}")
                exit(1)
            print("[ConfigManager] The config file has been created, please configure it and then restart the bot")
            exit(0)
        self.config.read(config_file)

    def get_discord_config(self):
        discord = self.config['Discord']
        try:
            return {
                'token': discord.get('token'),
                'allowed_role_ids': discord.get('allowed_role_ids'),
                'verbosity_to_discord': discord.getboolean('verbosity_to_discord')
            }
        except Exception as e:
            print(f"[ConfigManager] Error while reading Discord config: {repr(e)}")
            exit(1)
    
    def get_printer_config(self):
        print = self.config['Printer']
        try:
            return {
                'ip': print.get('ip'),
                'profile': print.get('profile'),
                'enable_multitone': print.getboolean('enable_multitone')
            }
        except Exception as e:
            print(f"[ConfigManager] Error while reading Printer config: {repr(e)}")
            exit(1)
    
    def write_config(self, config_file):
        self.config.add_section('Discord')
        self.config.set('Discord', '; Set your bot token, IDs of roles which are allowed to use the bot SEPARATED BY COMMA, and whether the bot should report the current state')
        self.config.set('Discord', 'token', '1234')
        self.config.set('Discord', 'allowed_role_ids', '1234')
        self.config.set('Discord', 'verbosity_to_discord', 'true')

        self.config.add_section('Printer')
        self.config.set('Printer', 'ip', "192.168.69.56")
        self.config.set('Printer', 'profile', "TM-T88V")
        self.config.set('Printer', 'enable_multitone', 'true')
        self.config.set('Printer', '; Enable multitone printing only on printers with hardware support.')
        self.config.set('Printer', '; For supported printers see https://github.com/dalpil/epson-multi-tone#epson-printers-with-4-bit-multi-tone-support')

        with open(config_file, 'w') as file:
            self.config.write(file)

def parse_paper_status(status):
    print(f"[parse_paper_status] Received paper status: {status}")
    if status == 0:
        return "There is no paper"
    elif status == 1:
        return "The paper is almost out"
    elif status == 2:
        return "There is plenty of paper"
    else:
        return "Unknown Status"

def calculate_brightness(image):
    greyscale_image = image.convert('L')
    histogram = greyscale_image.histogram()
    pixels = sum(histogram)
    brightness = scale = len(histogram)

    for index in range(0, scale):
        ratio = histogram[index] / pixels
        brightness += ratio * (-scale + index)

    return 1 if brightness == 255 else brightness / scale

def calculate_brightness_enhancement(brightness, max_enhancement=5):
    """
    Calculate how much to brighten an image based on its current brightness.
    
    Args:
        brightness: Float from 0.0 (dark) to 1.0 (bright)
        max_enhancement: Maximum brightening factor to apply (default 2.0)
    
    Returns:
        Float representing the enhancement multiplier (1.0 = no change)
    """
    return 1.0 + (1.0 - brightness) ** 3.9 * (max_enhancement - 1.0)

config = ConfigManager()

discordConfig = config.get_discord_config()
token = discordConfig["token"]
allowed_role_ids = list(map(int, str(discordConfig["allowed_role_ids"]).split(',')))
#this is ugly but! get role ids str -> split by comma to list -> turn list strs into int
verbosity_to_discord = discordConfig["verbosity_to_discord"]

printerConfig = config.get_printer_config()
printer_ip = printerConfig["ip"]
printer_profile = printerConfig["profile"]
enable_multitone = printerConfig["enable_multitone"]

if None in [allowed_role_ids, verbosity_to_discord, printer_ip, printer_profile, enable_multitone]:
    print("[escpos-printer-bot] Couldn't find a required configuration option, check your configuration file!")

print(f"[escpos-printer-bot] Read configuration, seems to be valid! The configuration is:\n                     Discord: Allowed roles are {allowed_role_ids} and verbosity to discord is {verbosity_to_discord}\n                     Printer: IP is {printer_ip}, profile is {printer_profile} and multitoning is {enable_multitone}")

supported_pil_image_types = (".png", ".jpg", ".jpeg", ".j2k", ".jpx", ".bmp", ".webp", ".tiff")

print("[escpos-printer-bot] Now starting the bot")

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("Hello from escpos-printer-bot")

@bot.slash_command(name="print", description="Print a message on the printer (5 second cooldown)")
@commands.cooldown(1, 5, commands.BucketType.user) 
@option("texttoprint", description="The text you want to print (200 character limit)", required=True)
async def print_message(ctx: discord.ApplicationContext, texttoprint: str):
    await ctx.defer()
    member = ctx.guild.get_member(ctx.author.id)
    if not member or not any(role_id in [role.id for role in member.roles] for role_id in allowed_role_ids):
        print(f"[print] User '{ctx.author.id}' does not have the required roles to use the print command")
        await ctx.respond("You don't have the required role to use this command")
        raise commands.CheckFailure
    callerDisplayname = member.display_name
    callerUsername = member.name

    msg = await ctx.respond(f"Preparing to print your text")
    print(f"[print] User '{callerDisplayname} ({callerUsername})' is printing message: {texttoprint}")
    try:
        if len(texttoprint) > 200:
            raise ValueError("The text to print is too long. Please limit it to 200 characters")
        
        if verbosity_to_discord: await msg.edit("Connecting to the printer... (1/2)")
        printer = Network(printer_ip, profile=printer_profile)
        printer.open()
        if printer.paper_status() == 0:
            printer.close()
            raise Exception("There is no paper in the printer")
        print("[print] Opened printer")
        if verbosity_to_discord: await msg.edit("Connected, now printing your text... (2/2)")
        printer.text(f"Message from '{callerDisplayname} ({callerUsername})':\n{texttoprint}\n")
        printer.cut()
        printer.close()
        print("[print] Closed printer")
    except Exception as e:
        print(repr(e))
        await msg.edit(f"An error occurred while trying to print: {repr(e)}")
        return
    await msg.edit(f"Message '{texttoprint}' printed successfully")

@bot.slash_command(name="image", description="Print an image on the printer (15 second cooldown)")
@commands.cooldown(1, 15, commands.BucketType.user) 
@option("imagetoprint", type=discord.Attachment, description="The image you want to print", required=True)
@option("multitone", type=bool, description="Higher quality by using 8 shades of gray instead of 2", required=False)
async def print_image(ctx: discord.ApplicationContext, imagetoprint: discord.Attachment, multitone: bool = False):
    await ctx.defer()
    member = ctx.guild.get_member(ctx.author.id)
    if not member or not any(role_id in [role.id for role in member.roles] for role_id in allowed_role_ids):
        print(f"[image] User '{ctx.author.id}' does not have the required roles to use the print command")
        await ctx.respond("You don't have the required role to use this command")
        raise commands.CheckFailure
    callerDisplayname = member.display_name
    callerUsername = member.name
    imagename = imagetoprint.filename

    msg = await ctx.respond(f"Preparing to print your image {imagename}")
    print(f"[image] User '{callerDisplayname} ({callerUsername})' is printing an image {imagename}")

    try:
        if not imagename.lower().endswith(supported_pil_image_types):
            raise ValueError(f"The file {imagename} is not an image. Supported types are: {(', '.join(supported_pil_image_types))}")
        print(f"[image] File is of type {(', '.join(supported_pil_image_types))}")
        
        if verbosity_to_discord: await msg.edit("Downloading your image (1/4)")
        print("[image] Downloading image")
        remote_file = requests.get(imagetoprint.url)

        image = Image.open(BytesIO(remote_file.content))
        print("[image] Image opened")
        # open image from file

        if verbosity_to_discord: await msg.edit("Applying processing to your image (2/4)")
        if not image.width < image.height:
            print("[image] Image is wide, rotating to landscape")
            image = image.rotate(270, expand=True)
        image = image.convert("L")
        #Acquire image, rotate and grayscale it

        brightness = calculate_brightness(image)
        print(f"[image] Calculated brightness: {brightness}")
        brightness_enhancement = calculate_brightness_enhancement(brightness)
        print(f"[image] Calculated brightness enhancement: {brightness_enhancement}")
        brightnessfilter = ImageEnhance.Brightness(image)
        image = brightnessfilter.enhance(brightness_enhancement)
        # Calculate brightness to apply and apply it
    
        contrastfilter = ImageEnhance.Contrast(image)
        image = contrastfilter.enhance(0.8)
        #screenshot = screenshot.quantize(colors=8)
        # Reduce contrast a bit

        image.thumbnail((512, 768), Image.Resampling.NEAREST)
        # Resize to be max 512 wide and 768 tall
        print("[image] Adjusted, grayscaled and resized image")

        byteImage = BytesIO()
        image.save(byteImage, "JPEG")
        byteImage.seek(0)
        discordFile = discord.File(fp=byteImage, filename=imagename, description="Image uploaded for printing")
        print("[image] Created discord file object from processed image")

        if multitone:
            if not enable_multitone:
                raise Exception("Multitoning is disabled in the configuration")
            print("[image] Processing multitone")
            contrastfilter = ImageEnhance.Contrast(image)
            image = contrastfilter.enhance(0.7)
            brightnessfilter = ImageEnhance.Brightness(image)
            image = brightnessfilter.enhance(1.28)

            tempBytes = BytesIO()
            tempBytes = multitoneImage(image=image, output_file=None, output_image=None, num_lines=100, resize=None, sharpness=None, contrast=None, cut=None, speed=1, heads_energizing=1, loglevel="INFO")
        
        if verbosity_to_discord: await msg.edit("Connecting to the printer... (3/4)")
        printer = Network(printer_ip, profile=printer_profile)
        printer.open()
        if printer.paper_status() == 0:
            printer.close()
            raise Exception("There is no paper in the printer")
        print("[image] Opened printer")
        try:
            if verbosity_to_discord: await msg.edit("Connected, now printing your image... (4/4)")
            printer.text(f"Image from '{callerDisplayname} ({callerUsername})':\n")
            if multitone:
                print("[image] Printing multitone")
                printer._raw(tempBytes)
                printer.set_with_default()
            else:
                print("[image] Printing normal")
                printer.image(image, center=True, impl='graphics')
            
            printer.cut()
            printer.close()
            print("[image] Closed printer")
        except Exception as e:
            printer.close()
            raise e
    except Exception as e:
        print(repr(e))
        await msg.edit(f"An error occurred while trying to print your image: {repr(e)}")
        #await ctx.respond(f"An error occurred while trying to print image: {repr(e)}")
        return
    await msg.edit(f"Image {imagename} printed successfully", file=discordFile)

@bot.slash_command(name="supportedimagetypes", description="Check what types of images are supported")
async def supported_image_types(ctx: discord.ApplicationContext):
    await ctx.defer()
    member = ctx.guild.get_member(ctx.author.id)
    callerDisplayname = member.display_name
    callerUsername = member.name
    try:
        await ctx.respond(f"Hi {callerDisplayname}, image types supported right now are {(', '.join(supported_pil_image_types))}")
    except Exception as e:
        print(repr(e))
        await ctx.respond(f"An error occurred while: {repr(e)}")
        return

@bot.slash_command(name="paperstatus", description="Check how much paper is left in the printer")
@commands.cooldown(1, 10, commands.BucketType.user) 
async def paper_status(ctx: discord.ApplicationContext):
    await ctx.defer()
    msg = await ctx.respond("Checking the paper status")
    try:
        if verbosity_to_discord: await msg.edit("Connecting to the printer... (1/1)")
        printer = Network(printer_ip, profile=printer_profile)
        printer.open()
        print("[paper_status] Opened printer")
        paper_status = parse_paper_status(printer.paper_status())
        printer.close()
    except Exception as e:
        print(repr(e))
        await msg.edit(f"An error occurred while getting paper status: {repr(e)}")
        return
    await msg.edit(f"Paper Status: {paper_status}")

@bot.slash_command(name="chat", description="Send a message to chat")
@option("texttoprint", description="The text you want to send (500 character limit)", required=True)
async def chat_message(ctx: discord.ApplicationContext, texttoprint: str):
    await ctx.defer()
    member = ctx.guild.get_member(ctx.author.id)
    callerDisplayname = member.display_name
    callerUsername = member.name
    try:
        if len(texttoprint) > 500:
            raise ValueError("The text to print is too long. Please limit it to 500 characters")
        await ctx.respond(f"{callerDisplayname}: '{texttoprint}'")
    except Exception as e:
        print(repr(e))
        await ctx.respond(f"An error occurred while: {repr(e)}")
        return
    
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: discord.DiscordException):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.respond("The used command is currently on cooldown!")
    elif isinstance(error, commands.MissingRole):
        await ctx.respond("You don't have the required role to use this command")
    else:
        raise error  # Here we raise other errors to ensure they aren't ignored

bot.run(token) # run the bot with the token
