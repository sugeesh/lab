import math
import heapq

class Solution:
    def kClosest(self, points: list[list[int]], k: int) -> list[list[int]]:
        distanceDic = {}
        for index, point in enumerate(points):
            dis = math.sqrt(point[0]**2 + point[1]**2)
            distanceDic[index] = dis
        
        heap = [(val, key) for key, val in distanceDic.items()]
        heapq.heapify(heap)

        returnArray = []
        for i in range(0,k):
            returnArray.append(points[heapq.heappop(heap)[1]])
        
        return returnArray
