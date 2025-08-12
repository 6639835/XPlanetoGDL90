#!/usr/bin/env python3
"""
详细检查我们的GDL90 Traffic Report实现是否符合官方规范
"""

import sys
import os
import binascii
import struct

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import InlineGDL90Encoder, TrafficTarget

def analyze_official_format():
    """分析官方Traffic Report格式"""
    print("🔍 官方 GDL-90 Traffic Report 格式分析")
    print("="*70)
    
    format_spec = "st aa aa aa ll ll ll nn nn nn dd dm ia hh hv vv tt ee cc cccc cc cc cc cc cc px"
    
    print("官方格式字符串:")
    print(f"  {format_spec}")
    print()
    
    print("字段定义:")
    print("  s  = Traffic Alert Status (1 bit)")
    print("  t  = Address Type (3 bits)")
    print("  aa = Participant Address (24 bits)")
    print("  ll = Latitude (24 bits)")
    print("  nn = Longitude (24 bits)")
    print("  dd = Altitude (12 bits)")
    print("  m  = Miscellaneous indicators (4 bits)")
    print("  i  = Navigation Integrity Category (4 bits)")
    print("  a  = Navigation Accuracy Category (4 bits)")
    print("  hh = Horizontal velocity (12 bits)")
    print("  vv = Vertical velocity (12 bits)")
    print("  tt = Track/Heading (8 bits)")
    print("  ee = Emitter Category (8 bits)")
    print("  cc = Call Sign (8 ASCII characters)")
    print("  p  = Emergency/Priority Code (4 bits)")
    print("  x  = Spare (4 bits)")
    print()
    
    print("字节布局分析:")
    print("  字节0: 消息ID = 0x14")
    print("  字节1: s(1) + t(3) + aa高4位")
    print("  字节2: aa中8位")
    print("  字节3: aa低8位")
    print("  字节4: ll高8位")
    print("  字节5: ll中8位")
    print("  字节6: ll低8位")
    print("  字节7: nn高8位")
    print("  字节8: nn中8位")
    print("  字节9: nn低8位")
    print("  字节10: dd高8位")
    print("  字节11: dd低4位 + m(4)")
    print("  字节12: i(4) + a(4)")
    print("  字节13: hh高8位")
    print("  字节14: hh低4位 + vv高4位")
    print("  字节15: vv低8位")
    print("  字节16: tt(8)")
    print("  字节17: ee(8)")
    print("  字节18-25: cc cc cc cc cc cc cc cc (8字节)")
    print("  字节26: p(4) + x(4)")
    print("  字节27-28: CRC16")
    
def check_current_implementation():
    """检查当前实现"""
    print("\n🔍 检查当前实现")
    print("="*70)
    
    encoder = InlineGDL90Encoder("TEST")
    target = TrafficTarget(1)
    target.data = {
        'lat': 47.7062,
        'lon': -122.2321, 
        'alt': 3500.0,
        'speed': 200.0,
        'track': 90.0,
        'vs': -200.0,
        'callsign': 'TEST001'
    }
    target.icao_address = 0x123456
    
    msg = encoder.create_traffic_report(target)
    
    print(f"生成的消息长度: {len(msg)} bytes")
    print(f"Hex: {binascii.hexlify(msg).decode()}")
    
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
        
        print(f"反转义后: {binascii.hexlify(unescaped).decode()}")
        print()
        
        if len(unescaped) >= 27:  # 至少需要消息ID + 26字节数据 + 2字节CRC
            print("字节分析:")
            for i, byte_val in enumerate(unescaped[:-2]):  # 除了CRC的所有字节
                print(f"  字节{i:2d}: 0x{byte_val:02X} ({byte_val:3d}) {byte_val:08b}")
            
            print(f"  CRC: {binascii.hexlify(unescaped[-2:]).decode()}")
            
            # 详细字段分析
            if unescaped[0] == 0x14:
                print(f"\n字段解析:")
                print(f"  消息ID: 0x{unescaped[0]:02X}")
                
                # 字节1: s(1) + t(3) + 4位填充
                byte1 = unescaped[1]
                s = (byte1 & 0x80) >> 7  # 最高位
                t = (byte1 & 0x70) >> 4  # 接下来3位
                padding = byte1 & 0x0F   # 低4位填充
                
                print(f"  字节1分解:")
                print(f"    Traffic Alert Status (s): {s}")
                print(f"    Address Type (t): {t}")
                print(f"    填充位: 0x{padding:X}")
                
                # 完整ICAO地址(字节2-4)
                icao_full = (unescaped[2] << 16) | (unescaped[3] << 8) | unescaped[4]
                print(f"  完整ICAO地址: 0x{icao_full:06X}")
                print(f"    字节2: 0x{unescaped[2]:02X}")
                print(f"    字节3: 0x{unescaped[3]:02X}")
                print(f"    字节4: 0x{unescaped[4]:02X}")
                
                # 纬度和经度(字节5-10)
                lat_raw = (unescaped[5] << 16) | (unescaped[6] << 8) | unescaped[7]
                if lat_raw & 0x800000:  # 负数
                    lat_raw = lat_raw - 0x1000000
                lat_decoded = lat_raw * (180.0 / 0x800000)
                
                lon_raw = (unescaped[8] << 16) | (unescaped[9] << 8) | unescaped[10]
                if lon_raw & 0x800000:  # 负数
                    lon_raw = lon_raw - 0x1000000
                lon_decoded = lon_raw * (180.0 / 0x800000)
                
                print(f"  纬度: {lat_decoded:.6f}°")
                print(f"  经度: {lon_decoded:.6f}°")
                
                # 高度(字节11-12)
                alt_byte1 = unescaped[11]
                alt_byte2 = unescaped[12] 
                alt_raw = (alt_byte1 << 4) | ((alt_byte2 & 0xF0) >> 4)
                alt_decoded = (alt_raw * 25) - 1000
                misc = alt_byte2 & 0x0F
                
                print(f"  高度: {alt_decoded}ft")
                print(f"  杂项指示器: 0x{misc:X}")
                
                # 验证ICAO地址是否符合预期
                expected_icao = 0x123456  # 测试数据中设定的
                if icao_full == expected_icao:
                    print(f"✅ ICAO地址编码正确!")
                else:
                    print(f"⚠️  ICAO地址: 期望0x{expected_icao:06X}, 实际0x{icao_full:06X}")
        
        return True
    
    return False

if __name__ == "__main__":
    analyze_official_format()
    check_current_implementation()
