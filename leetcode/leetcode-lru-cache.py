class LRUCache:

    def __init__(self, capacity: int):
        self.cache = {}
        self.capacity = capacity
        self.cacheRU = {} 

    def get(self, key: int) -> int:
        if self.cache.get(key) == None:
            return -1
        else:
            self.cacheRU[key] = max(self.cacheRU.values(), default=0)+1
            return self.cache.get(key)

    def put(self, key: int, value: int) -> None:
        if(self.cache.get(key) == None and (self.capacity <= len(self.cache))):
            lowest_key = min(self.cacheRU, key=self.cacheRU.get)
            self.cache.pop(lowest_key)
            self.cacheRU.pop(lowest_key)
        self.cacheRU[key] = max(self.cacheRU.values(), default=0)+1
        self.cache[key]=value
