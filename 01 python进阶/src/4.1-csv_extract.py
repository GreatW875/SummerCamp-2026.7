from pathlib import Path

current_dir = Path(__file__).parent.parent
data_dir = current_dir / "data"

count = 0

for f in data_dir.glob("*.csv"):
    with open(f, "r") as file:
        next(file)
        for line in file:
            count += 1

print(f"总行数: {count}")