<h3 align="center"><img src="https://i.imgur.com/5WgMACe.gif" width="200px"></h3>
<p align="center"><strong>nu-pywal</strong> - Generate and change color-schemes on the fly.</p>
<p align="center"><em>A modernized fork of pywal for contemporary Linux systems</em></p>

<p align="center">
<a href="https://github.com/NagyGeorge/nu-pywal/actions"><img src="https://github.com/NagyGeorge/nu-pywal/workflows/CI/badge.svg"></a>
<a href="./LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
<a href="https://github.com/NagyGeorge/nu-pywal/releases"><img src="https://img.shields.io/github/v/release/NagyGeorge/nu-pywal.svg"></a>
<a href="https://github.com/NagyGeorge/nu-pywal"><img src="https://img.shields.io/badge/python-3.8%2B-blue.svg"></a>
</p></p>

<img src="https://i.imgur.com/HhK3LDv.jpg" alt="img" align="right" width="400px">

**nu-pywal** is a modernized fork of pywal that generates color palettes from dominant colors in images and applies them system-wide on-the-fly. This fork focuses on contemporary Linux systems with enhanced Wayland support, modern terminal emulators, and updated security features.

## What's New in nu-pywal

- 🐧 **Wayland Support**: Full integration with modern compositors (Hyprland, Sway, River, Wayfire)
- 🖥️ **Modern Terminals**: Native support for Alacritty, WezTerm, Foot, Ghostty
- 🔒 **Enhanced Security**: Path validation, secure subprocess calls, updated dependencies
- 🐍 **Python 3.8+**: Modern Python features with improved performance
- ⚡ **Better CI/CD**: Comprehensive testing across platforms and Python versions
- 🎨 **Backward Compatible**: Works with existing pywal configurations and themes

There are currently 5+ supported color generation backends, each providing different palettes from images. nu-pywal maintains over 250 built-in themes while adding modern desktop environment support.

The goal remains unchanged: be as unobtrusive as possible. nu-pywal doesn't modify existing configuration files but provides enhanced tools for modern system integration.

Terminal emulators and TTYs update colors in real-time with no delay, now including modern Wayland-native terminals.

## Documentation

- 📦 **[Installation Guide](./INSTALLATION.md)** - Complete setup instructions for nu-pywal
- 🚀 **[Getting Started](https://github.com/dylanaraps/pywal/wiki/Getting-Started)** - Basic usage (compatible with nu-pywal)
- 🎨 **[Customization](https://github.com/dylanaraps/pywal/wiki/Customization)** - Advanced configuration
- 📖 **[Original Wiki](https://github.com/dylanaraps/pywal/wiki)** - Comprehensive documentation
- 🖼️ **[Screenshots](https://www.reddit.com/r/unixporn/search?q=wal&restrict_sr=on&sort=relevance&t=all)** - Community showcases
- 📋 **[Changelog](./CHANGELOG.md)** - What's new in nu-pywal

## Quick Start

```bash
# Install nu-pywal
pip install --user nu-pywal

# Generate colors from wallpaper
wal -i ~/Pictures/wallpaper.jpg

# Apply to supported programs
wal -R
```

## Original Project

This is a fork of the original [pywal](https://github.com/dylanaraps/pywal) by Dylan Araps. nu-pywal maintains compatibility while focusing on modern Linux system support.
