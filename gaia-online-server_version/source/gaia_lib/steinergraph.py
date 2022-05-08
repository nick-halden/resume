def power_set(A):
    length = len(A)
    return {
        frozenset({e for e, b in zip(A, f'{i:{length}b}') if b == '1'})
        for i in range(2 ** length)
    }


class Node:
    def __init__(self, name, neighbors=[]):
        self.name = name
        self.neighbors = neighbors
        self.visited = False
        self.previous = None


class SubGraph:
    def __init__(self, V, S):
        self.V = V  # [Nodes]
        self.S = S  # subset of V
        self.E = set()
        for v in self.V:
            for n in v.neighbors:
                self.S.add(frozenset([v, n]))

    def bfs(self, start, end):
        queue = [start]
        while queue:
            current_node = queue.pop(0)
            for node in current_node.neighbors:
                if not node.visited:
                    node.visited = True
                    queue.append(node)
                    node.previous = current_node
                    if node == end:
                        break
        path, length = set(), 0
        while node:
            path.add(frozenset([node, node.prev]))
            node = node.prev
            length += 1
        self.clear()
        return length, path

    def clear(self):
        for node in self.V:
            node.visited = False
            node.previous = None


class Graph(SubGraph):
    def __init__(self, V, S):
        super().__init__(V, S)
        self.steiner_V = []
        self.steiner_S = set()

    def steiner_tree(self, X, p):
        if len(X) < 3:
            minimum = 100000
            argmin = None
            for q in self.V:
                dist = self.bfs(X[0], q)[0] + self.bfs(X[1], q)[0] + self.bfs(p, q)[0]
                if dist < minimum:
                    argmin = SubGraph(
                        [X[0], X[1], p, q],
                        {frozenset([X[0], q]), frozenset([X[1], q]), frozenset([p, q])},
                    )
            return argmin
        else:
            for q in self.V:
                for E in power_set(X):
                    EC = X - E


C = {frozenset([1, 2]), frozenset([1, 3]), frozenset([1, 23])}

# print(power_set(C))
'''
Output:
{
frozenset({frozenset({1, 2})}), 
frozenset({frozenset({1, 3}), frozenset({1, 23})}), 
frozenset({frozenset({1, 2}), frozenset({1, 23})}), 
frozenset({frozenset({1, 2}), frozenset({1, 3}), frozenset({1, 23})}), 
frozenset({frozenset({1, 3}), frozenset({1, 2})}), 
frozenset({frozenset({1, 23})}), 
frozenset(), 
frozenset({frozenset({1, 3})})
}
'''

W = {frozenset([1, 2, 3]), frozenset([2, 4]), frozenset([2, 4]), frozenset([8])}
R = frozenset([frozenset([1, 2, 3]), frozenset([8])])
X = W - R
print(X)
