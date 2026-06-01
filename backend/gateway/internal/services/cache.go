package services

import (
    "log"
    "sync"
    "time"
)

type cacheEntry struct {
    data      any
    expiresAt time.Time
}

type ttlCache struct {
    mu    sync.RWMutex
    items map[string]*cacheEntry
    ttl   time.Duration
}

func newTTLCache(ttl time.Duration) *ttlCache {
    c := &ttlCache{
        items: make(map[string]*cacheEntry),
        ttl:   ttl,
    }
    go c.cleanup()
    return c
}

func (c *ttlCache) Get(key string) (any, bool) {
    c.mu.RLock()
    e, ok := c.items[key]
    c.mu.RUnlock()
    if !ok || time.Now().After(e.expiresAt) {
        return nil, false
    }
    return e.data, true
}

func (c *ttlCache) Set(key string, data any) {
    c.mu.Lock()
    c.items[key] = &cacheEntry{
        data:      data,
        expiresAt: time.Now().Add(c.ttl),
    }
    c.mu.Unlock()
}

func (c *ttlCache) cleanup() {
    // A panic in this long-lived goroutine would otherwise crash the
    // entire gateway process. Recover and re-arm the cleanup loop.
    defer func() {
        if r := recover(); r != nil {
            log.Printf("ttlCache.cleanup panic: %v — restarting", r)
            time.Sleep(time.Second)
            go c.cleanup()
        }
    }()
    for {
        time.Sleep(c.ttl)
        c.mu.Lock()
        now := time.Now()
        for k, e := range c.items {
            if now.After(e.expiresAt) {
                delete(c.items, k)
            }
        }
        c.mu.Unlock()
    }
}
