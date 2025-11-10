"""
交通控制系統配置管理
"""

DEVICE = {
    3:{
        "TC_ip" : "192.168.13.89",
        "TC_port" : 7002,
        "BackServer_ip" : "0.0.0.0",
        "BackServer_port": 8889,
        "TransServer_ip" : "0.0.0.0",
        "TransServer_port" : 5555,
    },
}

class TCConfig:
    """交通控制系統配置類"""
    
    def __init__(self, device_id):
        """初始化配置
        參數:
            device_id: 設備ID
        """
        self.device_id = device_id
        self.config = DEVICE.get(device_id)
        
    def get_tc_id(self):
        """獲取控制器ID"""
        return f"TC{self.device_id:03d}"
        
    def get_tc_ip(self):
        """獲取控制器IP"""
        return self.config["TC_ip"]
        
    def get_tc_port(self):
        """獲取控制器端口"""
        return self.config["TC_port"]
        
    def get_backserver_ip(self):
        """獲取中間層IP"""
        return self.config["BackServer_ip"]
        
    def get_backserver_port(self):
        """獲取中間層端口"""
        return self.config["BackServer_port"]
        
    def get_transserver_ip(self):
        """獲取轉譯端IP"""
        return self.config["TransServer_ip"]
        
    def get_transserver_port(self):
        """獲取轉譯端端口"""
        return self.config["TransServer_port"]