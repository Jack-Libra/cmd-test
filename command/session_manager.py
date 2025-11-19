"""
指令會話管理器
管理多步驟指令輸入的會話狀態
"""

import datetime
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

# session[xx] 改為 session.xx
@dataclass
class Session:
    """指令會話數據結構"""
    cmd_code: str
    definition: Dict[str, Any]
    current_step: int = 1
    total_steps: int = 1
    fields: Dict[str, Any] = field(default_factory=dict) # session["fields"]["name"] → session.fields["name"]
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    last_updated: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    def is_expired(self, timeout: int) -> bool:
        """檢查會話是否過期"""
        elapsed = (datetime.datetime.now() - self.last_updated).total_seconds()
        return elapsed > timeout
    
    def update_timestamp(self):
        """更新時間戳"""
        self.last_updated = datetime.datetime.now()


class SessionManager:
    """指令會話管理器"""
    
    def __init__(self, timeout: int = 300):
        """
        初始化會話管理器
        
        Args:
            timeout: 會話超時時間（秒），默認5分鐘
        """
        self.active_sessions: Dict[str, Session] = {}
        self.timeout = timeout
        self.lock = threading.Lock()
    
    def create_session(self, cmd_code: str, definition: Dict[str, Any]) -> Session:
        """創建新會話"""
        session = Session(
            cmd_code=cmd_code,
            definition=definition,
            total_steps=len(definition.get("steps", []))
        )
        
        with self.lock:
            self.active_sessions[cmd_code] = session
        
        return session
    
    def get_active_session(self) -> Optional[Session]:
        """獲取當前活動會話（自動清理過期會話）"""
        with self.lock:
            self._clear_expired_sessions()
            return next(iter(self.active_sessions.values())) if self.active_sessions else None
    
    
    def remove_session(self, cmd_code):
        """移除會話"""
        
        with self.lock:
            self.active_sessions.pop(cmd_code, None)

    
    def _clear_expired_sessions(self):
        """清除過期會話"""
        expired = [
            cmd_code for cmd_code, session in self.active_sessions.items()
            if session.is_expired(self.timeout)
        ]
        for cmd_code in expired:
            self.active_sessions.pop(cmd_code, None)