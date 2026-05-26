"""
inference_cache.py — Hash-based caching for repeated image predictions.

Caches prediction results keyed by image hash to avoid redundant computation
for identical or near-identical images. Useful when:
- Users retake the same image without meaningful changes
- Batch processing includes duplicate images
- A/B testing sends the same image through multiple model versions

Cache Strategy
--------------
- Primary key: SHA-256 hash of resized, normalized image bytes
- Secondary: Perceptual hash (pHash) for near-duplicate detection
- Tertiary: Average hash (aHash) for fast pre-filtering
- TTL: Configurable, default 24 hours
- Max size: LRU eviction when cache exceeds size limit
- Persistent: Optional disk-backed cache for cross-session persistence

Feature Extraction Cache
------------------------
Additionally caches intermediate feature extraction results to speed up
repeated feature extraction with the same image but different model configs.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

log = logging.getLogger("anemialens.cache")


@dataclass
class CacheEntry:
    """A single cached prediction result."""
    image_hash: str
    phash: int
    prediction: dict[str, Any]
    timestamp: float
    hit_count: int = 0
    model_version: str = ""
    quality_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class FeatureCacheEntry:
    """Cached feature extraction result."""
    image_hash: str
    features: dict[str, float]
    timestamp: float
    hit_count: int = 0
    config_hash: str = ""  # Hash of feature extraction config


@dataclass(frozen=True)
class CacheStats:
    """Comprehensive cache statistics."""
    size: int
    max_size: int
    hits: int
    misses: int
    hit_rate: float
    ttl_seconds: int
    oldest_entry_age_seconds: float
    newest_entry_age_seconds: float
    total_predictions_cached: int
    total_features_cached: int
    evictions: int
    disk_persisted: bool
    disk_path: str | None
    disk_entries: int


class InferenceCache:
    """
    LRU cache for image prediction results.

    Usage
    -----
    cache = InferenceCache(max_size=500, ttl_seconds=86400)
    key = cache.compute_hash(image)
    result = cache.get(key, phash)
    if result is not None:
        return result  # Cache hit!
    # ... run prediction ...
    cache.put(key, phash, prediction, model_version="v8")
    """

    def __init__(
        self,
        max_size: int = 500,
        ttl_seconds: int = 86400,
        phash_threshold: int = 8,
        persist_path: str | Path | None = None,
    ) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.phash_threshold = phash_threshold  # Max Hamming distance for near-duplicate
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._phash_index: dict[int, str] = {}  # phash → hash_key
        self._ahash_index: dict[int, str] = {}  # ahash → hash_key (fast pre-filter)
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._total_predictions_cached = 0
        self._total_features_cached = 0

        # Feature extraction cache
        self._feature_cache: dict[str, FeatureCacheEntry] = {}

        # Persistent storage
        self._persist_path = Path(persist_path) if persist_path else None
        self._disk_entries = 0
        if self._persist_path and self._persist_path.exists():
            self._load_from_disk()

    def compute_hash(self, image: Image.Image) -> str:
        """
        Compute SHA-256 hash of image content.

        Uses resized, normalized representation for consistent hashing.
        """
        # Resize to fixed size for consistent hashing
        resized = image.resize((64, 64)).convert("RGB")
        data = np.asarray(resized, dtype=np.uint8).tobytes()
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def compute_phash(image: Image.Image) -> int:
        """
        Compute perceptual hash (simplified DCT-based).

        Returns a 64-bit integer hash.
        """
        gray = image.resize((32, 32)).convert("L")
        pixels = np.asarray(gray, dtype=np.float64)

        # Simple DCT approximation using mean thresholding
        mean_val = pixels.mean()
        bits = (pixels > mean_val).flatten()

        # Convert bit array to integer
        phash = 0
        for i, bit in enumerate(bits[:64]):
            if bit:
                phash |= (1 << i)

        return phash

    @staticmethod
    def compute_ahash(image: Image.Image) -> int:
        """
        Compute average hash (aHash) for fast pre-filtering.

        Simpler and faster than phash, good for quick rejection.
        Returns a 64-bit integer hash.
        """
        gray = image.resize((8, 8)).convert("L")
        pixels = np.asarray(gray, dtype=np.float64)
        mean_val = pixels.mean()
        bits = (pixels > mean_val).flatten()

        ahash = 0
        for i, bit in enumerate(bits):
            if bit:
                ahash |= (1 << i)

        return ahash

    def get(
        self,
        image_hash: str,
        phash: int | None = None,
        ahash: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Look up a cached prediction.

        First tries exact hash match, then falls back to perceptual hash
        near-duplicate detection, then average hash for fast pre-filtering.

        Parameters
        ----------
        image_hash : SHA-256 hash of the image
        phash : Perceptual hash for near-duplicate detection
        ahash : Average hash for fast pre-filtering

        Returns
        -------
        Cached prediction dict or None
        """
        now = time.time()

        # Try exact match
        if image_hash in self._cache:
            entry = self._cache[image_hash]
            # Check TTL
            if now - entry.timestamp > self.ttl_seconds:
                self._remove(image_hash)
                self.misses += 1
                return None
            entry.hit_count += 1
            self.hits += 1
            # Move to end (most recently used)
            self._cache.move_to_end(image_hash)
            log.debug(
                "Cache HIT for image %s (hit #%d)",
                image_hash[:8], entry.hit_count,
            )
            return entry.prediction

        # Try near-duplicate via phash
        if phash is not None:
            for stored_phash, stored_hash in self._phash_index.items():
                if self._hamming_distance(phash, stored_phash) <= self.phash_threshold:
                    if stored_hash in self._cache:
                        entry = self._cache[stored_hash]
                        if now - entry.timestamp > self.ttl_seconds:
                            self._remove(stored_hash)
                            continue
                        entry.hit_count += 1
                        self.hits += 1
                        self._cache.move_to_end(stored_hash)
                        log.debug(
                            "Cache HIT (near-duplicate phash) for phash %x", phash
                        )
                        return entry.prediction

        # Fast pre-filter via ahash (wider threshold for speed)
        if ahash is not None:
            for stored_ahash, stored_hash in self._ahash_index.items():
                if self._hamming_distance(ahash, stored_ahash) <= 4:  # Tighter threshold for ahash
                    if stored_hash in self._cache:
                        entry = self._cache[stored_hash]
                        if now - entry.timestamp > self.ttl_seconds:
                            self._remove(stored_hash)
                            continue
                        entry.hit_count += 1
                        self.hits += 1
                        self._cache.move_to_end(stored_hash)
                        log.debug(
                            "Cache HIT (near-duplicate ahash) for ahash %x", ahash
                        )
                        return entry.prediction

        self.misses += 1
        return None

    def put(
        self,
        image_hash: str,
        phash: int | dict[str, Any],
        prediction: dict[str, Any] | None = None,
        model_version: str = "",
        quality_metrics: dict[str, float] | None = None,
        ahash: int | None = None,
    ) -> None:
        """
        Store a prediction in the cache.

        Parameters
        ----------
        image_hash : SHA-256 hash of the image
        phash : Perceptual hash
        prediction : Prediction result dict
        model_version : Version string of the model used
        quality_metrics : Quality metrics at prediction time
        ahash : Average hash for fast pre-filtering
        """
        if prediction is None and isinstance(phash, dict):
            prediction = phash
            phash = 0

        if prediction is None:
            raise ValueError("prediction payload is required when phash is provided explicitly")

        now = time.time()

        # Evict if at capacity
        if image_hash not in self._cache and len(self._cache) >= self.max_size:
            self._evict_lru()

        entry = CacheEntry(
            image_hash=image_hash,
            phash=int(phash),
            prediction=prediction,
            timestamp=now,
            model_version=model_version,
            quality_metrics=quality_metrics or {},
        )

        self._cache[image_hash] = entry
        self._cache.move_to_end(image_hash)
        self._phash_index[phash] = image_hash
        if ahash is not None:
            self._ahash_index[ahash] = image_hash

        self._total_predictions_cached += 1

        # Persist to disk if configured
        if self._persist_path:
            self._persist_to_disk()

        log.debug("Cache PUT for image %s", image_hash[:8])

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._phash_index.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> CacheStats:
        """Return comprehensive cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / max(total, 1)
        now = time.time()

        oldest_age = 0.0
        newest_age = 0.0
        if self._cache:
            ages = [now - entry.timestamp for entry in self._cache.values()]
            oldest_age = max(ages)
            newest_age = min(ages)

        return CacheStats(
            size=len(self._cache),
            max_size=self.max_size,
            hits=self.hits,
            misses=self.misses,
            hit_rate=round(hit_rate, 3),
            ttl_seconds=self.ttl_seconds,
            oldest_entry_age_seconds=round(oldest_age, 1),
            newest_entry_age_seconds=round(newest_age, 1),
            total_predictions_cached=self._total_predictions_cached,
            total_features_cached=self._total_features_cached,
            evictions=self.evictions,
            disk_persisted=self._persist_path is not None,
            disk_path=str(self._persist_path) if self._persist_path else None,
            disk_entries=self._disk_entries,
        )

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = time.time()
        expired = [
            key for key, entry in self._cache.items()
            if now - entry.timestamp > self.ttl_seconds
        ]
        for key in expired:
            self._remove(key)
        return len(expired)

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _remove(self, key: str) -> None:
        """Remove an entry from both cache and hash indices."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._phash_index.pop(entry.phash, None)
            # Remove from ahash index too
            ahash_to_remove = None
            for ahash_val, stored_hash in list(self._ahash_index.items()):
                if stored_hash == key:
                    ahash_to_remove = ahash_val
                    break
            if ahash_to_remove is not None:
                self._ahash_index.pop(ahash_to_remove, None)

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._phash_index.pop(entry.phash, None)
            # Remove from ahash index
            ahash_to_remove = None
            for ahash_val, stored_hash in list(self._ahash_index.items()):
                if stored_hash == key:
                    ahash_to_remove = ahash_val
                    break
            if ahash_to_remove is not None:
                self._ahash_index.pop(ahash_to_remove, None)
            self.evictions += 1
            log.debug("Cache LRU eviction: %s", key[:8])

    @staticmethod
    def _hamming_distance(a: int, b: int) -> int:
        """Count differing bits between two integers."""
        xor = a ^ b
        return bin(xor).count("1")

    # ──────────────────────────────────────────────────────────────────────
    # Disk persistence
    # ──────────────────────────────────────────────────────────────────────

    def _persist_to_disk(self) -> None:
        """Serialize cache to disk for cross-session persistence."""
        if not self._persist_path:
            return

        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "entries": [
                    {
                        "image_hash": e.image_hash, "phash": e.phash,
                        "prediction": e.prediction, "timestamp": e.timestamp,
                        "hit_count": e.hit_count, "model_version": e.model_version,
                        "quality_metrics": e.quality_metrics,
                    }
                    for e in self._cache.values()
                ],
                "metadata": {
                    "hits": self.hits, "misses": self.misses,
                    "evictions": self.evictions,
                    "total_predictions_cached": self._total_predictions_cached,
                    "saved_at": time.time(),
                },
            }
            temp_path = self._persist_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f, default=str)
            temp_path.replace(self._persist_path)
            self._disk_entries = len(data["entries"])
        except Exception as e:
            log.warning("Failed to persist cache to disk: %s", e)

    def _load_from_disk(self) -> None:
        """Load cache from disk if available."""
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
            now = time.time()
            loaded = 0
            for entry_data in data.get("entries", []):
                if now - entry_data["timestamp"] > self.ttl_seconds:
                    continue
                entry = CacheEntry(
                    image_hash=entry_data["image_hash"], phash=entry_data["phash"],
                    prediction=entry_data["prediction"], timestamp=entry_data["timestamp"],
                    hit_count=entry_data.get("hit_count", 0),
                    model_version=entry_data.get("model_version", ""),
                    quality_metrics=entry_data.get("quality_metrics", {}),
                )
                self._cache[entry.image_hash] = entry
                self._phash_index[entry.phash] = entry.image_hash
                loaded += 1
            metadata = data.get("metadata", {})
            self.hits = metadata.get("hits", 0)
            self.misses = metadata.get("misses", 0)
            self.evictions = metadata.get("evictions", 0)
            self._total_predictions_cached = metadata.get("total_predictions_cached", loaded)
            self._disk_entries = loaded
        except Exception as e:
            log.warning("Failed to load cache from disk: %s", e)

    # ──────────────────────────────────────────────────────────────────────
    # Feature extraction cache
    # ──────────────────────────────────────────────────────────────────────

    def get_cached_features(self, image_hash: str, config_hash: str = "") -> dict[str, float] | None:
        """Look up cached feature extraction result."""
        key = f"{image_hash}:{config_hash}"
        if key in self._feature_cache:
            entry = self._feature_cache[key]
            if time.time() - entry.timestamp > self.ttl_seconds:
                del self._feature_cache[key]
                return None
            entry.hit_count += 1
            return entry.features
        return None

    def cache_features(self, image_hash: str, features: dict[str, float], config_hash: str = "") -> None:
        """Store feature extraction result in cache."""
        key = f"{image_hash}:{config_hash}"
        if key not in self._feature_cache and len(self._feature_cache) >= 200:
            oldest_key = min(self._feature_cache, key=lambda k: self._feature_cache[k].timestamp)
            del self._feature_cache[oldest_key]
        self._feature_cache[key] = FeatureCacheEntry(
            image_hash=image_hash, features=features, timestamp=time.time(), config_hash=config_hash,
        )
        self._total_features_cached += 1

    def clear_features(self) -> None:
        """Clear all cached feature extraction results."""
        self._feature_cache.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────

_default_cache: InferenceCache | None = None


def get_inference_cache(
    max_size: int = 500,
    ttl_seconds: int = 86400,
) -> InferenceCache:
    """Get or create the singleton inference cache."""
    global _default_cache
    if _default_cache is None:
        _default_cache = InferenceCache(max_size=max_size, ttl_seconds=ttl_seconds)
    return _default_cache


def cache_prediction(
    image: Image.Image,
    prediction: dict[str, Any],
    model_version: str = "",
    quality_metrics: dict[str, float] | None = None,
) -> None:
    """Convenience function to cache a prediction."""
    cache = get_inference_cache()
    image_hash = cache.compute_hash(image)
    phash = cache.compute_phash(image)
    ahash = cache.compute_ahash(image)
    cache.put(image_hash, phash, prediction, model_version, quality_metrics, ahash)


def get_cached_prediction(
    image: Image.Image,
) -> dict[str, Any] | None:
    """Convenience function to look up a cached prediction."""
    cache = get_inference_cache()
    image_hash = cache.compute_hash(image)
    phash = cache.compute_phash(image)
    ahash = cache.compute_ahash(image)
    return cache.get(image_hash, phash, ahash)


def cache_feature_extraction(
    image: Image.Image,
    features: dict[str, float],
    config_hash: str = "",
) -> None:
    """Convenience function to cache feature extraction results."""
    cache = get_inference_cache()
    image_hash = cache.compute_hash(image)
    cache.cache_features(image_hash, features, config_hash)


def get_cached_features(
    image: Image.Image,
    config_hash: str = "",
) -> dict[str, float] | None:
    """Convenience function to look up cached feature extraction."""
    cache = get_inference_cache()
    image_hash = cache.compute_hash(image)
    return cache.get_cached_features(image_hash, config_hash)


def _compute_image_hash(image: Image.Image) -> str:
    """Legacy helper preserved for existing tests and scripts."""
    return get_inference_cache().compute_hash(image)
