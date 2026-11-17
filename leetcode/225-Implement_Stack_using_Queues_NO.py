class MyStack:

    def __init__(self):
        self.queue = []       
        self.tempQueue = []       

    def push(self, x: int) -> None:
        for i in range(0,len(self.queue)):
            item = self.queue.pop(0)
            self.tempQueue.append(item)
        self.queue.append(x)
        for i in range(0,len(self.tempQueue)):
            item = self.tempQueue.pop(0)
            self.queue.append(item)

    def pop(self) -> int:
        return self.queue.pop(0)

    def top(self) -> int:
        return self.queue[0]

    def empty(self) -> bool:
        return len(self.queue) == 0
