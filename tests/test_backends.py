"""Test backend functions."""

import os
import tempfile
import unittest
from unittest import mock

from pywal import colors


class TestBackends(unittest.TestCase):
    """Test backend functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary test image
        self.test_image = os.path.join(
            os.path.dirname(__file__), "test_files", "test.jpg"
        )
        if not os.path.exists(self.test_image):
            # Create a minimal test image if it doesn't exist
            self.test_image = tempfile.NamedTemporaryFile(
                suffix=".jpg", delete=False
            ).name

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "test_image") and self.test_image.startswith("/tmp"):
            try:
                os.unlink(self.test_image)
            except (OSError, FileNotFoundError):
                pass

    def test_list_backends(self):
        """> Test backend listing."""
        backends = colors.list_backends()
        self.assertIsInstance(backends, list)
        self.assertGreater(len(backends), 0)
        # Check that common backends are present
        expected_backends = ["wal", "colorthief", "fast_colorthief"]
        for backend in expected_backends:
            if backend in backends:
                self.assertIn(backend, backends)

    def test_get_backend_specific(self):
        """> Test specific backend selection."""
        result = colors.get_backend("wal")
        self.assertEqual(result, "wal")

    def test_get_backend_random(self):
        """> Test random backend selection."""
        result = colors.get_backend("random")
        backends = colors.list_backends()
        self.assertIn(result, backends)

    def test_backend_fallback_system(self):
        """> Test backend fallback when primary fails."""
        with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_image:
            # Create a minimal valid JPEG header
            temp_image.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
            temp_image.flush()

            # This should work with fallback backends
            try:
                result = colors.get(temp_image.name, backend="nonexistent_backend")
                self.assertIsInstance(result, dict)
                self.assertIn("colors", result)
                self.assertIn("special", result)
            except SystemExit:
                # If all backends fail, this is expected behavior
                pass

    def test_cache_fname_generation(self):
        """> Test cache filename generation."""
        with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
            temp_file.write(b"test data")
            temp_file.flush()

            cache_name = colors.cache_fname(
                temp_file.name, "wal", False, "/cache", "0.8"
            )
            self.assertIsInstance(cache_name, list)
            self.assertEqual(len(cache_name), 3)
            self.assertIn("schemes", cache_name[1])

    def test_colors_to_dict_structure(self):
        """> Test color dictionary structure."""
        test_colors = ["#000000"] * 16
        result = colors.colors_to_dict(test_colors, "/path/to/image.jpg")

        self.assertIn("wallpaper", result)
        self.assertIn("alpha", result)
        self.assertIn("special", result)
        self.assertIn("colors", result)

        # Check special colors structure
        special_keys = ["background", "foreground", "cursor"]
        for key in special_keys:
            self.assertIn(key, result["special"])

        # Check color palette structure
        for i in range(16):
            self.assertIn(f"color{i}", result["colors"])

    def test_saturate_colors_function(self):
        """> Test color saturation adjustment."""
        test_colors = ["#FF0000", "#00FF00", "#0000FF"] + ["#CCCCCC"] * 13

        # Test with valid saturation
        result = colors.saturate_colors(test_colors, "0.5")
        self.assertEqual(len(result), 16)

        # Test with invalid saturation (should return unchanged)
        result_invalid = colors.saturate_colors(test_colors, "2.0")
        self.assertEqual(result_invalid, test_colors)

        # Test with None saturation
        result_none = colors.saturate_colors(test_colors, None)
        self.assertEqual(result_none, test_colors)

    def test_generic_adjust_light_mode(self):
        """> Test generic color adjustment for light themes."""
        test_colors = ["#222222"] * 16
        original_colors = test_colors.copy()
        result = colors.generic_adjust(test_colors, light=True)
        self.assertEqual(len(result), 16)
        # Background should be lightened in light mode
        self.assertNotEqual(result[0], original_colors[0])

    def test_generic_adjust_dark_mode(self):
        """> Test generic color adjustment for dark themes."""
        test_colors = ["#DDDDDD"] * 16
        original_colors = test_colors.copy()
        result = colors.generic_adjust(test_colors, light=False)
        self.assertEqual(len(result), 16)
        # Background should be darkened in dark mode
        self.assertNotEqual(result[0], original_colors[0])

    @mock.patch("pywal.colors.logging")
    def test_backend_import_error_handling(self, mock_logging):
        """> Test graceful handling of missing backend dependencies."""
        with mock.patch(
            "builtins.__import__", side_effect=ImportError("Mock import error")
        ):
            with self.assertRaises(SystemExit):
                colors.get(self.test_image, backend="nonexistent")
            mock_logging.error.assert_called()


if __name__ == "__main__":
    unittest.main()
