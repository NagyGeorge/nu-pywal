"""Test parallel processing functionality."""

import tempfile
import unittest
from unittest import mock

from pywal import parallel


class TestParallelColorProcessor(unittest.TestCase):
    """Test parallel color processor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = parallel.ParallelColorProcessor(max_workers=2)

    def test_init_default_workers(self):
        """> Test processor initialization with default workers."""
        processor = parallel.ParallelColorProcessor()
        self.assertIsInstance(processor.max_workers, int)
        self.assertGreater(processor.max_workers, 0)

    def test_init_custom_workers(self):
        """> Test processor initialization with custom workers."""
        processor = parallel.ParallelColorProcessor(max_workers=8)
        self.assertEqual(processor.max_workers, 8)

    @mock.patch("pywal.parallel.colors.get")
    @mock.patch("pywal.parallel.os.path.isfile")
    @mock.patch("pywal.parallel.colors.cache_fname")
    def test_process_single_image_success(
        self, mock_cache_fname, mock_isfile, mock_colors_get
    ):
        """> Test successful single image processing."""
        mock_cache_fname.return_value = ["/cache", "schemes", "test.json"]
        mock_isfile.return_value = False  # No cache hit
        mock_colors_get.return_value = {"test": "colors"}

        result = self.processor._process_single_image(
            "/test/image.jpg", False, ["wal"], ""
        )

        self.assertEqual(result, {"test": "colors"})
        mock_colors_get.assert_called_once()

    @mock.patch("pywal.parallel.colors.get")
    def test_process_single_image_failure(self, mock_colors_get):
        """> Test single image processing with backend failure."""
        mock_colors_get.side_effect = Exception("Backend failed")

        result = self.processor._process_single_image(
            "/test/image.jpg", False, ["wal"], ""
        )

        self.assertIsNone(result)

    @mock.patch("pywal.parallel.os.path.isfile")
    @mock.patch("pywal.parallel.colors.file")
    @mock.patch("pywal.parallel.colors.cache_fname")
    def test_process_single_image_cache_hit(
        self, mock_cache_fname, mock_colors_file, mock_isfile
    ):
        """> Test single image processing with cache hit."""
        mock_cache_fname.return_value = ["/cache", "schemes", "test.json"]
        mock_isfile.return_value = True
        mock_colors_file.return_value = {"cached": "colors"}

        result = self.processor._process_single_image(
            "/test/image.jpg", False, ["wal"], ""
        )

        self.assertEqual(result, {"cached": "colors"})
        self.assertEqual(self.processor.stats["cache_hits"], 1)

    def test_calculate_contrast(self):
        """> Test contrast calculation between colors."""
        # Black and white should have high contrast
        contrast = self.processor._calculate_contrast("#000000", "#FFFFFF")
        self.assertGreater(contrast, 0.8)

        # Same colors should have low contrast
        contrast = self.processor._calculate_contrast("#FF0000", "#FF0000")
        self.assertLess(contrast, 0.1)

    def test_calculate_saturation(self):
        """> Test saturation calculation."""
        # Pure red should have high saturation
        saturation = self.processor._calculate_saturation("#FF0000")
        self.assertGreater(saturation, 0.8)

        # Gray should have low saturation
        saturation = self.processor._calculate_saturation("#808080")
        self.assertLess(saturation, 0.1)

    def test_calculate_variance(self):
        """> Test variance calculation."""
        # Different values should have high variance
        variance = self.processor._calculate_variance([0.0, 0.5, 1.0])
        self.assertGreater(variance, 0.1)

        # Similar values should have low variance
        variance = self.processor._calculate_variance([0.5, 0.51, 0.49])
        self.assertLess(variance, 0.01)

    def test_calculate_image_score(self):
        """> Test image quality score calculation."""
        good_scheme = {
            "colors": {
                f"color{i}": f"#{i * 15:02x}{i * 10:02x}{i * 5:02x}" for i in range(16)
            },
            "special": {"background": "#000000", "foreground": "#FFFFFF"},
        }

        score = self.processor._calculate_image_score(good_scheme)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_get_stats(self):
        """> Test statistics retrieval."""
        # Set some stats
        self.processor.stats["images_processed"] = 5
        self.processor.stats["cache_hits"] = 3
        self.processor.stats["cache_misses"] = 2
        self.processor.stats["total_time"] = 10.0

        stats = self.processor.get_stats()

        self.assertEqual(stats["images_processed"], 5)
        self.assertEqual(stats["cache_hit_rate"], 0.6)
        self.assertEqual(stats["avg_processing_time"], 2.0)

    def test_reset_stats(self):
        """> Test statistics reset."""
        # Set some stats
        self.processor.stats["images_processed"] = 10
        self.processor.stats["cache_hits"] = 5

        self.processor.reset_stats()

        self.assertEqual(self.processor.stats["images_processed"], 0)
        self.assertEqual(self.processor.stats["cache_hits"], 0)


class TestParallelImagePreprocessor(unittest.TestCase):
    """Test parallel image preprocessor functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.preprocessor = parallel.ParallelImagePreprocessor(max_workers=2)

    def test_init_default_workers(self):
        """> Test preprocessor initialization with default workers."""
        preprocessor = parallel.ParallelImagePreprocessor()
        self.assertIsInstance(preprocessor.max_workers, int)
        self.assertGreater(preprocessor.max_workers, 0)

    @mock.patch("pywal.parallel.util.run_command")
    @mock.patch("pywal.parallel.os.path.exists")
    def test_preprocess_single_image_success(self, mock_exists, mock_run_command):
        """> Test successful single image preprocessing."""
        mock_exists.return_value = True
        mock_run_command.return_value = mock.MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.preprocessor._preprocess_single_image(
                "/test/image.jpg", (256, 256), temp_dir
            )

            self.assertIsNotNone(result)
            self.assertTrue(result.startswith(temp_dir))

    @mock.patch("pywal.parallel.util.run_command")
    def test_preprocess_single_image_failure(self, mock_run_command):
        """> Test single image preprocessing failure."""
        mock_run_command.side_effect = Exception("Command failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.preprocessor._preprocess_single_image(
                "/test/image.jpg", (256, 256), temp_dir
            )

            self.assertIsNone(result)


class TestParallelUtilities(unittest.TestCase):
    """Test parallel processing utility functions."""

    @mock.patch("pywal.parallel.image.get_image_dir")
    @mock.patch("pywal.parallel.ParallelColorProcessor")
    def test_process_directory_parallel_non_recursive(
        self, mock_processor_class, mock_get_image_dir
    ):
        """> Test parallel directory processing without recursion."""
        mock_get_image_dir.return_value = (["image1.jpg", "image2.jpg"], "current.jpg")
        mock_processor = mock_processor_class.return_value
        mock_processor.process_image_batch.return_value = {"test": "result"}

        result = parallel.process_directory_parallel("/test/dir", find_best=False)

        self.assertEqual(result, {"test": "result"})
        mock_processor.process_image_batch.assert_called_once()

    @mock.patch("pywal.parallel.image.get_image_dir_recursive")
    @mock.patch("pywal.parallel.ParallelColorProcessor")
    def test_process_directory_parallel_recursive(
        self, mock_processor_class, mock_get_image_dir
    ):
        """> Test parallel directory processing with recursion."""
        mock_get_image_dir.return_value = (["/test/dir/image1.jpg"], "current.jpg")
        mock_processor = mock_processor_class.return_value
        mock_processor.process_image_batch.return_value = {"test": "result"}

        result = parallel.process_directory_parallel(
            "/test/dir", recursive=True, find_best=False
        )

        self.assertEqual(result, {"test": "result"})
        mock_processor.process_image_batch.assert_called_once()

    @mock.patch("pywal.parallel.image.get_image_dir")
    @mock.patch("pywal.parallel.ParallelColorProcessor")
    def test_process_directory_parallel_find_best(
        self, mock_processor_class, mock_get_image_dir
    ):
        """> Test parallel directory processing with find_best option."""
        mock_get_image_dir.return_value = (["image1.jpg"], "current.jpg")
        mock_processor = mock_processor_class.return_value
        mock_processor.find_best_images.return_value = [
            ("best.jpg", {"colors": "data"})
        ]

        result = parallel.process_directory_parallel(
            "/test/dir", find_best=True, best_count=3
        )

        self.assertEqual(result, [("best.jpg", {"colors": "data"})])
        mock_processor.find_best_images.assert_called_once_with(
            "/test/dir", count=3, recursive=False
        )

    @mock.patch("pywal.parallel.colors.get")
    @mock.patch("pywal.parallel.colors.list_backends")
    def test_benchmark_backends(self, mock_list_backends, mock_colors_get):
        """> Test backend benchmarking."""
        mock_list_backends.return_value = ["wal", "colorthief"]
        mock_colors_get.return_value = {"test": "colors"}

        # Mock successful backend module imports
        mock_backend = mock.MagicMock()
        mock_backend.get = mock.MagicMock()

        with mock.patch("builtins.__import__"):
            with mock.patch("pywal.parallel.sys.modules") as mock_modules:
                mock_modules.__getitem__.return_value = mock_backend
                results = parallel.benchmark_backends("/test/image.jpg", iterations=2)

        self.assertIn("wal", results)
        self.assertIn("colorthief", results)

        for _backend, stats in results.items():
            self.assertIn("times", stats)
            self.assertIn("success_count", stats)
            self.assertIn("error_count", stats)
            self.assertIn("avg_time", stats)
            self.assertIn("success_rate", stats)
            self.assertIn("status", stats)

    @mock.patch("pywal.parallel.colors.get")
    def test_benchmark_backends_with_failures(self, mock_colors_get):
        """> Test backend benchmarking with some failures."""
        # First call succeeds, second fails
        mock_colors_get.side_effect = [{"test": "colors"}, Exception("Backend failed")]

        # Mock successful backend module import
        mock_backend = mock.MagicMock()
        mock_backend.get = mock.MagicMock()

        with mock.patch("builtins.__import__"):
            with mock.patch("pywal.parallel.sys.modules") as mock_modules:
                mock_modules.__getitem__.return_value = mock_backend
                results = parallel.benchmark_backends(
                    "/test/image.jpg", backends=["wal"], iterations=2
                )

        self.assertIn("wal", results)
        stats = results["wal"]
        self.assertEqual(stats["success_count"], 1)
        self.assertEqual(stats["error_count"], 1)
        self.assertEqual(stats["success_rate"], 0.5)

    @mock.patch("pywal.parallel.colors.list_backends")
    def test_benchmark_backends_unavailable(self, mock_list_backends):
        """> Test backend benchmarking with unavailable backends."""
        mock_list_backends.return_value = ["unavailable_backend", "missing_backend"]

        # Mock import errors for unavailable backends
        with mock.patch(
            "builtins.__import__", side_effect=ImportError("Backend not found")
        ):
            results = parallel.benchmark_backends("/test/image.jpg", iterations=2)

        # When all backends are unavailable, should return empty dict
        self.assertEqual(results, {})

    @mock.patch("pywal.parallel.colors.list_backends")
    def test_benchmark_backends_mixed_availability(self, mock_list_backends):
        """> Test benchmark with mixed available/unavailable backends."""
        mock_list_backends.return_value = ["wal", "unavailable_backend"]

        def mock_import(module_name):
            if "unavailable_backend" in module_name:
                raise ImportError("Backend not found")
            # Allow other imports to succeed

        mock_backend = mock.MagicMock()
        mock_backend.get = mock.MagicMock()

        with mock.patch("builtins.__import__", side_effect=mock_import):
            with mock.patch("pywal.parallel.sys.modules") as mock_modules:
                mock_modules.__getitem__.return_value = mock_backend
                results = parallel.benchmark_backends("/test/image.jpg", iterations=2)

        # Should have both available and unavailable backends
        self.assertIn("wal", results)
        self.assertIn("unavailable_backend", results)

        # Check available backend
        self.assertEqual(results["wal"]["status"], "available")

        # Check unavailable backend
        self.assertEqual(results["unavailable_backend"]["status"], "unavailable")
        self.assertEqual(results["unavailable_backend"]["success_count"], 0)
        self.assertEqual(results["unavailable_backend"]["error_count"], 2)


class TestParallelIntegration(unittest.TestCase):
    """Test parallel processing integration."""

    @mock.patch("pywal.parallel.concurrent.futures.ThreadPoolExecutor")
    def test_thread_pool_usage(self, mock_executor):
        """> Test that thread pool executor is used correctly."""
        mock_executor_instance = mock.MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_executor_instance.submit.return_value = mock.MagicMock()

        processor = parallel.ParallelColorProcessor(max_workers=4)

        # Test that max_workers is set correctly
        self.assertEqual(processor.max_workers, 4)

    def test_error_handling(self):
        """> Test that errors are handled gracefully."""
        processor = parallel.ParallelColorProcessor()

        # Test with invalid color scheme
        score = processor._calculate_image_score({})
        self.assertGreaterEqual(score, 0.0)  # Should not crash, return some default

        # Test with invalid hex color - should handle gracefully
        contrast = processor._calculate_contrast("invalid", "#FFFFFF")
        self.assertIsInstance(contrast, float)
        self.assertGreaterEqual(contrast, 0.0)
        self.assertLessEqual(contrast, 1.0)


if __name__ == "__main__":
    unittest.main()
