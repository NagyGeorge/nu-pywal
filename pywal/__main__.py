"""
                                      '||
... ...  .... ... ... ... ...  ....    ||
 ||'  ||  '|.  |   ||  ||  |  '' .||   ||
 ||    |   '|.|     ||| |||   .|' ||   ||
 ||...'     '|       |   |    '|..'|' .||.
 ||      .. |
''''      ''
Created by Dylan Araps.
"""

import argparse
import logging
import os
import shutil
import sys

from . import (
    cache,
    colors,
    config,
    export,
    image,
    parallel,
    reload,
    sequences,
    theme,
    util,
    wallpaper,
)
from .settings import CACHE_DIR, CONF_DIR, __version__


def get_args():
    """Get the script arguments."""
    description = "wal - Generate colorschemes on the fly"
    arg = argparse.ArgumentParser(description=description)

    arg.add_argument(
        "-a",
        metavar='"alpha"',
        help="Set terminal background transparency. \
                           *Only works in URxvt*",
    )

    arg.add_argument("-b", metavar="background", help="Custom background color to use.")

    arg.add_argument(
        "--backend",
        metavar="backend",
        help="Which color backend to use. \
                           Use 'wal --backend' to list backends.",
        const="list_backends",
        type=str,
        nargs="?",
    )

    arg.add_argument(
        "--theme",
        "-f",
        metavar="/path/to/file or theme_name",
        help="Which colorscheme file to use. \
                           Use 'wal --theme' to list builtin and user themes.",
        const="list_themes",
        nargs="?",
    )

    arg.add_argument(
        "--iterative",
        action="store_true",
        help="When pywal is given a directory as input and this "
        "flag is used: Go through the images in order "
        "instead of shuffled.",
    )

    arg.add_argument(
        "--recursive",
        action="store_true",
        help="When pywal is given a directory as input and this "
        "flag is used: Search for images recursively in "
        "subdirectories instead of the root only.",
    )

    arg.add_argument("--saturate", metavar="0.0-1.0", help="Set the color saturation.")

    arg.add_argument(
        "--preview", action="store_true", help="Print the current color palette."
    )

    arg.add_argument(
        "--vte",
        action="store_true",
        help="Fix text-artifacts printed in VTE terminals.",
    )

    arg.add_argument("-c", action="store_true", help="Delete all cached colorschemes.")

    arg.add_argument(
        "-i", metavar='"/path/to/img.jpg"', help="Which image or directory to use."
    )

    arg.add_argument("-l", action="store_true", help="Generate a light colorscheme.")

    arg.add_argument("-n", action="store_true", help="Skip setting the wallpaper.")

    arg.add_argument(
        "-o",
        metavar='"script_name"',
        action="append",
        help='External script to run after "wal".',
    )

    arg.add_argument(
        "-p",
        metavar='"theme_name"',
        help="permanently save theme to "
        "$XDG_CONFIG_HOME/wal/colorschemes with "
        "the specified name",
    )

    arg.add_argument(
        "-q", action="store_true", help="Quiet mode, don't print anything."
    )

    arg.add_argument(
        "-r",
        action="store_true",
        help="'wal -r' is deprecated: Use \
                           (cat ~/.cache/wal/sequences &) instead.",
    )

    arg.add_argument("-R", action="store_true", help="Restore previous colorscheme.")

    arg.add_argument(
        "-s", action="store_true", help="Skip changing colors in terminals."
    )

    arg.add_argument("-t", action="store_true", help="Skip changing colors in tty.")

    arg.add_argument("-v", action="store_true", help='Print "wal" version.')

    arg.add_argument(
        "-w", action="store_true", help="Use last used wallpaper for color generation."
    )

    arg.add_argument(
        "-e", action="store_true", help="Skip reloading gtk/xrdb/i3/sway/polybar"
    )

    arg.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate nu-pywal configuration and installation",
    )

    arg.add_argument(
        "--repair-config",
        action="store_true",
        help="Attempt to repair nu-pywal configuration issues",
    )

    arg.add_argument(
        "--migrate-config",
        action="store_true",
        help="Migrate configuration to current version",
    )

    arg.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing for directory operations",
    )

    arg.add_argument(
        "--find-best",
        action="store_true",
        help="Find and use the best image from a directory (requires --parallel)",
    )

    arg.add_argument(
        "--best-count",
        type=int,
        default=5,
        metavar="N",
        help="Number of best images to consider (default: 5)",
    )

    arg.add_argument(
        "--benchmark", action="store_true", help="Benchmark backends on the input image"
    )

    arg.add_argument(
        "--cache-info",
        action="store_true",
        help="Show cache statistics and information",
    )

    arg.add_argument(
        "--cache-cleanup", action="store_true", help="Clean up old cache entries"
    )

    return arg


def parse_args_exit(parser):
    """Process args that exit."""
    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(1)

    if args.v:
        parser.exit(0, f"wal {__version__}\n")

    if args.preview:
        sys.stdout.write("Current colorscheme:")
        colors.palette()
        sys.exit(0)

    if args.i and args.theme:
        parser.error("Conflicting arguments -i and -f.")

    if args.r:
        reload.colors()
        sys.exit(0)

    if args.c:
        scheme_dir = os.path.join(CACHE_DIR, "schemes")
        shutil.rmtree(scheme_dir, ignore_errors=True)
        sys.exit(0)

    if (
        not args.i
        and not args.theme
        and not args.R
        and not args.w
        and not args.backend
        and not args.validate_config
        and not args.repair_config
        and not args.migrate_config
        and not args.benchmark
        and not args.cache_info
        and not args.cache_cleanup
    ):
        parser.error("No input specified.\n--backend, --theme, -i or -R are required.")

    if args.theme == "list_themes":
        theme.list_out()
        sys.exit(0)

    if args.backend == "list_backends":
        sys.stdout.write(
            "\n - ".join(["\033[1;32mBackends\033[0m:", *colors.list_backends()])
        )
        sys.exit(0)

    if args.validate_config:
        sys.exit(config.validate_config_cli())

    if args.repair_config:
        sys.exit(config.repair_config_cli())

    if args.migrate_config:
        sys.exit(config.migrate_config_cli())

    if args.benchmark and args.i:
        if os.path.isfile(args.i):
            sys.stdout.write("Starting backend benchmark...\n")
            # Use fast, reliable backends by default to avoid hanging
            fast_backends = ["wal", "colorthief", "haishoku"]
            results = parallel.benchmark_backends(args.i, backends=fast_backends)

            if not results:
                sys.stdout.write("\nNo backends could be benchmarked.\n")
                sys.stdout.write("This usually means missing backend dependencies.\n")
                sys.stdout.write("Try installing some backends:\n")
                sys.stdout.write("  pip install colorthief\n")
                sys.stdout.write("  pip install haishoku\n")
                sys.stdout.write("  pip install colorz\n")
                sys.exit(1)

            sys.stdout.write("\nBenchmark Results:\n")
            sys.stdout.write("=" * 70 + "\n")

            # Separate available and unavailable backends
            available = {
                k: v
                for k, v in results.items()
                if v.get("status") == "available" and v["success_count"] > 0
            }
            failed = {
                k: v
                for k, v in results.items()
                if v.get("status") == "available" and v["success_count"] == 0
            }
            unavailable = {
                k: v for k, v in results.items() if v.get("status") == "unavailable"
            }

            if available:
                sys.stdout.write("Available backends (sorted by performance):\n")
                for backend, stats in sorted(
                    available.items(), key=lambda x: x[1]["avg_time"]
                ):
                    min_time = stats.get("min_time", 0)
                    max_time = stats.get("max_time", 0)
                    sys.stdout.write(
                        f"{backend:15} | Avg: {stats['avg_time']:.3f}s | "
                        f"Range: {min_time:.3f}-{max_time:.3f}s | Success: {stats['success_rate']:.1%}\n"
                    )

            if failed:
                sys.stdout.write("\nFailed backends:\n")
                for backend in failed:
                    sys.stdout.write(f"{backend:15} | All iterations failed\n")

            if unavailable:
                sys.stdout.write("\nUnavailable backends:\n")
                for backend in unavailable:
                    sys.stdout.write(
                        f"{backend:15} | Missing dependencies or import error\n"
                    )

            sys.exit(0)
        else:
            parser.error(
                "Benchmark requires a single image file (-i /path/to/image.jpg)"
            )

    if args.find_best and not args.parallel:
        parser.error("--find-best requires --parallel to be enabled")

    if args.cache_info:
        sys.exit(cache.cache_info_cli())

    if args.cache_cleanup:
        sys.exit(cache.cache_cleanup_cli())


def setup_quiet_mode(args):
    """Configure quiet mode if requested."""
    if args.q:
        logging.getLogger().disabled = True
        sys.stdout = sys.stderr = open(os.devnull, "w")


def setup_alpha(args):
    """Configure alpha transparency if specified."""
    if args.a:
        util.Color.alpha_num = args.a


def get_colors_from_args(args, parser):
    """Extract colors from various input sources."""
    colors_plain = None

    if args.i:
        if os.path.isdir(args.i) and args.parallel:
            # Use parallel processing for directories
            if args.find_best:
                sys.stdout.write(
                    f"Finding best {args.best_count} images from directory...\n"
                )
                best_images = parallel.process_directory_parallel(
                    args.i,
                    light=args.l,
                    recursive=args.recursive,
                    find_best=True,
                    best_count=args.best_count,
                )
                if best_images:
                    # Use the best image found
                    image_file, colors_plain = best_images[0]
                    sys.stdout.write(
                        f"Selected best image: {os.path.basename(image_file)}\n"
                    )
                else:
                    logging.error("No suitable images found in directory.")
                    sys.exit(1)
            else:
                # Process all images and pick one
                sys.stdout.write("Processing directory with parallel backend...\n")
                all_results = parallel.process_directory_parallel(
                    args.i, light=args.l, recursive=args.recursive, find_best=False
                )
                if all_results:
                    # Pick the first successful result
                    image_file = list(all_results.keys())[0]
                    colors_plain = list(all_results.values())[0]
                    sys.stdout.write(f"Using: {os.path.basename(image_file)}\n")
                else:
                    logging.error("Failed to process any images in directory.")
                    sys.exit(1)
        else:
            # Standard single image or directory processing
            image_file = image.get(
                args.i, iterative=args.iterative, recursive=args.recursive
            )
            colors_plain = colors.get(
                image_file, args.l, args.backend, sat=args.saturate
            )

    if args.theme:
        colors_plain = theme.file(args.theme, args.l)

    if args.R:
        colors_plain = theme.file(os.path.join(CACHE_DIR, "colors.json"))

    if args.w:
        cached_wallpaper = util.read_file(os.path.join(CACHE_DIR, "wal"))
        colors_plain = colors.get(
            cached_wallpaper[0], args.l, args.backend, sat=args.saturate
        )

    # Validate that we have valid input
    if colors_plain is None:
        if args.backend and args.backend != "list_backends":
            parser.error(
                f"Backend '{args.backend}' specified but no input provided.\n"
                "Use -i /path/to/image, --theme theme_name, or -R to restore colors."
            )
        else:
            parser.error("No input specified.\n-i, --theme, -R, or -w are required.")

    return colors_plain


def apply_color_modifications(colors_plain, args):
    """Apply color modifications like custom background."""
    if args.b:
        args.b = f"#{args.b.strip('#')}"
        colors_plain["special"]["background"] = args.b
        colors_plain["colors"]["color0"] = args.b


def handle_wallpaper_and_theme_saving(colors_plain, args):
    """Handle wallpaper setting and theme saving."""
    if not args.n:
        wallpaper.change(colors_plain["wallpaper"])

    if args.p:
        theme.save(colors_plain, args.p, args.l)


def apply_colors_and_export(colors_plain, args):
    """Apply colors to terminals and export templates."""
    sequences.send(colors_plain, to_send=not args.s, vte_fix=args.vte)

    if sys.stdout.isatty():
        colors.palette()

    export.every(colors_plain)


def handle_reloading_and_scripts(args):
    """Handle environment reloading and external scripts."""
    if not args.e:
        reload.env(tty_reload=not args.t)

    if args.o:
        for cmd in args.o:
            util.disown([cmd])

    if not args.e:
        reload.gtk()


def parse_args(parser):
    """Process args."""
    args = parser.parse_args()

    setup_quiet_mode(args)
    setup_alpha(args)

    colors_plain = get_colors_from_args(args, parser)
    apply_color_modifications(colors_plain, args)
    handle_wallpaper_and_theme_saving(colors_plain, args)
    apply_colors_and_export(colors_plain, args)
    handle_reloading_and_scripts(args)


def main():
    """Main script function."""
    util.create_dir(os.path.join(CONF_DIR, "templates"))
    util.create_dir(os.path.join(CONF_DIR, "colorschemes/light/"))
    util.create_dir(os.path.join(CONF_DIR, "colorschemes/dark/"))

    util.setup_logging()
    parser = get_args()

    parse_args_exit(parser)
    parse_args(parser)


if __name__ == "__main__":
    main()
