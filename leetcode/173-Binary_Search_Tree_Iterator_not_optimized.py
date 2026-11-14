# Definition for a binary tree node.
# class TreeNode:
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right

class BSTIterator:

    def __init__(self, root: TreeNode | None):
        self.root = root
        self.leftMarked = False
        self.selfMarked = False
        self.rightMarked = False
        if(self.root.left == None):
            self.leftMarked = True
        else :
            self.leftTree = BSTIterator(self.root.left)
        if(self.root.right == None):
            self.rightMarked = True
        else: 
            self.rightTree = BSTIterator(self.root.right)
       
    def next(self) -> int:
        if (not self.leftMarked):
            print("Went to Left Tree : ", self.root.left.val)
            x = self.leftTree.next()
            if x is not None: return x
        if (not self.selfMarked):
            print("Went to the Element : ",self.root.val)
            self.selfMarked = True
            return self.root.val
        if (not self.rightMarked):
            print("Went to Left Tree : ",self.root.right.val)
            x = self.rightTree.next()
            if x is not None: return x
    
    def hasNext(self) -> bool:
        if (not self.leftMarked):
            x = self.leftTree.hasNext()
            if x is True: return x
        if (not self.selfMarked):
            return True
        if (not self.rightMarked):
            x = self.rightTree.hasNext()
            if x is True: return x
        return False

# Your BSTIterator object will be instantiated and called as such:
# obj = BSTIterator(root)
# param_1 = obj.next()
# param_2 = obj.hasNext()
