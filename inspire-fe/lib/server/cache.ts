type CacheRecord = {
  value: unknown;
  expiresAt: number;
};

class MemoryCache {
  private readonly store = new Map<string, CacheRecord>();

  get<T>(key: string): T | null {
    const record = this.store.get(key);
    if (!record) {
      return null;
    }

    if (record.expiresAt <= Date.now()) {
      this.store.delete(key);
      return null;
    }

    return record.value as T;
  }

  set(key: string, value: unknown, ttlMs: number) {
    this.store.set(key, {
      value,
      expiresAt: Date.now() + ttlMs,
    });
  }

  delete(key: string) {
    this.store.delete(key);
  }
}

export const cache = new MemoryCache();

