"""
Parallel processing utilities for nu-pywal.

This module provides concurrent processing capabilities for image analysis
and color generation to improve performance on multi-core systems.
"""

import concurrent.futures
import logging
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

from . import colors, image, util
from .settings import CACHE_DIR


class ParallelColorProcessor:
    """Handles parallel color generation from images."""

    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the parallel color processor.

        Args:
            max_workers: Maximum number of worker threads. If None, uses the number of CPUs
        """
        self.max_workers = max_workers or min(4, (os.cpu_count() or 1) + 1)
        self.stats = {
            "images_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time": 0.0,
            "backend_attempts": defaultdict(int),
            "backend_successes": defaultdict(int),
        }

    def process_image_batch(
        self,
        image_paths: List[str],
        light: bool = False,
        backends: Optional[List[str]] = None,
        sat: str = "",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process multiple images in parallel to generate color schemes.

        Args:
            image_paths: List of image file paths to process
            light: Whether to generate light color schemes
            backends: List of backends to try (None for default)
            sat: Saturation adjustment

        Returns:
            Dictionary mapping image paths to their color schemes
        """
        if not backends:
            backends = colors.list_backends()[:3]  # Use top 3 backends

        start_time = time.time()
        results = {}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit all tasks
            future_to_image = {
                executor.submit(
                    self._process_single_image, img_path, light, backends, sat
                ): img_path
                for img_path in image_paths
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_image):
                img_path = future_to_image[future]
                try:
                    result = future.result()
                    if result:
                        results[img_path] = result
                        self.stats["images_processed"] += 1
                        logging.info(f"Processed {img_path}")
                    else:
                        logging.warning(f"Failed to process {img_path}")
                except Exception as e:
                    logging.error(f"Error processing {img_path}: {e}")

        self.stats["total_time"] += time.time() - start_time
        return results

    def _process_single_image(
        self, img_path: str, light: bool, backends: List[str], sat: str
    ) -> Optional[Dict[str, Any]]:
        """Process a single image with fallback backends."""
        for backend in backends:
            try:
                self.stats["backend_attempts"][backend] += 1

                # Check cache first
                cache_name = colors.cache_fname(
                    img_path, backend, light, CACHE_DIR, sat
                )
                cache_file = os.path.join(*cache_name)

                if os.path.isfile(cache_file):
                    self.stats["cache_hits"] += 1
                    return colors.file(cache_file)

                # Generate new colors
                self.stats["cache_misses"] += 1
                result = colors.get(img_path, light, backend, CACHE_DIR, sat)
                self.stats["backend_successes"][backend] += 1
                return result

            except Exception as e:
                logging.debug(f"Backend {backend} failed for {img_path}: {e}")
                continue

        return None

    def find_best_images(
        self,
        img_dir: str,
        count: int = 5,
        recursive: bool = False,
        backends: Optional[List[str]] = None,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Find the best images in a directory based on color quality.

        Args:
            img_dir: Directory to search for images
            count: Number of best images to return
            recursive: Whether to search recursively
            backends: Backends to use for evaluation

        Returns:
            List of tuples (image_path, color_scheme) for the best images
        """
        if recursive:
            images, _ = image.get_image_dir_recursive(img_dir)
        else:
            images, _ = image.get_image_dir(img_dir)
            images = [os.path.join(img_dir, img) for img in images]

        if not images:
            return []

        # Limit the number of images to process for performance
        if len(images) > 20:
            import random

            images = random.sample(images, 20)

        # Process images in parallel
        results = self.process_image_batch(images, backends=backends)

        # Score images based on color diversity and quality
        scored_images = []
        for img_path, color_scheme in results.items():
            if color_scheme:
                score = self._calculate_image_score(color_scheme)
                scored_images.append((score, img_path, color_scheme))

        # Sort by score and return top results
        scored_images.sort(reverse=True)
        return [(img, scheme) for _, img, scheme in scored_images[:count]]

    def _calculate_image_score(self, color_scheme: Dict[str, Any]) -> float:
        """Calculate a quality score for a color scheme."""
        try:
            colors_dict = color_scheme.get("colors", {})
            special = color_scheme.get("special", {})

            # Basic score components
            score = 0.0

            # Color diversity - check how different the colors are
            color_values = list(colors_dict.values())
            if len(color_values) >= 16:
                unique_colors = len(set(color_values))
                score += (unique_colors / 16.0) * 0.3

            # Contrast between background and foreground
            bg = special.get("background", "#000000")
            fg = special.get("foreground", "#ffffff")
            if bg and fg:
                contrast_score = self._calculate_contrast(bg, fg)
                score += contrast_score * 0.4

            # Color saturation diversity
            saturations = []
            for color in color_values[:8]:  # Primary colors
                if color and color.startswith("#"):
                    sat = self._calculate_saturation(color)
                    saturations.append(sat)

            if saturations:
                sat_variance = self._calculate_variance(saturations)
                score += min(sat_variance, 1.0) * 0.3

            return score

        except Exception as e:
            logging.debug(f"Error calculating image score: {e}")
            return 0.0

    def _calculate_contrast(self, color1: str, color2: str) -> float:
        """Calculate contrast ratio between two colors."""
        try:

            def get_luminance(color):
                # Remove # and convert to RGB
                hex_color = color.lstrip("#")
                if len(hex_color) != 6:
                    return 0.5
                r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
                # Convert to relative luminance
                r, g, b = (x / 255.0 for x in (r, g, b))
                r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
                g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
                b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
                return 0.2126 * r + 0.7152 * g + 0.0722 * b

            l1 = get_luminance(color1)
            l2 = get_luminance(color2)
            lighter = max(l1, l2)
            darker = min(l1, l2)
            contrast = (lighter + 0.05) / (darker + 0.05)

            # Normalize to 0-1 range (max contrast is 21:1)
            return min(contrast / 21.0, 1.0)

        except Exception:
            return 0.5

    def _calculate_saturation(self, color: str) -> float:
        """Calculate saturation of a color."""
        try:
            hex_color = color.lstrip("#")
            if len(hex_color) != 6:
                return 0.0
            r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
            r, g, b = r / 255.0, g / 255.0, b / 255.0
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            return (max_val - min_val) / max_val if max_val > 0 else 0.0
        except Exception:
            return 0.0

    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self.stats.copy()

        # Calculate success rates
        if stats["images_processed"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / (
                stats["cache_hits"] + stats["cache_misses"]
            )
            stats["avg_processing_time"] = (
                stats["total_time"] / stats["images_processed"]
            )

        # Backend success rates
        backend_success_rates = {}
        for backend, attempts in stats["backend_attempts"].items():
            if attempts > 0:
                successes = stats["backend_successes"][backend]
                backend_success_rates[backend] = successes / attempts

        stats["backend_success_rates"] = backend_success_rates
        return stats

    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            "images_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_time": 0.0,
            "backend_attempts": defaultdict(int),
            "backend_successes": defaultdict(int),
        }


class ParallelImagePreprocessor:
    """Handles parallel image preprocessing operations."""

    def __init__(self, max_workers: Optional[int] = None):
        """Initialize the parallel preprocessor."""
        self.max_workers = max_workers or min(4, (os.cpu_count() or 1) + 1)

    def preprocess_images(
        self,
        image_paths: List[str],
        target_size: Tuple[int, int] = (256, 256),
        output_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Preprocess multiple images in parallel.

        Args:
            image_paths: List of image paths to preprocess
            target_size: Target size for resizing (width, height)
            output_dir: Directory to save preprocessed images (None for temp)

        Returns:
            Dictionary mapping original paths to preprocessed paths
        """
        if output_dir is None:
            import tempfile

            output_dir = tempfile.mkdtemp(prefix="nu_pywal_preprocess_")

        util.create_dir(output_dir)
        results = {}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_path = {
                executor.submit(
                    self._preprocess_single_image, img_path, target_size, output_dir
                ): img_path
                for img_path in image_paths
            }

            for future in concurrent.futures.as_completed(future_to_path):
                original_path = future_to_path[future]
                try:
                    preprocessed_path = future.result()
                    if preprocessed_path:
                        results[original_path] = preprocessed_path
                except Exception as e:
                    logging.error(f"Error preprocessing {original_path}: {e}")

        return results

    def _preprocess_single_image(
        self, img_path: str, target_size: Tuple[int, int], output_dir: str
    ) -> Optional[str]:
        """Preprocess a single image."""
        try:
            import hashlib

            # Generate unique output filename
            img_hash = hashlib.md5(
                img_path.encode(), usedforsecurity=False
            ).hexdigest()[:8]
            ext = os.path.splitext(img_path)[1] or ".jpg"
            output_path = os.path.join(output_dir, f"preprocessed_{img_hash}{ext}")

            # Skip if already processed
            if os.path.exists(output_path):
                return output_path

            # Use ImageMagick to resize
            cmd = [
                "magick",
                img_path,
                "-resize",
                f"{target_size[0]}x{target_size[1]}!",
                output_path,
            ]
            util.run_command(cmd, timeout=30, capture_output=True)

            if os.path.exists(output_path):
                return output_path
            else:
                logging.warning(f"Failed to preprocess {img_path}")
                return None

        except Exception as e:
            logging.debug(f"Preprocessing failed for {img_path}: {e}")
            return None


def process_directory_parallel(
    img_dir: str,
    light: bool = False,
    recursive: bool = False,
    max_workers: Optional[int] = None,
    find_best: bool = False,
    best_count: int = 5,
) -> Union[Dict[str, Any], List[Tuple[str, Dict[str, Any]]]]:
    """
    Process a directory of images in parallel.

    Args:
        img_dir: Directory containing images
        light: Generate light color schemes
        recursive: Search recursively
        max_workers: Maximum number of worker threads
        find_best: Whether to find and return the best images
        best_count: Number of best images to return (if find_best=True)

    Returns:
        If find_best=True: List of (image_path, color_scheme) tuples for best images
        If find_best=False: Dictionary of all processed images and their color schemes
    """
    processor = ParallelColorProcessor(max_workers=max_workers)

    if find_best:
        return processor.find_best_images(
            img_dir, count=best_count, recursive=recursive
        )
    else:
        if recursive:
            images, _ = image.get_image_dir_recursive(img_dir)
        else:
            images, _ = image.get_image_dir(img_dir)
            images = [os.path.join(img_dir, img) for img in images]

        return processor.process_image_batch(images, light=light)


def benchmark_backends(
    img_path: str, backends: Optional[List[str]] = None, iterations: int = 3
) -> Dict[str, Dict[str, Any]]:
    """
    Benchmark different backends on an image.

    Args:
        img_path: Path to test image
        backends: List of backends to test (None for all)
        iterations: Number of iterations per backend

    Returns:
        Dictionary with benchmark results for each backend
    """
    if backends is None:
        backends = colors.list_backends()

    results = {}
    available_backends = []
    unavailable_backends = []

    # First, check which backends are available
    for backend in backends:
        try:
            # Try to import the backend module to check availability
            __import__(f"pywal.backends.{backend}")
            backend_module = sys.modules[f"pywal.backends.{backend}"]

            # Verify the backend has required methods
            if hasattr(backend_module, "get"):
                available_backends.append(backend)
                logging.info(f"Backend '{backend}' is available for benchmarking")
            else:
                unavailable_backends.append(backend)
                logging.warning(f"Backend '{backend}' missing required 'get' method")

        except ImportError as e:
            unavailable_backends.append(backend)
            logging.warning(f"Backend '{backend}' not available: {e}")
        except Exception as e:
            unavailable_backends.append(backend)
            logging.warning(f"Backend '{backend}' check failed: {e}")

    if not available_backends:
        return {}

    if unavailable_backends:
        pass

    # Benchmark available backends
    for backend in available_backends:
        backend_results = {
            "times": [],
            "success_count": 0,
            "error_count": 0,
            "avg_time": 0.0,
            "success_rate": 0.0,
            "status": "available",
        }

        logging.info(
            f"Benchmarking backend '{backend}' with {iterations} iterations..."
        )

        for i in range(iterations):
            start_time = time.time()
            try:
                colors.get(img_path, backend=backend)
                execution_time = time.time() - start_time
                backend_results["times"].append(execution_time)
                backend_results["success_count"] += 1
                logging.debug(
                    f"Backend {backend} iteration {i+1}: {execution_time:.3f}s"
                )
            except Exception as e:
                backend_results["error_count"] += 1
                logging.debug(f"Backend {backend} iteration {i+1} failed: {e}")

        if backend_results["times"]:
            backend_results["avg_time"] = sum(backend_results["times"]) / len(
                backend_results["times"]
            )
            backend_results["min_time"] = min(backend_results["times"])
            backend_results["max_time"] = max(backend_results["times"])

        backend_results["success_rate"] = backend_results["success_count"] / iterations
        results[backend] = backend_results

        if backend_results["success_count"] > 0:
            logging.info(
                f"Backend '{backend}': {backend_results['avg_time']:.3f}s avg, "
                f"{backend_results['success_rate']:.1%} success rate"
            )
        else:
            logging.warning(f"Backend '{backend}' failed all iterations")

    # Add unavailable backends to results for completeness
    for backend in unavailable_backends:
        results[backend] = {
            "times": [],
            "success_count": 0,
            "error_count": iterations,
            "avg_time": 0.0,
            "success_rate": 0.0,
            "status": "unavailable",
        }

    return results
