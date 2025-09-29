"""
Advanced caching system for nu-pywal.

This module provides enhanced caching capabilities including cache cleanup,
analytics, compression, and performance optimizations.
"""

import gzip
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import util
from .settings import CACHE_DIR, __cache_version__, __version__


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""

    key: str
    file_path: str
    size: int
    created_time: float
    last_accessed: float
    access_count: int = 0
    backend: str = "unknown"
    image_hash: str = ""
    compressed: bool = False


@dataclass
class CacheStats:
    """Cache statistics and analytics."""

    total_entries: int = 0
    total_size: int = 0
    hit_count: int = 0
    miss_count: int = 0
    cleanup_count: int = 0
    compression_saved: int = 0
    avg_access_time: float = 0.0
    most_accessed: List[Tuple[str, int]] = field(default_factory=list)
    backend_usage: Dict[str, int] = field(default_factory=dict)


class AdvancedCache:
    """Advanced caching system with analytics and optimization."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        """Initialize the advanced cache system."""
        self.cache_dir = cache_dir
        self.schemes_dir = os.path.join(cache_dir, "schemes")
        self.db_path = os.path.join(cache_dir, "cache.db")
        self.stats = CacheStats()

        # Ensure cache directories exist
        util.create_dir(self.schemes_dir)
        self._init_database()

    def _init_database(self):
        """Initialize the cache database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        file_path TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        created_time REAL NOT NULL,
                        last_accessed REAL NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        backend TEXT DEFAULT 'unknown',
                        image_hash TEXT DEFAULT '',
                        compressed INTEGER DEFAULT 0
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache_stats (
                        id INTEGER PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        hit_count INTEGER NOT NULL,
                        miss_count INTEGER NOT NULL,
                        total_entries INTEGER NOT NULL,
                        total_size INTEGER NOT NULL
                    )
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_accessed
                    ON cache_entries(last_accessed)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_access_count
                    ON cache_entries(access_count DESC)
                """)

        except sqlite3.Error as e:
            logging.warning(f"Cache database initialization failed: {e}")

    def generate_cache_key(
        self, img_path: str, backend: str, light: bool, sat: str = ""
    ) -> str:
        """Generate a robust cache key for an image."""
        try:
            # Get file stats for cache invalidation
            stat = os.stat(img_path)
            file_size = stat.st_size
            file_mtime = stat.st_mtime

            # Create image hash for deduplication
            image_hash = self._get_image_hash(img_path)

            # Combine all factors into cache key
            key_components = [
                image_hash,
                backend,
                "light" if light else "dark",
                sat or "0",
                str(file_size),
                str(int(file_mtime)),
                __cache_version__,
            ]

            cache_key = "_".join(key_components)
            return hashlib.sha256(cache_key.encode()).hexdigest()[:16]

        except OSError as e:
            logging.debug(f"Failed to generate cache key for {img_path}: {e}")
            # Fallback to simple key
            return hashlib.md5(
                f"{img_path}_{backend}_{light}_{sat}".encode(), usedforsecurity=False
            ).hexdigest()[:16]

    def _get_image_hash(self, img_path: str, chunk_size: int = 8192) -> str:
        """Generate a hash of the image content for deduplication."""
        try:
            hasher = hashlib.md5(usedforsecurity=False)
            with open(img_path, "rb") as f:
                # Hash first and last chunks for performance
                chunk = f.read(chunk_size)
                if chunk:
                    hasher.update(chunk)

                # Seek to end and read last chunk
                f.seek(-min(chunk_size, f.tell()), 2)
                chunk = f.read(chunk_size)
                if chunk:
                    hasher.update(chunk)

            return hasher.hexdigest()[:12]
        except OSError:
            return "unknown"

    def get(
        self, cache_key: str, img_path: str = "", backend: str = "unknown"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached color scheme."""
        start_time = time.time()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT file_path, compressed, access_count FROM cache_entries WHERE key = ?",
                    (cache_key,),
                )
                row = cursor.fetchone()

                if not row:
                    self.stats.miss_count += 1
                    return None

                file_path, compressed, access_count = row

                # Check if file exists
                if not os.path.exists(file_path):
                    self._remove_entry(cache_key)
                    self.stats.miss_count += 1
                    return None

                # Load the cached data
                try:
                    if compressed:
                        with gzip.open(file_path, "rt", encoding="utf-8") as f:
                            data = json.load(f)
                    else:
                        with open(file_path, encoding="utf-8") as f:
                            data = json.load(f)

                    # Update access statistics
                    current_time = time.time()
                    conn.execute(
                        "UPDATE cache_entries SET last_accessed = ?, access_count = ? WHERE key = ?",
                        (current_time, access_count + 1, cache_key),
                    )

                    self.stats.hit_count += 1
                    self.stats.avg_access_time = (
                        self.stats.avg_access_time + (time.time() - start_time)
                    ) / 2

                    logging.info(f"Cache hit for {cache_key}")
                    return data

                except (OSError, json.JSONDecodeError, gzip.BadGzipFile) as e:
                    logging.warning(f"Failed to load cached data for {cache_key}: {e}")
                    self._remove_entry(cache_key)
                    self.stats.miss_count += 1
                    return None

        except sqlite3.Error as e:
            logging.warning(f"Cache database error: {e}")
            self.stats.miss_count += 1
            return None

    def put(
        self,
        cache_key: str,
        data: Dict[str, Any],
        img_path: str = "",
        backend: str = "unknown",
        compress: bool = True,
    ) -> bool:
        """Store a color scheme in the cache."""
        try:
            # Generate file path
            cache_file = os.path.join(self.schemes_dir, f"{cache_key}.json")
            if compress:
                cache_file += ".gz"

            # Save the data
            if compress:
                with gzip.open(cache_file, "wt", encoding="utf-8") as f:
                    json.dump(data, f, separators=(",", ":"))
            else:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

            # Get file info
            stat = os.stat(cache_file)
            current_time = time.time()
            image_hash = self._get_image_hash(img_path) if img_path else ""

            # Store metadata in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO cache_entries
                       (key, file_path, size, created_time, last_accessed,
                        access_count, backend, image_hash, compressed)
                       VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                    (
                        cache_key,
                        cache_file,
                        stat.st_size,
                        current_time,
                        current_time,
                        backend,
                        image_hash,
                        1 if compress else 0,
                    ),
                )

            self.stats.total_entries += 1
            self.stats.total_size += stat.st_size

            if compress:
                # Estimate compression savings
                uncompressed_size = len(json.dumps(data, indent=2))
                self.stats.compression_saved += max(0, uncompressed_size - stat.st_size)

            logging.debug(f"Cached {cache_key} ({stat.st_size} bytes)")
            return True

        except (OSError, sqlite3.Error, gzip.BadGzipFile, TypeError, ValueError) as e:
            logging.warning(f"Failed to cache {cache_key}: {e}")
            return False

    def cleanup(
        self,
        max_size_mb: int = 100,
        max_age_days: int = 30,
        keep_most_accessed: int = 50,
    ) -> int:
        """Clean up old or large cache entries."""
        cleanup_count = 0
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        max_size_bytes = max_size_mb * 1024 * 1024

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current cache statistics
                cursor = conn.execute("SELECT SUM(size), COUNT(*) FROM cache_entries")
                total_size, total_entries = cursor.fetchone()
                total_size = total_size or 0
                total_entries = total_entries or 0

                if total_size <= max_size_bytes and total_entries < 1000:
                    return 0

                # Get candidates for cleanup (exclude most accessed)
                cursor = conn.execute(
                    """
                    SELECT key, file_path, size, created_time, last_accessed, access_count
                    FROM cache_entries
                    WHERE key NOT IN (
                        SELECT key FROM cache_entries
                        ORDER BY access_count DESC, last_accessed DESC
                        LIMIT ?
                    )
                    ORDER BY last_accessed ASC, access_count ASC
                """,
                    (keep_most_accessed,),
                )

                candidates = cursor.fetchall()
                size_freed = 0

                for (
                    key,
                    file_path,
                    size,
                    _created_time,
                    last_accessed,
                    _access_count,
                ) in candidates:
                    should_remove = False

                    # Remove if too old
                    if current_time - last_accessed > max_age_seconds:
                        should_remove = True
                        logging.debug(f"Removing old cache entry: {key}")

                    # Remove if cache is too large
                    elif total_size - size_freed > max_size_bytes:
                        should_remove = True
                        logging.debug(f"Removing cache entry for size: {key}")

                    if should_remove:
                        if self._remove_entry(key, file_path):
                            cleanup_count += 1
                            size_freed += size

                self.stats.cleanup_count += cleanup_count
                logging.info(
                    f"Cache cleanup: removed {cleanup_count} entries, freed {size_freed/1024/1024:.1f}MB"
                )

        except sqlite3.Error as e:
            logging.warning(f"Cache cleanup failed: {e}")

        return cleanup_count

    def _remove_entry(self, key: str, file_path: str = "") -> bool:
        """Remove a cache entry and its file."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if not file_path:
                    cursor = conn.execute(
                        "SELECT file_path FROM cache_entries WHERE key = ?", (key,)
                    )
                    row = cursor.fetchone()
                    if row:
                        file_path = row[0]

                # Remove from database
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))

                # Remove file
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)

                return True

        except (sqlite3.Error, OSError) as e:
            logging.debug(f"Failed to remove cache entry {key}: {e}")
            return False

    def get_analytics(self) -> CacheStats:
        """Get detailed cache analytics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update current stats
                cursor = conn.execute(
                    "SELECT COUNT(*), SUM(size), AVG(access_count) FROM cache_entries"
                )
                count, total_size, avg_access = cursor.fetchone()

                self.stats.total_entries = count or 0
                self.stats.total_size = total_size or 0

                # Most accessed entries
                cursor = conn.execute(
                    "SELECT key, access_count FROM cache_entries ORDER BY access_count DESC LIMIT 10"
                )
                self.stats.most_accessed = cursor.fetchall()

                # Backend usage statistics
                cursor = conn.execute(
                    "SELECT backend, COUNT(*) FROM cache_entries GROUP BY backend"
                )
                self.stats.backend_usage = dict(cursor.fetchall())

        except (sqlite3.Error, Exception) as e:
            logging.warning(f"Failed to get cache analytics: {e}")

        return self.stats

    def deduplicate(self) -> int:
        """Remove duplicate cache entries based on image hash."""
        duplicates_removed = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Find entries with same image hash but different keys
                cursor = conn.execute("""
                    SELECT image_hash, COUNT(*) as count
                    FROM cache_entries
                    WHERE image_hash != ''
                    GROUP BY image_hash
                    HAVING count > 1
                """)

                for image_hash, _count in cursor.fetchall():
                    # Keep the most recently accessed entry
                    duplicate_cursor = conn.execute(
                        """
                        SELECT key, file_path, last_accessed
                        FROM cache_entries
                        WHERE image_hash = ?
                        ORDER BY last_accessed DESC
                    """,
                        (image_hash,),
                    )

                    entries = duplicate_cursor.fetchall()
                    # Keep the first (most recent), remove the rest
                    for key, file_path, _ in entries[1:]:
                        if self._remove_entry(key, file_path):
                            duplicates_removed += 1

                logging.info(
                    f"Deduplication: removed {duplicates_removed} duplicate entries"
                )

        except sqlite3.Error as e:
            logging.warning(f"Cache deduplication failed: {e}")

        return duplicates_removed

    def export_cache_info(self, output_file: str) -> bool:
        """Export cache information to a JSON file."""
        try:
            analytics = self.get_analytics()

            cache_info = {
                "version": __version__,
                "cache_version": __cache_version__,
                "timestamp": time.time(),
                "stats": {
                    "total_entries": analytics.total_entries,
                    "total_size_mb": analytics.total_size / (1024 * 1024),
                    "hit_rate": analytics.hit_count
                    / max(1, analytics.hit_count + analytics.miss_count),
                    "avg_access_time_ms": analytics.avg_access_time * 1000,
                    "compression_saved_mb": analytics.compression_saved / (1024 * 1024),
                    "cleanup_count": analytics.cleanup_count,
                },
                "backend_usage": analytics.backend_usage,
                "most_accessed": analytics.most_accessed[:10],
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(cache_info, f, indent=2)

            return True

        except (OSError, sqlite3.Error) as e:
            logging.error(f"Failed to export cache info: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all cache entries."""
        try:
            # Remove all files
            if os.path.exists(self.schemes_dir):
                shutil.rmtree(self.schemes_dir)
                util.create_dir(self.schemes_dir)

            # Clear database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries")
                conn.execute("DELETE FROM cache_stats")

            # Reset stats
            self.stats = CacheStats()

            logging.info("Cache cleared successfully")
            return True

        except (OSError, sqlite3.Error) as e:
            logging.error(f"Failed to clear cache: {e}")
            return False


# Global cache instance
_cache_instance: Optional[AdvancedCache] = None


def get_cache() -> AdvancedCache:
    """Get the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AdvancedCache()
    return _cache_instance


def cache_get(
    img_path: str, backend: str, light: bool, sat: str = ""
) -> Optional[Dict[str, Any]]:
    """Get cached color scheme using the advanced cache."""
    cache = get_cache()
    cache_key = cache.generate_cache_key(img_path, backend, light, sat)
    return cache.get(cache_key, img_path, backend)


def cache_put(
    img_path: str, backend: str, light: bool, data: Dict[str, Any], sat: str = ""
) -> bool:
    """Store color scheme in the advanced cache."""
    cache = get_cache()
    cache_key = cache.generate_cache_key(img_path, backend, light, sat)
    return cache.put(cache_key, data, img_path, backend)


def cache_cleanup_cli() -> int:
    """CLI command for cache cleanup."""
    cache = get_cache()

    removed = cache.cleanup()

    if removed > 0:
        pass
    else:
        pass

    # Show analytics
    cache.get_analytics()

    return 0


def cache_info_cli() -> int:
    """CLI command for cache information."""
    cache = get_cache()
    stats = cache.get_analytics()

    if stats.hit_count + stats.miss_count > 0:
        stats.hit_count / (stats.hit_count + stats.miss_count)

    if stats.avg_access_time > 0:
        pass

    if stats.compression_saved > 0:
        pass

    for _backend, _count in stats.backend_usage.items():
        pass

    if stats.most_accessed:
        for _key, _count in stats.most_accessed[:5]:
            pass

    return 0
