class NumArray:

    def __init__(self, nums: list[int]):
        self.numList = nums
        self.sumList = []
        total = 0
        for value in nums:
            total += value
            self.sumList.append(total)

    def sumRange(self, left: int, right: int) -> int:
        if left != 0:
            print("A ", self.sumList[right], " ",self.sumList[left-1])
            return self.sumList[right] - self.sumList[left-1]
        return self.sumList[right] - 0
        
