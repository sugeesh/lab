from dataclasses import dataclass

@dataclass
class LetterNode:
    nextLetter: dict[str, LetterNode]
    value: str
    isEndNode: bool

    def __init__(self, value):
        self.value = value
        self.nextLetter = {}
        self.isEndNode = False

    def addNext(self, value) -> LetterNode:
        existingNext = self.nextLetter.get(value)
        if (existingNext == None):
            self.nextLetter[value] = LetterNode(value)
            return self.nextLetter[value]
        return existingNext

    def searchNext(self, word) -> bool:
        if( len(word)==1 ):
            if(word != "."):
                endNode = self.nextLetter.get(word)
                if(endNode != None and endNode.isEndNode):
                    return True
                else:
                    return False
            else:
                for item in self.nextLetter.values():
                    if item.isEndNode:
                        return True
                return False
        else:
            if(word[0] != "."):
                nextNode = self.nextLetter.get(word[0])
                if(nextNode != None):
                    return nextNode.searchNext(word[1:])
                else:
                    return False
            else:
                resultList = []
                for item in self.nextLetter.values():
                    resultList.append(item.searchNext(word[1:]))
                return any(resultList)

class WordDictionary:

    def __init__(self):
        self.initNode = LetterNode("*")

    def addWord(self, word: str) -> None:
        pointer = self.initNode
        for char in word:
            pointer = pointer.addNext(char)
        pointer.isEndNode = True

    def search(self, word: str) -> bool:
        return self.initNode.searchNext(word)


# Your WordDictionary object will be instantiated and called as such:
# obj = WordDictionary()
# obj.addWord(word)
# param_2 = obj.search(word)
