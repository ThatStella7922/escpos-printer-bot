import discord
import os
import requests
from dotenv import load_dotenv
from discord import option
from discord.ext import commands
from escpos.printer import Network
from PIL import Image
from PIL import ImageEnhance
from io import BytesIO

load_dotenv() # load all the variables from the env file

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



token = os.getenv('token', "bruh")
printer_ip = os.getenv('printer_ip', "192.168.69.56")
printer_profile = os.getenv('printer_profile', "TM-T88V")
allowed_role_id = int(os.getenv('allowed_role_id', "975115151437103236"))
# Sane enough defaults

allowed_role_ids = [allowed_role_id, 1294376414547673161, 1472742124566089871, 1396670499848982528] # List of allowed role IDs, mostly for including more roles than just the one in dotenv

supported_pil_image_types = (".png", ".jpg", ".jpeg", ".j2k", ".jpx", ".bmp", ".webp", ".tiff")

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("Hello from escpos-printer-bot")

@bot.slash_command(name="print", description="Print a message on the printer (30 second cooldown)")
@commands.cooldown(1, 30, commands.BucketType.user) 
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
    print(f"[print] User '{callerDisplayname} ({callerUsername})' is printing message: {texttoprint}")
    try:
        if len(texttoprint) > 200:
            raise ValueError("The text to print is too long. Please limit it to 200 characters")
        
        printer = Network(printer_ip, profile=printer_profile)
        printer.open()
        if printer.paper_status() == 0:
            printer.close()
            raise Exception("There is no paper in the printer")
        print("[print] Opened printer")
        printer.text(f"Message from '{callerDisplayname} ({callerUsername})':\n{texttoprint}\n")
        printer.cut()
        printer.close()
        print("[print] Closed printer")
    except Exception as e:
        print(repr(e))
        await ctx.respond(f"An error occurred while trying to print: {repr(e)}")
        return
    await ctx.respond(f"Message '{texttoprint}' printed successfully")

@bot.slash_command(name="image", description="Print an image on the printer (30 second cooldown)")
@commands.cooldown(1, 30, commands.BucketType.user) 
@option("imagetoprint", type=discord.Attachment, description="The image you want to print", required=True)
async def print_image(ctx: discord.ApplicationContext, imagetoprint: discord.Attachment):
    await ctx.defer()
    member = ctx.guild.get_member(ctx.author.id)
    if not member or not any(role_id in [role.id for role in member.roles] for role_id in allowed_role_ids):
        print(f"[image] User '{ctx.author.id}' does not have the required roles to use the print command")
        await ctx.respond("You don't have the required role to use this command")
        raise commands.CheckFailure
    callerDisplayname = member.display_name
    callerUsername = member.name
    imagename = imagetoprint.filename

    print(f"[image] User '{callerDisplayname} ({callerUsername})' is printing an image {imagename}")
    try:
        if not imagename.endswith(supported_pil_image_types):
            raise ValueError(f"The file {imagename} is not an image. Supported types are: {(', '.join(supported_pil_image_types))}")
        print(f"[image] File is of type {(', '.join(supported_pil_image_types))}")
        
        remote_file = requests.get(imagetoprint.url)
        print("[image] Downloaded image")

        image = Image.open(BytesIO(remote_file.content))
        print("[image] Image opened")
        # open image from file

        if not image.width < image.height:
            print("[image] Image is wide, rotating to landscape")
            image = image.rotate(270, expand=True)
        image = image.convert("L")
        #Acquire image, rotate and grayscale it

        brightness = calculate_brightness(image)
        #print(f"[image] Calculated brightness: {brightness}")
        brightness_enhancement = calculate_brightness_enhancement(brightness)
        #print(f"[image] Calculated brightness enhancement: {brightness_enhancement}")
        brightnessfilter = ImageEnhance.Brightness(image)
        image = brightnessfilter.enhance(brightness_enhancement)
        # Calculate brightness to apply and apply it
    
        contrastfilter = ImageEnhance.Contrast(image)
        image = contrastfilter.enhance(0.7)
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
        
        printer = Network(printer_ip, profile=printer_profile)
        printer.open()
        if printer.paper_status() == 0:
            printer.close()
            raise Exception("There is no paper in the printer")
        print("[image] Opened printer")
        try:
            printer.text(f"Image from '{callerDisplayname} ({callerUsername})':\n")
            printer.image(image, center=True, impl='graphics')
            printer.cut()
            printer.close()
            print("[image] Closed printer")
        except Exception as e:
            printer.close()
            raise e
    except Exception as e:
        print(repr(e))
        await ctx.respond(f"An error occurred while trying to print image: {repr(e)}")
        return
    await ctx.respond(f"Image {imagename} printed successfully", file=discordFile)

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
    try:
        printer = Network(printer_ip, profile=printer_profile)
        printer.open()
        print("[paper_status] Opened printer")
        paper_status = parse_paper_status(printer.paper_status())
        printer.close()
    except Exception as e:
        print(repr(e))
        await ctx.respond(f"An error occurred while getting paper status: {repr(e)}")
        return
    await ctx.respond(f"Paper Status: {paper_status}")

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