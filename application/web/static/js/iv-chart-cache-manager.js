// static/js/iv-chart-cache-manager.js
/**
 * 客户端数据缓存管理器 - 负责 ECharts 所需的首访JSON数据缓存
 */

class IVChartCacheManager {
  constructor() {
    this.cacheName = 'iv-chart-json-cache-v1';
    this.memoryCache = new Map(); // 内存级缓存
    this.useCacheAPI = 'caches' in window;
    
    console.log(`[CacheManager] 缓存管理器初始化. 支持Cache API: ${this.useCacheAPI}`);
  }

  /**
   * 生成缓存Key (必须包含时间戳或文件Hash等防脱轨标记，以便在重处理后更新)
   */
  generateKey(jsonUrl) {
    try {
      const urlObj = new URL(jsonUrl, window.location.origin);
      // 保留完整 query，包含可能代表版本号的 cache buster
      return urlObj.toString();
    } catch (e) {
      return jsonUrl;
    }
  }

  /**
   * 获取缓存数据或发起请求
   */
  async fetchWithCache(jsonUrl) {
    const cacheKey = this.generateKey(jsonUrl);

    // 1. 优先内存缓冲
    if (this.memoryCache.has(cacheKey)) {
      // console.log(`[CacheManager] 命中内存缓存: ${cacheKey}`);
      return this.memoryCache.get(cacheKey);
    }

    // 2. 查询浏览器 CacheStorage
    if (this.useCacheAPI) {
      try {
        const cache = await caches.open(this.cacheName);
        const cachedResponse = await cache.match(cacheKey);
        
        if (cachedResponse) {
          // console.log(`[CacheManager] 命中 CacheStorage: ${cacheKey}`);
          const jsonData = await cachedResponse.json();
          this.memoryCache.set(cacheKey, jsonData);
          return jsonData;
        }
      } catch (err) {
        console.warn('[CacheManager] 读取 Cache API 失败:', err);
      }
    }

    // 3. 网络请求回退
    console.log(`[CacheManager] 发起网络请求加载(Miss): ${jsonUrl}`);
    const response = await fetch(jsonUrl);
    
    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status}`);
    }

    const jsonData = await response.json();

    // 异步回写缓存
    this.memoryCache.set(cacheKey, jsonData);
    if (this.useCacheAPI) {
      try {
        const cache = await caches.open(this.cacheName);
        const resToCache = new Response(JSON.stringify(jsonData), {
          headers: { 'Content-Type': 'application/json' }
        });
        await cache.put(cacheKey, resToCache); // 无阻塞记录缓存
      } catch (err) {
        console.warn('[CacheManager] 写入 Cache API 失败:', err);
      }
    }

    return jsonData;
  }

  /**
   * 清理过期或者失效数据集缓存
   */
  async clearCache() {
    this.memoryCache.clear();
    if (this.useCacheAPI) {
      try {
        await caches.delete(this.cacheName);
      } catch (e) {}
    }
    console.log('[CacheManager] 数据缓存已清空');
  }
}

// 暴露全局实例
window.ivChartCache = new IVChartCacheManager();
