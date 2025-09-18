"""
Misc helper functions.
"""

import colorsys
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys


class Color:
    """Color formats."""

    alpha_num = "100"

    def __init__(self, hex_color):
        self.hex_color = hex_color

    def __str__(self):
        return self.hex_color

    @property
    def rgb(self):
        """Convert a hex color to rgb."""
        return "{},{},{}".format(*hex_to_rgb(self.hex_color))

    @property
    def xrgba(self):
        """Convert a hex color to xrdb rgba."""
        return hex_to_xrgba(self.hex_color)

    @property
    def rgba(self):
        """Convert a hex color to rgba."""
        return "rgba({},{},{},{})".format(*hex_to_rgb(self.hex_color), self.alpha_dec)

    @property
    def alpha(self):
        """Add URxvt alpha value to color."""
        return f"[{self.alpha_num}]{self.hex_color}"

    @property
    def alpha_dec(self):
        """Export the alpha value as a decimal number in [0, 1]."""
        return int(self.alpha_num) / 100

    @property
    def decimal(self):
        """Export color in decimal."""
        return "{}{}".format("#", int(self.hex_color[1:], 16))

    @property
    def decimal_strip(self):
        """Strip '#' from decimal color."""
        return int(self.hex_color[1:], 16)

    @property
    def octal(self):
        """Export color in octal."""
        return "{}{}".format("#", oct(int(self.hex_color[1:], 16))[2:])

    @property
    def octal_strip(self):
        """Strip '#' from octal color."""
        return oct(int(self.hex_color[1:], 16))[2:]

    @property
    def strip(self):
        """Strip '#' from color."""
        return self.hex_color[1:]

    @property
    def red(self):
        """Red value as float between 0 and 1."""
        return "%.3f" % (hex_to_rgb(self.hex_color)[0] / 255.0)

    @property
    def green(self):
        """Green value as float between 0 and 1."""
        return "%.3f" % (hex_to_rgb(self.hex_color)[1] / 255.0)

    @property
    def blue(self):
        """Blue value as float between 0 and 1."""
        return "%.3f" % (hex_to_rgb(self.hex_color)[2] / 255.0)

    def lighten(self, percent):
        """Lighten color by percent."""
        percent = float(re.sub(r"[\D\.]", "", str(percent)))
        return Color(lighten_color(self.hex_color, percent / 100))

    def darken(self, percent):
        """Darken color by percent."""
        percent = float(re.sub(r"[\D\.]", "", str(percent)))
        return Color(darken_color(self.hex_color, percent / 100))

    def saturate(self, percent):
        """Saturate a color."""
        percent = float(re.sub(r"[\D\.]", "", str(percent)))
        return Color(saturate_color(self.hex_color, percent / 100))


def validate_path(file_path):
    """Validate file path for security."""
    # Security: Prevent directory traversal attacks
    if ".." in file_path or file_path.startswith(("/proc", "/sys")):
        raise ValueError(f"Invalid file path: {file_path}")

    # Normalize the path
    normalized_path = os.path.normpath(file_path)
    if normalized_path != file_path:
        logging.warning(f"Path normalized from {file_path} to {normalized_path}")

    return normalized_path


def read_file(input_file):
    """Read data from a file and trim newlines."""
    validated_path = validate_path(input_file)
    with open(validated_path) as file:
        return file.read().splitlines()


def read_file_json(input_file):
    """Read data from a json file."""
    validated_path = validate_path(input_file)
    with open(validated_path) as json_file:
        return json.load(json_file)


def read_file_raw(input_file):
    """Read data from a file as is, don't strip
    newlines or other special characters."""
    validated_path = validate_path(input_file)
    with open(validated_path) as file:
        return file.readlines()


def save_file(data, export_file):
    """Write data to a file."""
    create_dir(os.path.dirname(export_file))

    try:
        with open(export_file, "w") as file:
            file.write(data)
    except PermissionError:
        logging.warning("Couldn't write to %s.", export_file)


def save_file_json(data, export_file):
    """Write data to a json file."""
    create_dir(os.path.dirname(export_file))

    with open(export_file, "w") as file:
        json.dump(data, file, indent=4)


def create_dir(directory):
    """Alias to create the cache dir."""
    os.makedirs(directory, exist_ok=True)


def setup_logging():
    """Logging config."""
    logging.basicConfig(
        format=("[%(levelname)s\033[0m] \033[1;31m%(module)s\033[0m: %(message)s"),
        level=logging.INFO,
        stream=sys.stdout,
    )
    logging.addLevelName(logging.ERROR, "\033[1;31mE")
    logging.addLevelName(logging.INFO, "\033[1;32mI")
    logging.addLevelName(logging.WARNING, "\033[1;33mW")


def hex_to_rgb(color):
    """Convert a hex color to rgb."""
    return tuple(bytes.fromhex(color.strip("#")))


def hex_to_xrgba(color):
    """Convert a hex color to xrdb rgba."""
    col = color.lower().strip("#")
    return "{}{}/{}{}/{}{}/ff".format(*col)


def rgb_to_hex(color):
    """Convert an rgb color to hex."""
    return "#{:02x}{:02x}{:02x}".format(*color)


def darken_color(color, amount):
    """Darken a hex color."""
    color = [int(col * (1 - amount)) for col in hex_to_rgb(color)]
    return rgb_to_hex(color)


def lighten_color(color, amount):
    """Lighten a hex color."""
    color = [int(col + (255 - col) * amount) for col in hex_to_rgb(color)]
    return rgb_to_hex(color)


def blend_color(color, color2):
    """Blend two colors together."""
    r1, g1, b1 = hex_to_rgb(color)
    r2, g2, b2 = hex_to_rgb(color2)

    r3 = int(0.5 * r1 + 0.5 * r2)
    g3 = int(0.5 * g1 + 0.5 * g2)
    b3 = int(0.5 * b1 + 0.5 * b2)

    return rgb_to_hex((r3, g3, b3))


def saturate_color(color, amount):
    """Saturate a hex color."""
    r, g, b = hex_to_rgb(color)
    r, g, b = (x / 255.0 for x in (r, g, b))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    s = amount
    r, g, b = colorsys.hls_to_rgb(h, lightness, s)
    r, g, b = (x * 255.0 for x in (r, g, b))

    return rgb_to_hex((int(r), int(g), int(b)))


def rgb_to_yiq(color):
    """Sort a list of colors."""
    return colorsys.rgb_to_yiq(*hex_to_rgb(color))


def disown(cmd):
    """Call a system command in the background,
    disown it and hide it's output."""
    # Security: Ensure cmd is a list to prevent shell injection
    if isinstance(cmd, str):
        logging.warning("Command passed as string, converting to list for security")
        cmd = cmd.split()

    # Security: Validate that the command exists
    if not cmd or not shutil.which(cmd[0]):
        logging.error(f"Command not found: {cmd[0] if cmd else 'empty command'}")
        return False

    try:
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False
        )  # Explicitly disable shell
        return True
    except (subprocess.SubprocessError, OSError) as e:
        logging.error(f"Failed to execute command {cmd}: {e}")
        return False


def get_pid(name):
    """Check if process is running by name."""
    if not shutil.which("pidof"):
        return False

    # Security: Validate process name to prevent injection
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", name):
        logging.warning(f"Invalid process name: {name}")
        return False

    try:
        if platform.system() != "Darwin":
            subprocess.check_output(["pidof", "-s", name], stderr=subprocess.DEVNULL)
        else:
            subprocess.check_output(["pidof", name], stderr=subprocess.DEVNULL)

    except subprocess.CalledProcessError:
        return False

    return True
