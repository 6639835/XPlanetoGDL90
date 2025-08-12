#!/usr/bin/env python3
"""
测试官方GDL-90 Traffic Report示例
用于验证接收器解码的准确性

官方示例数据:
- ICAO地址: 52642511₈ (八进制) = 0xAB4549 (十六进制)
- 纬度: 44.90708° (North)
- 经度: -122.99488° (West) 
- 高度: 5,000 feet
- 地速: 123 knots at 45°
- 垂直速度: 64 FPM climb
- 呼号: N825V
"""

import socket
import struct
import time
import binascii

# 从main.py导入CRC计算函数
GDL90_CRC16_TABLE = (
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0,
)

def gdl90_crc_compute(data):
    """计算GDL90 CRC-16-CCITT校验码"""
    mask16bit = 0xffff
    crc_array = bytearray()
    
    crc = 0
    for c in data:
        m = (crc << 8) & mask16bit
        crc = GDL90_CRC16_TABLE[(crc >> 8)] ^ m ^ c
    
    crc_array.append(crc & 0x00ff)
    crc_array.append((crc & 0xff00) >> 8)
    return crc_array

def escape_message(msg):
    """转义GDL-90消息"""
    msg_new = bytearray()
    escape_char = 0x7d
    chars_to_escape = [0x7d, 0x7e]
    
    for c in msg:
        if c in chars_to_escape:
            msg_new.append(escape_char)  # 插入转义字符
            msg_new.append(c ^ 0x20)     # 修改原字节
        else:
            msg_new.append(c)
    
    return msg_new

def create_official_traffic_report():
    """创建官方示例的Traffic Report消息"""
    
    # 官方示例的原始数据 (来自Table 12)
    official_data = bytearray([
        0x14,  # Message ID
        0x00,  # st (状态字节)
        0xAB, 0x45, 0x49,  # aa aa aa (ICAO地址)
        0x1F, 0xEF, 0x15,  # ll ll ll (纬度)
        0xA8, 0x89, 0x78,  # nn nn nn (经度)
        0x0F, 0x09,        # dd dm (高度 + 杂项)
        0xA9,              # ia (NIC + NACp)
        0x07, 0xB0, 0x01,  # hh hv vv (水平速度 + 垂直速度)
        0x20,              # tt (航向)
        0x01,              # ee (发射器类别)
        0x4E, 0x38, 0x32, 0x35, 0x56, 0x20, 0x20, 0x20,  # cc...cc (呼号 "N825V   ")
        0x00               # px (应急代码 + 备用)
    ])
    
    # 计算CRC
    crc_bytes = gdl90_crc_compute(official_data)
    official_data.extend(crc_bytes)
    
    # 转义
    escaped_data = escape_message(official_data)
    
    # 添加帧标记
    framed_message = bytearray([0x7e])
    framed_message.extend(escaped_data)
    framed_message.append(0x7e)
    
    return framed_message

def send_official_example():
    """发送官方示例给接收器测试"""
    
    # 创建官方示例消息
    message = create_official_traffic_report()
    
    print("🧪 GDL-90官方Traffic Report示例测试")
    print("=" * 60)
    print("📊 官方示例数据:")
    print("   ICAO地址: 52642511₈ (八进制) = 0xAB4549")
    print("   纬度: 44.90708° (North)")
    print("   经度: -122.99488° (West)")
    print("   高度: 5,000 feet")
    print("   地速: 123 knots")
    print("   航向: 45°")
    print("   垂直速度: 64 FPM (climb)")
    print("   呼号: N825V")
    print("   发射器类别: Light (1)")
    print("   NIC: 10, NACp: 9")
    print()
    print(f"📦 生成的消息 ({len(message)} 字节):")
    print(f"   十六进制: {binascii.hexlify(message).decode().upper()}")
    print()
    
    # 发送消息
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        target_ip = "127.0.0.1"  # 本地测试
        target_port = 4000       # 默认接收器端口
        
        print(f"📡 发送到 {target_ip}:{target_port}")
        print("💡 确保接收器正在运行: python gdl90_receiver.py --traffic-only")
        print()
        
        # 发送消息
        sock.sendto(message, (target_ip, target_port))
        print("✅ 官方示例已发送!")
        print()
        print("🔍 期望的接收器输出应该显示:")
        print("   📋 消息类型: Traffic Report")
        print("   🏷️  ICAO地址: 0xAB4549")
        print("   🌍 位置: LAT=44.907080°, LON=-122.994880°")
        print("   📏 高度: 5000ft")
        print("   🚀 地速: 123 kts")
        print("   ⬆️  垂直速度: 64 fpm")
        print("   🧭 航向: 45.0°")
        print("   📻 呼号: 'N825V   '")
        print("   ✈️  发射器类别: 1")
        print("   📡 导航完整性: 10, 精度: 9")
        print()
        print("如果接收器显示上述信息，说明解码完全正确! 🎉")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ 发送失败: {e}")

def analyze_official_data():
    """分析官方示例数据的详细构成"""
    
    print("\n📋 官方示例数据分析")
    print("=" * 60)
    
    # 原始数据
    data = bytearray([
        0x14,  # Message ID
        0x00,  # st
        0xAB, 0x45, 0x49,  # ICAO地址
        0x1F, 0xEF, 0x15,  # 纬度
        0xA8, 0x89, 0x78,  # 经度  
        0x0F, 0x09,        # 高度 + 杂项
        0xA9,              # NIC + NACp
        0x07, 0xB0, 0x01,  # 速度
        0x20,              # 航向
        0x01,              # 发射器类别
        0x4E, 0x38, 0x32, 0x35, 0x56, 0x20, 0x20, 0x20,  # 呼号
        0x00               # 应急代码
    ])
    
    # 解析ICAO地址
    icao = (data[2] << 16) | (data[3] << 8) | data[4]
    print(f"🏷️  ICAO地址: 0x{icao:06X} (十六进制)")
    print(f"           {oct(icao)} (八进制)")
    
    # 解析纬度
    lat_raw = (data[5] << 16) | (data[6] << 8) | data[7]
    if lat_raw & 0x800000:
        lat_raw = lat_raw - 0x1000000
    latitude = lat_raw * (180.0 / 0x800000)
    print(f"🌍 纬度: {latitude:.6f}°")
    
    # 解析经度
    lon_raw = (data[8] << 16) | (data[9] << 8) | data[10]
    if lon_raw & 0x800000:
        lon_raw = lon_raw - 0x1000000
    longitude = lon_raw * (180.0 / 0x800000)
    print(f"🌍 经度: {longitude:.6f}°")
    
    # 解析高度
    alt_raw = (data[11] << 8) | data[12]
    altitude = ((alt_raw & 0xfff0) >> 4) * 25 - 1000
    misc = alt_raw & 0x0f
    print(f"📏 高度: {altitude}ft (杂项: {misc})")
    
    # 解析NIC和NACp
    nic = (data[13] & 0xf0) >> 4
    nacp = data[13] & 0x0f
    print(f"📡 NIC: {nic}, NACp: {nacp}")
    
    # 解析速度
    speed_raw = (data[14] << 16) | (data[15] << 8) | data[16]
    h_vel = (speed_raw & 0xfff000) >> 12
    v_vel = speed_raw & 0xfff
    if v_vel & 0x800:
        v_vel = v_vel - 0x1000
    vs_fpm = v_vel * 64
    print(f"🚀 地速: {h_vel} kts")
    print(f"⬆️  垂直速度: {vs_fpm} fpm")
    
    # 解析航向
    track = data[17] * (360.0 / 256)
    print(f"🧭 航向: {track:.1f}°")
    
    # 解析发射器类别
    emitter = data[18]
    print(f"✈️  发射器类别: {emitter}")
    
    # 解析呼号
    callsign = data[19:27].decode('ascii', errors='replace')
    print(f"📻 呼号: '{callsign}'")
    
    # 解析应急代码
    emergency = (data[27] & 0xf0) >> 4
    spare = data[27] & 0x0f
    print(f"🚨 应急代码: {emergency} (备用: {spare})")

def main():
    """主程序"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试官方GDL-90 Traffic Report示例")
    parser.add_argument('--analyze', '-a', action='store_true', help='仅分析数据，不发送')
    parser.add_argument('--port', '-p', type=int, default=4000, help='接收器端口')
    parser.add_argument('--ip', type=str, default='127.0.0.1', help='接收器IP地址')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_official_data()
    else:
        send_official_example()

if __name__ == "__main__":
    main()
