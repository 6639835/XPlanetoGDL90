#!/usr/bin/env python3
"""
对比官方example验证我的实现
"""

print("🔍 分析官方Traffic Report Example")
print("="*60)

# 官方example数据
print("官方Example数据:")
print("- ICAO地址 (octal): 526425118")
print("- 纬度: 44.90708° N") 
print("- 经度: -122.99488° W")
print("- 高度: 5,000 ft")
print("- 地速: 123 knots at 45°")
print("- 垂直速度: 64 FPM 上升")
print("- 呼号: N825V")

# 转换ICAO地址 - 文档中的526425118看起来像是打字错误，应该是十进制或十六进制
# 从example字节来看: 0xAB4549 = 11224393 (decimal)
icao_from_example = 0xAB4549
print(f"\nICAO地址分析:")
print(f"- Example字节显示: 0xAB4549")
print(f"- Decimal: {icao_from_example}")
print(f"- Hex: 0x{icao_from_example:06X}")

# 官方example的字节序列
example_bytes = [
    0x14,  # Message ID
    0x00,  # st  
    0xAB,  # aa
    0x45,  # aa
    0x49,  # aa
    0x1F,  # ll
    0xEF,  # ll
    0x15,  # ll
    0xA8,  # nn
    0x89,  # nn
    0x78,  # nn
    0x0F,  # dd
    0x09,  # dm
    0xA9,  # ia
    0x07,  # hh
    0xB0,  # hv
    0x01,  # vv
    0x20,  # tt
    0x01,  # ee
    0x4E,  # cc (N)
    0x38,  # cc (8)
    0x32,  # cc (2)
    0x35,  # cc (5)
    0x56,  # cc (V)
    0x20,  # cc (space)
    0x20,  # cc (space)
    0x20,  # cc (space)
    0x00   # px
]

print(f"\n官方Example字节序列:")
hex_str = " ".join([f"{b:02X}" for b in example_bytes])
print(f"Hex: {hex_str}")

print(f"\n关键字段分析:")
print(f"字节1 (st): 0x{example_bytes[1]:02X}")
st_byte = example_bytes[1]
s = (st_byte >> 7) & 0x1
t = (st_byte >> 4) & 0x7
remaining = st_byte & 0x0F
print(f"  - s (Traffic Alert): {s}")
print(f"  - t (Address Type): {t}") 
print(f"  - 剩余4位: 0x{remaining:X}")

print(f"\nICAO地址字节 (aa aa aa):")
icao_from_bytes = (example_bytes[2] << 16) | (example_bytes[3] << 8) | example_bytes[4]
print(f"  - 字节2: 0x{example_bytes[2]:02X}")
print(f"  - 字节3: 0x{example_bytes[3]:02X}") 
print(f"  - 字节4: 0x{example_bytes[4]:02X}")
print(f"  - 组合ICAO: 0x{icao_from_bytes:06X}")
print(f"  - 期望ICAO: 0x{icao_from_example:06X}")

if icao_from_bytes == icao_from_example:
    print("✅ ICAO地址匹配!")
else:
    print("❌ ICAO地址不匹配!")
    
print(f"\n结论:")
print("官方格式 'st aa aa aa' 的含义:")
print("- st: s(1位) + t(3位) + 4位填充(通常为0)")
print("- aa aa aa: 完整的24位ICAO地址(3字节)")
print("- 不是我之前理解的ICAO地址分散在st中!")
