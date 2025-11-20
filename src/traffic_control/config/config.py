"""
配置管理器
"""

from .constants import DEVICE_CONFIG

class TCConfig:
    """交通控制系統配置類"""
    
    def __init__(self, device_id):
        """初始化配置
        參數:
            device_id: 設備ID
        """
        self.device_id = device_id
        self.config = DEVICE_CONFIG.get(device_id, {})
        
    def get_tc_id(self):
        """獲取控制器ID"""
        return f"TC{self.device_id:03d}"
        
    def get_tc_ip(self):
        """獲取控制器IP"""
        return self.config.get("TC_ip", "0.0.0.0")
        
    def get_tc_port(self):
        """獲取控制器端口"""
        return self.config.get("TC_port", 7002)
        
    def get_backserver_ip(self):
        """獲取中間層IP"""
        return self.config.get("BackServer_ip", "0.0.0.0")
        
    def get_backserver_port(self):
        """獲取中間層端口"""
        return self.config.get("BackServer_port", 8889)
        
    def get_transserver_ip(self):
        """獲取轉譯端IP"""
        return self.config.get("TransServer_ip", "0.0.0.0")
        
    def get_transserver_port(self):
        """獲取轉譯端端口"""
        return self.config.get("TransServer_port", 5555)