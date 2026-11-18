from dataclasses import dataclass, field

@dataclass
class MyStack:

    def __init__(self):
        self.stack = []
    
    def push(self, x: int) -> None:
        self.stack.append(x)

    def pop(self) -> int:
        return self.stack.pop()
    
    def peek(self) -> int:
        return self.stack[self.size()-1]

    def size(self) -> int:
        return len(self.stack)    

class MyQueue:

    def __init__(self):
        self.mainStack = MyStack()
        self.tempStack = MyStack()

    def push(self, x: int) -> None:
        self.mainStack.push(x)

    def pop(self) -> int:
        for i in range(0,self.mainStack.size()):
            self.tempStack.push(self.mainStack.pop())
        value = self.tempStack.pop()
        for i in range(0,self.tempStack.size()):
            self.mainStack.push(self.tempStack.pop())
        return value

    def peek(self) -> int:
        for i in range(0,self.mainStack.size()):
            self.tempStack.push(self.mainStack.pop())
        value = self.tempStack.peek()
        for i in range(0,self.tempStack.size()):
            self.mainStack.push(self.tempStack.pop())
        return value
        

    def empty(self) -> bool:
        return self.mainStack.size() == 0

