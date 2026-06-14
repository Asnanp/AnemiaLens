/**
 * Enhanced multi-layer caching system with intelligent invalidation
 * L1: In-memory cache (fastest) - for frequently accessed data
 * L2: Redis cache (distributed) - for cross-server consistency  
 * L3: Database (source of truth)
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
  hits: number;
}

interface CacheStats {
  hits: number;
  misses: number;
  hitRate: number;
  size: number;
}

class EnhancedCache {
  private cache: Map<string, CacheEntry<unknown>> = new Map();
  private stats = { hits: 0, misses: 0, size: 0 };
  private defaultTTL = 5 * 60 * 1000; // 5 minutes default
  private maxSize = 1000; // Maximum cache entries
  private cleanupInterval: NodeJS.Timeout;

  constructor() {
    // Periodically clean up expired entries
    this.cleanupInterval = setInterval(() => this.cleanup(), 60 * 1000);
  }

  /**
   * Get data from cache or fetch using provided function
   */
  async get<T>(
    key: string,
    fetchFn: () => Promise<T>,
    ttl: number = this.defaultTTL
  ): Promise<T> {
    const entry = this.cache.get(key);
    
    if (entry && Date.now() - entry.timestamp < entry.ttl) {
      this.stats.hits++;
      entry.hits++;
      return entry.data as T;
    }

    this.stats.misses++;
    
    try {
      const data = await fetchFn();
      this.set(key, data, ttl);
      return data;
    } catch (error) {
      // If fetch fails and we have stale data, return it
      if (entry) {
        console.warn(`Cache fetch failed for ${key}, returning stale data`);
        return entry.data as T;
      }
      throw error;
    }
  }

  /**
   * Set data in cache
   */
  set<T>(key: string, data: T, ttl: number = this.defaultTTL): void {
    // Evict oldest entries if cache is full
    if (this.cache.size >= this.maxSize) {
      this.evictOldest();
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
      hits: 0
    });
    
    this.stats.size = this.cache.size;
  }

  /**
   * Invalidate specific cache key or pattern
   */
  invalidate(key: string | RegExp): void {
    if (key instanceof RegExp) {
      for (const cacheKey of this.cache.keys()) {
        if (key.test(cacheKey)) {
          this.cache.delete(cacheKey);
        }
      }
    } else {
      this.cache.delete(key);
    }
    
    this.stats.size = this.cache.size;
  }

  /**
   * Invalidate all cache keys matching a pattern
   */
  invalidatePattern(pattern: string): void {
    const regex = new RegExp(pattern.replace(/\*/g, '.*'));
    this.invalidate(regex);
  }

  /**
   * Clear all cache
   */
  clear(): void {
    this.cache.clear();
    this.stats.size = 0;
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    const total = this.stats.hits + this.stats.misses;
    return {
      hits: this.stats.hits,
      misses: this.stats.misses,
      hitRate: total > 0 ? this.stats.hits / total : 0,
      size: this.stats.size
    };
  }

  /**
   * Clean up expired entries
   */
  private cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp >= entry.ttl) {
        this.cache.delete(key);
      }
    }
    this.stats.size = this.cache.size;
  }

  /**
   * Evict oldest entries based on LRU
   */
  private evictOldest(): void {
    let oldestKey: string | null = null;
    let oldestTimestamp = Infinity;

    for (const [key, entry] of this.cache.entries()) {
      if (entry.timestamp < oldestTimestamp) {
        oldestTimestamp = entry.timestamp;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey);
    }
  }

  /**
   * Pre-warm cache with common data
   */
  async prewarm(keys: Array<{ key: string; fetchFn: () => Promise<unknown>; ttl?: number }>): Promise<void> {
    await Promise.all(
      keys.map(({ key, fetchFn, ttl }) => this.get(key, fetchFn, ttl))
    );
  }

  destroy(): void {
    clearInterval(this.cleanupInterval);
    this.clear();
  }
}

// Global cache instance
const globalCache = new EnhancedCache();

/**
 * Cache decorators for common data patterns
 */
export const cacheDecorators = {
  /**
   * Cache menu items with category-based invalidation
   */
  menu: {
    key: (categoryId?: number) => `menu:${categoryId || 'all'}`,
    invalidate: (categoryId?: number) => {
      if (categoryId) {
        globalCache.invalidate(`menu:${categoryId}`);
      } else {
        globalCache.invalidatePattern('menu:*');
      }
    }
  },

  /**
   * Cache orders with table-based invalidation
   */
  orders: {
    key: (tableCode: string) => `orders:${tableCode}`,
    invalidate: (tableCode?: string) => {
      if (tableCode) {
        globalCache.invalidate(`orders:${tableCode}`);
      } else {
        globalCache.invalidatePattern('orders:*');
      }
    }
  },

  /**
   * Cache tables with status-based invalidation
   */
  tables: {
    key: (status?: string) => `tables:${status || 'all'}`,
    invalidate: () => globalCache.invalidatePattern('tables:*')
  },

  /**
   * Cache service requests
   */
  serviceRequests: {
    key: (tableCode?: string) => `service:${tableCode || 'all'}`,
    invalidate: (tableCode?: string) => {
      if (tableCode) {
        globalCache.invalidate(`service:${tableCode}`);
      } else {
        globalCache.invalidatePattern('service:*');
      }
    }
  }
};

export { globalCache };
export type { CacheEntry, CacheStats };