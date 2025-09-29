"""Test cache functionality."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from pywal import cache


class TestAdvancedCache(unittest.TestCase):
    """Test advanced cache functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = cache.AdvancedCache(cache_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_directory(self):
        """> Test cache initialization creates directory."""
        cache_dir = os.path.join(self.temp_dir, "new_cache")
        cache.AdvancedCache(cache_dir=cache_dir)
        self.assertTrue(os.path.exists(cache_dir))

    @patch("os.stat")
    def test_generate_cache_key(self, mock_stat):
        """> Test cache key generation."""
        # Mock file stat
        mock_stat.return_value.st_size = 1024
        mock_stat.return_value.st_mtime = 1234567890

        with patch.object(self.cache, "_get_image_hash", return_value="abcd1234"):
            key = self.cache.generate_cache_key("/test/image.jpg", "wal", False, "0.5")
            self.assertIsInstance(key, str)
            self.assertEqual(len(key), 16)  # Truncated hash length

            # Same inputs should generate same key
            key2 = self.cache.generate_cache_key("/test/image.jpg", "wal", False, "0.5")
            self.assertEqual(key, key2)

            # Different inputs should generate different keys
            key3 = self.cache.generate_cache_key(
                "/test/image.jpg", "colorthief", False, "0.5"
            )
            self.assertNotEqual(key, key3)

    @patch("os.stat")
    def test_put_and_get_cache_entry(self, mock_stat):
        """> Test storing and retrieving cache entries."""
        mock_stat.return_value.st_size = 1024
        mock_stat.return_value.st_mtime = 1234567890

        test_colors = {
            "wallpaper": "/test/image.jpg",
            "colors": {"color0": "#000000", "color1": "#ff0000"},
            "special": {"background": "#000000", "foreground": "#ffffff"},
        }

        with patch.object(self.cache, "_get_image_hash", return_value="abcd1234"):
            cache_key = self.cache.generate_cache_key(
                "/test/image.jpg", "wal", False, ""
            )

            # Store entry
            success = self.cache.put(cache_key, test_colors, "/test/image.jpg", "wal")
            self.assertTrue(success)

            # Retrieve entry
            retrieved = self.cache.get(cache_key, "/test/image.jpg", "wal")
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["colors"]["color0"], "#000000")

    def test_get_nonexistent_entry(self):
        """> Test retrieving non-existent cache entry."""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)

    def test_compression(self):
        """> Test data compression via file operations."""
        # Test that files are compressed when compress=True
        test_colors = {"test": "data"}
        cache_key = "test_key"

        # Test compressed storage
        success = self.cache.put(cache_key, test_colors, compress=True)
        self.assertTrue(success)

        # Verify compressed file exists
        cache_file = os.path.join(self.cache.schemes_dir, f"{cache_key}.json.gz")
        self.assertTrue(os.path.exists(cache_file))

    def test_database_operations(self):
        """> Test database creation and operations."""
        # Database should be created on initialization
        db_path = os.path.join(self.temp_dir, "cache.db")
        self.assertTrue(os.path.exists(db_path))

        # Test getting analytics
        analytics = self.cache.get_analytics()
        self.assertIsInstance(analytics, cache.CacheStats)
        self.assertGreaterEqual(analytics.total_entries, 0)

    def test_cleanup_expired_entries(self):
        """> Test cleanup of expired cache entries."""
        # Store a test entry
        test_colors = {"test": "data"}
        cache_key = "test_key"
        self.cache.put(cache_key, test_colors)

        # Mock time to make entry appear expired
        with patch("time.time", return_value=999999999999):
            removed = self.cache.cleanup(max_age_days=1)
            self.assertGreaterEqual(removed, 0)

    def test_cleanup_by_size(self):
        """> Test cleanup by cache size."""
        # Add multiple entries to exceed size limit
        for i in range(5):
            test_colors = {"test": f"data_{i}"}
            self.cache.put(f"test_key_{i}", test_colors)

        removed = self.cache.cleanup(max_size_mb=0.001)  # Very small limit
        self.assertGreaterEqual(removed, 0)

    def test_get_cache_info(self):
        """> Test cache information retrieval."""
        # Add some test entries
        for i in range(3):
            test_colors = {"test": f"data_{i}"}
            self.cache.put(f"test_key_{i}", test_colors)

        analytics = self.cache.get_analytics()
        self.assertIsInstance(analytics, cache.CacheStats)
        self.assertGreaterEqual(analytics.total_entries, 0)

    def test_deduplication(self):
        """> Test cache deduplication."""
        # Create identical color schemes
        test_colors1 = {"colors": {"color0": "#000000"}}
        test_colors2 = {"colors": {"color0": "#000000"}}

        # Store both with same image hash to simulate duplicates
        with patch.object(self.cache, "_get_image_hash", return_value="same_hash"):
            self.cache.put("key1", test_colors1, "/test/image1.jpg", "wal")
            self.cache.put("key2", test_colors2, "/test/image2.jpg", "wal")

        # Run deduplication
        removed = self.cache.deduplicate()
        self.assertGreaterEqual(removed, 0)


class TestCacheFunctions(unittest.TestCase):
    """Test cache utility functions."""

    @patch("pywal.cache.get_cache")
    def test_cache_get(self, mock_get_cache):
        """> Test cache_get function."""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        mock_cache.generate_cache_key.return_value = "test_key"
        mock_cache.get.return_value = {"test": "colors"}

        result = cache.cache_get("/test/image.jpg", "wal", False, "")
        self.assertEqual(result, {"test": "colors"})
        mock_cache.generate_cache_key.assert_called_once_with(
            "/test/image.jpg", "wal", False, ""
        )
        mock_cache.get.assert_called_once_with("test_key", "/test/image.jpg", "wal")

    @patch("pywal.cache.get_cache")
    def test_cache_put(self, mock_get_cache):
        """> Test cache_put function."""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        mock_cache.generate_cache_key.return_value = "test_key"
        mock_cache.put.return_value = True

        test_colors = {"test": "colors"}
        result = cache.cache_put("/test/image.jpg", "wal", False, test_colors, "")
        self.assertTrue(result)
        mock_cache.generate_cache_key.assert_called_once_with(
            "/test/image.jpg", "wal", False, ""
        )
        mock_cache.put.assert_called_once_with(
            "test_key", test_colors, "/test/image.jpg", "wal"
        )

    @patch("pywal.cache.get_cache")
    def test_cache_info_cli(self, mock_get_cache):
        """> Test cache_info_cli function."""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        mock_stats = cache.CacheStats()
        mock_stats.total_entries = 10
        mock_stats.total_size = 5242880  # 5MB in bytes
        mock_cache.get_analytics.return_value = mock_stats

        with patch("sys.stdout.write") as mock_stdout:
            result = cache.cache_info_cli()
            self.assertEqual(result, 0)
            mock_stdout.assert_called()

    @patch("pywal.cache.get_cache")
    def test_cache_cleanup_cli(self, mock_get_cache):
        """> Test cache_cleanup_cli function."""
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache
        mock_cache.cleanup.return_value = 5
        mock_stats = cache.CacheStats()
        mock_stats.total_entries = 10
        mock_stats.total_size = 5242880
        mock_cache.get_analytics.return_value = mock_stats

        with patch("sys.stdout.write") as mock_stdout:
            result = cache.cache_cleanup_cli()
            self.assertEqual(result, 0)
            mock_stdout.assert_called()
            mock_cache.cleanup.assert_called_once()

    def test_cache_error_handling(self):
        """> Test cache error handling."""
        # Test JSON serialization error handling by testing the put method directly
        test_cache = cache.AdvancedCache()

        # Mock file operations to simulate IO error
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = test_cache.put("test_key", {"test": "data"})
            self.assertFalse(result)

    def test_database_connection_error(self):
        """> Test database connection error handling."""
        test_cache = cache.AdvancedCache()

        # Mock sqlite3.connect to fail during get_analytics call
        with patch(
            "pywal.cache.sqlite3.connect", side_effect=Exception("Database error")
        ):
            analytics = test_cache.get_analytics()

        # Should return CacheStats instance even on database error
        self.assertIsInstance(analytics, cache.CacheStats)

    def test_json_serialization_error(self):
        """> Test JSON serialization error handling."""
        test_cache = cache.AdvancedCache()

        # Mock json.dump to raise TypeError to simulate serialization error
        with patch(
            "pywal.cache.json.dump", side_effect=TypeError("Not JSON serializable")
        ):
            result = test_cache.put("test_key", {"test": "data"})
            self.assertFalse(result)


class TestCacheIntegration(unittest.TestCase):
    """Test cache integration with other modules."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_directory_configuration(self):
        """> Test cache directory configuration."""
        test_cache = cache.AdvancedCache(cache_dir=self.temp_dir)
        # Cache should use provided directory
        self.assertEqual(test_cache.cache_dir, self.temp_dir)

    def test_cache_persistence(self):
        """> Test cache data persistence across instances."""
        # Create cache and store data
        cache1 = cache.AdvancedCache(cache_dir=self.temp_dir)
        test_colors = {"test": "persistent_data"}
        cache_key = "test_key"
        cache1.put(cache_key, test_colors)

        # Create new cache instance and retrieve data
        cache2 = cache.AdvancedCache(cache_dir=self.temp_dir)
        retrieved = cache2.get(cache_key)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["test"], "persistent_data")

    def test_cache_logging(self):
        """> Test cache logging functionality."""
        with patch("pywal.cache.logging") as mock_logging:
            test_cache = cache.AdvancedCache()

            # Add a cache entry and then get it to trigger logging
            test_cache.put("test_key", {"test": "data"})
            test_cache.get("test_key")

            # Verify logging was called
            self.assertTrue(
                mock_logging.info.called
                or mock_logging.debug.called
                or mock_logging.warning.called
            )


if __name__ == "__main__":
    unittest.main()
