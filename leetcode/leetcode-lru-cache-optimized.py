class LRUCache:

    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key: int) -> int:
        if self.cache.get(key) == None:
            return -1
        else:
            self.cache.move_to_end(key)
            return self.cache.get(key)

    def put(self, key: int, value: int) -> None:
        if(self.cache.get(key) == None and (self.capacity <= len(self.cache))):
            self.cache.popitem(last=False)
        elif (self.cache.get(key) != None):
            self.cache.move_to_end(key)
        self.cache[key]=value
        
