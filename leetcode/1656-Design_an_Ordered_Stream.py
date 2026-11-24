class OrderedStream:

    def __init__(self, n: int):
        self.pointer = 0
        self.size = n
        self.orderDic = {i: '' for i in range(0, n)}


    def insert(self, idKey: int, value: str) -> list[str]:
        self.orderDic[idKey-1] = value
        if self.orderDic.get(self.pointer) == '':
            return []
        else:
            returnValues = []
            
            while (self.orderDic.get(self.pointer) != ''):
                returnValues.append(self.orderDic.get(self.pointer))
                if self.pointer == self.size-1 :
                    break
                self.pointer+=1
            return returnValues
