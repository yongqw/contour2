# 地形隧道计算器 - 代码重构和优化建议
## Terrain Tunneling Calculator - Code Refactoring and Optimization Recommendations

### 1. 架构重构建议 / Architecture Refactoring Recommendations

#### 1.1 依赖注入模式 / Dependency Injection Pattern
```python
# 当前问题: 硬编码依赖关系
# 问题示例: visualization_3d.py 第658行直接导入ImprovedSemicircularTunnelGeometry

# 建议解决方案: 依赖注入容器
class ServiceContainer:
    """服务容器 - 管理所有依赖关系"""
    
    def __init__(self):
        self._services = {}
        self._factories = {}
    
    def register(self, interface: Type, implementation: Type):
        """注册服务实现"""
        self._services[interface] = implementation
    
    def register_factory(self, interface: Type, factory: Callable):
        """注册工厂函数"""
        self._factories[interface] = factory
    
    def get(self, interface: Type):
        """获取服务实例"""
        if interface in self._services:
            return self._services[interface]()
        elif interface in self._factories:
            return self._factories[interface]()
        else:
            raise ValueError(f"Service {interface} not registered")

# 使用示例
container = ServiceContainer()
container.register(TunnelGeometryFactory, ImprovedSemicircularTunnelFactory)
```

#### 1.2 命令模式重构 / Command Pattern Refactoring
```python
# 当前问题: GUI组件直接调用服务方法
# 问题示例: main_window.py 中的直接方法调用

# 建议解决方案: 命令模式
from abc import ABC, abstractmethod

class Command(ABC):
    """命令接口"""
    
    @abstractmethod
    def execute(self) -> bool:
        """执行命令"""
        pass
    
    @abstractmethod
    def undo(self) -> bool:
        """撤销命令"""
        pass

class CreateTunnelCommand(Command):
    """创建隧道命令"""
    
    def __init__(self, request: TunnelCreationRequest, 
                 tunnel_service: TunnelGeometryService,
                 contour_data: ContourData):
        self.request = request
        self.service = tunnel_service
        self.contour_data = contour_data
        self.result = None
    
    def execute(self) -> bool:
        """执行隧道创建"""
        self.result = self.service.create_tunnel_from_request(
            self.request, self.contour_data
        )
        return self.result.success
    
    def undo(self) -> bool:
        """撤销隧道创建"""
        # 实现撤销逻辑
        return True

class CommandInvoker:
    """命令调用器 - 支持撤销/重做"""
    
    def __init__(self):
        self.history = []
        self.current_index = -1
    
    def execute_command(self, command: Command) -> bool:
        """执行命令并记录历史"""
        if command.execute():
            # 清除重做历史
            self.history = self.history[:self.current_index + 1]
            self.history.append(command)
            self.current_index += 1
            return True
        return False
    
    def undo(self) -> bool:
        """撤销上一个命令"""
        if self.current_index >= 0:
            command = self.history[self.current_index]
            if command.undo():
                self.current_index -= 1
                return True
        return False
```

#### 1.3 观察者模式重构 / Observer Pattern Refactoring
```python
# 当前问题: 数据变化时GUI更新不及时
# 问题示例: 可视化状态管理分散在各个组件中

# 建议解决方案: 事件驱动架构
from typing import Protocol, Any
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    """事件类型枚举"""
    TUNNEL_CREATED = "tunnel_created"
    TUNNEL_MODIFIED = "tunnel_modified"
    TERRAIN_LOADED = "terrain_loaded"
    VISUALIZATION_MODE_CHANGED = "viz_mode_changed"

@dataclass
class Event:
    """事件数据结构"""
    type: EventType
    data: Any
    source: Any
    timestamp: float

class EventListener(Protocol):
    """事件监听器接口"""
    
    def handle_event(self, event: Event) -> None:
        """处理事件"""
        pass

class EventBus:
    """事件总线 - 解耦组件间通信"""
    
    def __init__(self):
        self._listeners = {}
    
    def subscribe(self, event_type: EventType, listener: EventListener):
        """订阅事件"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
    
    def unsubscribe(self, event_type: EventType, listener: EventListener):
        """取消订阅"""
        if event_type in self._listeners:
            self._listeners[event_type].remove(listener)
    
    def publish(self, event: Event):
        """发布事件"""
        if event.type in self._listeners:
            for listener in self._listeners[event.type]:
                try:
                    listener.handle_event(event)
                except Exception as e:
                    print(f"Error handling event {event.type}: {e}")

# 全局事件总线实例
event_bus = EventBus()
```

### 2. 性能优化建议 / Performance Optimization Recommendations

#### 2.1 地形网格优化 / Terrain Mesh Optimization
```python
# 当前问题: 大型地形数据渲染性能差
# 问题示例: 三角化服务没有LOD支持

# 建议解决方案: 多级细节系统
class LODTerrainMesh:
    """多级细节地形网格"""
    
    def __init__(self, vertices: np.ndarray, triangles: List[Triangle]):
        self.original_vertices = vertices
        self.original_triangles = triangles
        self.lod_levels = {}
        self._generate_lod_levels()
    
    def _generate_lod_levels(self):
        """生成多级细节网格"""
        # LOD 0: 原始精度
        self.lod_levels[0] = (self.original_vertices, self.original_triangles)
        
        # LOD 1: 50%精度
        self.lod_levels[1] = self._simplify_mesh(0.5)
        
        # LOD 2: 25%精度
        self.lod_levels[2] = self._simplify_mesh(0.25)
        
        # LOD 3: 10%精度
        self.lod_levels[3] = self._simplify_mesh(0.1)
    
    def _simplify_mesh(self, ratio: float) -> Tuple[np.ndarray, List[Triangle]]:
        """简化网格到指定比例"""
        # 使用边折叠算法简化网格
        # 这里简化实现，实际应该使用QEM或类似算法
        num_vertices = int(len(self.original_vertices) * ratio)
        
        # 随机采样简化版本
        indices = np.random.choice(
            len(self.original_vertices), 
            size=num_vertices, 
            replace=False
        )
        
        simplified_vertices = self.original_vertices[indices]
        
        # 重新三角化简化后的顶点
        # 这里需要实现适当的三角化算法
        simplified_triangles = self._retriangulate(simplified_vertices)
        
        return simplified_vertices, simplified_triangles
    
    def get_lod(self, camera_distance: float) -> Tuple[np.ndarray, List[Triangle]]:
        """根据相机距离获取合适的LOD级别"""
        if camera_distance < 50:
            return self.lod_levels[0]
        elif camera_distance < 100:
            return self.lod_levels[1]
        elif camera_distance < 200:
            return self.lod_levels[2]
        else:
            return self.lod_levels[3]

class FrustumCuller:
    """视锥体剔除器"""
    
    def __init__(self, view_matrix: np.ndarray, proj_matrix: np.ndarray):
        self.view_matrix = view_matrix
        self.proj_matrix = proj_matrix
        self.view_proj_matrix = proj_matrix @ view_matrix
    
    def is_triangle_visible(self, triangle: Triangle, vertices: np.ndarray) -> bool:
        """检查三角形是否在视锥体内"""
        # 获取三角形的三个顶点
        v0, v1, v2 = [
            vertices[triangle.vertex_indices[0]],
            vertices[triangle.vertex_indices[1]],
            vertices[triangle.vertex_indices[2]]
        ]
        
        # 检查所有顶点是否都在视锥体同一侧外面
        # 简化实现，实际应该使用完整的视锥体剔除算法
        for vertex in [v0, v1, v2]:
            # 转换到裁剪空间
            clip_pos = self.view_proj_matrix @ np.append(vertex, 1.0)
            
            # 检查是否在视锥体外
            if (abs(clip_pos[0]) > clip_pos[3] and 
                abs(clip_pos[1]) > clip_pos[3] and
                clip_pos[2] < 0):
                return False
        
        return True
```

#### 2.2 内存优化策略 / Memory Optimization Strategies
```python
# 当前问题: 内存使用效率低，存在内存泄漏
# 问题示例: 大量临时对象创建，缺乏对象池

# 建议解决方案: 对象池和内存管理
class ObjectPool:
    """通用对象池"""
    
    def __init__(self, factory: Callable, max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self.pool = []
        self.in_use = set()
    
    def acquire(self) -> Any:
        """获取对象"""
        if self.pool:
            obj = self.pool.pop()
        else:
            obj = self.factory()
        
        self.in_use.add(id(obj))
        return obj
    
    def release(self, obj: Any):
        """释放对象"""
        obj_id = id(obj)
        if obj_id in self.in_use:
            self.in_use.remove(obj_id)
            
            # 重置对象状态
            if hasattr(obj, 'reset'):
                obj.reset()
            
            # 如果池未满，放回池中
            if len(self.pool) < self.max_size:
                self.pool.append(obj)

class MemoryManager:
    """内存管理器"""
    
    def __init__(self):
        self.object_pools = {}
        self.memory_usage = {}
    
    def get_pool(self, obj_type: Type) -> ObjectPool:
        """获取对象池"""
        if obj_type not in self.object_pools:
            self.object_pools[obj_type] = ObjectPool(obj_type)
        return self.object_pools[obj_type]
    
    def track_memory(self, name: str, size: int):
        """跟踪内存使用"""
        if name not in self.memory_usage:
            self.memory_usage[name] = 0
        self.memory_usage[name] += size
    
    def get_memory_report(self) -> Dict[str, int]:
        """获取内存使用报告"""
        return self.memory_usage.copy()

# 全局内存管理器
memory_manager = MemoryManager()

# 使用示例
class Triangle:
    """三角形对象 - 支持对象池"""
    
    def reset(self):
        """重置对象状态"""
        self.vertex_indices = [0, 0, 0]
        self.normal = np.array([0.0, 0.0, 0.0])
        self.area = 0.0

# 获取三角形对象池
triangle_pool = memory_manager.get_pool(Triangle)

# 使用对象池
triangle = triangle_pool.acquire()
# 使用三角形...
triangle_pool.release(triangle)
```

#### 2.3 计算缓存优化 / Computation Cache Optimization
```python
# 当前问题: 重复计算，缺乏缓存机制
# 问题示例: 体积计算、可视化数据重复生成

# 建议解决方案: 智能缓存系统
from functools import lru_cache
import hashlib
import pickle

class ComputationCache:
    """计算缓存系统"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_order = []
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        # 使用参数的哈希值作为键
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }
        key_str = pickle.dumps(key_data)
        return hashlib.md5(key_str).hexdigest()
    
    def get(self, func_name: str, args: tuple, kwargs: dict) -> Any:
        """获取缓存结果"""
        key = self._generate_key(func_name, args, kwargs)
        
        if key in self.cache:
            # 更新访问顺序
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        
        return None
    
    def put(self, func_name: str, args: tuple, kwargs: dict, result: Any):
        """存储计算结果"""
        key = self._generate_key(func_name, args, kwargs)
        
        # 如果缓存已满，删除最久未访问的项
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = result
        if key not in self.access_order:
            self.access_order.append(key)

def cached_computation(cache: ComputationCache):
    """计算缓存装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 尝试从缓存获取
            cached_result = cache.get(func.__name__, args, kwargs)
            if cached_result is not None:
                return cached_result
            
            # 执行计算
            result = func(*args, **kwargs)
            
            # 存储到缓存
            cache.put(func.__name__, args, kwargs, result)
            
            return result
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

# 使用示例
computation_cache = ComputationCache()

@cached_computation(computation_cache)
def calculate_tunnel_volume(tunnel_geometry: TunnelGeometry) -> float:
    """计算隧道体积 - 带缓存"""
    # 实际的体积计算逻辑
    pass

@cached_computation(computation_cache)
def generate_terrain_mesh(contour_data: ContourData, density: str) -> TerrainMesh:
    """生成地形网格 - 带缓存"""
    # 实际的网格生成逻辑
    pass
```

### 3. 代码质量改进 / Code Quality Improvements

#### 3.1 类型安全增强 / Type Safety Enhancement
```python
# 当前问题: 类型注解不完整，缺乏运行时检查
# 问题示例: 很多方法缺少类型注解

# 建议解决方案: 严格的类型系统
from typing import TypeVar, Generic, Protocol, runtime_checkable
from dataclasses import dataclass

T = TypeVar('T')

@runtime_checkable
class Validated(Protocol[T]):
    """验证协议接口"""
    
    def validate(self) -> bool:
        """验证对象有效性"""
        pass

@dataclass
class ValidatedFloat:
    """验证过的浮点数"""
    value: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def __post_init__(self):
        self.validate()
    
    def validate(self) -> bool:
        """验证浮点数范围"""
        if self.min_value is not None and self.value < self.min_value:
            raise ValueError(f"Value {self.value} below minimum {self.min_value}")
        if self.max_value is not None and self.value > self.max_value:
            raise ValueError(f"Value {self.value} above maximum {self.max_value}")
        return True
    
    def __float__(self) -> float:
        return self.value

@dataclass
class ValidatedCoordinate:
    """验证过的坐标"""
    x: ValidatedFloat
    y: ValidatedFloat
    z: ValidatedFloat
    
    def validate(self) -> bool:
        """验证坐标有效性"""
        return (self.x.validate() and 
                self.y.validate() and 
                self.z.validate())

# 使用示例
def create_tunnel_waypoint(x: float, y: float, z: float, radius: float) -> TunnelWaypoint:
    """创建隧道航点 - 带类型验证"""
    validated_x = ValidatedFloat(x, min_value=0.0)
    validated_y = ValidatedFloat(y, min_value=0.0)
    validated_z = ValidatedFloat(z, min_value=-1000.0, max_value=10000.0)
    validated_radius = ValidatedFloat(radius, min_value=1.0, max_value=100.0)
    
    coordinate = ValidatedCoordinate(validated_x, validated_y, validated_z)
    
    return TunnelWaypoint(
        x=float(coordinate.x),
        y=float(coordinate.y),
        z=float(coordinate.z),
        radius=float(validated_radius)
    )
```

#### 3.2 错误处理改进 / Error Handling Improvements
```python
# 当前问题: 错误处理不一致，缺乏详细的错误信息
# 问题示例: 很多地方使用通用的Exception

# 建议解决方案: 结构化错误处理
class TerrainTunnelingError(Exception):
    """基础异常类"""
    
    def __init__(self, message: str, error_code: str = None, 
                 context: Dict[str, Any] = None, cause: Exception = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': str(self),
            'error_code': self.error_code,
            'context': self.context,
            'cause': str(self.cause) if self.cause else None,
            'timestamp': self.timestamp
        }

class ValidationError(TerrainTunnelingError):
    """数据验证错误"""
    
    def __init__(self, field: str, value: Any, constraint: str, 
                 message: str = None):
        self.field = field
        self.value = value
        self.constraint = constraint
        
        if message is None:
            message = f"Validation failed for field '{field}': {constraint}"
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            context={
                'field': field,
                'value': value,
                'constraint': constraint
            }
        )

class ComputationError(TerrainTunnelingError):
    """计算错误"""
    
    def __init__(self, operation: str, input_data: Any, 
                 message: str = None, cause: Exception = None):
        self.operation = operation
        self.input_data = input_data
        
        if message is None:
            message = f"Computation failed for operation '{operation}'"
        
        super().__init__(
            message=message,
            error_code="COMPUTATION_ERROR",
            context={
                'operation': operation,
                'input_type': type(input_data).__name__
            },
            cause=cause
        )

class ErrorReporter:
    """错误报告器"""
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file
        self.error_counts = {}
    
    def report_error(self, error: TerrainTunnelingError):
        """报告错误"""
        # 统计错误类型
        error_type = error.__class__.__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # 记录错误日志
        error_data = error.to_dict()
        
        if self.log_file:
            with open(self.log_file, 'a') as f:
                json.dump(error_data, f, indent=2)
                f.write('\n')
        
        # 控制台输出
        print(f"[ERROR] {error_data['message']}")
        
        # 如果有原因异常，打印堆栈跟踪
        if error.cause:
            import traceback
            traceback.print_exception(type(error.cause), error.cause, error.cause.__traceback__)
    
    def get_error_summary(self) -> Dict[str, int]:
        """获取错误统计摘要"""
        return self.error_counts.copy()

# 全局错误报告器
error_reporter = ErrorReporter("logs/errors.log")

# 使用示例
def validate_tunnel_radius(radius: float) -> ValidatedFloat:
    """验证隧道半径 - 带详细错误报告"""
    try:
        return ValidatedFloat(
            radius, 
            min_value=1.0, 
            max_value=50.0
        )
    except ValueError as e:
        error = ValidationError(
            field="radius",
            value=radius,
            constraint="1.0 <= radius <= 50.0",
            message=f"Invalid tunnel radius: {radius}. Must be between 1.0 and 50.0 meters."
        )
        error_reporter.report_error(error)
        raise error
```

#### 3.3 异步处理优化 / Asynchronous Processing Optimization
```python
# 当前问题: 长时间操作阻塞UI线程
# 问题示例: 大型地形处理、复杂计算时界面无响应

# 建议解决方案: 异步任务系统
import asyncio
import concurrent.futures
from typing import Callable, Any

class AsyncTask:
    """异步任务"""
    
    def __init__(self, func: Callable, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.future = None
        self.progress_callback = None
        self.completion_callback = None
    
    def set_progress_callback(self, callback: Callable[[float], None]):
        """设置进度回调"""
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable[[Any], None]):
        """设置完成回调"""
        self.completion_callback = callback
    
    async def execute(self) -> Any:
        """异步执行任务"""
        loop = asyncio.get_event_loop()
        
        # 在线程池中执行CPU密集型任务
        with concurrent.futures.ThreadPoolExecutor() as executor:
            self.future = loop.run_in_executor(
                executor, 
                self._execute_with_progress
            )
            
            result = await self.future
            
            # 调用完成回调
            if self.completion_callback:
                self.completion_callback(result)
            
            return result
    
    def _execute_with_progress(self) -> Any:
        """带进度报告的执行"""
        # 如果函数支持进度报告，设置回调
        if hasattr(self.func, 'supports_progress') and self.progress_callback:
            # 这里需要修改原函数以支持进度回调
            return self.func(*self.args, **self.kwargs)
        else:
            return self.func(*self.args, **self.kwargs)

class AsyncTaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_concurrent_tasks: int = 4):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks = []
        self.completed_tasks = []
        self.task_queue = asyncio.Queue()
    
    async def submit_task(self, task: AsyncTask) -> Any:
        """提交任务"""
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            # 等待有空闲槽位
            await self._wait_for_slot()
        
        self.running_tasks.append(task)
        
        try:
            result = await task.execute()
            self.completed_tasks.append(task)
            return result
        finally:
            self.running_tasks.remove(task)
    
    async def _wait_for_slot(self):
        """等待空闲槽位"""
        while len(self.running_tasks) >= self.max_concurrent_tasks:
            await asyncio.sleep(0.1)
    
    def get_running_tasks_count(self) -> int:
        """获取运行中任务数量"""
        return len(self.running_tasks)

# 全局任务管理器
task_manager = AsyncTaskManager()

# 使用示例
async def load_large_terrain(file_path: str) -> ContourData:
    """异步加载大型地形文件"""
    
    def load_terrain_sync():
        # 模拟长时间运行的任务
        import time
        time.sleep(2)  # 模拟加载时间
        return DemoDataGenerator().generate_hill_terrain()
    
    task = AsyncTask(load_terrain_sync)
    
    # 设置进度回调
    def progress_callback(progress: float):
        print(f"Loading terrain: {progress * 100:.1f}%")
    
    task.set_progress_callback(progress_callback)
    
    # 设置完成回调
    def completion_callback(result):
        print("Terrain loading completed!")
    
    task.set_completion_callback(completion_callback)
    
    return await task_manager.submit_task(task)

# GUI中的异步使用示例
class AsyncGUIComponent:
    """支持异步操作的GUI组件"""
    
    def __init__(self):
        self.pending_tasks = {}
    
    def start_async_task(self, task_name: str, coro):
        """启动异步任务"""
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 在后台线程中运行异步任务
        def run_async():
            loop.run_until_complete(coro)
            loop.close()
        
        import threading
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
        
        self.pending_tasks[task_name] = thread
        return thread
    
    def is_task_running(self, task_name: str) -> bool:
        """检查任务是否在运行"""
        thread = self.pending_tasks.get(task_name)
        return thread and thread.is_alive()
```

### 4. 测试改进建议 / Testing Improvements

#### 4.1 测试数据工厂 / Test Data Factory
```python
# 当前问题: 测试数据重复，缺乏统一的测试数据生成
# 建议解决方案: 测试数据工厂模式

class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def create_simple_contour_data(num_contours: int = 5) -> ContourData:
        """创建简单等高线测试数据"""
        contours = []
        center_x, center_y = 50.0, 50.0
        
        for i in range(num_contours):
            elevation = 100.0 + i * 10.0
            radius = 40.0 - i * 5.0
            
            # 生成圆形等高线
            angles = np.linspace(0, 2 * np.pi, 20, endpoint=False)
            points = []
            for angle in angles:
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                points.append([x, y])
            
            contour = ContourLine(
                elevation=elevation,
                points=np.array(points),
                is_closed=True
            )
            contours.append(contour)
        
        metadata = ContourMetadata(
            name="Test Terrain",
            units="meters",
            coordinate_system=CoordinateSystem.LOCAL,
            created_date=datetime.now().isoformat(),
            source="test_generator",
            description="Simple test terrain for unit testing"
        )
        
        return ContourData(
            metadata=metadata,
            contours=contours,
            bounding_box=BoundingBox(0, 100, 0, 100),
            coordinate_system=CoordinateSystem.LOCAL
        )
    
    @staticmethod
    def create_tunnel_geometry(waypoints_count: int = 3) -> TunnelGeometry:
        """创建隧道几何测试数据"""
        waypoints = []
        
        for i in range(waypoints_count):
            waypoint = TunnelWaypoint(
                x=25.0 + i * 25.0,
                y=25.0 + i * 25.0,
                elevation=120.0 + i * 5.0,
                radius=20.0
            )
            waypoints.append(waypoint)
        
        path = TunnelPath()
        path.cross_section_type = CrossSectionType.SEMICIRCULAR
        for waypoint in waypoints:
            path.add_waypoint(waypoint.x, waypoint.y, waypoint.elevation, waypoint.radius)
        
        return TunnelGeometry(path=path)
    
    @staticmethod
    def create_complex_terrain_mesh(vertex_count: int = 1000) -> TerrainMesh:
        """创建复杂地形网格测试数据"""
        # 生成随机地形
        np.random.seed(42)  # 确保可重现
        
        vertices = []
        for i in range(vertex_count):
            x = np.random.uniform(0, 100)
            y = np.random.uniform(0, 100)
            z = np.random.uniform(100, 150)
            vertices.append([x, y, z])
        
        vertices = np.array(vertices)
        
        # 简单的三角化（用于测试）
        triangles = []
        for i in range(0, len(vertices) - 2, 3):
            if i + 2 < len(vertices):
                triangles.append(Triangle(vertex_indices=[i, i+1, i+2]))
        
        return TerrainMesh(vertices=vertices, triangles=triangles)
```

#### 4.2 性能测试框架 / Performance Testing Framework
```python
# 当前问题: 缺乏性能测试，无法检测性能回归
# 建议解决方案: 性能测试框架

import time
import psutil
import tracemalloc
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class PerformanceMetrics:
    """性能指标"""
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    peak_memory_mb: float
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'execution_time': self.execution_time,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'peak_memory_mb': self.peak_memory_mb
        }

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.baseline_metrics = {}
        self.current_metrics = {}
    
    def measure_performance(self, func: Callable, *args, **kwargs) -> tuple[Any, PerformanceMetrics]:
        """测量函数性能"""
        # 开始内存跟踪
        tracemalloc.start()
        
        # 记录开始时间和资源使用
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        cpu_before = psutil.cpu_percent()
        
        # 执行函数
        result = func(*args, **kwargs)
        
        # 记录结束时间和资源使用
        end_time = time.perf_counter()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        cpu_after = psutil.cpu_percent(interval=0.1)
        
        # 获取内存使用峰值
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 计算性能指标
        metrics = PerformanceMetrics(
            execution_time=end_time - start_time,
            memory_usage_mb=end_memory - start_memory,
            cpu_usage_percent=(cpu_before + cpu_after) / 2,
            peak_memory_mb=peak / 1024 / 1024
        )
        
        return result, metrics
    
    def set_baseline(self, test_name: str, metrics: PerformanceMetrics):
        """设置性能基线"""
        self.baseline_metrics[test_name] = metrics
    
    def compare_with_baseline(self, test_name: str, current_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """与基线比较性能"""
        if test_name not in self.baseline_metrics:
            return {'status': 'no_baseline'}
        
        baseline = self.baseline_metrics[test_name]
        
        # 计算性能变化
        time_change = (current_metrics.execution_time - baseline.execution_time) / baseline.execution_time
        memory_change = (current_metrics.memory_usage_mb - baseline.memory_usage_mb) / baseline.memory_usage_mb
        
        # 判断性能是否显著变化（阈值：10%）
        significant_threshold = 0.1
        
        status = 'passed'
        if abs(time_change) > significant_threshold:
            status = 'failed'
        elif abs(memory_change) > significant_threshold:
            status = 'warning'
        
        return {
            'status': status,
            'time_change_percent': time_change * 100,
            'memory_change_percent': memory_change * 100,
            'baseline': baseline.to_dict(),
            'current': current_metrics.to_dict()
        }

# 性能测试装饰器
def performance_test(test_name: str, performance_tester: PerformanceTester = None):
    """性能测试装饰器"""
    if performance_tester is None:
        performance_tester = PerformanceTester()
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            result, metrics = performance_tester.measure_performance(func, *args, **kwargs)
            
            # 比较性能
            comparison = performance_tester.compare_with_baseline(test_name, metrics)
            
            print(f"Performance Test: {test_name}")
            print(f"Execution Time: {metrics.execution_time:.3f}s")
            print(f"Memory Usage: {metrics.memory_usage_mb:.2f}MB")
            print(f"Status: {comparison['status']}")
            
            if comparison['status'] != 'passed':
                print(f"Performance regression detected!")
                print(f"Time change: {comparison['time_change_percent']:.2f}%")
                print(f"Memory change: {comparison['memory_change_percent']:.2f}%")
            
            return result
        
        return wrapper
    return decorator

# 使用示例
performance_tester = PerformanceTester()

@performance_test("terrain_triangulation", performance_tester)
def test_terrain_triangulation_performance():
    """测试地形三角化性能"""
    contour_data = TestDataFactory.create_simple_contour_data(num_contours=20)
    triangulation_service = TriangulationService()
    return triangulation_service.triangulate_contours(contour_data)
```

### 5. 部署和分发优化 / Deployment and Distribution Optimization

#### 5.1 容器化部署 / Containerized Deployment
```dockerfile
# Dockerfile - 容器化部署
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY start_gui.py .
COPY config.json .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# 暴露端口（如果需要Web界面）
EXPOSE 8080

# 启动命令
CMD ["python", "start_gui.py"]
```

```yaml
# docker-compose.yml - 完整部署环境
version: '3.8'

services:
  terrain-tunneling-calculator:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    environment:
      - PYTHONPATH=/app/src
      - LOG_LEVEL=INFO
    restart: unless-stopped
    
  # 可选：数据库服务
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: terrain_tunneling
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppassword
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

#### 5.2 CI/CD流水线 / CI/CD Pipeline
```yaml
# .github/workflows/ci.yml - GitHub Actions配置
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .
    
    - name: Run linting
      run: |
        pip install flake8 black isort mypy
        flake8 src/ tests/
        black --check src/ tests/
        isort --check-only src/ tests/
        mypy src/
    
    - name: Run unit tests
      run: |
        pytest tests/ --cov=src --cov-report=xml --cov-report=html
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
    
    - name: Build package
      run: |
        python -m build
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist-${{ matrix.python-version }}
        path: dist/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build and publish
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        python -m build
        twine upload dist/*
```

### 6. 总结和实施建议 / Summary and Implementation Recommendations

#### 6.1 重构优先级 / Refactoring Priority
```
高优先级 (立即实施):
1. 依赖注入模式 - 解耦组件依赖
2. 错误处理改进 - 统一异常处理
3. 性能测试框架 - 建立性能基线

中优先级 (短期实施):
1. 异步任务系统 - 提升UI响应性
2. 内存优化 - 减少内存使用
3. 测试数据工厂 - 提高测试质量

低优先级 (长期规划):
1. 插件架构 - 支持扩展功能
2. 容器化部署 - 简化部署流程
3. CI/CD流水线 - 自动化测试和部署
```

#### 6.2 实施策略 / Implementation Strategy
```
阶段1: 基础重构 (2-3周)
- 实施依赖注入容器
- 统一错误处理机制
- 建立性能测试框架

阶段2: 性能优化 (3-4周)
- 实施异步任务系统
- 优化内存使用
- 添加计算缓存

阶段3: 质量提升 (2-3周)
- 完善测试覆盖率
- 实施测试数据工厂
- 添加性能监控

阶段4: 部署优化 (1-2周)
- 容器化应用
- 建立CI/CD流水线
- 优化分发流程
```

#### 6.3 风险评估 / Risk Assessment
```
技术风险:
- 重构可能引入新bug (缓解措施: 完善的测试覆盖)
- 性能优化可能影响功能 (缓解措施: 渐进式优化)
- 异步改造可能影响稳定性 (缓解措施: 充分的测试)

项目风险:
- 重构时间可能超出预期 (缓解措施: 分阶段实施)
- 团队学习成本 (缓解措施: 技术分享和文档)
- 用户界面变化 (缓解措施: 保持向后兼容)
```

---

这份重构和优化建议文档提供了全面的改进方案，涵盖了架构、性能、代码质量、测试和部署等各个方面。建议按照优先级分阶段实施，确保每个阶段都有明确的目标和验收标准。