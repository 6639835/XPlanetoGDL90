# 📝 GDL-90接收器日志功能说明

## 🎯 日志功能概览

GDL-90接收器现在支持完整的日志记录功能，可以将所有接收到的消息和系统信息记录到文件中，避免终端信息过多的问题。

## 📋 日志类型

### 1. 主日志文件 (`*.log`)
记录系统信息：
- 接收器启动/停止事件
- 错误和警告信息
- 统计信息
- 系统状态变化

### 2. 消息日志文件 (`*_messages.log`)
专门记录GDL-90消息详情：
- JSON格式的结构化数据
- 每个消息的完整内容
- 时间戳和发送方信息
- 消息序号

## 🚀 使用方法

### 基本日志记录
```bash
# 记录到默认日志文件
python gdl90_receiver.py -l gdl90_receiver.log

# 同时显示终端输出和记录日志
python gdl90_receiver.py -l receiver.log --traffic-only
```

### 安静模式（仅日志）
```bash
# 只记录日志，不显示终端输出
python gdl90_receiver.py -l receiver.log --quiet

# 安静模式 + 特定消息类型
python gdl90_receiver.py -l receiver.log --quiet --traffic-only
```

### 不同日志级别
```bash
# 调试级别（最详细）
python gdl90_receiver.py -l receiver.log --log-level DEBUG

# 信息级别（默认）
python gdl90_receiver.py -l receiver.log --log-level INFO

# 警告级别（只记录警告和错误）
python gdl90_receiver.py -l receiver.log --log-level WARNING

# 错误级别（只记录错误）
python gdl90_receiver.py -l receiver.log --log-level ERROR
```

## 📄 日志文件格式

### 主日志文件示例 (`receiver.log`)
```
2024-01-15 14:30:25 - GDL90Receiver - INFO - GDL-90接收器启动 - 端口: 4000
2024-01-15 14:30:55 - GDL90Receiver - INFO - 统计信息 - 总计: 245, 心跳: 60, 自机: 120, 交通: 65, CRC错误: 0
2024-01-15 14:31:25 - GDL90Receiver - INFO - 统计信息 - 总计: 490, 心跳: 120, 自机: 240, 交通: 130, CRC错误: 0
2024-01-15 14:35:10 - GDL90Receiver - INFO - GDL-90接收器停止
```

### 消息日志文件示例 (`receiver_messages.log`)
```json
2024-01-15 14:30:25.123 - {"seq": 1, "timestamp": "2024-01-15T14:30:25.123456", "sender": "10.16.25.146:54321", "message_type": "Traffic Report", "data": {"icao_address": "0x100001", "latitude": 37.621311, "longitude": -122.378968, "altitude_ft": 2500, "ground_speed_kts": 150, "vertical_speed_fpm": 800, "track_deg": 90.0, "callsign": "UAL123", "emitter_category": 1, "nav_integrity": 11, "nav_accuracy": 10, "emergency_code": 0}}

2024-01-15 14:30:25.623 - {"seq": 2, "timestamp": "2024-01-15T14:30:25.623789", "sender": "10.16.25.146:54321", "message_type": "Heartbeat", "data": {"timestamp": "14:30:25", "timestamp_raw": 52225, "status1": "0x81", "status2": "0x01", "message_count": 1}}
```

## 📊 日志分析

### 使用JSON工具分析消息
```bash
# 统计消息类型
grep "Traffic Report" receiver_messages.log | wc -l

# 提取特定ICAO地址的消息
grep "0x100001" receiver_messages.log

# 使用jq分析JSON数据（如果安装了jq）
grep "Traffic Report" receiver_messages.log | cut -d' ' -f3- | jq '.data.callsign'
```

### Python脚本分析示例
```python
import json
import datetime

def analyze_log(log_file):
    traffic_count = 0
    callsigns = set()
    
    with open(log_file, 'r') as f:
        for line in f:
            if 'Traffic Report' in line:
                try:
                    # 提取JSON部分
                    json_str = line.split(' - ', 2)[2]
                    data = json.loads(json_str)
                    
                    traffic_count += 1
                    callsigns.add(data['data']['callsign'])
                except:
                    continue
    
    print(f"交通报告总数: {traffic_count}")
    print(f"唯一呼号: {len(callsigns)}")
    print(f"呼号列表: {sorted(callsigns)}")

# 使用方法
analyze_log('receiver_messages.log')
```

## 🔧 高级配置

### 自动日志轮转（需要额外脚本）
```bash
# 创建按日期命名的日志文件
LOG_FILE="logs/gdl90_$(date +%Y%m%d_%H%M%S).log"
python gdl90_receiver.py -l "$LOG_FILE" --quiet
```

### 组合使用示例
```bash
# 监控交通报告并记录详细日志
python gdl90_receiver.py \
    --traffic-only \
    --no-errors \
    -l "logs/traffic_$(date +%Y%m%d).log" \
    --log-level DEBUG

# 后台运行（Linux/macOS）
nohup python gdl90_receiver.py -l receiver.log --quiet &

# Windows后台运行
start /B python gdl90_receiver.py -l receiver.log --quiet
```

## 🛠️ 故障排除

### 问题：日志文件权限错误
```bash
# 确保日志目录存在且有写权限
mkdir -p logs
chmod 755 logs
```

### 问题：日志文件过大
```bash
# 检查日志文件大小
ls -lh *.log

# 清理旧日志（谨慎操作）
find . -name "*.log" -mtime +7 -delete
```

### 问题：JSON格式错误
```bash
# 验证JSON格式
python -m json.tool < receiver_messages.log
```

## 💡 使用建议

### 1. 开发和调试
```bash
# 详细日志 + 终端显示
python gdl90_receiver.py -l debug.log --log-level DEBUG --traffic-only
```

### 2. 生产监控
```bash
# 安静模式 + 定期轮转
python gdl90_receiver.py -l receiver.log --quiet --no-heartbeat
```

### 3. 数据收集
```bash
# 收集所有消息数据用于分析
python gdl90_receiver.py -l data_collection.log --quiet
```

### 4. 性能测试
```bash
# 最小开销模式
python gdl90_receiver.py -l perf.log --quiet --no-heartbeat --no-ownship
```

## 📈 日志文件管理

### 定期清理脚本
```bash
#!/bin/bash
# cleanup_logs.sh - 清理7天前的日志
find . -name "*.log" -mtime +7 -delete
echo "已清理7天前的日志文件"
```

### 日志压缩
```bash
# 压缩旧日志文件
gzip receiver_*.log

# 查看压缩日志
zcat receiver_messages.log.gz | grep "Traffic Report"
```

这个日志系统让你可以高效地记录和分析所有GDL-90通信，而不会被终端输出干扰！
