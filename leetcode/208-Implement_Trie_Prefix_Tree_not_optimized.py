class Trie:

    def __init__(self):
        self.wordSet = set()
        self.prefixDic = {}

    def insert(self, word: str) -> None:
        appendChar = ""
        self.wordSet.add(word)
        for char in word:
            appendChar += char
            self.prefixDic[appendChar] = word

    def search(self, word: str) -> bool:
        return word in self.wordSet

    def startsWith(self, prefix: str) -> bool:
        if (self.prefixDic.get(prefix) != None ):
            return True
        else :
            return False
        
