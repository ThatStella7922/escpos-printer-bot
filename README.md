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
Create a file named `.env` in the project folder with these contents:
```
token = {your bot token}
printer_ip = {your printer ip}
printer_profile = {your printer profile}
allowed_role_id = {the id of a role to allow}
```

Then edit the values to match your setup.

- `token`: This should be your bot token from Discord Developer
- `printer_ip`: The IP of your receipt printer
- `printer_profile`: Profile that most closely matches your printer
  - See [python-escpos documentation](https://python-escpos.readthedocs.io/en/latest/printer_profiles/available-profiles.html) for available profiles
  - If there is no matching profile, you can specify `default` which is "suitable for standards-compliant or Epson-branded printers"
- `allowed_role_id`: Numerical ID of a role to allow printing. Users without the role will not be able to print.

For example, to configure for an allowed role id, and an epson tm-t88v on the IP 192.168.69.56:
```
token = blah blah blah my token
printer_ip = 192.168.69.56
printer_profile = TM-T88V
allowed_role_id = 975115151437103236
```

If you want to allow multiple roles, see the `allowed_role_ids` variable specified in line 58 of `main.py`. This is a list of role IDs, specified as integers. Later on I'll make this more seamless and part of the .env file.

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