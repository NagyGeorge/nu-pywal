"""Test configuration validation and management."""

import json
import os
import tempfile
import unittest
from unittest import mock

from pywal import config


class TestConfigValidator(unittest.TestCase):
    """Test configuration validator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = config.ConfigValidator()

    def test_validate_hex_color_valid(self):
        """> Test valid hex color validation."""
        valid_colors = ["#FF0000", "#00ff00", "#0000FF", "fff", "000000"]
        for color in valid_colors:
            self.assertTrue(self.validator.validate_hex_color(color))

    def test_validate_hex_color_invalid(self):
        """> Test invalid hex color validation."""
        invalid_colors = ["#GG0000", "12345", "#1234567", "", "red", None, 123]
        for color in invalid_colors:
            self.assertFalse(self.validator.validate_hex_color(color))

    def test_validate_color_palette_valid(self):
        """> Test valid color palette validation."""
        valid_palette = {
            "special": {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "cursor": "#FF0000",
            },
            "colors": {f"color{i}": f"#{i:02x}{i:02x}{i:02x}" for i in range(16)},
        }
        self.assertTrue(self.validator.validate_color_palette(valid_palette))

    def test_validate_color_palette_missing_special(self):
        """> Test color palette validation with missing special colors."""
        invalid_palette = {
            "colors": {f"color{i}": f"#{i:02x}{i:02x}{i:02x}" for i in range(16)}
        }
        self.assertFalse(self.validator.validate_color_palette(invalid_palette))
        self.assertIn("Missing 'special' colors section", self.validator.get_errors())

    def test_validate_color_palette_missing_colors(self):
        """> Test color palette validation with missing colors."""
        invalid_palette = {
            "special": {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "cursor": "#FF0000",
            },
            "colors": {"color0": "#000000"},  # Missing colors 1-15
        }
        self.assertFalse(self.validator.validate_color_palette(invalid_palette))
        errors = self.validator.get_errors()
        self.assertTrue(any("Missing colors:" in error for error in errors))

    def test_validate_color_palette_invalid_hex(self):
        """> Test color palette validation with invalid hex colors."""
        invalid_palette = {
            "special": {
                "background": "invalid_color",
                "foreground": "#FFFFFF",
                "cursor": "#FF0000",
            },
            "colors": {f"color{i}": f"#{i:02x}{i:02x}{i:02x}" for i in range(16)},
        }
        self.assertFalse(self.validator.validate_color_palette(invalid_palette))
        errors = self.validator.get_errors()
        self.assertTrue(any("Invalid hex color" in error for error in errors))

    def test_validate_color_scheme_valid(self):
        """> Test valid color scheme validation."""
        valid_scheme = {
            "wallpaper": "/path/to/image.jpg",
            "alpha": "100",
            "special": {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "cursor": "#FF0000",
            },
            "colors": {f"color{i}": f"#{i:02x}{i:02x}{i:02x}" for i in range(16)},
        }
        self.assertTrue(self.validator.validate_color_scheme(valid_scheme))

    def test_validate_color_scheme_missing_required(self):
        """> Test color scheme validation with missing required fields."""
        invalid_scheme = {
            "wallpaper": "/path/to/image.jpg",
            # Missing alpha, special, colors
        }
        self.assertFalse(self.validator.validate_color_scheme(invalid_scheme))
        errors = self.validator.get_errors()
        self.assertTrue(any("Missing required fields" in error for error in errors))

    def test_validate_color_scheme_invalid_alpha(self):
        """> Test color scheme validation with invalid alpha."""
        invalid_scheme = {
            "wallpaper": "/path/to/image.jpg",
            "alpha": "invalid",
            "special": {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "cursor": "#FF0000",
            },
            "colors": {f"color{i}": f"#{i:02x}{i:02x}{i:02x}" for i in range(16)},
        }
        self.assertFalse(self.validator.validate_color_scheme(invalid_scheme))

    def test_validate_template_file_valid(self):
        """> Test valid template file validation."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".template", delete=False
        ) as f:
            f.write("background: {background}\ncolor0: {color0}")
            f.flush()

            try:
                self.assertTrue(self.validator.validate_template_file(f.name))
            finally:
                os.unlink(f.name)

    def test_validate_template_file_with_warnings(self):
        """> Test template file validation with unknown placeholders."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".template", delete=False
        ) as f:
            f.write("background: {background}\ninvalid: {unknown_placeholder}")
            f.flush()

            try:
                # Should still pass but with warnings
                self.assertTrue(self.validator.validate_template_file(f.name))
                warnings = self.validator.get_warnings()
                self.assertTrue(
                    any("Unknown placeholders" in warning for warning in warnings)
                )
            finally:
                os.unlink(f.name)

    def test_validate_template_file_nonexistent(self):
        """> Test template file validation with non-existent file."""
        self.assertFalse(self.validator.validate_template_file("/nonexistent/file"))
        errors = self.validator.get_errors()
        self.assertTrue(any("does not exist" in error for error in errors))


class TestConfigManager(unittest.TestCase):
    """Test configuration manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = config.ConfigManager()

    @mock.patch("pywal.config.CONF_DIR")
    @mock.patch("pywal.config.CACHE_DIR")
    def test_validate_color_scheme_file_valid(self, mock_cache_dir, mock_conf_dir):
        """> Test valid color scheme file validation."""
        valid_scheme = {
            "wallpaper": "/path/to/image.jpg",
            "alpha": "100",
            "special": {
                "background": "#000000",
                "foreground": "#FFFFFF",
                "cursor": "#FF0000",
            },
            "colors": {f"color{i}": f"#{i:02x}{i:02x}{i:02x}" for i in range(16)},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_scheme, f)
            f.flush()

            try:
                self.assertTrue(self.config_manager.validate_color_scheme_file(f.name))
            finally:
                os.unlink(f.name)

    def test_validate_color_scheme_file_invalid_json(self):
        """> Test color scheme file validation with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {")
            f.flush()

            try:
                self.assertFalse(self.config_manager.validate_color_scheme_file(f.name))
            finally:
                os.unlink(f.name)

    def test_validate_color_scheme_file_nonexistent(self):
        """> Test color scheme file validation with non-existent file."""
        self.assertFalse(
            self.config_manager.validate_color_scheme_file("/nonexistent/file.json")
        )

    @mock.patch("pywal.config.os.path.exists")
    @mock.patch("pywal.config.os.path.isdir")
    @mock.patch("pywal.config.os.access")
    def test_validate_directory_structure(self, mock_access, mock_isdir, mock_exists):
        """> Test directory structure validation."""
        # Mock all directories exist, are directories, and are accessible
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_access.return_value = True

        self.assertTrue(self.config_manager.validator.validate_directory_structure())

    @mock.patch("pywal.config.os.path.exists")
    def test_validate_directory_structure_missing_dirs(self, mock_exists):
        """> Test directory structure validation with missing directories."""
        mock_exists.return_value = False

        self.assertTrue(self.config_manager.validator.validate_directory_structure())
        warnings = self.config_manager.validator.get_warnings()
        self.assertTrue(any("does not exist" in warning for warning in warnings))

    @mock.patch("pywal.config.util.create_dir")
    def test_repair_installation(self, mock_create_dir):
        """> Test installation repair."""
        mock_create_dir.return_value = None  # Success

        self.assertTrue(self.config_manager.repair_installation())
        # Should be called for each required directory
        self.assertGreater(mock_create_dir.call_count, 0)

    @mock.patch("pywal.config.util.create_dir")
    def test_repair_installation_failure(self, mock_create_dir):
        """> Test installation repair with failure."""
        mock_create_dir.side_effect = Exception("Failed to create directory")

        self.assertFalse(self.config_manager.repair_installation())


class TestConfigCLI(unittest.TestCase):
    """Test configuration CLI commands."""

    @mock.patch("pywal.config.ConfigManager")
    @mock.patch("builtins.print")
    def test_validate_config_cli_success(self, mock_print, mock_config_manager):
        """> Test successful config validation CLI."""
        mock_manager = mock_config_manager.return_value
        mock_manager.validate_installation.return_value = True

        result = config.validate_config_cli()
        self.assertEqual(result, 0)
        mock_print.assert_called_with("\nConfiguration validation passed!")

    @mock.patch("pywal.config.ConfigManager")
    @mock.patch("builtins.print")
    def test_validate_config_cli_failure(self, mock_print, mock_config_manager):
        """> Test failed config validation CLI."""
        mock_manager = mock_config_manager.return_value
        mock_manager.validate_installation.return_value = False

        result = config.validate_config_cli()
        self.assertEqual(result, 1)
        mock_print.assert_called_with(
            "\nValidation failed. Use 'wal --repair-config' to attempt repair."
        )

    @mock.patch("pywal.config.ConfigManager")
    @mock.patch("builtins.print")
    def test_repair_config_cli_success(self, mock_print, mock_config_manager):
        """> Test successful config repair CLI."""
        mock_manager = mock_config_manager.return_value
        mock_manager.repair_installation.return_value = True
        mock_manager.validate_installation.return_value = True

        result = config.repair_config_cli()
        self.assertEqual(result, 0)
        # Should print completion and validation messages
        self.assertEqual(mock_print.call_count, 2)

    @mock.patch("pywal.config.ConfigManager")
    @mock.patch("builtins.print")
    def test_repair_config_cli_failure(self, mock_print, mock_config_manager):
        """> Test failed config repair CLI."""
        mock_manager = mock_config_manager.return_value
        mock_manager.repair_installation.return_value = False

        result = config.repair_config_cli()
        self.assertEqual(result, 1)
        mock_print.assert_called_with("\nConfiguration repair failed.")


class TestConfigMigration(unittest.TestCase):
    """Test configuration migration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.migration = config.ConfigMigration()

    def test_needs_migration_no_version_file(self):
        """> Test migration needed when no version file exists."""
        with mock.patch.object(
            self.migration, "get_current_config_version"
        ) as mock_get:
            mock_get.return_value = None
            self.assertTrue(self.migration.needs_migration())

    def test_needs_migration_different_version(self):
        """> Test migration needed when version differs."""
        with mock.patch.object(
            self.migration, "get_current_config_version"
        ) as mock_get:
            mock_get.return_value = "0.8.0"  # Different from current
            self.assertTrue(self.migration.needs_migration())

    def test_needs_migration_same_version(self):
        """> Test no migration needed when version matches."""
        with mock.patch.object(
            self.migration, "get_current_config_version"
        ) as mock_get:
            mock_get.return_value = config.__version__
            self.assertFalse(self.migration.needs_migration())

    @mock.patch("pywal.config.os.path.exists")
    @mock.patch("pywal.config.os.scandir")
    @mock.patch("pywal.config.util.create_dir")
    def test_migrate_cache_structure(self, mock_create_dir, mock_scandir, mock_exists):
        """> Test cache structure migration."""

        # Mock old cache directory exists, new doesn't
        def mock_exists_func(path):
            return "colorschemes" in path and "schemes" not in path

        mock_exists.side_effect = mock_exists_func

        # Mock file entries
        mock_file = mock.MagicMock()
        mock_file.name = "test_scheme.json"
        mock_file.path = "/cache/colorschemes/test_scheme.json"
        mock_scandir.return_value = [mock_file]

        with mock.patch("pywal.config.os.rename") as mock_rename:
            result = self.migration.migrate_cache_structure()
            self.assertTrue(result)
            # Only called if old directory exists and new doesn't
            if mock_exists.side_effect(
                "/cache/colorschemes"
            ) and not mock_exists.side_effect("/cache/schemes"):
                mock_create_dir.assert_called()
                mock_rename.assert_called()

    @mock.patch("pywal.config.util.create_dir")
    def test_migrate_config_structure(self, mock_create_dir):
        """> Test config structure migration."""
        with mock.patch("pywal.config.os.path.exists") as mock_exists:
            mock_exists.return_value = False  # No old directories

            result = self.migration.migrate_config_structure()
            self.assertTrue(result)
            # Should create required directories
            self.assertGreater(mock_create_dir.call_count, 0)

    @mock.patch("pywal.config.os.path.exists")
    @mock.patch("pywal.config.os.scandir")
    def test_migrate_template_variables(self, mock_scandir, mock_exists):
        """> Test template variable migration."""
        mock_exists.return_value = True

        # Mock template file
        mock_file = mock.MagicMock()
        mock_file.is_file.return_value = True
        mock_file.path = "/conf/templates/test.template"
        mock_file.name = "test.template"
        mock_scandir.return_value = [mock_file]

        template_content = (
            "background: {color.background}\nforeground: {color.foreground}"
        )
        expected_content = "background: {background}\nforeground: {foreground}"

        with mock.patch(
            "builtins.open", mock.mock_open(read_data=template_content)
        ) as mock_open:
            result = self.migration.migrate_template_variables()
            self.assertTrue(result)

            # Check that file was written with updated content
            mock_open.assert_called()
            handle = mock_open()
            handle.write.assert_called_with(expected_content)

    @mock.patch.object(config.ConfigMigration, "migrate_cache_structure")
    @mock.patch.object(config.ConfigMigration, "migrate_config_structure")
    @mock.patch.object(config.ConfigMigration, "migrate_template_variables")
    @mock.patch.object(config.ConfigMigration, "set_config_version")
    def test_run_migration_success(
        self,
        mock_set_version,
        mock_migrate_templates,
        mock_migrate_config,
        mock_migrate_cache,
    ):
        """> Test successful migration run."""
        # Mock all migration steps to succeed
        mock_migrate_cache.return_value = True
        mock_migrate_config.return_value = True
        mock_migrate_templates.return_value = True
        mock_set_version.return_value = True

        with mock.patch.object(self.migration, "needs_migration") as mock_needs:
            mock_needs.return_value = True

            result = self.migration.run_migration()
            self.assertTrue(result)

            # All migration steps should be called
            mock_migrate_cache.assert_called_once()
            mock_migrate_config.assert_called_once()
            mock_migrate_templates.assert_called_once()
            mock_set_version.assert_called_once()

    @mock.patch.object(config.ConfigMigration, "migrate_cache_structure")
    def test_run_migration_failure(self, mock_migrate_cache):
        """> Test migration failure."""
        mock_migrate_cache.return_value = False  # First step fails

        with mock.patch.object(self.migration, "needs_migration") as mock_needs:
            mock_needs.return_value = True

            result = self.migration.run_migration()
            self.assertFalse(result)

    @mock.patch("shutil.copytree")
    @mock.patch("shutil.copy2")
    @mock.patch("pywal.config.os.listdir")
    @mock.patch("pywal.config.os.path.exists")
    @mock.patch("pywal.config.os.path.isdir")
    @mock.patch("pywal.config.util.create_dir")
    def test_backup_config(
        self,
        mock_create_dir,
        mock_isdir,
        mock_exists,
        mock_listdir,
        mock_copy2,
        mock_copytree,
    ):
        """> Test configuration backup."""
        mock_exists.return_value = True
        mock_listdir.return_value = ["templates", "colorschemes", "version"]
        mock_isdir.side_effect = lambda x: "templates" in x or "colorschemes" in x

        backup_dir = self.migration.backup_config()
        self.assertIsNotNone(backup_dir)
        self.assertIn("backup_", backup_dir)

        # Should create backup directory and copy files
        mock_create_dir.assert_called()
        mock_copytree.assert_called()  # For directories
        mock_copy2.assert_called()  # For files


class TestMigrationCLI(unittest.TestCase):
    """Test migration CLI commands."""

    @mock.patch("pywal.config.ConfigMigration")
    @mock.patch("builtins.print")
    def test_migrate_config_cli_no_migration_needed(
        self, mock_print, mock_migration_class
    ):
        """> Test migration CLI when no migration needed."""
        mock_migration = mock_migration_class.return_value
        mock_migration.needs_migration.return_value = False

        result = config.migrate_config_cli()
        self.assertEqual(result, 0)
        mock_print.assert_called_with("Configuration is already up to date!")

    @mock.patch("pywal.config.ConfigMigration")
    @mock.patch("builtins.print")
    def test_migrate_config_cli_success(self, mock_print, mock_migration_class):
        """> Test successful migration CLI."""
        mock_migration = mock_migration_class.return_value
        mock_migration.needs_migration.return_value = True
        mock_migration.backup_config.return_value = "/backup/dir"
        mock_migration.run_migration.return_value = True

        result = config.migrate_config_cli()
        self.assertEqual(result, 0)

        # Should print success message
        mock_print.assert_any_call("\nConfiguration migration completed successfully!")

    @mock.patch("pywal.config.ConfigMigration")
    @mock.patch("builtins.print")
    @mock.patch("builtins.input")
    def test_migrate_config_cli_no_backup_abort(
        self, mock_input, mock_print, mock_migration_class
    ):
        """> Test migration CLI with no backup and user abort."""
        mock_migration = mock_migration_class.return_value
        mock_migration.needs_migration.return_value = True
        mock_migration.backup_config.return_value = None  # Backup failed
        mock_input.return_value = "n"  # User chooses not to continue

        result = config.migrate_config_cli()
        self.assertEqual(result, 1)
        mock_print.assert_any_call("Migration aborted.")


if __name__ == "__main__":
    unittest.main()
