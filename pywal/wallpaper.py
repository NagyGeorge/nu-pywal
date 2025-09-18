"""Set the wallpaper."""

import ctypes
import logging
import os
import re
import shutil
import subprocess
import urllib.parse

from . import util
from .settings import CACHE_DIR, HOME, OS


def get_desktop_env():
    """Identify the current running desktop environment."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP")
    if desktop:
        return desktop

    desktop = os.environ.get("DESKTOP_SESSION")
    if desktop:
        return desktop

    desktop = os.environ.get("GNOME_DESKTOP_SESSION_ID")
    if desktop:
        return "GNOME"

    desktop = os.environ.get("MATE_DESKTOP_SESSION_ID")
    if desktop:
        return "MATE"

    desktop = os.environ.get("SWAYSOCK")
    if desktop:
        return "SWAY"

    # Check for Hyprland
    desktop = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if desktop:
        return "HYPRLAND"

    # Check for River
    desktop = os.environ.get("RIVER_INIT")
    if desktop:
        return "RIVER"

    # Check for Wayfire
    desktop = os.environ.get("WAYFIRE_CONFIG_FILE")
    if desktop:
        return "WAYFIRE"

    # Check for other Wayland compositors
    wayland_display = os.environ.get("WAYLAND_DISPLAY")
    if wayland_display:
        # Generic Wayland detection
        return "WAYLAND"

    desktop = os.environ.get("DESKTOP_STARTUP_ID")
    if desktop and "awesome" in desktop:
        return "AWESOME"

    return None


def xfconf(img):
    """Call xfconf to set the wallpaper on XFCE."""
    xfconf_re = re.compile(
        r"^/backdrop/screen\d/monitor(?:0|\w*)/"
        r"(?:(?:image-path|last-image)|workspace\d/last-image)$",
        flags=re.M,
    )
    xfconf_data = subprocess.check_output(
        ["xfconf-query", "--channel", "xfce4-desktop", "--list"],
        stderr=subprocess.DEVNULL,
    ).decode("utf8")
    paths = xfconf_re.findall(xfconf_data)
    for path in paths:
        util.disown(
            [
                "xfconf-query",
                "--channel",
                "xfce4-desktop",
                "--property",
                path,
                "--set",
                img,
            ]
        )


def set_wm_wallpaper(img):
    """Set the wallpaper for non desktop environments."""
    if shutil.which("feh"):
        util.disown(["feh", "--bg-fill", img])

    elif shutil.which("xwallpaper"):
        util.disown(["xwallpaper", "--zoom", img])

    elif shutil.which("hsetroot"):
        util.disown(["hsetroot", "-fill", img])

    elif shutil.which("nitrogen"):
        util.disown(["nitrogen", "--set-zoom-fill", img])

    elif shutil.which("bgs"):
        util.disown(["bgs", "-z", img])

    elif shutil.which("hsetroot"):
        util.disown(["hsetroot", "-fill", img])

    elif shutil.which("habak"):
        util.disown(["habak", "-mS", img])

    elif shutil.which("display"):
        util.disown(["display", "-backdrop", "-window", "root", img])

    else:
        logging.error("No wallpaper setter found.")
        return


def set_desktop_wallpaper(desktop, img):
    """Set the wallpaper for the desktop environment."""
    desktop = str(desktop).lower()

    if "xfce" in desktop or "xubuntu" in desktop:
        xfconf(img)

    elif "muffin" in desktop or "cinnamon" in desktop:
        util.disown(
            [
                "gsettings",
                "set",
                "org.cinnamon.desktop.background",
                "picture-uri",
                "file://" + urllib.parse.quote(img),
            ]
        )

    elif "gnome" in desktop or "unity" in desktop:
        util.disown(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.background",
                "picture-uri",
                "file://" + urllib.parse.quote(img),
            ]
        )

    elif "mate" in desktop:
        util.disown(
            ["gsettings", "set", "org.mate.background", "picture-filename", img]
        )

    elif "sway" in desktop:
        util.disown(["swaymsg", "output", "*", "bg", img, "fill"])

    elif "hyprland" in desktop:
        util.disown(["hyprctl", "hyprpaper", "wallpaper", f",{img}"])

    elif "river" in desktop:
        util.disown(["riverctl", "spawn", "swaybg", "-i", img, "-m", "fill"])

    elif "wayfire" in desktop:
        util.disown(["wayfire", "-c", f"background = {img}"])

    elif "wayland" in desktop:
        # Generic Wayland fallback - try common Wayland wallpaper setters
        if shutil.which("swaybg"):
            util.disown(["swaybg", "-i", img, "-m", "fill"])
        elif shutil.which("oguri"):
            util.disown(["oguri"])
        elif shutil.which("wpaperd"):
            util.disown(["wpaperd"])
        else:
            logging.warning("No Wayland wallpaper setter found")

    elif "awesome" in desktop:
        util.disown(
            [
                "awesome-client",
                f"require('gears').wallpaper.maximized('{img}')",
            ]
        )

    elif "kde" in desktop:
        string = """
            var allDesktops = desktops();for (i=0;i<allDesktops.length;i++){
            d = allDesktops[i];d.wallpaperPlugin = "org.kde.image";
            d.currentConfigGroup = Array("Wallpaper", "org.kde.image",
            "General");d.writeConfig("Image", "%s")};
        """
        util.disown(
            [
                "qdbus",
                "org.kde.plasmashell",
                "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript",
                string % img,
            ]
        )
    else:
        set_wm_wallpaper(img)


def set_mac_wallpaper(img):
    """Set the wallpaper on macOS."""
    db_file = "Library/Application Support/Dock/desktoppicture.db"
    db_path = os.path.join(HOME, db_file)

    # Put the image path in the database
    sql = f'insert into data values("{img}"); '
    subprocess.run(["sqlite3", db_path, sql], check=False)

    # Get the index of the new entry
    sql = "select max(rowid) from data;"
    new_entry = subprocess.check_output(["sqlite3", db_path, sql])
    new_entry = new_entry.decode("utf8").strip("\n")

    # Get all picture ids (monitor/space pairs)
    get_pics_cmd = ["sqlite3", db_path, "select rowid from pictures;"]
    pictures = subprocess.check_output(get_pics_cmd)
    pictures = pictures.decode("utf8").split("\n")

    # Clear all existing preferences
    sql += "delete from preferences; "

    # Write all pictures to the new image
    for pic in pictures:
        if pic:
            sql += "insert into preferences (key, data_id, picture_id) "
            sql += f"values(1, {new_entry}, {pic}); "

    subprocess.run(["sqlite3", db_path, sql], check=False)

    # Kill the dock to fix issues with cached wallpapers.
    # macOS caches wallpapers and if a wallpaper is set that shares
    # the filename with a cached wallpaper, the cached wallpaper is
    # used instead.
    subprocess.run(["killall", "Dock"], check=False)


def set_win_wallpaper(img):
    """Set the wallpaper on Windows."""
    # There's a different command depending on the architecture
    # of Windows. We check the PROGRAMFILES envar since using
    # platform is unreliable.
    if "x86" in os.environ["PROGRAMFILES"]:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, img, 3)
    else:
        ctypes.windll.user32.SystemParametersInfoA(20, 0, img, 3)


def change(img):
    """Set the wallpaper."""
    if not os.path.isfile(img):
        return

    desktop = get_desktop_env()

    if OS == "Darwin":
        set_mac_wallpaper(img)

    elif OS == "Windows":
        set_win_wallpaper(img)

    else:
        set_desktop_wallpaper(desktop, img)

    logging.info("Set the new wallpaper.")


def get(cache_dir=CACHE_DIR):
    """Get the current wallpaper."""
    current_wall = os.path.join(cache_dir, "wal")

    if os.path.isfile(current_wall):
        return util.read_file(current_wall)[0]

    return "None"
