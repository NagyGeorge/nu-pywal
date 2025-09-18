"""
Reload programs.
"""

import logging
import os
import shutil
import sys

from . import util
from .settings import CACHE_DIR, MODULE_DIR, OS


def tty(tty_reload):
    """Load colors in tty."""
    tty_script = os.path.join(CACHE_DIR, "colors-tty.sh")
    term = os.environ.get("TERM")

    if tty_reload and term == "linux":
        util.disown(["sh", tty_script])


def xrdb(xrdb_files=None):
    """Merge the colors into the X db so new terminals use them."""
    xrdb_files = xrdb_files or [os.path.join(CACHE_DIR, "colors.Xresources")]

    if OS != "Darwin":
        for file in xrdb_files:
            try:
                util.run_command(["xrdb", "-merge", "-quiet", file], timeout=10)
            except util.PywalError as e:
                logging.warning(f"Failed to merge Xresources: {e}")


def gtk():
    """Reload GTK theme on the fly."""
    # Use the modern Python 3 GTK reload script
    gtk_reload = os.path.join(MODULE_DIR, "scripts", "gtk_reload.py")
    util.disown(["python3", gtk_reload])


def i3():
    """Reload i3 colors."""
    if shutil.which("i3-msg") and util.get_pid("i3"):
        util.disown(["i3-msg", "reload"])


def bspwm():
    """Reload bspwm colors."""
    if shutil.which("bspc") and util.get_pid("bspwm"):
        util.disown(["bspc", "wm", "-r"])


def kitty():
    """Reload kitty colors."""
    if util.get_pid("kitty") and os.getenv("TERM") == "xterm-kitty":
        try:
            util.run_command(
                [
                    "kitty",
                    "@",
                    "set-colors",
                    "--all",
                    os.path.join(CACHE_DIR, "colors-kitty.conf"),
                ],
                timeout=10,
            )
        except util.PywalError as e:
            logging.warning(f"Failed to reload kitty colors: {e}")


def alacritty():
    """Reload Alacritty colors."""
    if shutil.which("alacritty") and util.get_pid("alacritty"):
        # Alacritty doesn't support runtime color changes,
        # but we can touch the config file to trigger a reload if watch mode is enabled
        alacritty_config = os.path.expanduser("~/.config/alacritty/alacritty.yml")
        if os.path.exists(alacritty_config):
            try:
                os.utime(alacritty_config, None)
                logging.info("Touched Alacritty config file for reload")
            except OSError:
                logging.warning("Failed to touch Alacritty config file")


def wezterm():
    """Reload WezTerm colors."""
    if util.get_pid("wezterm-gui"):
        # WezTerm supports runtime color reloading via CLI
        try:
            util.run_command(
                [
                    "wezterm",
                    "cli",
                    "spawn",
                    "--",
                    "sh",
                    "-c",
                    f"cat {os.path.join(CACHE_DIR, 'sequences')}",
                ],
                timeout=10,
            )
        except util.PywalError as e:
            logging.warning(f"Failed to reload WezTerm colors: {e}")


def foot():
    """Reload Foot terminal colors."""
    if util.get_pid("foot"):
        # Foot supports OSC sequences for color changes
        sequences_file = os.path.join(CACHE_DIR, "sequences")
        if os.path.exists(sequences_file):
            try:
                with open(sequences_file) as f:
                    f.read()
                # Send sequences to all foot instances
                util.run_command(["pkill", "-USR1", "foot"], timeout=5)
            except (OSError, util.PywalError) as e:
                logging.warning(f"Failed to reload Foot colors: {e}")


def ghostty():
    """Reload Ghostty colors."""
    if util.get_pid("ghostty"):
        # Ghostty supports OSC sequences like most modern terminals
        sequences_file = os.path.join(CACHE_DIR, "sequences")
        if os.path.exists(sequences_file):
            try:
                util.run_command(
                    ["ghostty", "+send-osc", f"@{sequences_file}"], timeout=10
                )
            except util.PywalError as e:
                logging.warning(f"Failed to reload Ghostty colors: {e}")


def polybar():
    """Reload polybar colors."""
    if shutil.which("polybar") and util.get_pid("polybar"):
        util.disown(["pkill", "-USR1", "polybar"])


def sway():
    """Reload sway colors."""
    if shutil.which("swaymsg") and util.get_pid("sway"):
        util.disown(["swaymsg", "reload"])


def hyprland():
    """Reload Hyprland colors."""
    if shutil.which("hyprctl") and util.get_pid("Hyprland"):
        util.disown(["hyprctl", "reload"])


def river():
    """Reload River colors."""
    if shutil.which("riverctl") and util.get_pid("river"):
        # River doesn't have a direct reload, but we can restart rivercarro or similar
        util.disown(["pkill", "-USR1", "river"])


def wayfire():
    """Reload Wayfire colors."""
    if shutil.which("wayfire") and util.get_pid("wayfire"):
        util.disown(["pkill", "-USR1", "wayfire"])


def colors(cache_dir=CACHE_DIR):
    """Reload colors. (Deprecated)"""
    sequences = os.path.join(cache_dir, "sequences")

    logging.error("'wal -r' is deprecated: Use 'cat %s' instead.", sequences)

    if os.path.isfile(sequences):
        sys.stdout.write("".join(util.read_file(sequences)))


def env(xrdb_file=None, tty_reload=True):
    """Reload environment."""
    xrdb(xrdb_file)
    i3()
    bspwm()
    kitty()
    alacritty()
    wezterm()
    foot()
    ghostty()
    sway()
    hyprland()
    river()
    wayfire()
    polybar()
    logging.info("Reloaded environment.")
    tty(tty_reload)
