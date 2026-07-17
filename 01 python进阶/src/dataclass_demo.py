"""@dataclass 用法示例"""

from dataclasses import dataclass, field


# ===== 1. 基本用法 =====
@dataclass
class SensorReading:
    """传感器读数：字段 + 类型注解 + 默认值"""
    timestamp: float
    value: float
    is_valid: bool = True


print("===== 基本用法 =====")
r1 = SensorReading(1.0, 42)
r2 = SensorReading(1.0, 42)
print(r1)            # 自动生成 __repr__
print(r1 == r2)      # 自动生成 __eq__，按值比较


# ===== 2. frozen=True：不可变对象 =====
@dataclass(frozen=True)
class Config:
    threshold: float = 0.5
    window_size: int = 5


print("\n===== 不可变对象 =====")
c = Config()
print(c)
# c.threshold = 0.8   # 取消注释会报 FrozenInstanceError


# ===== 3. field() 精细控制 =====
@dataclass
class Experiment:
    name: str
    readings: list = field(default_factory=list)       # 可变默认值必须用这个
    timestamp: float = field(init=False, default=0.0)  # 不接受外部传参
    _id: str = field(repr=False, default="unknown")    # repr 时不显示


print("\n===== field() 控制 =====")
e1 = Experiment("run1")
e2 = Experiment("run2")
e1.readings.append(42)
print(e2.readings)   # [] —— 独立，不受 e1 影响
print(e1)            # _id 不显示
print(e1._id)        # 但可以访问


# ===== 4. @dataclass + @property =====
@dataclass
class ExperimentConfig:
    name: str
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100

    @property
    def total_steps(self):
        return self.epochs * self.batch_size


print("\n===== @dataclass + @property =====")
cfg = ExperimentConfig("baseline")
print(f"{cfg.total_steps = }")   # 3200
