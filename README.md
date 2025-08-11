# X-Plane 12 到 FDPRO GDL-90 数据广播器

这是一个Python程序，用于将X-Plane 12飞行模拟器的实时飞行数据转换为GDL-90格式，并广播给FDPRO等飞行显示应用。

## ✈️ 项目功能

- 🔗 **自动连接X-Plane 12**：使用内置XPlane-UDP库自动发现和连接X-Plane
- 📡 **实时数据传输**：获取飞机位置、高度、速度、航向等关键飞行参数
- 🛰️ **GDL-90格式转换**：将X-Plane数据转换为标准GDL-90格式
- 📤 **UDP广播**：通过UDP协议广播数据到FDPRO应用
- 🔄 **心跳监控**：定期发送心跳信号确保连接稳定
- 🛡️ **状态检测**：自动检测X-Plane运行状态

## 🎯 适用场景

- 在iPad等设备上使用FDPRO作为飞行显示器
- 将X-Plane 12作为飞行训练模拟器
- 需要将模拟器数据传输到外部飞行应用

## 📋 系统要求

- Python 3.6+
- X-Plane 12
- FDPRO应用
- 网络连接（局域网或本机回环）

## 🚀 快速开始

### 1. 下载和运行

```bash
# 克隆或下载项目
git clone <your-repo-url>
cd XPlanetoFDPro

# 直接运行（无需安装依赖）
python3 main.py
```

### 2. X-Plane 12 设置

**方法1：Data Output（推荐）**

1. 启动X-Plane 12
2. 进入 `Settings → Data Input & Output → Data Set`
3. 勾选以下数据项的 `UDP` 列：
   - ✅ 17 - lat, lon, altitude
   - ✅ 18 - speed, Mach, VVI
   - ✅ 19 - pitch, roll, headings
4. 点击 `Internet` 标签
5. 设置IP地址：
   - 本机运行：`127.0.0.1`
   - 网络共享：你的本机IP地址
6. 设置端口：`49002`

**方法2：RREF连接（备用）**

1. 进入 `Settings → Network`
2. 勾选 `Accept incoming connections`
3. 端口设为：`49000`

### 3. FDPRO 设置

1. 启动FDPRO应用
2. 确保FDPRO监听端口为 `4000`
3. 配置接收GDL-90数据

### 4. 网络配置

在 `main.py` 中配置目标设备IP：

```python
# 修改这些变量以匹配你的网络环境
BROADCAST_IP = "10.16.25.146"    # iPad/FDPRO设备的IP地址
FDPRO_PORT = 4000                # FDPRO监听端口
```

## 🔧 配置选项

### 网络配置
```python
XPLANE_IP = "192.168.0.1"        # X-Plane主机IP
XPLANE_PORT = 49000              # X-Plane命令端口
XPLANE_DATA_PORT = 49002         # Data Output接收端口
FDPRO_PORT = 4000               # FDPRO监听端口
```

### 飞机设置
```python
# 在GDL90Encoder初始化中修改
encoder = GDL90Encoder(aircraft_id="PYTHON1")  # 8字符呼号
```

## 📊 数据传输详情

### 发送的数据类型

**心跳消息（每秒1次）**
- GDL-90心跳信号
- 确保连接稳定

**位置报告（每秒2次）**
- 纬度/经度（度）
- 高度（英尺 MSL）
- 地速（节）
- 航向（度）
- 垂直速度（英尺/分钟）
- 姿态数据（俯仰、横滚）

### 数据格式转换

- **高度**：米 → 英尺（×3.28084）
- **速度**：米/秒 → 节（×1.94384）
- **GDL-90编码**：符合标准GDL-90协议规范

## 🔍 故障排除

### X-Plane连接问题

1. **检查X-Plane是否运行**
   ```
   ✅ 找到X-Plane: {'IP': '127.0.0.1', 'Port': 49000, ...}
   ```

2. **检查网络设置**
   - 确保防火墙允许UDP连接
   - 验证IP地址配置正确

3. **检查数据输出**
   - 确保飞机已加载
   - 验证Data Output设置正确

### FDPRO连接问题

1. **检查IP地址**
   - 确认FDPRO设备的IP地址
   - 测试网络连通性

2. **检查端口**
   - 验证FDPRO监听端口4000
   - 确认无端口冲突

### 数据接收问题

1. **无数据显示**
   ```
   ⚠️  5秒后仍未收到数据
   ```
   - 重新检查X-Plane Data Output设置
   - 确保飞机在飞行中（不在静止状态）

2. **连接超时**
   - 检查网络连接
   - 重启X-Plane和程序

## 📝 日志输出示例

```
🔍 检查X-Plane状态...
✅ 检测到X-Plane运行在: 127.0.0.1
✅ 成功使用XPlane-UDP方式接收数据
💓 发送心跳到 10.16.25.146:4000 (8 bytes): 7e0081017abc5d5e
✈️  位置报告到 10.16.25.146:4000 (42 bytes)
   LAT=37.621311, LON=-122.378955, ALT=131ft
   GDL90 hex: 7e0a00abcdef1a2b3c4d5e6f708192a3b4c5d6e7f8...
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目基于开源协议发布，具体许可证信息请参考项目根目录。

## ⚠️ 免责声明

本工具仅用于飞行模拟和教育目的，不得用于实际航空飞行。使用者需自行承担使用风险。

---

**作者**: Justin
**版本**: 1.0  
**最后更新**: 2025
