# escpos-printer-bot

(working name)

## Overview
Discord bot to print to an ESC/POS network printer

escpos-printer-bot exposes 6 slash commands, they are documented here:

- `/hello` - Say hello to the bot
  - Mostly to test the bot is working
- `/print` - Print a message on the printer (30 second cooldown)
  - Prints basic text, up to 200 characters
- `/image` - Print an image on the printer (30 second cooldown)
  - Prints an image, it gets processed to make sure it isn't too dark/bright and wide images get rotated so you can print them the long way
  - Multi-toning is available as well, it increases the printed image quality by using eight shades of gray instead of two
- `/supportedimagetypes` - Check what types of images are supported
  - This is so users can tell what formats they can give the /image command before trying it
- `/paperstatus` - Check how much paper is left in the printer
  - Simply connects to the printer and checks how much paper is left
- `/chat` - Send a message to chat
  - This will have the bot repeat your message (up to 500 characters) and was mostly a test for arguments. Unused but i left it in because why not

## Usage
### Requirements
- Python 3.10 or newer but not 3.14
- Receipt printer supporting ESC/POS over TCP/IP
- A Discord server to invite the bot to

### Setup
Clone the repo to a directory, then create a venv if you need one. Now install dependencies with `pip install -r requirements.txt`.

Also create a bot application on the Discord Developers site.

### Configuration
Run the bot a single time to create the config file, then you can edit the values in `escpos-printer-bot.ini` to match your setup.

It will look like this:
```ini
[Discord]
; set your bot token, ids of roles which are allowed to use the bot, and whether the bot should report the current state
token = my_token
allowed_role_ids = 634265, 24256, 1234, 553476, 412356
verbosity_to_discord = true

[Printer]
ip = 192.168.69.56
profile = TM-T88V
enable_multitone = true
; enable multitone printing only on printers with hardware support.
; for supported printers see https://github.com/dalpil/epson-multi-tone#epson-printers-with-4-bit-multi-tone-support
```

The `true`/`false` keywords aren't case sensitive.

#### Discord
- `token`: This should be your bot token from Discord Developer
- `allowed_role_ids`: Numerical ID of a role to allow printing. Users without the role will not be able to print.
- `verbosity_to_discord`: Report the current state of printing back to wherever the command was run with status messages
  - Example: "Downloading image", "Printing image", "Connecting to the printer"

#### Printer
- `printer_ip`: The IP of your receipt printer
- `printer_profile`: Profile that most closely matches your printer
  - See [python-escpos documentation](https://python-escpos.readthedocs.io/en/latest/printer_profiles/available-profiles.html) for available profiles
  - If there is no matching profile, you can specify `default` which is "suitable for standards-compliant or Epson-branded printers"
- `enable_multitone`: Enable multitone printing for higher quality images (8 shades of gray instead of two)
  - Enable only on printers with hardware support for it, see [this repo](https://github.com/dalpil/epson-multi-tone#epson-printers-with-4-bit-multi-tone-support) for a list

If you need to reset your configuration file because you messed up the format or something, just delete it and the bot will make another when run.

### Invite the bot
On the Discord Developers website, select the application then go to the Installation tab.

We will now do some setup for the permissions:
1. In the **Installation Contexts** section, make sure only `Guild Install` is checked
2. Scroll down to **Default Install Settings** section
3. In the Scopes subsection, add `applications.commands` and `bot`
4. In the Permissions subsection, add `Attach Files` and `Send Messages`
5. Save the changes

Now you can scroll slightly up to the **Install Link** section, and copy the **Discord Provided Link**. Open that link in a new tab to invite the bot to your server.

### Running
Once you configured everything properly, start up the bot by running `main.py`. Once you see the output `Stellar Receipt Printer#1227 is ready and online!`, you can start using it.

The logs in the terminal window should show you everything that's happening.

## Credits
The multitoning was ripped straight out of [dalphil's epson-multi-tone](https://github.com/dalpil/epson-multi-tone) project and slightly modified for use in this bot.