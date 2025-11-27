# 地形隧道计算器 (Terrain Tunneling Calculator)

一个用于计算隧道开挖体积的Python应用程序，支持3D可视化和分析。

## 功能特性

- 地形等高线数据的导入和处理
- 隧道路径规划和几何计算
- 3D地形网格生成和可视化
- 隧道体积和表面积计算
- 高级分析功能（成本估算、风险评估等）
- GUI界面和命令行工具

## 安装和设置

### 系统要求

- Python 3.11 或更高版本
- 8GB RAM（推荐）
- 支持OpenGL的显卡（用于3D可视化）

### 安装步骤

1. 克隆仓库：
   ```
   git clone https://github.com/contour2/contour2.git
   cd contour2
   ```

2. 创建虚拟环境：
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

3. 安装依赖：
   ```
   pip install -e .
   ```

### 可选依赖

开发依赖：
```
pip install -e ".[dev]"
```

高级可视化：
```
pip install -e ".[advanced]"
```

## 使用方法

### GUI界面

启动图形界面：
```
python start_gui.py
```

或使用命令行：
```
python -m src.main --gui
```

### 命令行工具

生成示例数据：
```
python -m src.main --demo
```

加载并可视化地形文件：
```
python -m src.main --file data/terrain.json --output visualizations/
```

## 项目结构

```
contour2/
├── src/                    # 源代码
│   ├── gui/               # GUI界面组件
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑服务
│   └── utils/            # 工具函数
├── data/                  # 数据文件
├── tests/                 # 测试用例
├── docs/                  # 文档
└── scripts/               # 辅助脚本
```

## 数据格式

### 地形数据格式

地形数据应为JSON格式，包含等高线信息：

```json
{
  "metadata": {
    "name": "地形名称",
    "description": "地形描述",
    "coordinate_system": "投影坐标系",
    "units": "单位"
  },
  "contours": [
    {
      "elevation": 100.0,
      "points": [[x1, y1], [x2, y2], ...]
    },
    ...
  ]
}
```

### 隧道路径格式

隧道路径数据格式：

```json
{
  "waypoints": [
    {
      "x": 0.0,
      "y": 0.0,
      "elevation": 100.0,
      "radius": 5.0
    },
    ...
  ],
  "cross_section_type": "circular",
  "material_properties": {
    "density": 2500.0,
    "strength": 50.0,
    "permeability": 1e-9
  }
}
```

## API参考

### 主要类

- `TerrainMesh`: 表示3D地形网格
- `TunnelGeometry`: 表示隧道几何形状
- `TriangulationService`: 处理地形三角剖分
- `VolumeCalculator`: 计算开挖体积

### 示例代码

```python
from src.models.terrain_mesh import TerrainMesh
from src.models.tunnel_geometry import TunnelGeometry
from src.services.volume_calculator import VolumeCalculator

# 加载地形和隧道数据
terrain = TerrainMesh.from_file("terrain.json")
tunnel = TunnelGeometry.from_dict(tunnel_data)

# 计算体积
calculator = VolumeCalculator()
result = calculator.calculate_tunnel_volume(tunnel, terrain)

print(f"隧道体积: {result.volume} 立方米")
```

## 开发

### 运行测试

```
pytest
```

### 代码格式化

```
black src/
isort src/
```

### 类型检查

```
mypy src/
```

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 更新日志

### v0.1.0 (当前版本)
- 初始版本发布
- 基础地形和隧道计算功能
- GUI界面和3D可视化

## 联系方式

- 项目主页: https://github.com/contour2/contour2
- 问题反馈: https://github.com/contour2/contour2/issues
- 邮箱: team@contour2.com