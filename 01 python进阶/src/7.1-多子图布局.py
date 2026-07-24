import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(2, 1, figsize=(10, 6))

x = np.linspace(0, 1, 100)
y = np.random.uniform(0, 1, 100)

axes[0].scatter(x, y)
axes[1].plot(x, y)

plt.tight_layout()
plt.show()