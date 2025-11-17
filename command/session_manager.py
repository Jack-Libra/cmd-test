"""
指令會話管理器
管理多步驟指令輸入的會話狀態
"""

import datetime
from typing import Dict, Optional
import threading


class SessionManager:
    """指令會話管理器"""
    
    def __init__(self, timeout: int = 300):
        """
        初始化會話管理器
        
        Args:
            timeout: 會話超時時間（秒），默認5分鐘
        """
        self.active_sessions: Dict[str, Dict] = {}
        self.timeout = timeout
        self.lock = threading.Lock()
    
    def create_session(self, cmd_code: str, definition: Dict) -> Dict:
        """
        創建新會話
        
        Args:
            cmd_code: 指令代碼
            definition: 指令定義
            
        Returns:
            會話字典
        """
        steps = definition.get("steps", [])
        session = {
            "cmd_code": cmd_code,
            "definition": definition,
            "current_step": 1,
            "total_steps": len(steps),
            "fields": {},
            "created_at": datetime.datetime.now(),
            "last_updated": datetime.datetime.now()
        }
        
        with self.lock:
            self.active_sessions[cmd_code] = session
        
        return session
    
    def get_active_session(self) -> Optional[Dict]:
        """
        獲取當前活動會話
        
        Returns:
            會話字典，如果沒有則返回 None
        """
        with self.lock:
            # 清理過期會話
            self._clear_expired_sessions()
            
            # 返回第一個活動會話（簡化設計：只支持一個會話）
            if self.active_sessions:
                return next(iter(self.active_sessions.values()))
            return None
    
    def get_session(self, cmd_code: str) -> Optional[Dict]:
        """
        獲取指定指令的會話
        
        Args:
            cmd_code: 指令代碼
            
        Returns:
            會話字典，如果不存在或已過期則返回 None
        """
        with self.lock:
            session = self.active_sessions.get(cmd_code)
            if session:
                # 檢查是否過期
                if self._is_expired(session):
                    self.active_sessions.pop(cmd_code, None)
                    return None
            return session
    
    def remove_session(self, cmd_code: str):
        """
        移除會話
        
        Args:
            cmd_code: 指令代碼
        """
        with self.lock:
            self.active_sessions.pop(cmd_code, None)
    
    def update_session(self, cmd_code: str, updates: Dict):
        """
        更新會話
        
        Args:
            cmd_code: 指令代碼
            updates: 要更新的字段字典
        """
        with self.lock:
            session = self.active_sessions.get(cmd_code)
            if session:
                session.update(updates)
                session["last_updated"] = datetime.datetime.now()
    
    def _is_expired(self, session: Dict) -> bool:
        """
        檢查會話是否過期
        
        Args:
            session: 會話字典
            
        Returns:
            是否過期
        """
        elapsed = (datetime.datetime.now() - session["last_updated"]).total_seconds()
        return elapsed > self.timeout
    
    def _clear_expired_sessions(self):
        """清除過期會話"""
        expired = []
        for cmd_code, session in self.active_sessions.items():
            if self._is_expired(session):
                expired.append(cmd_code)
        
        for cmd_code in expired:
            self.active_sessions.pop(cmd_code, None)