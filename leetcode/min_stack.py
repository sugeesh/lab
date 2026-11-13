from dataclasses import dataclass

@dataclass
class DataObj:
    value : int
    currentMinValue : int

class MinStack:

    def __init__(self):
        self.stack = []
        self.minValue = None
    
    def push(self, value: int) -> None:
        self.stack.append(DataObj(value,self.minValue))
        if self.minValue == None:
            self.minValue = value
        elif self.minValue > value:
            self.minValue = value
        
        
    def pop(self) -> None:
        val = self.stack.pop()
        self.minValue = val.currentMinValue

    def top(self) -> int:
        return self.stack[-1].value

    def getMin(self) -> int:
        return self.minValue
