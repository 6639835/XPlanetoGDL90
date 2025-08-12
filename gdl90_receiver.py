#!/usr/bin/env python3
"""
GDL-90 消息接收器和解码器
用于测试和验证X-Plane发送的GDL-90 Traffic Report消息

支持的消息类型:
- 0x00: Heartbeat (心跳)
- 0x0A: Ownship Report (自机位置报告)  
- 0x14: Traffic Report (交通目标报告)
"""

import socket
import struct
import time
import binascii
import threading
import datetime
import argparse
from typing import Optional, Dict, Any, List, Tuple

# 配置
DEFAULT_LISTEN_PORT = 4000  # 默认监听端口 (FDPRO端口)

# GDL-90 CRC-16-CCITT 查找表 (与main.py相同)
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

def gdl90_crc_compute(data: bytearray) -> bytearray:
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

def gdl90_crc_verify(data: bytearray) -> bool:
    """验证GDL90 CRC校验码"""
    if len(data) < 2:
        return False
    
    # 分离消息内容和CRC
    msg_data = data[:-2]
    received_crc = data[-2:]
    
    # 计算期望的CRC
    expected_crc = gdl90_crc_compute(msg_data)
    
    return received_crc == expected_crc

class GDL90Decoder:
    """GDL-90消息解码器"""
    
    def __init__(self):
        self.message_stats = {
            'total_messages': 0,
            'heartbeat_count': 0,
            'ownship_count': 0,
            'traffic_count': 0,
            'unknown_count': 0,
            'crc_errors': 0
        }
        
        # 消息类型映射
        self.message_types = {
            0x00: "Heartbeat",
            0x0A: "Ownship Report", 
            0x14: "Traffic Report"
        }
    
    def unescape_message(self, escaped_data: bytearray) -> bytearray:
        """反转义GDL-90消息"""
        unescaped = bytearray()
        i = 0
        
        while i < len(escaped_data):
            if escaped_data[i] == 0x7d and i + 1 < len(escaped_data):
                # 转义字符，下一个字节需要异或0x20
                unescaped.append(escaped_data[i + 1] ^ 0x20)
                i += 2
            else:
                unescaped.append(escaped_data[i])
                i += 1
        
        return unescaped
    
    def unpack_24bit(self, data: bytearray, offset: int) -> int:
        """解包24位数据(大端序)"""
        if offset + 3 > len(data):
            raise ValueError("数据长度不足")
        
        value = (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]
        return value
    
    def decode_latitude(self, lat_24bit: int) -> float:
        """解码24位纬度为度数"""
        # 检查是否为负数(2的补码)
        if lat_24bit & 0x800000:
            lat_24bit = lat_24bit - 0x1000000
        
        latitude = lat_24bit * (180.0 / 0x800000)
        return latitude
    
    def decode_longitude(self, lon_24bit: int) -> float:
        """解码24位经度为度数"""
        # 检查是否为负数(2的补码)
        if lon_24bit & 0x800000:
            lon_24bit = lon_24bit - 0x1000000
        
        longitude = lon_24bit * (180.0 / 0x800000)
        return longitude
    
    def decode_heartbeat(self, data: bytearray) -> Dict[str, Any]:
        """解码心跳消息"""
        if len(data) < 7:  # 消息ID(1) + 状态(2) + 时间戳(2) + 消息计数(2)
            raise ValueError("心跳消息长度不足")
        
        status1 = data[1]
        status2 = data[2]
        timestamp = struct.unpack('<H', data[3:5])[0]  # 小端序
        msg_count = struct.unpack('>H', data[5:7])[0]  # 大端序
        
        # 重构完整的时间戳
        ts_bit16 = (status2 & 0x80) >> 7  # 第16位
        full_timestamp = timestamp | (ts_bit16 << 16)
        
        # 转换为时:分:秒
        hours = full_timestamp // 3600
        minutes = (full_timestamp % 3600) // 60 
        seconds = full_timestamp % 60
        
        return {
            'message_type': 'Heartbeat',
            'status1': f"0x{status1:02X}",
            'status2': f"0x{status2:02X}",
            'timestamp': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            'timestamp_raw': full_timestamp,
            'message_count': msg_count
        }
    
    def decode_position_report(self, data: bytearray, is_ownship: bool = True) -> Dict[str, Any]:
        """解码位置报告消息 (Ownship Report 0x0A 或 Traffic Report 0x14)"""
        msg_type = "Ownship Report" if is_ownship else "Traffic Report"
        
        if len(data) < 28:
            raise ValueError(f"{msg_type}消息长度不足")
        
        offset = 1  # 跳过消息ID
        
        # 状态和地址类型
        status_addr = data[offset]
        if is_ownship:
            status = (status_addr & 0xf0) >> 4
            addr_type = status_addr & 0x0f
        else:
            # Traffic Report格式: s(1位) + t(3位) + 4位填充
            traffic_alert = (status_addr & 0x80) >> 7
            addr_type = (status_addr & 0x70) >> 4
            status = traffic_alert  # 简化显示
        
        offset += 1
        
        # ICAO地址(24位)
        icao_address = self.unpack_24bit(data, offset)
        offset += 3
        
        # 纬度(24位)
        lat_24bit = self.unpack_24bit(data, offset)
        latitude = self.decode_latitude(lat_24bit)
        offset += 3
        
        # 经度(24位) 
        lon_24bit = self.unpack_24bit(data, offset)
        longitude = self.decode_longitude(lon_24bit)
        offset += 3
        
        # 高度(12位) + 杂项(4位) = 2字节
        alt_misc = struct.unpack('>H', data[offset:offset+2])[0]
        altitude_raw = (alt_misc & 0xfff0) >> 4
        misc = alt_misc & 0x0f
        # 高度转换: 25英尺增量，偏移-1000英尺
        altitude_ft = (altitude_raw * 25) - 1000
        offset += 2
        
        # 导航完整性类别 + 导航精度类别
        nav_cat = data[offset]
        nav_integrity = (nav_cat & 0xf0) >> 4
        nav_accuracy = nav_cat & 0x0f
        offset += 1
        
        # 速度信息(3字节): 水平速度(12位) + 垂直速度(12位)
        speed_data = data[offset:offset+3]
        h_vel_vs = (speed_data[0] << 16) | (speed_data[1] << 8) | speed_data[2]
        
        h_velocity = (h_vel_vs & 0xfff000) >> 12  # 水平速度(节)
        v_velocity = h_vel_vs & 0xfff  # 垂直速度
        
        # 垂直速度转换(12位2的补码, 64fpm增量)
        if v_velocity & 0x800:
            v_velocity = v_velocity - 0x1000
        vs_fpm = v_velocity * 64
        offset += 3
        
        # 航向/航道
        track_raw = data[offset]
        track_deg = track_raw * (360.0 / 256)  # 1.4度分辨率
        offset += 1
        
        # 发射器类别
        emitter_cat = data[offset]
        offset += 1
        
        # 呼号(8字节ASCII)
        callsign_bytes = data[offset:offset+8]
        callsign = callsign_bytes.decode('ascii', errors='replace').strip()
        offset += 8
        
        # 代码字段
        if offset < len(data):
            code_field = data[offset]
            emergency_code = (code_field & 0xf0) >> 4
            spare = code_field & 0x0f
        else:
            emergency_code = 0
            spare = 0
        
        return {
            'message_type': msg_type,
            'status': status,
            'addr_type': addr_type,
            'icao_address': f"0x{icao_address:06X}",
            'latitude': latitude,
            'longitude': longitude,
            'altitude_ft': altitude_ft,
            'misc': misc,
            'nav_integrity': nav_integrity,
            'nav_accuracy': nav_accuracy,
            'ground_speed_kts': h_velocity if h_velocity != 0xfff else None,
            'vertical_speed_fpm': vs_fpm if v_velocity != 0x800 else None,
            'track_deg': track_deg,
            'emitter_category': emitter_cat,
            'callsign': callsign,
            'emergency_code': emergency_code
        }
    
    def decode_message(self, raw_data: bytearray) -> Optional[Dict[str, Any]]:
        """解码GDL-90消息"""
        try:
            self.message_stats['total_messages'] += 1
            
            # 检查消息格式：应该以0x7E开头和结尾
            if len(raw_data) < 4 or raw_data[0] != 0x7e or raw_data[-1] != 0x7e:
                raise ValueError("无效的GDL-90消息格式")
            
            # 移除开始和结束标记
            escaped_data = raw_data[1:-1]
            
            # 反转义
            unescaped_data = self.unescape_message(escaped_data)
            
            # 验证CRC
            if not gdl90_crc_verify(unescaped_data):
                self.message_stats['crc_errors'] += 1
                return {
                    'error': 'CRC校验失败',
                    'raw_hex': binascii.hexlify(raw_data).decode(),
                    'length': len(raw_data)
                }
            
            # 移除CRC(最后2字节)
            msg_data = unescaped_data[:-2]
            
            if len(msg_data) == 0:
                raise ValueError("消息数据为空")
            
            # 获取消息ID
            msg_id = msg_data[0]
            
            # 根据消息类型解码
            if msg_id == 0x00:  # Heartbeat
                self.message_stats['heartbeat_count'] += 1
                return self.decode_heartbeat(msg_data)
            
            elif msg_id == 0x0A:  # Ownship Report
                self.message_stats['ownship_count'] += 1
                return self.decode_position_report(msg_data, is_ownship=True)
            
            elif msg_id == 0x14:  # Traffic Report
                self.message_stats['traffic_count'] += 1
                return self.decode_position_report(msg_data, is_ownship=False)
            
            else:
                self.message_stats['unknown_count'] += 1
                return {
                    'message_type': 'Unknown',
                    'message_id': f"0x{msg_id:02X}",
                    'raw_hex': binascii.hexlify(raw_data).decode(),
                    'length': len(raw_data)
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'raw_hex': binascii.hexlify(raw_data).decode(),
                'length': len(raw_data)
            }
    
    def get_stats(self) -> Dict[str, int]:
        """获取消息统计信息"""
        return self.message_stats.copy()

class GDL90Receiver:
    """GDL-90消息接收器"""
    
    def __init__(self, port: int = DEFAULT_LISTEN_PORT):
        self.port = port
        self.running = False
        self.decoder = GDL90Decoder()
        self.socket = None
        
        # 显示选项
        self.show_heartbeat = True
        self.show_ownship = True  
        self.show_traffic = True
        self.show_unknown = True
        self.show_errors = True
        
        # 统计信息
        self.last_stats_time = time.time()
        self.stats_interval = 30.0  # 每30秒显示统计
    
    def start(self):
        """启动接收器"""
        try:
            # 创建UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', self.port))
            self.socket.settimeout(1.0)  # 1秒超时，用于检查运行状态
            
            print(f"🎯 GDL-90接收器已启动")
            print(f"📡 监听端口: {self.port}")
            print(f"⏰ {datetime.datetime.now().strftime('%H:%M:%S')}")
            print("=" * 60)
            
            self.running = True
            
            # 开始接收循环
            self._receive_loop()
            
        except Exception as e:
            print(f"❌ 启动接收器失败: {e}")
            return False
    
    def stop(self):
        """停止接收器"""
        print("\n🛑 正在停止接收器...")
        self.running = False
        if self.socket:
            self.socket.close()
    
    def _receive_loop(self):
        """接收消息循环"""
        try:
            while self.running:
                try:
                    # 接收数据
                    data, addr = self.socket.recvfrom(1024)
                    
                    if data:
                        # 解码消息
                        decoded = self.decoder.decode_message(bytearray(data))
                        
                        if decoded:
                            self._display_message(decoded, addr)
                        
                        # 定期显示统计信息
                        current_time = time.time()
                        if current_time - self.last_stats_time >= self.stats_interval:
                            self._show_stats()
                            self.last_stats_time = current_time
                
                except socket.timeout:
                    # 超时，检查是否应该继续运行
                    continue
                except Exception as e:
                    if self.running:
                        print(f"⚠️  接收错误: {e}")
                    break
        
        except KeyboardInterrupt:
            pass
        finally:
            if self.socket:
                self.socket.close()
            print("\n📊 最终统计信息:")
            self._show_stats()
    
    def _display_message(self, decoded: Dict[str, Any], sender_addr: Tuple[str, int]):
        """显示解码后的消息"""
        msg_type = decoded.get('message_type', 'Unknown')
        current_time = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # 根据设置过滤显示
        if msg_type == 'Heartbeat' and not self.show_heartbeat:
            return
        elif msg_type == 'Ownship Report' and not self.show_ownship:
            return
        elif msg_type == 'Traffic Report' and not self.show_traffic:
            return
        elif msg_type == 'Unknown' and not self.show_unknown:
            return
        elif 'error' in decoded and not self.show_errors:
            return
        
        print(f"\n[{current_time}] 📨 从 {sender_addr[0]}:{sender_addr[1]}")
        
        if 'error' in decoded:
            print(f"❌ 错误: {decoded['error']}")
            print(f"🔍 原始数据: {decoded.get('raw_hex', 'N/A')}")
            print(f"📏 长度: {decoded.get('length', 0)} 字节")
            return
        
        print(f"📋 消息类型: {msg_type}")
        
        if msg_type == 'Heartbeat':
            print(f"⏰ 时间戳: {decoded['timestamp']} ({decoded['timestamp_raw']}s)")
            print(f"📊 状态1: {decoded['status1']}")
            print(f"📊 状态2: {decoded['status2']}")
            print(f"🔢 消息计数: {decoded['message_count']}")
        
        elif msg_type in ['Ownship Report', 'Traffic Report']:
            print(f"🏷️  ICAO地址: {decoded['icao_address']}")
            print(f"🌍 位置: LAT={decoded['latitude']:.6f}°, LON={decoded['longitude']:.6f}°")
            print(f"📏 高度: {decoded['altitude_ft']:.0f}ft")
            
            if decoded['ground_speed_kts'] is not None:
                print(f"🚀 地速: {decoded['ground_speed_kts']} kts")
            else:
                print(f"🚀 地速: 无数据")
                
            if decoded['vertical_speed_fpm'] is not None:
                print(f"⬆️  垂直速度: {decoded['vertical_speed_fpm']:.0f} fpm")
            else:
                print(f"⬆️  垂直速度: 无数据")
                
            print(f"🧭 航向: {decoded['track_deg']:.1f}°")
            print(f"📻 呼号: '{decoded['callsign']}'")
            print(f"✈️  发射器类别: {decoded['emitter_category']}")
            
            # Traffic Report特有信息
            if msg_type == 'Traffic Report':
                if decoded['emergency_code'] != 0:
                    print(f"🚨 应急代码: {decoded['emergency_code']}")
            
            # 导航质量信息
            print(f"📡 导航完整性: {decoded['nav_integrity']}, 精度: {decoded['nav_accuracy']}")
        
        print("-" * 40)
    
    def _show_stats(self):
        """显示统计信息"""
        stats = self.decoder.get_stats()
        print(f"\n📈 统计信息 [{datetime.datetime.now().strftime('%H:%M:%S')}]:")
        print(f"   总消息数: {stats['total_messages']}")
        print(f"   心跳: {stats['heartbeat_count']}")
        print(f"   自机报告: {stats['ownship_count']}")
        print(f"   交通报告: {stats['traffic_count']}")
        if stats['unknown_count'] > 0:
            print(f"   未知消息: {stats['unknown_count']}")
        if stats['crc_errors'] > 0:
            print(f"   CRC错误: {stats['crc_errors']}")
        print("-" * 40)

def main():
    """主程序"""
    parser = argparse.ArgumentParser(
        description="GDL-90消息接收器和解码器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python gdl90_receiver.py                    # 默认端口4000
  python gdl90_receiver.py -p 5000           # 指定端口5000
  python gdl90_receiver.py --no-heartbeat    # 不显示心跳消息
  python gdl90_receiver.py --traffic-only    # 只显示交通报告
        """
    )
    
    parser.add_argument(
        '-p', '--port',
        type=int,
        default=DEFAULT_LISTEN_PORT,
        help=f'监听端口 (默认: {DEFAULT_LISTEN_PORT})'
    )
    
    parser.add_argument(
        '--no-heartbeat',
        action='store_true',
        help='不显示心跳消息'
    )
    
    parser.add_argument(
        '--no-ownship',
        action='store_true', 
        help='不显示自机位置报告'
    )
    
    parser.add_argument(
        '--traffic-only',
        action='store_true',
        help='只显示交通报告消息'
    )
    
    parser.add_argument(
        '--no-errors',
        action='store_true',
        help='不显示错误消息'
    )
    
    args = parser.parse_args()
    
    # 创建接收器
    receiver = GDL90Receiver(port=args.port)
    
    # 设置显示选项
    if args.no_heartbeat:
        receiver.show_heartbeat = False
    if args.no_ownship:
        receiver.show_ownship = False
    if args.traffic_only:
        receiver.show_heartbeat = False
        receiver.show_ownship = False
        receiver.show_unknown = False
    if args.no_errors:
        receiver.show_errors = False
    
    print("=" * 60)
    print("🛩️  GDL-90 消息接收器和解码器")
    print("=" * 60)
    print(f"📡 监听端口: {args.port}")
    
    # 显示过滤设置
    filters = []
    if not receiver.show_heartbeat:
        filters.append("心跳")
    if not receiver.show_ownship:
        filters.append("自机报告")
    if not receiver.show_traffic:
        filters.append("交通报告")
    if not receiver.show_unknown:
        filters.append("未知消息")
    if not receiver.show_errors:
        filters.append("错误")
    
    if filters:
        print(f"🔇 过滤消息: {', '.join(filters)}")
    
    print("\n💡 使用 Ctrl+C 停止接收器")
    print("=" * 60)
    
    try:
        receiver.start()
    except KeyboardInterrupt:
        print("\n👋 接收器已停止")

if __name__ == "__main__":
    main()
