#!/usr/bin/env python3
"""
X-Plane 12 到 FDPRO 的 GDL-90 数据广播 - 独立版本
包含所有必要的依赖代码，无需外部库
"""

import socket
import struct
import time
import threading
import binascii
import math
import subprocess
import re
import urllib.request
import json
import platform
import datetime

# X-Plane 配置
XPLANE_IP = "192.168.0.1"  # X-Plane 12 运行在本机
XPLANE_PORT = 49000      # X-Plane默认UDP命令端口 - 官方文档确认

# X-Plane Data Output 配置  
XPLANE_DATA_PORT = 49002  # 接收X-Plane Data Output的端口

# FDPRO 配置
FDPRO_PORT = 4000        # FDPRO 默认监听端口

# 广播地址选择 (基于iPad IP地址)：
BROADCAST_IP = "10.16.25.146"     # iPad的具体IP地址 (直接发送)
# BROADCAST_IP = "10.16.25.255"     # iPad所在网段的广播地址
# BROADCAST_IP = "255.255.255.255"  # 全网络广播 (备用)
# BROADCAST_IP = "10.16.31.205"     # X-Plane设备IP (如果FDPRO也在该设备)

# =============================================================================
# 内置GDL90编码器 (基于标准GDL90库)
# =============================================================================

# GDL-90 CRC-16-CCITT 查找表
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

class InlineGDL90Encoder:
    """内置GDL90编码器 - 包含所有必要功能"""
    
    def __init__(self, aircraft_id="PYTHON"):
        self.aircraft_id = aircraft_id[:8].ljust(8)  # 8字符呼号
        self.icao_address = 0xABCDEF  # 24位ICAO地址
    
    def _add_crc(self, msg):
        """计算CRC并添加到消息"""
        crc_bytes = gdl90_crc_compute(msg)
        msg.extend(crc_bytes)
    
    def _escape(self, msg):
        """转义0x7d和0x7e字符"""
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
    
    def _prepared_message(self, msg):
        """准备消息：添加CRC，转义，添加开始/结束标记"""
        self._add_crc(msg)
        new_msg = self._escape(msg)
        new_msg.insert(0, 0x7e)
        new_msg.append(0x7e)
        return new_msg
    
    def _pack24bit(self, num):
        """打包24位数字为字节数组(大端序)"""
        if ((num & 0xFFFFFF) != num) or num < 0:
            raise ValueError("输入不是24位无符号值")
        a = bytearray()
        a.append((num & 0xff0000) >> 16)
        a.append((num & 0x00ff00) >> 8)
        a.append(num & 0xff)
        return a
    
    def _make_latitude(self, latitude):
        """将纬度转换为2的补码，准备24位打包"""
        if latitude > 90.0: latitude = 90.0
        if latitude < -90.0: latitude = -90.0
        latitude = int(latitude * (0x800000 / 180.0))
        if latitude < 0:
            latitude = (0x1000000 + latitude) & 0xffffff  # 2的补码
        return latitude
    
    def _make_longitude(self, longitude):
        """将经度转换为2的补码，准备24位打包"""
        if longitude > 180.0: longitude = 180.0
        if longitude < -180.0: longitude = -180.0
        longitude = int(longitude * (0x800000 / 180.0))
        if longitude < 0:
            longitude = (0x1000000 + longitude) & 0xffffff  # 2的补码
        return longitude
    
    def create_heartbeat(self, st1=0x81, st2=0x01):
        """创建心跳消息(ID 0x00)"""
        # 自动填充时间戳
        dt = datetime.datetime.now(datetime.timezone.utc)
        ts = (dt.hour * 3600) + (dt.minute * 60) + dt.second
        
        # 将时间戳的第16位移动到状态字节2的第7位
        ts_bit16 = (ts & 0x10000) >> 16
        st2 = (st2 & 0b01111111) | (ts_bit16 << 7)
        
        msg = bytearray([0x00])
        msg.extend(struct.pack('>BB', st1, st2))        # 状态字节
        msg.extend(struct.pack('<H', ts & 0xFFFF))       # 时间戳(小端序)
        msg.extend(struct.pack('>H', 0x0000))           # 消息计数
        
        return self._prepared_message(msg)
    
    def create_position_report(self, data):
        """
        创建位置报告消息 - Ownship Report (ID 0x0a)
        
        data: 包含以下键的字典
          - lat: 纬度 (度)
          - lon: 经度 (度)  
          - alt: 高度 (英尺, MSL)
          - speed: 地速 (节)
          - track: 航向 (度)
          - vs: 垂直速度 (英尺/分钟)
        """
        # 获取并验证数据
        lat_deg = data.get('lat', 0.0)
        lon_deg = data.get('lon', 0.0)
        alt_ft = data.get('alt', 0.0)
        speed_kts = data.get('speed', 0.0)
        track_deg = data.get('track', 0.0)
        vs_fpm = data.get('vs', 0.0)
        
        # 检查数据有效性
        if not (-90 <= lat_deg <= 90) or not (-180 <= lon_deg <= 180):
            print(f"警告: 无效的经纬度数据 LAT={lat_deg}, LON={lon_deg}")
            lat_deg = lon_deg = 0.0
        
        # 构建Ownship Report消息(ID 0x0a)
        msg = bytearray([0x0a])  # 消息ID
        
        # 状态和地址类型
        status = 0
        addr_type = 0
        b = ((status & 0xf) << 4) | (addr_type & 0xf)
        msg.append(b)
        
        # ICAO地址(24位)
        msg.extend(self._pack24bit(self.icao_address))
        
        # 纬度(24位)
        msg.extend(self._pack24bit(self._make_latitude(lat_deg)))
        
        # 经度(24位)
        msg.extend(self._pack24bit(self._make_longitude(lon_deg)))
        
        # 高度：25英尺增量，偏移+1000英尺
        altitude = int((alt_ft + 1000) / 25.0)
        if altitude < 0: altitude = 0
        if altitude > 0xffe: altitude = 0xffe
        
        # 高度是位15-4，杂项代码是位3-0
        misc = 9  # 默认杂项值
        msg.append((altitude & 0x0ff0) >> 4)  # 高度的高8位
        msg.append(((altitude & 0x0f) << 4) | (misc & 0xf))
        
        # 导航完整性类别和精度类别
        nav_integrity_cat = 11
        nav_accuracy_cat = 11
        msg.append(((nav_integrity_cat & 0xf) << 4) | (nav_accuracy_cat & 0xf))
        
        # 水平速度
        h_velocity = int(speed_kts) if speed_kts is not None else 0xfff
        if h_velocity < 0:
            h_velocity = 0
        elif h_velocity > 0xffe:
            h_velocity = 0xffe
        
        # 垂直速度
        if vs_fpm is None:
            v_velocity = 0x800
        else:
            if vs_fpm > 32576:
                v_velocity = 0x1fe
            elif vs_fpm < -32576:
                v_velocity = 0xe02
            else:
                v_velocity = int(vs_fpm / 64)  # 转换为64fpm增量
                if v_velocity < 0:
                    v_velocity = (0x1000000 + v_velocity) & 0xffffff  # 2的补码
        
        # 打包水平速度和垂直速度为3字节：hh hv vv
        msg.append((h_velocity & 0xff0) >> 4)
        msg.append(((h_velocity & 0xf) << 4) | ((v_velocity & 0xf00) >> 8))
        msg.append(v_velocity & 0xff)
        
        # 航向/航道
        track_heading = int(track_deg / (360. / 256))  # 转换为1.4度单字节
        msg.append(track_heading & 0xff)
        
        # 发射器类别
        emitter_cat = 1  # 轻型飞机
        msg.append(emitter_cat & 0xff)
        
        # 呼号(8字节)
        call_sign = bytearray(str(self.aircraft_id + " " * 8)[:8], 'ascii')
        msg.extend(call_sign)
        
        # 代码是高4位，低4位是'备用'
        code = 0
        msg.append((code & 0xf) << 4)
        
        return self._prepared_message(msg)

# =============================================================================
# 内置XPlane UDP功能 (基于XPlane-UDP库)
# =============================================================================

class XPlaneUdpInline:
    """内置XPlane UDP类 - 包含必要的连接和数据获取功能"""
    
    # 常量
    MCAST_GRP = "239.255.1.1"
    MCAST_PORT = 49707
    
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(3.0)
        self.dataref_idx = 0
        self.datarefs = {}  # key = idx, value = dataref
        self.beacon_data = {}
        self.xplane_values = {}
        self.default_freq = 1
    
    def find_ip(self):
        """在网络中找到XPlane主机的IP"""
        self.beacon_data = {}
        
        # 为多播组打开socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if platform.system() == "Windows":
            sock.bind(('', self.MCAST_PORT))
        else:
            sock.bind((self.MCAST_GRP, self.MCAST_PORT))
        
        mreq = struct.pack("=4sl", socket.inet_aton(self.MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(3.0)
        
        try:
            packet, sender = sock.recvfrom(1472)
            
            # 解码数据
            header = packet[0:5]
            if header != b"BECN\x00":
                print("未知数据包来自" + sender[0])
                raise Exception("未知beacon格式")
            
            # 解析beacon数据结构
            data = packet[5:21]
            (beacon_major_version, beacon_minor_version, application_host_id, 
             xplane_version_number, role, port) = struct.unpack("<BBiiIH", data)
            
            hostname = packet[21:-1]
            hostname = hostname[0:hostname.find(0)]
            
            if (beacon_major_version == 1 and beacon_minor_version <= 2 and 
                application_host_id == 1):
                self.beacon_data["IP"] = sender[0]
                self.beacon_data["Port"] = port
                self.beacon_data["hostname"] = hostname.decode()
                self.beacon_data["XPlaneVersion"] = xplane_version_number
                self.beacon_data["role"] = role
            else:
                raise Exception(f"不支持的XPlane Beacon版本: {beacon_major_version}.{beacon_minor_version}.{application_host_id}")
        
        except socket.timeout:
            raise Exception("未找到XPlane IP")
        finally:
            sock.close()
        
        return self.beacon_data
    
    def add_dataref(self, dataref, freq=None):
        """配置XPlane发送dataref数据"""
        if freq is None:
            freq = self.default_freq
        
        idx = -9999
        if dataref in self.datarefs.values():
            idx = list(self.datarefs.keys())[list(self.datarefs.values()).index(dataref)]
            if freq == 0:
                if dataref in self.xplane_values.keys():
                    del self.xplane_values[dataref]
                del self.datarefs[idx]
        else:
            idx = self.dataref_idx
            self.datarefs[self.dataref_idx] = dataref
            self.dataref_idx += 1
        
        cmd = b"RREF\x00"
        string = dataref.encode()
        message = struct.pack("<5sii400s", cmd, freq, idx, string)
        assert(len(message) == 413)
        self.socket.sendto(message, (self.beacon_data["IP"], self.beacon_data["Port"]))
        
        if (self.dataref_idx % 100 == 0):
            time.sleep(0.2)
    
    def get_values(self):
        """获取XPlane发送的dataref值"""
        try:
            data, addr = self.socket.recvfrom(1472)
            
            ret_values = {}
            header = data[0:5]
            if header != b"RREF,":
                print("未知数据包:", binascii.hexlify(data))
                return self.xplane_values
            
            # 解析8字节的dataref数据
            values = data[5:]
            len_value = 8
            num_values = int(len(values) / len_value)
            
            for i in range(0, num_values):
                single_data = data[(5 + len_value * i):(5 + len_value * (i + 1))]
                (idx, value) = struct.unpack("<if", single_data)
                if idx in self.datarefs.keys():
                    # 转换-0.0值为正0.0
                    if value < 0.0 and value > -0.001:
                        value = 0.0
                    ret_values[self.datarefs[idx]] = value
            
            self.xplane_values.update(ret_values)
        except:
            raise Exception("XPlane超时")
        
        return self.xplane_values
    
    def __del__(self):
        for i in range(len(self.datarefs)):
            self.add_dataref(next(iter(self.datarefs.values())), freq=0)
        self.socket.close()

# =============================================================================
# 主程序类 (更新后使用内置库)
# =============================================================================

class GDL90Encoder:
    """GDL90编码器包装类"""
    def __init__(self, aircraft_id="PYTHON"):
        self.encoder = InlineGDL90Encoder(aircraft_id)
    
    def create_heartbeat(self):
        return self.encoder.create_heartbeat()
    
    def create_position_report(self, data):
        return self.encoder.create_position_report(data)

class XPlaneDataReceiverNew:
    """使用内置XPlane-UDP功能的数据接收器"""
    def __init__(self):
        self.xplane_udp = XPlaneUdpInline()
        self.current_data = {
            'lat': 0.0, 'lon': 0.0, 'alt': 0.0, 'speed': 0.0,
            'track': 0.0, 'vs': 0.0, 'pitch': 0.0, 'roll': 0.0
        }
        self.running = False
        self.beacon_data = None
    
    def start(self):
        """开始接收X-Plane数据"""
        try:
            print("正在寻找X-Plane...")
            self.beacon_data = self.xplane_udp.find_ip()
            print(f"✅ 找到X-Plane: {self.beacon_data}")
            
            # 订阅需要的datarefs
            print("订阅flight数据...")
            datarefs = [
                ("sim/flightmodel/position/latitude", 'lat'),
                ("sim/flightmodel/position/longitude", 'lon'),
                ("sim/flightmodel/position/elevation", 'alt'),
                ("sim/flightmodel/position/groundspeed", 'speed'),
                ("sim/flightmodel/position/psi", 'track'),
                ("sim/flightmodel/position/vh_ind_fpm", 'vs'),
                ("sim/flightmodel/position/theta", 'pitch'),
                ("sim/flightmodel/position/phi", 'roll')
            ]
            
            for dataref, key in datarefs:
                self.xplane_udp.add_dataref(dataref, freq=10)
                print(f"  订阅: {dataref}")
            
            self.running = True
            threading.Thread(target=self._receive_loop, daemon=True).start()
            
            # 等待数据
            print("等待5秒钟查看是否收到数据...")
            time.sleep(5)
            
            # 检查是否收到数据
            values = self.xplane_udp.get_values()
            if values:
                print("✅ 成功接收到飞行数据!")
                self._update_current_data(values)
                return True
            else:
                print("⚠️  5秒后仍未收到数据")
                return False
                
        except Exception as e:
            print(f"启动XPlane连接失败: {e}")
            # 检查X-Plane是否还在运行
            running, ip = is_xplane_running()
            if not running:
                print("❌ X-Plane似乎已经关闭，程序将退出")
                print("请先启动X-Plane再运行本程序")
                exit(1)
            return False
    
    def _update_current_data(self, xplane_values):
        """更新当前数据，进行单位转换"""
        dataref_mapping = {
            'sim/flightmodel/position/latitude': 'lat',
            'sim/flightmodel/position/longitude': 'lon',
            'sim/flightmodel/position/elevation': 'alt',
            'sim/flightmodel/position/groundspeed': 'speed',
            'sim/flightmodel/position/psi': 'track',
            'sim/flightmodel/position/vh_ind_fpm': 'vs',
            'sim/flightmodel/position/theta': 'pitch',
            'sim/flightmodel/position/phi': 'roll'
        }
        
        for dataref, value in xplane_values.items():
            if dataref in dataref_mapping:
                key = dataref_mapping[dataref]
                
                if key == 'alt':
                    # 高度从米转换为英尺
                    self.current_data[key] = value * 3.28084
                elif key == 'speed':
                    # 地速从米/秒转换为节
                    self.current_data[key] = value * 1.94384
                else:
                    # 其他数据直接使用
                    self.current_data[key] = value
    
    def _receive_loop(self):
        """接收数据循环"""
        print("开始接收XPlane数据...")
        while self.running:
            try:
                values = self.xplane_udp.get_values()
                if values:
                    self._update_current_data(values)
                time.sleep(0.1)
            except Exception as e:
                if self.running:
                    print(f"接收数据错误: {e}")
                break
    
    def stop(self):
        """停止接收数据"""
        print("停止接收数据...")
        self.running = False

# =============================================================================
# X-Plane状态检测功能
# =============================================================================

def get_local_ip():
    """获取本机IP地址"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def is_xplane_running():
    """快速检测X-Plane是否仍在运行"""
    try:
        # 方法1: 尝试beacon发现
        xp_test = XPlaneUdpInline()
        beacon = xp_test.find_ip()
        if beacon:
            return True, beacon['IP']
    except Exception:
        pass
    
    # 方法2: 尝试Web API检测
    try:
        local_ip = get_local_ip()
        ip_parts = local_ip.split('.')
        network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        
        # 测试常见IP地址
        test_ips = ["127.0.0.1", local_ip, f"{network}.205"]
        
        for ip in test_ips:
            try:
                url = f"http://{ip}:8086/api/capabilities"
                req = urllib.request.Request(url)
                req.add_header('Accept', 'application/json')
                
                with urllib.request.urlopen(req, timeout=1) as response:
                    if response.status == 200:
                        return True, ip
            except Exception:
                continue
    except Exception:
        pass
    
    return False, None

# =============================================================================
# 主程序逻辑
# =============================================================================

def check_xplane_settings():
    """检查X-Plane设置并提供详细指导"""
    local_ip = get_local_ip()
    
    print("\n" + "="*50)
    print("🔧 X-Plane 数据输出设置")
    print("="*50)
    print("请按照以下步骤配置X-Plane数据输出:")
    print()
    print("方法1: 使用Data Output (推荐)")
    print("1. 打开X-Plane")
    print("2. 进入 Settings → Data Input & Output → Data Set")
    print("3. 找到并勾选以下数据项的 'UDP' 列:")
    print("   ✅ 17 - lat, lon, altitude")
    print("   ✅ 18 - speed, Mach, VVI") 
    print("   ✅ 19 - pitch, roll, headings")
    print("4. 点击 'Internet' 标签")
    print("5. 设置IP地址 (选择其中一个):")
    print(f"   📍 本机IP: {local_ip} (推荐)")
    print(f"   📍 本地回环: 127.0.0.1 (备用)")
    print(f"6. 端口设为 {XPLANE_DATA_PORT}")
    print()
    print("💡 IP地址选择说明:")
    print("- 如果X-Plane和本程序在同一台电脑: 使用 127.0.0.1")
    print(f"- 如果需要网络访问或不确定: 使用 {local_ip}")
    print()
    print("方法2: 使用RREF (如果方法1不工作)")
    print("1. 进入 Settings → Network")
    print("2. 确保 'Accept incoming connections' 勾选")
    print("3. 端口应该是 49000")
    print()
    print("重要: 加载一架飞机并确保在飞行中!")
    print("   - 空飞机场不会有移动数据")
    print("   - 可以使用自动飞行或手动飞行")
    print("="*50)

def broadcast_gdl90():
    """广播GDL-90数据给FDPRO"""
    # 首先检查X-Plane是否运行
    print("🔍 检查X-Plane状态...")
    running, detected_ip = is_xplane_running()
    if not running:
        print("❌ 未检测到X-Plane正在运行!")
        print("请先启动X-Plane，然后重新运行本程序")
        print("\n提示:")
        print("1. 启动X-Plane应用程序")
        print("2. 加载一架飞机")
        print("3. 确保Settings → Network → Accept incoming connections已启用")
        return
    else:
        print(f"✅ 检测到X-Plane运行在: {detected_ip}")
    
    # 提供设置指导
    check_xplane_settings()
    
    # 等待用户确认
    print("\n请确认已按照上述指导检查X-Plane设置，然后按 Enter 继续...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n程序已取消")
        return
    
    # 创建UDP广播套接字
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    # 创建GDL-90编码器
    encoder = GDL90Encoder(aircraft_id="PYTHON1")
    
    # 使用XPlane-UDP方式
    print("\n=== 使用XPlane-UDP库自动发现和连接 ===")
    xplane_receiver = XPlaneDataReceiverNew()
    
    if not xplane_receiver.start():
        print("❌ 无法连接到X-Plane")
        
        # 再次检查X-Plane状态
        running, _ = is_xplane_running()
        if not running:
            print("❌ X-Plane似乎已经关闭，程序将退出")
            return
        
        print("\n请检查:")
        print("1. X-Plane -> Settings -> Network -> 是否启用了 'Accept incoming connections'")
        print("2. 飞机是否已加载并在飞行中")
        print("3. 防火墙设置是否允许UDP连接")
        return
    else:
        print("✅ 成功使用XPlane-UDP方式接收数据")
    
    try:
        heartbeat_interval = 1.0  # 心跳每秒发送一次
        position_interval = 0.5   # 位置报告每秒发送两次
        xplane_check_interval = 10.0  # 每10秒检查一次X-Plane状态
        
        last_heartbeat = time.time()
        last_position = time.time()
        last_xplane_check = time.time()
        
        print("开始广播GDL-90数据到FDPRO...")
        
        while True:
            current_time = time.time()
            
            # 定期检查X-Plane状态
            if current_time - last_xplane_check >= xplane_check_interval:
                running, _ = is_xplane_running()
                if not running:
                    print("\n❌ X-Plane已关闭，程序将退出")
                    break
                last_xplane_check = current_time
            
            # 发送心跳消息
            if current_time - last_heartbeat >= heartbeat_interval:
                heartbeat_msg = encoder.create_heartbeat()
                broadcast_sock.sendto(heartbeat_msg, (BROADCAST_IP, FDPRO_PORT))
                last_heartbeat = current_time
                print(f"💓 发送心跳到 {BROADCAST_IP}:{FDPRO_PORT} ({len(heartbeat_msg)} bytes): {binascii.hexlify(heartbeat_msg).decode()}")
            
            # 发送位置报告
            if current_time - last_position >= position_interval:
                try:
                    position_msg = encoder.create_position_report(xplane_receiver.current_data)
                    broadcast_sock.sendto(position_msg, (BROADCAST_IP, FDPRO_PORT))
                    last_position = current_time
                    # 打印位置信息和调试信息
                    data = xplane_receiver.current_data
                    print(f"✈️  位置报告到 {BROADCAST_IP}:{FDPRO_PORT} ({len(position_msg)} bytes)")
                    print(f"   LAT={data['lat']:.6f}, LON={data['lon']:.6f}, ALT={data['alt']:.0f}ft")
                    print(f"   GDL90 hex: {binascii.hexlify(position_msg).decode()[:64]}...")
                except Exception as e:
                    print(f"GDL-90编码错误: {e}")
                    print(f"数据: {xplane_receiver.current_data}")
                    last_position = current_time  # 防止重复错误
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n停止广播...")
        xplane_receiver.stop()
        broadcast_sock.close()

if __name__ == "__main__":
    # 提示信息
    print("="*70)
    print("X-Plane 12 到 FDPRO 的 GDL-90 数据广播 - 独立版本")
    print("="*70)
    print("确保:")
    print("1. X-Plane 12 正在运行")
    print("   - 使用内置XPlane-UDP库进行连接")
    print("2. FDPRO 正在运行并监听GDL-90数据")
    print(f"   - 监听端口: {FDPRO_PORT}")
    print(f"   - 广播地址: {BROADCAST_IP}")
    print("="*70)
    
    broadcast_gdl90()
