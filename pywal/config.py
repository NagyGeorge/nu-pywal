"""
Configuration validation and management for nu-pywal.

This module provides comprehensive configuration validation, schema checking,
and configuration migration capabilities.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from . import util
from .settings import CACHE_DIR, CONF_DIR, __cache_version__, __version__


@dataclass
class ConfigSchema:
    """Schema definition for configuration validation."""

    required_fields: Set[str] = field(default_factory=set)
    optional_fields: Set[str] = field(default_factory=set)
    field_types: Dict[str, type] = field(default_factory=dict)
    field_patterns: Dict[str, str] = field(default_factory=dict)
    field_ranges: Dict[str, tuple] = field(default_factory=dict)


class ConfigValidator:
    """Validates nu-pywal configuration files and settings."""

    # Color scheme schema
    COLOR_SCHEME_SCHEMA = ConfigSchema(
        required_fields={"special", "colors", "wallpaper", "alpha"},
        optional_fields={"version", "name", "author", "description"},
        field_types={
            "wallpaper": str,
            "alpha": str,
            "special": dict,
            "colors": dict,
            "version": str,
            "name": str,
            "author": str,
            "description": str,
        },
        field_patterns={
            "alpha": r"^\d{1,3}$",  # 0-999
            "wallpaper": r"^.*\.(jpg|jpeg|png|gif|bmp|webp)$|^None$",
        },
        field_ranges={"alpha": (0, 100)},
    )

    # Template schema
    TEMPLATE_SCHEMA = ConfigSchema(
        required_fields=set(),  # Templates are flexible
        optional_fields={"name", "description", "author", "version"},
        field_types={"name": str, "description": str, "author": str, "version": str},
    )

    def __init__(self):
        """Initialize the configuration validator."""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_color_scheme(
        self, scheme_data: Dict[str, Any], file_path: Optional[str] = None
    ) -> bool:
        """
        Validate a color scheme against the schema.

        Args:
            scheme_data: The color scheme data to validate
            file_path: Optional file path for error reporting

        Returns:
            True if valid, False otherwise
        """
        self.errors.clear()
        self.warnings.clear()

        return self._validate_against_schema(
            scheme_data, self.COLOR_SCHEME_SCHEMA, file_path
        )

    def validate_hex_color(self, color: str) -> bool:
        """Validate a hex color string."""
        if not isinstance(color, str):
            return False

        # Remove # if present
        color = color.lstrip("#")

        # Check if it's a valid hex color (3 or 6 characters)
        if len(color) not in [3, 6]:
            return False

        try:
            int(color, 16)
            return True
        except ValueError:
            return False

    def validate_color_palette(self, colors: Dict[str, Any]) -> bool:
        """Validate a complete color palette."""
        required_special = {"background", "foreground", "cursor"}
        required_colors = {f"color{i}" for i in range(16)}

        # Check special colors
        if "special" not in colors:
            self.errors.append("Missing 'special' colors section")
            return False

        special = colors["special"]
        missing_special = required_special - set(special.keys())
        if missing_special:
            self.errors.append(f"Missing special colors: {missing_special}")

        # Validate special color values
        for name, color in special.items():
            if not self.validate_hex_color(color):
                self.errors.append(f"Invalid hex color for special.{name}: {color}")

        # Check color palette
        if "colors" not in colors:
            self.errors.append("Missing 'colors' section")
            return False

        color_palette = colors["colors"]
        missing_colors = required_colors - set(color_palette.keys())
        if missing_colors:
            self.errors.append(f"Missing colors: {missing_colors}")

        # Validate color values
        for name, color in color_palette.items():
            if not self.validate_hex_color(color):
                self.errors.append(f"Invalid hex color for {name}: {color}")

        return len(self.errors) == 0

    def validate_directory_structure(self) -> bool:
        """Validate the nu-pywal directory structure."""
        self.errors.clear()
        self.warnings.clear()

        required_dirs = [
            CONF_DIR,
            os.path.join(CONF_DIR, "templates"),
            os.path.join(CONF_DIR, "colorschemes"),
            os.path.join(CONF_DIR, "colorschemes", "dark"),
            os.path.join(CONF_DIR, "colorschemes", "light"),
            CACHE_DIR,
            os.path.join(CACHE_DIR, "schemes"),
        ]

        for directory in required_dirs:
            if not os.path.exists(directory):
                self.warnings.append(f"Directory does not exist: {directory}")
            elif not os.path.isdir(directory):
                self.errors.append(f"Path exists but is not a directory: {directory}")
            elif not os.access(directory, os.R_OK | os.W_OK):
                self.errors.append(f"Directory not readable/writable: {directory}")

        return len(self.errors) == 0

    def validate_template_file(self, template_path: str) -> bool:
        """Validate a template file."""
        self.errors.clear()
        self.warnings.clear()

        if not os.path.exists(template_path):
            self.errors.append(f"Template file does not exist: {template_path}")
            return False

        try:
            with open(template_path, encoding="utf-8") as f:
                content = f.read()

            # Check for basic template syntax
            placeholders = re.findall(r"\{([^}]+)\}", content)
            valid_placeholders = {
                "wallpaper",
                "alpha",
                "background",
                "foreground",
                "cursor",
            }
            valid_placeholders.update(f"color{i}" for i in range(16))

            invalid_placeholders = []
            for placeholder in placeholders:
                # Remove function calls (e.g., color0.strip, background.rgb)
                base_placeholder = placeholder.split(".")[0]
                if base_placeholder not in valid_placeholders:
                    invalid_placeholders.append(placeholder)

            if invalid_placeholders:
                self.warnings.append(
                    f"Unknown placeholders in {template_path}: {invalid_placeholders}"
                )

        except (OSError, UnicodeDecodeError) as e:
            self.errors.append(f"Cannot read template file {template_path}: {e}")
            return False

        return len(self.errors) == 0

    def _validate_against_schema(
        self,
        data: Dict[str, Any],
        schema: ConfigSchema,
        file_path: Optional[str] = None,
    ) -> bool:
        """Validate data against a schema."""
        context = f" in {file_path}" if file_path else ""

        # Check required fields
        missing_required = schema.required_fields - set(data.keys())
        if missing_required:
            self.errors.append(f"Missing required fields{context}: {missing_required}")

        # Check field types
        for field_name, expected_type in schema.field_types.items():
            if field_name in data and not isinstance(data[field_name], expected_type):
                self.errors.append(
                    f"Field '{field_name}'{context} must be {expected_type.__name__}, "
                    f"got {type(data[field_name]).__name__}"
                )

        # Check field patterns
        for field_name, pattern in schema.field_patterns.items():
            if field_name in data and isinstance(data[field_name], str):
                if not re.match(pattern, data[field_name], re.IGNORECASE):
                    self.errors.append(
                        f"Field '{field_name}'{context} does not match required pattern"
                    )

        # Check field ranges
        for field_name, (min_val, max_val) in schema.field_ranges.items():
            if field_name in data:
                try:
                    value = float(data[field_name])
                    if not min_val <= value <= max_val:
                        self.errors.append(
                            f"Field '{field_name}'{context} must be between {min_val} and {max_val}"
                        )
                except (ValueError, TypeError):
                    self.errors.append(f"Field '{field_name}'{context} must be numeric")

        return len(self.errors) == 0

    def get_errors(self) -> List[str]:
        """Get validation errors."""
        return self.errors.copy()

    def get_warnings(self) -> List[str]:
        """Get validation warnings."""
        return self.warnings.copy()


class ConfigManager:
    """Manages nu-pywal configuration files and settings."""

    def __init__(self):
        """Initialize the configuration manager."""
        self.validator = ConfigValidator()

    def validate_installation(self) -> bool:
        """
        Validate the entire nu-pywal installation.

        Returns:
            True if installation is valid, False otherwise
        """
        logging.info("Validating nu-pywal installation...")

        # Validate directory structure
        if not self.validator.validate_directory_structure():
            logging.error("Directory structure validation failed:")
            for error in self.validator.get_errors():
                logging.error(f"  - {error}")
            return False

        # Check for warnings
        for warning in self.validator.get_warnings():
            logging.warning(f"  - {warning}")

        # Validate existing color schemes
        self._validate_color_schemes()

        # Validate templates
        self._validate_templates()

        logging.info("Installation validation complete")
        return True

    def validate_color_scheme_file(self, file_path: str) -> bool:
        """Validate a specific color scheme file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                scheme_data = json.load(f)

            is_valid = self.validator.validate_color_scheme(scheme_data, file_path)

            if not is_valid:
                logging.error(f"Color scheme validation failed for {file_path}:")
                for error in self.validator.get_errors():
                    logging.error(f"  - {error}")

            # Log warnings
            for warning in self.validator.get_warnings():
                logging.warning(f"  - {warning}")

            return is_valid

        except (OSError, json.JSONDecodeError) as e:
            logging.error(f"Cannot read color scheme file {file_path}: {e}")
            return False

    def repair_installation(self) -> bool:
        """
        Attempt to repair common installation issues.

        Returns:
            True if repair was successful, False otherwise
        """
        logging.info("Attempting to repair nu-pywal installation...")

        # Create missing directories
        required_dirs = [
            CONF_DIR,
            os.path.join(CONF_DIR, "templates"),
            os.path.join(CONF_DIR, "colorschemes"),
            os.path.join(CONF_DIR, "colorschemes", "dark"),
            os.path.join(CONF_DIR, "colorschemes", "light"),
            CACHE_DIR,
            os.path.join(CACHE_DIR, "schemes"),
        ]

        for directory in required_dirs:
            try:
                util.create_dir(directory)
                logging.info(f"Created directory: {directory}")
            except Exception as e:
                logging.error(f"Failed to create directory {directory}: {e}")
                return False

        logging.info("Installation repair complete")
        return True

    def _validate_color_schemes(self):
        """Validate all color scheme files."""
        scheme_dirs = [
            os.path.join(CONF_DIR, "colorschemes", "dark"),
            os.path.join(CONF_DIR, "colorschemes", "light"),
        ]

        for scheme_dir in scheme_dirs:
            if not os.path.exists(scheme_dir):
                continue

            for file_entry in os.scandir(scheme_dir):
                if file_entry.name.endswith(".json"):
                    self.validate_color_scheme_file(file_entry.path)

    def _validate_templates(self):
        """Validate all template files."""
        template_dir = os.path.join(CONF_DIR, "templates")

        if not os.path.exists(template_dir):
            return

        for file_entry in os.scandir(template_dir):
            if file_entry.is_file():
                self.validator.validate_template_file(file_entry.path)

                # Log any warnings
                for warning in self.validator.get_warnings():
                    logging.warning(f"Template {file_entry.name}: {warning}")


def validate_config_cli() -> int:
    """
    CLI command to validate configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config_manager = ConfigManager()

    # Set up logging for CLI output
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    is_valid = config_manager.validate_installation()

    if not is_valid:
        return 1
    else:
        return 0


def repair_config_cli() -> int:
    """
    CLI command to repair configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config_manager = ConfigManager()

    # Set up logging for CLI output
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    success = config_manager.repair_installation()

    if success:
        # Validate again after repair
        if config_manager.validate_installation():
            return 0
        else:
            return 1
    else:
        return 1


class ConfigMigration:
    """Handles configuration migration between nu-pywal versions."""

    # Version migration map: old_version -> migration_function
    MIGRATIONS = {}

    def __init__(self):
        """Initialize the configuration migration handler."""
        self.version_file = os.path.join(CONF_DIR, "version")

    def get_current_config_version(self) -> Optional[str]:
        """Get the current configuration version."""
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, encoding="utf-8") as f:
                    return f.read().strip()
        except OSError:
            pass
        return None

    def set_config_version(self, version: str) -> bool:
        """Set the configuration version."""
        try:
            util.create_dir(os.path.dirname(self.version_file))
            with open(self.version_file, "w", encoding="utf-8") as f:
                f.write(version)
            return True
        except OSError as e:
            logging.error(f"Failed to set config version: {e}")
            return False

    def needs_migration(self) -> bool:
        """Check if configuration migration is needed."""
        current_version = self.get_current_config_version()
        if current_version is None:
            # First time setup or very old version
            return True
        return current_version != __version__

    def migrate_cache_structure(self) -> bool:
        """Migrate cache structure to new format."""
        try:
            # Old cache structure used different naming
            old_cache_dir = os.path.join(CACHE_DIR, "colorschemes")
            new_cache_dir = os.path.join(CACHE_DIR, "schemes")

            if os.path.exists(old_cache_dir) and not os.path.exists(new_cache_dir):
                logging.info("Migrating cache structure from old format...")

                # Create new directory
                util.create_dir(new_cache_dir)

                # Move cache files to new location with updated naming
                for file_entry in os.scandir(old_cache_dir):
                    if file_entry.name.endswith(".json"):
                        old_path = file_entry.path
                        # Update filename to include cache version
                        new_name = f"{file_entry.name.replace('.json', '')}_{__cache_version__}.json"
                        new_path = os.path.join(new_cache_dir, new_name)

                        try:
                            os.rename(old_path, new_path)
                            logging.info(
                                f"Migrated cache file: {file_entry.name} -> {new_name}"
                            )
                        except OSError as e:
                            logging.warning(f"Failed to migrate {file_entry.name}: {e}")

                # Remove old cache directory if empty
                try:
                    os.rmdir(old_cache_dir)
                    logging.info("Removed old cache directory")
                except OSError:
                    logging.info("Old cache directory not empty, keeping it")

            return True
        except Exception as e:
            logging.error(f"Cache migration failed: {e}")
            return False

    def migrate_config_structure(self) -> bool:
        """Migrate configuration structure to new format."""
        try:
            # Ensure all required directories exist
            required_dirs = [
                os.path.join(CONF_DIR, "templates"),
                os.path.join(CONF_DIR, "colorschemes", "dark"),
                os.path.join(CONF_DIR, "colorschemes", "light"),
            ]

            for directory in required_dirs:
                util.create_dir(directory)

            # Migrate old user themes to new structure
            old_themes_dir = os.path.join(CONF_DIR, "themes")
            if os.path.exists(old_themes_dir):
                logging.info("Migrating user themes to new structure...")

                for file_entry in os.scandir(old_themes_dir):
                    if file_entry.name.endswith(".json"):
                        # Try to determine if it's a light or dark theme
                        try:
                            with open(file_entry.path, encoding="utf-8") as f:
                                theme_data = json.load(f)

                            # Simple heuristic: check background brightness
                            bg_color = theme_data.get("special", {}).get(
                                "background", "#000000"
                            )
                            # Convert hex to RGB and calculate brightness
                            hex_color = bg_color.lstrip("#")
                            if len(hex_color) == 6:
                                r, g, b = tuple(
                                    int(hex_color[i : i + 2], 16) for i in (0, 2, 4)
                                )
                                brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255

                                target_dir = "light" if brightness > 0.5 else "dark"
                                new_path = os.path.join(
                                    CONF_DIR,
                                    "colorschemes",
                                    target_dir,
                                    file_entry.name,
                                )

                                os.rename(file_entry.path, new_path)
                                logging.info(
                                    f"Migrated theme {file_entry.name} to {target_dir}"
                                )
                        except (
                            json.JSONDecodeError,
                            KeyError,
                            ValueError,
                            OSError,
                        ) as e:
                            logging.warning(
                                f"Failed to migrate theme {file_entry.name}: {e}"
                            )

                # Remove old themes directory if empty
                try:
                    os.rmdir(old_themes_dir)
                    logging.info("Removed old themes directory")
                except OSError:
                    logging.info("Old themes directory not empty, keeping it")

            return True
        except Exception as e:
            logging.error(f"Config migration failed: {e}")
            return False

    def migrate_template_variables(self) -> bool:
        """Migrate template files to use new variable names."""
        try:
            template_dir = os.path.join(CONF_DIR, "templates")
            if not os.path.exists(template_dir):
                return True

            # Variable name mappings: old_name -> new_name
            variable_mappings = {
                "{color.background}": "{background}",
                "{color.foreground}": "{foreground}",
                "{color.cursor}": "{cursor}",
            }

            for file_entry in os.scandir(template_dir):
                if file_entry.is_file():
                    try:
                        with open(file_entry.path, encoding="utf-8") as f:
                            content = f.read()

                        original_content = content
                        for old_var, new_var in variable_mappings.items():
                            content = content.replace(old_var, new_var)

                        # Only write if content changed
                        if content != original_content:
                            with open(file_entry.path, "w", encoding="utf-8") as f:
                                f.write(content)
                            logging.info(
                                f"Updated template variables in {file_entry.name}"
                            )

                    except (OSError, UnicodeDecodeError) as e:
                        logging.warning(
                            f"Failed to update template {file_entry.name}: {e}"
                        )

            return True
        except Exception as e:
            logging.error(f"Template migration failed: {e}")
            return False

    def run_migration(self) -> bool:
        """Run all necessary migrations."""
        if not self.needs_migration():
            logging.info("No migration needed")
            return True

        current_version = self.get_current_config_version()
        logging.info(
            f"Migrating configuration from {current_version or 'unknown'} to {__version__}"
        )

        migration_steps = [
            ("cache structure", self.migrate_cache_structure),
            ("config structure", self.migrate_config_structure),
            ("template variables", self.migrate_template_variables),
        ]

        for step_name, migration_func in migration_steps:
            logging.info(f"Running migration: {step_name}")
            if not migration_func():
                logging.error(f"Migration step '{step_name}' failed")
                return False

        # Update version file
        if not self.set_config_version(__version__):
            logging.error("Failed to update configuration version")
            return False

        logging.info("Configuration migration completed successfully")
        return True

    def backup_config(self) -> Optional[str]:
        """Create a backup of the current configuration."""
        try:
            import datetime
            import shutil

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(CONF_DIR, f"backup_{timestamp}")

            if os.path.exists(CONF_DIR):
                # Create backup directory
                util.create_dir(backup_dir)

                # Copy all config files
                for item in os.listdir(CONF_DIR):
                    if item.startswith("backup_"):
                        continue  # Skip existing backups

                    src_path = os.path.join(CONF_DIR, item)
                    dst_path = os.path.join(backup_dir, item)

                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)

                logging.info(f"Configuration backup created: {backup_dir}")
                return backup_dir

        except Exception as e:
            logging.error(f"Failed to create configuration backup: {e}")

        return None


def migrate_config_cli() -> int:
    """
    CLI command to migrate configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    migration = ConfigMigration()

    # Set up logging for CLI output
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not migration.needs_migration():
        logging.info("Configuration is already up to date!")
        return 0

    # Create backup before migration
    backup_dir = migration.backup_config()
    if backup_dir:
        logging.info(f"Backup created at: {backup_dir}")
    else:
        logging.warning("Failed to create backup. Continue migration? (y/N): ")
        if input().lower() != "y":
            logging.info("Migration aborted.")
            return 1

    # Run migration
    success = migration.run_migration()

    if success:
        logging.info("Configuration migration completed successfully!")
        return 0
    else:
        logging.error("Configuration migration failed.")
        if backup_dir:
            logging.info(f"You can restore from backup: {backup_dir}")
        return 1
