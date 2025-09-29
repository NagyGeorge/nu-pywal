# nu-pywal Installation Guide

nu-pywal is a modernized fork of pywal, designed for contemporary Linux systems with enhanced Wayland support, modern terminal emulators, and updated security features.

## Requirements

### System Requirements
- **Python**: 3.8+ (updated from original pywal's 3.5+ requirement)
- **ImageMagick**: For color extraction and image processing
- **Operating Systems**: Linux, BSD, macOS (limited Windows support)

### Dependencies
- `pidof` or `pgrep` (for program detection)
- Desktop environment support: XFCE, GNOME, Cinnamon, MATE, KDE
- **Wayland compositor support**: Hyprland, Sway, River, Wayfire
- Wallpaper setting tools: `feh`, `nitrogen`, `bgs`, `hsetroot`, `habak`, `display`

## Installation Methods

### 1. From GitHub Releases (Recommended)

Download the latest release from the [releases page](https://github.com/NagyGeorge/nu-pywal/releases):

```bash
# Download and install the wheel file
pip install --user nu-pywal-0.9.0-py3-none-any.whl
```

### 2. From Source (Development)

```bash
# Clone the repository
git clone https://github.com/NagyGeorge/nu-pywal.git
cd nu-pywal

# Install in development mode
pip install --user -e .

# Or build and install
python -m build
pip install --user dist/nu_pywal-0.9.0-py3-none-any.whl
```

### 3. Using UV (Modern Python Package Manager)

```bash
# Clone and install with UV
git clone https://github.com/NagyGeorge/nu-pywal.git
cd nu-pywal
uv sync
```

### 4. PATH Configuration

If installing with `--user`, add to your shell's configuration file (`.bashrc`, `.zshrc`, etc.):

```bash
export PATH="${PATH}:${HOME}/.local/bin/"
```

## System Dependencies

### Arch Linux
```bash
sudo pacman -S python-pip imagemagick
# Optional: feh for wallpaper setting
sudo pacman -S feh
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3-pip imagemagick
# Optional: feh for wallpaper setting
sudo apt install feh
```

### Fedora
```bash
sudo dnf install python3-pip ImageMagick
# Optional: feh for wallpaper setting
sudo dnf install feh
```

### macOS
```bash
brew install imagemagick
pip3 install --user nu-pywal
```

## Modern Desktop Environment Support

nu-pywal includes enhanced support for modern environments:

### Wayland Compositors
- **Hyprland**: Full color scheme integration
- **Sway**: Wallpaper and color setting
- **River**: Basic wallpaper support
- **Wayfire**: Color scheme updates

### X11 Desktop Environments
- **GNOME**: Complete theming support
- **KDE/Plasma**: Wallpaper and color integration
- **XFCE**: Full theme application
- **i3/bspwm**: Window manager color updates

## Terminal Emulator Compatibility

### Fully Supported (Modern)
- **Alacritty**: Live color updates with template
- **WezTerm**: Complete color scheme support
- **Foot**: Wayland-native with live updates
- **Ghostty**: Modern terminal support

### Traditional Support
- **xterm**, **urxvt**: Classic terminal support
- **GNOME Terminal**, **Konsole**: Basic color updates
- **iTerm2** (macOS): Full color integration

### Testing Terminal Compatibility

Test if your terminal supports color changes:

```bash
# Test escape sequence support
printf "%b" "\033]11;#ff0000\007"

# This should temporarily change your terminal background to red
# Press Ctrl+C to stop, then run:
printf "%b" "\033]11;#000000\007"  # Reset to black
```

## Application Integration

nu-pywal supports over 30 applications and tools through template files. While terminal emulators update automatically, some applications require manual configuration.

### Waybar (Wayland Status Bar)

Waybar requires manual CSS import setup but provides full color scheme integration:

#### Setup Steps

1. **Add import to waybar CSS**: Edit your `~/.config/waybar/style.css` and add this line at the very top:

```css
@import url("file:///home/USERNAME/.cache/wal/colors-waybar.css");
```

Replace `USERNAME` with your actual username, or use the full path: `file://$HOME/.cache/wal/colors-waybar.css`

2. **Use color variables in your CSS**: Replace hardcoded colors with pywal variables:

```css
/* Instead of hardcoded colors: */
#clock { background: #ABE9B3; }

/* Use pywal variables: */
#clock { background: @color2; }
```

#### Available Color Variables

- `@foreground` - Primary text color
- `@background` - Primary background color
- `@cursor` - Cursor color
- `@color0` through `@color15` - The 16 terminal colors
- Use `alpha(@background, 0.5)` for transparency

#### Applying Changes

After running `wal -i image.jpg`, restart waybar to apply new colors:

```bash
pkill waybar && waybar &
```

### Auto-Reload Applications

These applications update colors automatically when running `wal -i`:

- **Terminal Emulators**: Alacritty, WezTerm, Foot, Ghostty, Kitty
- **Window Managers**: i3, bspwm, Sway, Hyprland
- **Status Bars**: Polybar
- **System**: GTK themes, X resources

### Manual Integration Applications

These require restart or manual configuration:

- **Waybar**: CSS import (documented above)
- **Rofi**: Uses generated theme files
- **Firefox**: Browser theme extensions
- **VSCode**: Color theme extensions

## Optional Backend Support

Install additional color extraction backends:

```bash
# Fast color extraction
pip install --user fast-colorthief

# Alternative backends
pip install --user colorz
pip install --user haishoku
pip install --user colorthief
```

## Verification

Test your installation:

```bash
# Check version
wal --version

# Generate colors from an image
wal -i /path/to/your/wallpaper.jpg

# List available themes
wal --theme list

# Test backend functionality
wal --backend list
```

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure `~/.local/bin` is in your PATH
2. **ImageMagick errors**: Install ImageMagick system package
3. **Permission errors**: Use `--user` flag with pip
4. **Wayland issues**: Ensure compositor-specific tools are installed

### Getting Help

1. Check the [Issues page](https://github.com/NagyGeorge/nu-pywal/issues)
2. Review the [original pywal documentation](https://github.com/dylanaraps/pywal/wiki)
3. Test with minimal configuration first

## What's New in nu-pywal

- **Python 3.8+ requirement** (improved security and performance)
- **Wayland compositor support** for modern Linux setups
- **Enhanced terminal emulator support** (Alacritty, WezTerm, Foot)
- **Modern development workflow** with comprehensive testing
- **Security improvements** with path validation and safer subprocess calls
- **Updated desktop environment detection** for contemporary Linux distributions

## Migration from Original pywal

nu-pywal maintains backward compatibility with original pywal configurations and color schemes. Simply replace `pywal` with `nu-pywal` in your installation and existing configurations should work unchanged.
