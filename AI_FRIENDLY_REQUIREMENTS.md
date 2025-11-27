# 地形隧道计算器 - AI友好需求文档
## Terrain Tunneling Calculator - AI-Friendly Requirements Document

### 1. 项目概述 / Project Overview

#### 1.1 项目目标 / Project Goals
- **主要功能**: 地形隧道规划与可视化系统
- **核心用途**: 基于地形等高线数据进行隧道几何设计、体积计算和3D可视化
- **目标用户**: 土木工程师、隧道设计师、地质工程师
- **应用场景**: 隧道工程可行性研究、设计方案可视化、施工规划

#### 1.2 技术栈要求 / Technical Stack Requirements
- **编程语言**: Python 3.11+
- **GUI框架**: tkinter + customtkinter (现代化界面)
- **3D可视化**: plotly (交互式3D图表)
- **2D可视化**: matplotlib (等高线图、剖面图)
- **数值计算**: numpy (向量和矩阵运算)
- **数据处理**: JSON格式数据持久化
- **测试框架**: pytest + coverage

### 2. 核心架构设计 / Core Architecture Design

#### 2.1 模块化架构原则 / Modular Architecture Principles
```
src/
├── models/           # 数据模型层 - 业务实体定义
├── services/         # 服务层 - 业务逻辑实现
├── gui/             # 界面层 - 用户交互组件
├── utils/           # 工具层 - 通用工具函数
└── main.py          # 应用入口 - CLI和GUI启动
```

#### 2.2 设计模式要求 / Design Pattern Requirements
- **MVC模式**: 严格分离模型(Model)、视图(View)、控制器(Controller)
- **服务层模式**: 业务逻辑封装在服务类中
- **工厂模式**: 用于创建不同类型的几何体和可视化对象
- **观察者模式**: GUI组件响应数据变化
- **策略模式**: 支持不同的计算和可视化策略

### 3. 核心数据模型 / Core Data Models

#### 3.1 地形数据模型 / Terrain Data Models
```python
@dataclass
class ContourData:
    """等高线数据模型 - 必需字段"""
    metadata: ContourMetadata          # 元数据信息
    contours: List[ContourLine]        # 等高线列表
    bounds: BoundingBox               # 边界框
    coordinate_system: CoordinateSystem # 坐标系统

@dataclass
class ContourLine:
    """单条等高线 - 必需字段"""
    elevation: float                  # 海拔高度
    points: np.ndarray              # 点坐标数组 [N, 2]
    is_closed: bool                 # 是否闭合
```

#### 3.2 隧道几何模型 / Tunnel Geometry Models
```python
@dataclass
class TunnelGeometry:
    """隧道几何体 - 核心业务对象"""
    path: TunnelPath                 # 隧道路径
    cross_section_type: CrossSectionType  # 截面类型
    volume: float                   # 体积(计算得出)
    surface_area: float            # 表面积(计算得出)

@dataclass
class TunnelPath:
    """隧道路径 - 路径规划核心"""
    waypoints: List[TunnelWaypoint]  # 航点列表
    cross_section_type: CrossSectionType
    total_length: float (computed)     # 总长度

@dataclass
class TunnelWaypoint:
    """隧道航点 - 路径节点"""
    x: float, y: float, z: float      # 3D坐标
    radius: float                     # 隧道半径
    elevation: float (computed)        # 从地形插值得出
```

#### 3.3 地形网格模型 / Terrain Mesh Models
```python
@dataclass
class TerrainMesh:
    """地形网格 - 3D可视化基础"""
    vertices: np.ndarray              # 顶点坐标 [N, 3]
    triangles: List[Triangle]         # 三角面列表
    elevation_data: np.ndarray        # 高程数据 [N]
    vertex_count: int (computed)     # 顶点数量
    triangle_count: int (computed)    # 三角面数量
```

### 4. 核心算法规范 / Core Algorithm Specifications

#### 4.1 地形三角化算法 / Terrain Triangulation Algorithm
```python
class TriangulationService:
    """Delaunay三角化服务 - 核心算法"""
    
    def triangulate_contours(self, contour_data: ContourData) -> TerrainMesh:
        """
        算法要求:
        1. 输入: 等高线数据 (ContourData)
        2. 处理: 
           - 边界点提取
           - Delaunay三角化 (scipy.spatial.Delaunay)
           - 点密度控制 (避免过密网格)
        3. 输出: 地形网格 (TerrainMesh)
        4. 性能: 支持1000+顶点的实时处理
        """
```

#### 4.2 隧道几何生成算法 / Tunnel Geometry Generation
```python
class TunnelGeometryService:
    """隧道几何生成服务 - 设计核心"""
    
    def create_tunnel_from_request(self, request: TunnelCreationRequest, 
                              contour_data: ContourData) -> TunnelCreationResult:
        """
        算法要求:
        1. 输入: 隧道创建请求 + 地形数据
        2. 处理:
           - 路径验证 (自相交检测)
           - 高程插值 (从等高线获取Z值)
           - 几何体生成 (根据截面类型)
           - 体积计算 (分段圆柱体近似)
        3. 输出: 隧道几何体 + 验证结果
        """
```

#### 4.3 半圆形隧道几何算法 / Semicircular Tunnel Geometry
```python
class ImprovedSemicircularTunnelGeometry:
    """改进的半圆形隧道 - 特殊几何体"""
    
    def get_mesh_vertices(self, waypoints, segments_per_section=32, points_per_segment=30):
        """
        算法规范:
        1. 输入: 航点列表 + 分段参数
        2. 几何体特征:
           - 半圆形顶部 (180度弧形)
           - 平坦底部 (车辆行驶面)
           - 连续表面 (无视觉间隙)
        3. 生成步骤:
           - 路径插值 (线性插值)
           - 截面生成 (半圆形轮廓)
           - 顶点计算 (3D坐标变换)
        4. 输出: 顶点数组 [N, 3]
        """
```

### 5. 可视化系统规范 / Visualization System Specifications

#### 5.1 3D可视化服务 / 3D Visualization Service
```python
class Visualization3DService:
    """3D可视化服务 - plotly实现"""
    
    def create_integrated_scene(self, terrain_mesh: TerrainMesh, 
                             tunnel_geometry: TunnelGeometry) -> go.Figure:
        """
        可视化要求:
        1. 地形渲染:
           - 棕色到白色渐变 (高程映射)
           - 0.6透明度 (可见内部结构)
           - 三角网格渲染
        2. 隧道渲染:
           - 灰色半圆形几何体
           - 底部支撑面 (相同颜色)
           - 红色中心线路径
           - 黄色虚线道路边缘
        3. 交互功能:
           - 鼠标旋转/缩放
           - 相机角度控制
           - 图例显示
        """
```

#### 5.2 2D等高线可视化 / 2D Contour Visualization
```python
class Visualization2DService:
    """2D可视化服务 - matplotlib实现"""
    
    def create_contour_plot(self, contour_data: ContourData) -> plt.Figure:
        """
        可视化要求:
        1. 等高线绘制:
           - 颜色映射 (terrain色彩方案)
           - 高程标签显示
           - 填充等高线区域
        2. 坐标系统:
           - 等比例显示 (aspect='equal')
           - 网格线可选
           - 边界自动调整
        """
```

### 6. 动画系统规范 / Animation System Specifications

#### 6.1 隧道行车动画 / Tunnel Driving Animation
```python
class AnimationService:
    """动画服务 - 车辆移动模拟"""
    
    def create_animation_frames(self, tunnel_geometry: TunnelGeometry, 
                             duration: float = None) -> List[AnimationFrame]:
        """
        动画算法要求:
        1. 路径插值:
           - 车辆位置沿隧道中心线移动
           - 方向向量计算 (切线方向)
           - 平滑过渡 (线性插值)
        2. 相机跟随:
           - 第三人称视角
           - 固定距离跟随
           - 高度偏移 (俯视角度)
        3. 车辆模型:
           - 简化车体 (长方体+驾驶室)
           - 车轮显示
           - 前照灯光效
        4. 输出格式:
           - HTML交互式动画
           - 播放控制按钮
           - 速度调节滑块
        """
```

### 7. 数据持久化规范 / Data Persistence Specifications

#### 7.1 文件格式要求 / File Format Requirements
```python
class ExportService:
    """数据导出服务 - 多格式支持"""
    
    def export_stl(self, terrain_mesh: TerrainMesh, 
                   tunnel_geometry: TunnelGeometry) -> str:
        """STL导出 - 3D打印兼容格式"""
        
    def export_obj(self, terrain_mesh: TerrainMesh) -> str:
        """OBJ导出 - 3D建模软件兼容"""
        
    def export_csv(self, data: Union[TerrainMesh, ContourData]) -> str:
        """CSV导出 - 数据分析兼容"""
```

#### 7.2 配置管理 / Configuration Management
```python
# config.json 结构要求
{
    "app": {
        "name": "Terrain Tunneling Calculator",
        "version": "0.1.0",
        "debug": false
    },
    "visualization": {
        "default_3d_view": "integrated",
        "color_scheme": "terrain",
        "animation_fps": 30
    },
    "calculation": {
        "default_tunnel_radius": 20.0,
        "max_tunnel_length": 1000.0,
        "mesh_density": "medium"
    }
}
```

### 8. 用户界面规范 / User Interface Specifications

#### 8.1 主窗口设计 / Main Window Design
```python
class MainWindow:
    """主窗口 - 现代化GUI设计"""
    
    def __init__(self):
        """
        界面要求:
        1. 布局:
           - 左侧: 2D等高线视图 (交互式)
           - 右侧: 控制面板 (分层组织)
           - 底部: 状态栏 (信息显示)
        2. 高DPI支持:
           - 自动缩放因子检测
           - 字体和图标适配
           - 工具栏图标大小调整
        3. 主题支持:
           - 现代化外观 (customtkinter)
           - 深色/浅色主题切换
           - 高对比度模式
        """
```

#### 8.2 交互式等高线视图 / Interactive Contour View
```python
class ContourView:
    """等高线视图 - 隧道规划交互"""
    
    def _on_mouse_click(self, event):
        """
        交互要求:
        1. 点选择模式:
           - 左键点击选择路径点
           - 视觉反馈 (标记显示)
           - 路径连线预览
        2. 右键菜单:
           - 隧道规划命令
           - 视图模式切换
           - 导出选项
        3. 键盘快捷键:
           - 'A': 添加点模式
           - 'E': 编辑模式
           - 'ESC': 清除选择
        """
```

### 9. 验证和测试规范 / Validation and Testing Specifications

#### 9.1 数据验证框架 / Data Validation Framework
```python
class ValidationFramework:
    """验证框架 - 数据完整性检查"""
    
    def validate_tunnel_geometry(self, tunnel: TunnelGeometry) -> ValidationResult:
        """
        验证规则:
        1. 几何约束:
           - 最小/最大半径检查
           - 路径长度限制
           - 坡度限制 (<15%)
        2. 拓扑检查:
           - 自相交检测
           - 路径连续性
           - 截面有效性
        3. 工程约束:
           - 最小净空 (2.0m)
           - 曲率半径限制
           - 地形相交检查
        """
```

#### 9.2 测试覆盖要求 / Test Coverage Requirements
```python
# 测试结构要求
tests/
├── test_models/          # 模型层单元测试
├── test_services/        # 服务层集成测试
├── test_gui/           # GUI层功能测试
├── test_utils/          # 工具层工具测试
└── conftest.py         # 测试配置和fixtures

# 覆盖率目标
- 整体覆盖率: >80%
- 核心算法: >95%
- GUI组件: >60%
```

### 10. 性能优化要求 / Performance Optimization Requirements

#### 10.1 计算性能 / Computational Performance
```python
# 性能基准要求
性能指标:
1. 地形三角化:
   - 1000顶点: <1秒
   - 5000顶点: <5秒
   - 内存使用: <100MB
2. 隧道几何生成:
   - 简单路径: <0.5秒
   - 复杂路径: <2秒
3. 3D可视化:
   - 初始渲染: <3秒
   - 交互响应: <100ms
   - 动画帧率: >25fps
```

#### 10.2 内存管理 / Memory Management
```python
# 内存优化策略
1. 数据结构优化:
   - 使用numpy数组替代Python列表
   - 延迟计算大型数据集
   - 及时释放临时对象
2. 可视化优化:
   - LOD (Level of Detail) 系统
   - 视锥体剔除
   - 纹理压缩
3. 缓存策略:
   - 计算结果缓存
   - 网格数据缓存
   - LRU缓存机制
```

### 11. 扩展性设计 / Extensibility Design

#### 11.1 插件架构 / Plugin Architecture
```python
# 插件接口设计
class TunnelGeometryPlugin:
    """隧道几何插件接口"""
    def create_geometry(self, waypoints: List[TunnelWaypoint]) -> TunnelGeometry:
        """创建特定类型的隧道几何体"""
        pass

class VisualizationPlugin:
    """可视化插件接口"""
    def create_visualization(self, data: Any) -> Any:
        """创建特定类型的可视化"""
        pass
```

#### 11.2 配置驱动开发 / Configuration-Driven Development
```python
# 配置化设计原则
1. 算法参数化:
   - 三角化密度控制
   - 插值算法选择
   - 精度要求设置
2. 可视化参数化:
   - 颜色方案配置
   - 渲染质量设置
   - 交互行为定制
3. 导出格式扩展:
   - 新格式插件接口
   - 转换参数配置
   - 批量处理支持
```

### 12. 错误处理和日志 / Error Handling and Logging

#### 12.1 异常处理策略 / Exception Handling Strategy
```python
# 自定义异常层次
class TerrainTunnelingError(Exception):
    """基础异常类"""
    pass

class ValidationError(TerrainTunnelingError):
    """数据验证异常"""
    pass

class VisualizationError(TerrainTunnelingError):
    """可视化异常"""
    pass

class ExportError(TerrainTunnelingError):
    """导出异常"""
    pass
```

#### 12.2 日志系统 / Logging System
```python
# 日志配置要求
import logging

# 日志级别
- DEBUG: 详细调试信息
- INFO: 一般信息记录
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

# 日志格式
格式: [时间戳] [级别] [模块名] 消息内容
文件: logs/app_YYYYMMDD.log
轮转: 每日轮转，保留30天
```

### 13. 部署和分发 / Deployment and Distribution

#### 13.1 打包要求 / Packaging Requirements
```python
# pyproject.toml 配置
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "terrain-tunneling-calculator"
version = "0.1.0"
description = "Professional tunnel planning and visualization tool"
dependencies = [
    "numpy>=1.21.0",
    "matplotlib>=3.5.0",
    "plotly>=5.0.0",
    "customtkinter>=5.0.0",
    "scipy>=1.7.0"
]
```

#### 13.2 安装脚本 / Installation Scripts
```python
# 环境设置脚本
# scripts/setup_env.ps1 (Windows)
# scripts/setup_env.sh (Linux/Mac)

# 功能:
1. Python环境检查 (3.11+)
2. 依赖包安装
3. 配置文件初始化
4. 快捷方式创建
5. 环境变量设置
```

### 14. AI实现指导原则 / AI Implementation Guidelines

#### 14.1 代码生成优先级 / Code Generation Priority
```
优先级1 (核心功能):
- 数据模型定义 (models/)
- 核心算法实现 (services/)
- 基础GUI框架 (gui/)

优先级2 (重要功能):
- 可视化服务 (visualization_2d/3d)
- 动画系统 (animation)
- 导出功能 (export)

优先级3 (增强功能):
- 高级GUI组件
- 性能优化
- 插件系统
```

#### 14.2 代码质量标准 / Code Quality Standards
```python
# 代码规范要求
1. 类型注解:
   - 所有公共方法必须有类型注解
   - 使用typing模块的类型提示
   - 复杂数据结构使用TypedDict

2. 文档字符串:
   - 所有类和方法必须有docstring
   - 使用Google风格的docstring
   - 包含参数说明和返回值

3. 错误处理:
   - 使用具体的异常类型
   - 提供有意义的错误消息
   - 记录详细的错误日志

4. 测试驱动:
   - 先写测试，再实现功能
   - 单元测试覆盖率>80%
   - 集成测试覆盖主要流程
```

#### 14.3 实现检查清单 / Implementation Checklist
```
□ 数据模型完整性和类型安全
□ 核心算法的正确性和性能
□ GUI的响应性和用户体验
□ 可视化的准确性和美观性
□ 错误处理的完备性
□ 测试覆盖率和质量
□ 文档的完整性和准确性
□ 代码的可维护性和扩展性
□ 性能优化和内存管理
□ 部署和分发的便利性
```

---

## 总结 / Summary

这份需求文档为AI工具提供了完整的地形隧道计算器实现指导。文档包含了：

1. **架构设计**: 模块化、可扩展的系统架构
2. **核心算法**: 详细的算法规范和实现要求
3. **数据模型**: 完整的业务实体定义
4. **可视化系统**: 2D/3D可视化的技术规范
5. **用户界面**: 现代化GUI的设计要求
6. **质量保证**: 测试、验证、性能优化标准
7. **部署分发**: 完整的打包和部署流程

AI工具应该按照这个文档的规范，优先实现核心功能，确保代码质量，并遵循最佳实践。