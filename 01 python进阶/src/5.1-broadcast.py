import numpy as np

temp = np.random.rand(100)
# print(temp)
# print(temp.shape)
# print(np.zeros(100))
mean = np.mean(temp)
print(mean)

result = temp - mean
print(result)
print(result.mean())

a = np.array([[1, 3, 5],[2, 3, 4],[3, 3, 3]])     # shape (3,3) —— 列向量
b = np.array([10,20,30])        # shape (1,3) 或 (3,) —— 行向量
c = a + b
print(c)
print(c.shape)