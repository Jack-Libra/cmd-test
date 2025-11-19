"""
步驟處理器
處理多步驟指令輸入的步驟邏輯
"""

import datetime
from utils import validate_param_range


class StepProcessor:
    """步驟處理器"""
    
    def __init__(self, packet_def):

        self.packet_def = packet_def
    
    def get_step_prompt(self, session):
        """
        獲取當前步驟的提示信息
        
        Args:
            session: 會話字典
            
        Returns:
            提示字符串
        """
        step_config = self._get_step_config(session, session.current_step)
        if not step_config:
            return "錯誤: 無法獲取步驟配置"
        
        prompt_template = step_config.get("prompt", "步驟 {step}/{total}: {description}\n> ")
        
        # 準備替換變量
        replacements = {
            "step": session.current_step,
            "total": session.total_steps,
            "description": step_config.get("description", ""),
            **session.fields  # 已輸入的字段值
        }
        
        # 處理動態計數
        if "dynamic_count" in step_config:
            dc = step_config["dynamic_count"]
            field_value = session.fields.get(dc["field"])
            multiplier_value = session.fields.get(dc["multiplier"])
            total = field_value * multiplier_value
            replacements["total"] = total
        
        # 處理預覽
        if step_config.get("preview") and step_config.get("type") == "confirmation":
            preview = self._generate_preview(session)
            replacements["preview"] = preview
        
        # 格式化提示
        try:
            return prompt_template.format(**replacements)
        except KeyError as e:
            return f"提示格式錯誤: 缺少變量 {e}"
    
    def process_step(self, session, user_input):
        """
        處理步驟輸入
        
        Args:
            session: 會話字典
            input: 用戶輸入
            
        Returns:
            (success, message, is_complete)
        """
        step_config = self._get_step_config(session, session.current_step)
        if not step_config:
            return False, "錯誤: 無法獲取步驟配置", False
        
        # 處理確認步驟
        if step_config.get("type") == "confirmation":
            
            if user_input.strip().lower() in ['y', 'yes', '是', '確認', 'ok','']:
                return True, "指令已確認，準備發送", True
            elif user_input.strip().lower() in ['n', 'no', '否', '取消', 'cancel']:
                return False, "指令已取消", True
            else:
                return False, "請輸入 y(確認) 或 n(取消)", False
            
        
        # 解析輸入(字串→列表)
        parts = user_input.split()
        
        # 驗證和解析輸入
        errors = []
        fields_to_parse = step_config.get("fields")
        
        # 處理固定字段
        for i, field_name in enumerate(fields_to_parse):
            if i >= len(parts):
                errors.append(f"缺少參數: {field_name}")
                continue
            
            # 獲取字段定義
            field_def = self.packet_def.get_field_definition(session.definition, field_name)
            if not field_def:
                errors.append(f"未找到字段定義: {field_name}")
                continue
            
            # 解析參數
            try:
                value = self.packet_def.parse_input(parts[i], field_def, field_name)

                # 驗證範圍
                min_val = field_def.get("min", 0)
                max_val = field_def.get("max", 0xFF)
                validate_param_range(value, field_name, min_val, max_val)

                
                session.fields[field_name] = value
                
            except ValueError as e:
                errors.append(str(e))
                continue
        
        # 處理動態列表字段
        if "dynamic_count" in step_config:
            dc = step_config["dynamic_count"]
            field_value = session.fields.get(dc["field"])
            multiplier_value = session.fields.get(dc["multiplier"])
            total_count = field_value * multiplier_value
            
            if len(parts) < len(fields_to_parse) + total_count:
                errors.append(f"需要 {total_count} 個列表值，但只提供了 {len(parts) - len(fields_to_parse)} 個")
            else:
                list_values = []
                for i in range(total_count):
                    idx = len(fields_to_parse) + i
                    try:
                        value = int(parts[idx], 10)
                        validate_param_range(value, f"列表值 {i+1}", 0, 0xFF)
                        list_values.append(value)
                    except ValueError:
                        errors.append(str(e))
                
                
                if not errors:
                    # 使用步驟配置中指定的字段名，或默認使用 "信號狀態列表"
                    list_field_name = step_config.get("list_field_name", "信號狀態列表")
                    session.fields[list_field_name] = list_values
        
        if errors:
            return False, "\n".join(errors), False
        
        # 進入下一步
        session.current_step += 1
        session.update_timestamp()
        
        # 檢查是否完成
        if session.current_step > session.total_steps:
            return True, "所有步驟完成，準備發送", True
        
        # 獲取下一步提示
        next_prompt = self.get_step_prompt(session)
        return True, next_prompt, False
    
    
    def _generate_preview(self, session):
        """
        生成預覽信息
        
        Args:
            session: 會話字典
            
        Returns:
            預覽字符串
        """
        lines = [f"\n指令: {session.cmd_code}"]
        lines.append(f"描述: {session.definition.get('description', '')}")
        lines.append("\n已輸入參數:")
        
        for field_name, value in session.fields.items():
            if isinstance(value, list):
                # 列表值只顯示前幾個和總數
                if len(value) <= 10:
                    values_str = ", ".join([f"0x{v:02X}" for v in value])
                    lines.append(f"  {field_name}: [{values_str}]")
                else:
                    preview_str = ", ".join([f"0x{v:02X}" for v in value[:5]])
                    lines.append(f"  {field_name}: [{preview_str}...] (共 {len(value)} 個值)")
            else:
                lines.append(f"  {field_name}: 0x{value:02X} ({value})")
        
        return "\n".join(lines)
    
    def _get_step_config(self, session, step_num):
        """
        獲取步驟配置
        
        Args:
            session: 會話字典
            step_num: 步驟編號
            
        Returns:
            步驟配置字典
        """
        steps = session.definition.get("steps", [])
        for step_config in steps:
            if step_config.get("step") == step_num:
                return step_config
        return None
    
    def get_session_fields(self, session):
        """
        獲取會話的所有字段數據
        
        Args:
            session: 會話字典
            
        Returns:
            字段字典的副本
        """
        return session.fields.copy()