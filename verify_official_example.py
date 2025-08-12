#!/usr/bin/env python3
"""
根据官方Traffic Report Example验证我的实现
"""

import sys
import os
import binascii
import struct
import math

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import InlineGDL90Encoder, TrafficTarget

def analyze_official_example():
    """分析官方example"""
    print("🔍 官方 Traffic Report Example 分析")
    print("="*60)
    
    # 官方example数据
    print("官方Example数据:")
    print("- ICAO地址 (octal): 526425118 (疑似文档错误)")
    print("- 纬度: 44.90708° N") 
    print("- 经度: -122.99488° W")
    print("- 高度: 5,000 ft")
    print("- 地速: 123 knots at 45°")
    print("- 垂直速度: 64 FPM 上升")
    print("- 呼号: N825V")
    print("- NIC: 10, NACp: 9")
    
    # 官方example的字节序列（不含CRC）
    official_bytes = [
        0x14,  # 1 - Message ID
        0x00,  # 2 - st  
        0xAB,  # 3 - aa
        0x45,  # 4 - aa
        0x49,  # 5 - aa
        0x1F,  # 6 - ll
        0xEF,  # 7 - ll
        0x15,  # 8 - ll
        0xA8,  # 9 - nn
        0x89,  # 10 - nn
        0x78,  # 11 - nn
        0x0F,  # 12 - dd
        0x09,  # 13 - dm
        0xA9,  # 14 - ia
        0x07,  # 15 - hh
        0xB0,  # 16 - hv
        0x01,  # 17 - vv
        0x20,  # 18 - tt
        0x01,  # 19 - ee
        0x4E,  # 20 - cc (N)
        0x38,  # 21 - cc (8)
        0x32,  # 22 - cc (2)
        0x35,  # 23 - cc (5)
        0x56,  # 24 - cc (V)
        0x20,  # 25 - cc (space)
        0x20,  # 26 - cc (space)
        0x20,  # 27 - cc (space)
        0x00   # 28 - px
    ]
    
    print(f"\n官方Example字节序列:")
    hex_str = " ".join([f"{b:02X}" for b in official_bytes])
    print(f"Hex: {hex_str}")
    
    # 分析关键字段
    print(f"\n🔍 字段分析:")
    
    # ICAO地址
    icao_addr = (official_bytes[2] << 16) | (official_bytes[3] << 8) | official_bytes[4]
    print(f"ICAO地址: 0x{icao_addr:06X}")
    
    # 纬度解码
    lat_raw = (official_bytes[5] << 16) | (official_bytes[6] << 8) | official_bytes[7]
    if lat_raw & 0x800000:  # 检查符号位
        lat_raw = lat_raw - 0x1000000  # 2的补码
    lat_degrees = lat_raw * (180.0 / (1 << 23))  # 转换为度
    
    # 经度解码
    lon_raw = (official_bytes[8] << 16) | (official_bytes[9] << 8) | official_bytes[10]
    if lon_raw & 0x800000:  # 检查符号位
        lon_raw = lon_raw - 0x1000000  # 2的补码
    lon_degrees = lon_raw * (180.0 / (1 << 23))  # 转换为度
    
    # 高度解码
    alt_raw = (official_bytes[11] << 4) | ((official_bytes[12] & 0xF0) >> 4)
    alt_feet = (alt_raw * 25) - 1000
    misc = official_bytes[12] & 0x0F
    
    # NIC和NACp
    nic = (official_bytes[13] & 0xF0) >> 4
    nacp = official_bytes[13] & 0x0F
    
    # 水平速度
    h_vel_raw = (official_bytes[14] << 4) | ((official_bytes[15] & 0xF0) >> 4)
    
    # 垂直速度
    v_vel_raw = ((official_bytes[15] & 0x0F) << 8) | official_bytes[16]
    if v_vel_raw & 0x800:  # 检查符号位
        v_vel_raw = v_vel_raw - 0x1000  # 12位2的补码
    v_vel_fpm = v_vel_raw * 64
    
    # 航向
    track_raw = official_bytes[17]
    track_degrees = track_raw * (360.0 / 256)
    
    # 发射器类别
    emitter_cat = official_bytes[18]
    
    # 呼号
    callsign = ''.join([chr(b) for b in official_bytes[19:27]]).rstrip()
    
    print(f"解码结果:")
    print(f"  纬度: {lat_degrees:.6f}° (期望: 44.90708)")
    print(f"  经度: {lon_degrees:.6f}° (期望: -122.99488)")
    print(f"  高度: {alt_feet}ft (期望: 5000)")
    print(f"  杂项: 0x{misc:X}")
    print(f"  NIC: {nic} (期望: 10)")
    print(f"  NACp: {nacp} (期望: 9)")
    print(f"  水平速度: {h_vel_raw}kt (期望: 123)")
    print(f"  垂直速度: {v_vel_fpm}fpm (期望: 64)")
    print(f"  航向: {track_degrees:.1f}° (期望: 45)")
    print(f"  发射器类别: {emitter_cat} (期望: 1=Light)")
    print(f"  呼号: '{callsign}' (期望: 'N825V')")
    
    return {
        'icao': icao_addr,
        'lat': lat_degrees,
        'lon': lon_degrees,
        'alt': alt_feet,
        'speed': h_vel_raw,
        'vs': v_vel_fpm,
        'track': track_degrees,
        'callsign': callsign
    }

def test_my_implementation():
    """测试我的实现"""
    print("\n" + "="*60)
    print("🧪 测试我的实现")
    print("="*60)
    
    # 使用官方example的数据创建测试
    encoder = InlineGDL90Encoder("TEST")
    
    # 从官方example推导的数据
    test_data = {
        'lat': 44.90708,
        'lon': -122.99488,
        'alt': 5000.0,
        'speed': 123.0,
        'track': 45.0,
        'vs': 64.0,
        'callsign': 'N825V',
        'icao_address': 0xAB4549  # 从官方example字节推导
    }
    
    print("使用的测试数据:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    
    # 生成消息
    msg = encoder.create_traffic_report(test_data)
    
    print(f"\n生成的消息:")
    print(f"完整消息: {binascii.hexlify(msg).decode()}")
    
    # 去掉开始/结束标记并反转义
    if len(msg) >= 4 and msg[0] == 0x7e and msg[-1] == 0x7e:
        escaped = msg[1:-1]
        unescaped = bytearray()
        i = 0
        while i < len(escaped):
            if escaped[i] == 0x7d and i + 1 < len(escaped):
                unescaped.append(escaped[i + 1] ^ 0x20)
                i += 2
            else:
                unescaped.append(escaped[i])
                i += 1
        
        print(f"消息内容: {binascii.hexlify(unescaped[:-2]).decode()}")  # 除去CRC
        print(f"CRC: {binascii.hexlify(unescaped[-2:]).decode()}")
        
        return unescaped[:-2]  # 返回除CRC外的消息内容
    
    return None

def compare_with_official(my_msg):
    """对比官方example"""
    print("\n" + "="*60)
    print("📊 对比分析")
    print("="*60)
    
    # 官方字节（除CRC）
    official = [
        0x14, 0x00, 0xAB, 0x45, 0x49, 0x1F, 0xEF, 0x15,
        0xA8, 0x89, 0x78, 0x0F, 0x09, 0xA9, 0x07, 0xB0,
        0x01, 0x20, 0x01, 0x4E, 0x38, 0x32, 0x35, 0x56,
        0x20, 0x20, 0x20, 0x00
    ]
    
    if my_msg and len(my_msg) >= len(official):
        print("字节对比:")
        print("位置  官方  我的  字段     匹配")
        print("-" * 40)
        
        field_names = [
            "ID", "st", "aa", "aa", "aa", "ll", "ll", "ll",
            "nn", "nn", "nn", "dd", "dm", "ia", "hh", "hv",
            "vv", "tt", "ee", "cc", "cc", "cc", "cc", "cc",
            "cc", "cc", "cc", "px"
        ]
        
        matches = 0
        for i in range(min(len(official), len(my_msg))):
            match = "✅" if official[i] == my_msg[i] else "❌"
            if official[i] == my_msg[i]:
                matches += 1
            field = field_names[i] if i < len(field_names) else "??"
            print(f"{i+1:2d}    0x{official[i]:02X}  0x{my_msg[i]:02X}  {field:6s}  {match}")
        
        print(f"\n匹配率: {matches}/{len(official)} ({matches/len(official)*100:.1f}%)")
        
        if matches == len(official):
            print("🎉 完全匹配官方example!")
        else:
            print("⚠️  存在差异，需要检查实现")

if __name__ == "__main__":
    # 分析官方example
    official_data = analyze_official_example()
    
    # 测试我的实现
    my_msg = test_my_implementation()
    
    # 对比结果
    compare_with_official(my_msg)
