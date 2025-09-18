#!/usr/bin/env python3
"""
Modern Python 3 script to reload GTK themes.

This script attempts to reload GTK themes using various methods
compatible with both GTK2 and GTK3/4.
"""

import logging
import os
import sys

# Add parent directory to path to import util
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from util import ExecutableNotFoundError, PywalError, run_command


def reload_gtk_via_gsettings():
    """Reload GTK themes via gsettings (GTK3/4)."""
    try:
        # Get current theme name
        current_theme = (
            run_command(
                ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                timeout=10,
                capture_output=True,
            )
            .strip()
            .strip("'\"")
        )

        # Set theme to something else temporarily, then back
        run_command(
            ["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", "Adwaita"],
            timeout=10,
        )
        run_command(
            [
                "gsettings",
                "set",
                "org.gnome.desktop.interface",
                "gtk-theme",
                current_theme,
            ],
            timeout=10,
        )
        return True
    except (PywalError, ExecutableNotFoundError):
        return False


def reload_gtk_via_xsettingsd():
    """Reload GTK themes via xsettingsd restart."""
    try:
        run_command(["pkill", "-HUP", "xsettingsd"], timeout=5)
        return True
    except (PywalError, ExecutableNotFoundError):
        return False


def reload_gtk_via_xrdb():
    """Reload GTK themes via xrdb (fallback for older systems)."""
    try:
        # This method works by triggering a property change that GTK applications watch
        run_command(["xrdb", "-merge", "/dev/null"], timeout=10)
        return True
    except (PywalError, ExecutableNotFoundError):
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
