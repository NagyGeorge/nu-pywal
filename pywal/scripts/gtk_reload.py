#!/usr/bin/env python3
"""
Modern Python 3 script to reload GTK themes.

This script attempts to reload GTK themes using various methods
compatible with both GTK2 and GTK3/4.
"""

import logging
import subprocess


def reload_gtk_via_gsettings():
    """Reload GTK themes via gsettings (GTK3/4)."""
    try:
        # Get current theme name
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_theme = result.stdout.strip().strip("'\"")

        # Set theme to something else temporarily, then back
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita"],
            check=True,
        )
        subprocess.run(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.interface",
                "gtk-theme",
                current_theme,
            ],
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def reload_gtk_via_xsettingsd():
    """Reload GTK themes via xsettingsd restart."""
    try:
        subprocess.run(["pkill", "-HUP", "xsettingsd"], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def reload_gtk_via_xrdb():
    """Reload GTK themes via xrdb (fallback for older systems)."""
    try:
        # This method works by triggering a property change that GTK applications watch
        subprocess.run(
            ["xrdb", "-merge", "/dev/null"], check=True, stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def gtk_reload():
    """Reload GTK themes using available methods."""
    methods = [
        ("gsettings", reload_gtk_via_gsettings),
        ("xsettingsd", reload_gtk_via_xsettingsd),
        ("xrdb", reload_gtk_via_xrdb),
    ]

    for method_name, method_func in methods:
        try:
            if method_func():
                logging.info(f"GTK reload successful via {method_name}")
                return True
        except Exception as e:
            logging.debug(f"GTK reload via {method_name} failed: {e}")
            continue

    logging.warning("GTK reload failed: no working method found")
    return False


if __name__ == "__main__":
    gtk_reload()
