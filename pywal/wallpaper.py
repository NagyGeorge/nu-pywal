"""Set the wallpaper."""

import ctypes
import logging
import os
import re
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
    try:
        xfconf_data = util.run_command(
            ["xfconf-query", "--channel", "xfce4-desktop", "--list"],
            timeout=10,
            capture_output=True,
        )
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
    except util.PywalError as e:
        logging.error(f"Failed to set XFCE wallpaper: {e}")


def set_wm_wallpaper(img):
    """Set the wallpaper for non desktop environments."""
    wallpaper_setters = [
        (["feh", "--bg-fill", img], "feh"),
        (["xwallpaper", "--zoom", img], "xwallpaper"),
        (["hsetroot", "-fill", img], "hsetroot"),
        (["nitrogen", "--set-zoom-fill", img], "nitrogen"),
        (["bgs", "-z", img], "bgs"),
        (["habak", "-mS", img], "habak"),
        (["display", "-backdrop", "-window", "root", img], "display"),
    ]

    for cmd, setter_name in wallpaper_setters:
        try:
            util.disown(cmd)
            logging.info(f"Wallpaper set using {setter_name}")
            return
        except util.ExecutableNotFoundError:
            logging.debug(f"Wallpaper setter '{setter_name}' not found")
            continue

    logging.error(
        "No wallpaper setter found. Install one of: feh, xwallpaper, hsetroot, nitrogen, bgs, habak, imagemagick"
    )
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
        wayland_setters = [
            (["swaybg", "-i", img, "-m", "fill"], "swaybg"),
            (["oguri"], "oguri"),
            (["wpaperd"], "wpaperd"),
        ]

        for cmd, setter_name in wayland_setters:
            try:
                util.disown(cmd)
                logging.info(f"Wayland wallpaper set using {setter_name}")
                return
            except util.ExecutableNotFoundError:
                logging.debug(f"Wayland wallpaper setter '{setter_name}' not found")
                continue

        logging.warning(
            "No Wayland wallpaper setter found. Install swaybg, oguri, or wpaperd"
        )

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

    try:
        # Put the image path in the database
        sql = f'insert into data values("{img}"); '
        util.run_command(["sqlite3", db_path, sql], timeout=10)

        # Get the index of the new entry
        sql = "select max(rowid) from data;"
        new_entry = util.run_command(
            ["sqlite3", db_path, sql], timeout=10, capture_output=True
        )
        new_entry = new_entry.strip()

        # Get all picture ids (monitor/space pairs)
        get_pics_cmd = ["sqlite3", db_path, "select rowid from pictures;"]
        pictures = util.run_command(get_pics_cmd, timeout=10, capture_output=True)
        pictures = pictures.split("\n")

        # Clear all existing preferences
        sql += "delete from preferences; "

        # Write all pictures to the new image
        for pic in pictures:
            if pic:
                sql += "insert into preferences (key, data_id, picture_id) "
                sql += f"values(1, {new_entry}, {pic}); "

        util.run_command(["sqlite3", db_path, sql], timeout=10)

        # Kill the dock to fix issues with cached wallpapers.
        # macOS caches wallpapers and if a wallpaper is set that shares
        # the filename with a cached wallpaper, the cached wallpaper is
        # used instead.
        util.run_command(["killall", "Dock"], timeout=10)
    except util.PywalError as e:
        logging.error(f"Failed to set macOS wallpaper: {e}")


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
