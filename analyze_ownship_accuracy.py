#!/usr/bin/env python3
"""
分析Ownship Report中的精度信息 (NIC/NACp)
"""

import sys
import os
import binascii

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import InlineGDL90Encoder

def analyze_ownship_accuracy():
    """分析Ownship Report中的精度字段"""
    print("🔍 分析 Ownship Report 中的精度信息")
    print("="*60)
    
    encoder = InlineGDL90Encoder("TEST")
    
    # 创建测试数据
    test_data = {
        'lat': 47.6062,      # 西雅图纬度
        'lon': -122.3321,    # 西雅图经度
        'alt': 2500.0,       # 2500英尺
        'speed': 150.0,      # 150节
        'track': 270.0,      # 西向
        'vs': 500.0          # 上升500英尺/分钟
    }
    
    print("测试数据:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    
    # 生成Ownship Report
    msg = encoder.create_position_report(test_data)
    
    print(f"\n生成的Ownship Report:")
    print(f"完整消息: {binascii.hexlify(msg).decode()}")
    
    # 解析消息
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
        
        print(f"消息内容: {binascii.hexlify(unescaped[:-2]).decode()}")
        
        if len(unescaped) >= 14:  # 确保有足够长度到达NIC/NACp字段
            print(f"\n📋 字段详细分析:")
            print(f"消息ID: 0x{unescaped[0]:02X}")
            
            # 找到NIC/NACp字段的位置
            # Ownship Report格式: ID(1) + status/addr(1) + ICAO(3) + lat(3) + lon(3) + alt(2) + nic/nacp(1) + ...
            if len(unescaped) >= 14:
                nic_nacp_byte = unescaped[13]  # 第14个字节 (index 13)
                nic = (nic_nacp_byte & 0xF0) >> 4
                nacp = nic_nacp_byte & 0x0F
                
                print(f"NIC/NACp字节位置: 字节14 (index 13)")
                print(f"NIC/NACp字节值: 0x{nic_nacp_byte:02X}")
                print(f"NIC (Navigation Integrity Category): {nic}")
                print(f"NACp (Navigation Accuracy Category): {nacp}")
                
                # 解释NIC和NACp的含义
                print(f"\n📖 精度含义:")
                nic_meanings = {
                    0: "Unknown",
                    1: "< 20.0 NM",
                    2: "< 8.0 NM", 
                    3: "< 4.0 NM",
                    4: "< 2.0 NM",
                    5: "< 1.0 NM",
                    6: "< 0.6 NM",
                    7: "< 0.2 NM",
                    8: "< 0.1 NM",
                    9: "HPL < 75m, VPL < 112m",
                    10: "HPL < 25m, VPL < 37.5m",
                    11: "HPL < 7.5m, VPL < 11m"
                }
                
                nacp_meanings = {
                    0: "Unknown",
                    1: "< 10.0 NM",
                    2: "< 4.0 NM",
                    3: "< 2.0 NM", 
                    4: "< 1.0 NM",
                    5: "< 0.5 NM",
                    6: "< 0.3 NM",
                    7: "< 0.1 NM",
                    8: "< 0.05 NM",
                    9: "HFOM < 30m, VFOM < 45m",
                    10: "HFOM < 10m, VFOM < 15m",
                    11: "HFOM < 3m, VFOM < 4m"
                }
                
                print(f"NIC {nic}: {nic_meanings.get(nic, 'Reserved')}")
                print(f"NACp {nacp}: {nacp_meanings.get(nacp, 'Reserved')}")
                
                # 评估精度等级
                if nic >= 10 and nacp >= 9:
                    print(f"\n✅ 高精度GPS: 位置精度 < 25-30米")
                elif nic >= 7 and nacp >= 7:
                    print(f"\n🟡 中等精度GPS: 位置精度 < 0.1-0.2海里")
                elif nic >= 4 and nacp >= 4:
                    print(f"\n🟠 基础精度GPS: 位置精度 < 1-2海里")
                else:
                    print(f"\n🔴 低精度或未知精度")
                
                return True
        
        return False

def compare_with_traffic():
    """对比Ownship和Traffic Report的精度字段"""
    print("\n" + "="*60)
    print("🔄 对比 Ownship vs Traffic Report 精度字段")
    print("="*60)
    
    encoder = InlineGDL90Encoder("TEST")
    
    # 相同的测试数据
    base_data = {
        'lat': 47.6062,
        'lon': -122.3321,
        'alt': 2500.0,
        'speed': 150.0,
        'track': 270.0,
        'vs': 500.0
    }
    
    # Ownship数据
    ownship_msg = encoder.create_position_report(base_data)
    
    # Traffic数据  
    traffic_data = base_data.copy()
    traffic_data.update({
        'callsign': 'TEST001',
        'icao_address': 0x123456
    })
    traffic_msg = encoder.create_traffic_report(traffic_data)
    
    def extract_nic_nacp(msg):
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
            
            if unescaped[0] == 0x0A and len(unescaped) >= 14:  # Ownship
                nic_nacp_byte = unescaped[13]
                return (nic_nacp_byte & 0xF0) >> 4, nic_nacp_byte & 0x0F
            elif unescaped[0] == 0x14 and len(unescaped) >= 14:  # Traffic  
                nic_nacp_byte = unescaped[13]  # Traffic Report的NIC/NACp在不同位置
                return (nic_nacp_byte & 0xF0) >> 4, nic_nacp_byte & 0x0F
        
        return None, None
    
    ownship_nic, ownship_nacp = extract_nic_nacp(ownship_msg)
    traffic_nic, traffic_nacp = extract_nic_nacp(traffic_msg)
    
    print("精度字段对比:")
    print(f"Ownship Report (ID 0x0A):")
    print(f"  NIC: {ownship_nic}, NACp: {ownship_nacp}")
    print(f"Traffic Report (ID 0x14):")
    print(f"  NIC: {traffic_nic}, NACp: {traffic_nacp}")
    
    if ownship_nic == traffic_nic and ownship_nacp == traffic_nacp:
        print("✅ 两种报告使用相同的精度值")
    else:
        print("⚠️  不同报告使用了不同的精度值")
        
    print(f"\n💡 结论:")
    print("Ownship Report 确实包含并发送 NIC/NACp 精度信息!")
    print("这些信息告诉接收器自己飞机的GPS定位精度等级。")

if __name__ == "__main__":
    analyze_ownship_accuracy()
    compare_with_traffic()
