"""
步驟處理器

處理多步驟指令輸入的步驟邏輯
"""

from typing import Dict, Any, Optional, Tuple
from utils import validate_param_range
from packet.packet_definition import PacketDefinitionProtocol



# ============= 輸入驗證器 =============

class InputValidator:
    """輸入驗證器 - 專門處理輸入解析和驗證"""
    
    def __init__(self, packet_def: PacketDefinitionProtocol):
        self.packet_def = packet_def
    
    def parse_and_validate(self, value_str: str, field_def: Dict[str, Any], 
                         field_name: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        解析並驗證輸入值
        
        Returns:
            (success, value, error_message)
        """
        try:
            value = self.packet_def.parse_input(value_str, field_def, field_name)
            
            min_val = field_def.get("min", 0)
            max_val = field_def.get("max", 0xFF)
            validate_param_range(value, field_name, min_val, max_val)
            
            return True, value, None
            
        except ValueError as e:
            return False, None, str(e)
    
    def parse_list_values(self, parts: list, start_idx: int, count: int, 
                         field_def: Dict[str, Any], field_name: str) -> Tuple[bool, list, Optional[str]]:
        """
        解析列表值
        
        Returns:
            (success, values, error_message)
        """
        if len(parts) < start_idx + count:
            return False, [], f"{field_name} 需要 {count} 個值，但只提供了 {len(parts) - start_idx} 個"
        
        values = []
        item_type = field_def.get("item_type", "uint8")
        item_field_def = {"type": item_type}
        
        for i in range(count):
            idx = start_idx + i
            try:
                value = self.packet_def.parse_input(parts[idx], item_field_def, f"{field_name}[{i+1}]")
                
                # 驗證範圍
                min_val = field_def.get("min", 0)
                max_val = field_def.get("max", 0xFF)
                validate_param_range(value, f"{field_name}[{i+1}]", min_val, max_val)
                
                values.append(value)
            except ValueError as e:
                return False, [], str(e)
        
        return True, values, None


# ============= 步驟處理器 =============

class StepProcessor:
    """步驟處理器"""
    
    def __init__(self, packet_def: PacketDefinitionProtocol):
        self.packet_def = packet_def
        self.validator = InputValidator(packet_def)
    
    def get_step_prompt(self, session) -> str:
        """獲取當前步驟的提示信息"""
        steps = session.definition.get("steps", [])
        
        # next()
        step = next((step for step in steps if step.get("step") == session.current_step))
        
        prompt_template = step.get("prompt", "步驟 {step}/{total}: {description}\n> ")
        
        replacements = {
            "step": session.current_step,
            "total": session.total_steps,
            "description": step.get("description", ""),
            **session.fields
        }
        
        # 檢查是否有count_from需要計算數量
        # get_step_prompt 提示用戶需要輸入數量
        # process_step 處理用戶輸入數量
        for field_name in step.get("fields", []):
            
            field_def = self.packet_def.get_field_definition(session.definition, field_name)
            
            if field_def and field_def.get("count_from"):
                
                # lambda函式=field_def["count_from"]，類型統一為int
                # 執行lambda函式，傳入session.fields
                count = int(field_def["count_from"](session.fields)) 
                
                replacements["total"] = count
                
                break  # 一個step一個count_from
        
        # 處理預覽
        if step.get("preview") and step.get("type") == "confirmation":
            replacements["preview"] = self._generate_preview(session)
        
        try:
            return prompt_template.format(**replacements)
        except KeyError as e:
            return f"提示格式錯誤: 缺少變量 {e}"
    
    def process_step(self, session, user_input: str) -> Tuple[bool, str, bool]:
        """
        處理步驟輸入
        
        Returns:
            (success, message, is_complete)
        """
        steps = session.definition.get("steps", [])
        step = next((step for step in steps if step.get("step") == session.current_step))

        if not step:
            return False, "錯誤: 無法獲取步驟配置", False
        
        # 處理確認步驟
        if step.get("type") == "confirmation":
            return self._handle_confirmation(user_input)
        
        # 解析輸入
        parts = user_input.split()
        errors = []
        fields_to_parse = step.get("fields", [])
        
        # 處理字段
        i = 0
        for field_name in fields_to_parse:
            if i >= len(parts):
                errors.append(f"缺少參數: {field_name}")
                continue
            
            field_def = self.packet_def.get_field_definition(session.definition, field_name)
            if not field_def:
                errors.append(f"未找到字段定義: {field_name}")
                continue
            
            # 處理列表字段
            if field_def.get("type") == "list":
                
                count = int(field_def["count_from"](session.fields)) # 類型統一為int

                success, list_values, error = self.validator.parse_list_values(
                    parts, i, count, field_def, field_name
                )
                if success:
                    session.fields[field_name] = list_values
                    i += count  # 跳過已處理的列表項
                else:
                    errors.append(error)
                    break  # 列表解析失敗，停止處理
            else:
                # 處理普通字段
                success, value, error = self.validator.parse_and_validate(parts[i], field_def, field_name)
                if success:
                    session.fields[field_name] = value
                    i += 1
                else:
                    errors.append(error)
        
        if errors:
            return False, "\n".join(errors), False
        
        # 進入下一步
        session.current_step += 1
        session.update_timestamp()
        
        if session.current_step > session.total_steps:
            return True, "所有步驟完成，準備發送", True
        
        return True, "", False
    
    
    # ============= 私有方法 =============
    
    def _handle_confirmation(self, user_input: str) -> Tuple[bool, str, bool]:
        """處理確認步驟"""
        input_lower = user_input.strip().lower()
        if input_lower in ['y', 'yes', '是', '確認', 'ok', '']:
            return True, "指令已確認，準備發送", True
        elif input_lower in ['n', 'no', '否', '取消', 'cancel']:
            return False, "指令已取消", True
        else:
            return False, "請輸入 y(確認) 或 n(取消)", False
    
    
    def _generate_preview(self, session) -> str:
        """生成預覽信息"""
        lines = [f"\n指令: {session.cmd_code}"]
        lines.append(f"描述: {session.definition.get('description', '')}")
        lines.append("\n已輸入參數:")
        
        for field_name, value in session.fields.items():
            if isinstance(value, list):
                if len(value) <= 10:
                    values_str = ", ".join([f"0x{v:02X}" for v in value])
                    lines.append(f"  {field_name}: [{values_str}]")
                else:
                    preview_str = ", ".join([f"0x{v:02X}" for v in value[:5]])
                    lines.append(f"  {field_name}: [{preview_str}...] (共 {len(value)} 個值)")
            else:
                lines.append(f"  {field_name}: 0x{value:02X} ({value})")
        
        return "\n".join(lines)
    
