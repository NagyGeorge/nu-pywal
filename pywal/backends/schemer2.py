"""
Generate a colorscheme using Schemer2.
"""

import logging
import sys

from .. import colors, util


def gen_colors(img):
    """Generate a colorscheme using Schemer2."""
    cmd = ["schemer2", "-format", "img::colors", "-minBright", "75", "-in"]
    try:
        output = util.run_command([*cmd, img], timeout=30, capture_output=True)
        return output.splitlines()
    except util.PywalError as e:
        logging.error(f"Schemer2 failed to generate colors: {e}")
        sys.exit(1)


def adjust(cols, light):
    """Create palette."""
    cols.sort(key=util.rgb_to_yiq)
    raw_colors = [*cols[8:], *cols[8:]]

    return colors.generic_adjust(raw_colors, light)


def get(img, light=False):
    """Get colorscheme."""
    try:
        cols = gen_colors(img)
        # Handle both string and bytes output
        if cols and isinstance(cols[0], bytes):
            cols = [col.decode("UTF-8") for col in cols]
        return adjust(cols, light)
    except util.ExecutableNotFoundError:
        logging.error("Schemer2 wasn't found on your system.")
        logging.error("Try another backend. (wal --backend)")
        sys.exit(1)
