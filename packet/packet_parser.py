"""
資料驅動封包解析器
"""
import binascii
from core.frame import FrameDecoder
from packet.packet_definition import PacketDefinition
from log_config.setup import get_logger
import datetime

class PacketParser():
    """封包解析器"""
    
    def __init__(self,  mode="receive"):
        self.logger = get_logger(f"tc.{mode}")
        self.field_parser = UnifiedFieldParser()
        self.frame_decoder = FrameDecoder()
    
    def parse(self, frame):
        """解析封包"""
        try:
            
            decoded = self.frame_decoder.decode(frame)
            
            # ACK 框處理
            if decoded["type"] == "ACK":
                return {
                    "type": "ACK",
                    "序列號": decoded["seq"],
                    "addr": decoded["addr"],
                    "len": decoded["len"]
                }
            
            # STX 框處理
            if decoded["type"] == "STX":
                return self._parse_stx(decoded, frame)
            
            return None
            
        except Exception as e:
            #self.logger.error(f"解析失敗: {e}", exc_info=True)
            return None
    
    def _parse_stx(self, decoded, frame):
        """解析 STX 框"""
        payload = decoded["payload"]  
        
        if len(payload) < 2:
            return None
        
        # 構建指令碼
        command_prefix = payload[0]
        command_suffix = payload[1]
        cmd_code = f"{command_prefix:02X}{command_suffix:02X}"
        
        # 查找定義
        definition = PacketDefinition().get_definition(cmd_code=cmd_code)
        
        header = {
        "序列號": decoded["seq"],
        "addr": decoded["addr"],
        "len": decoded["len"]
        }        
        
        # 未定義的指令碼(包含5F80)
        if not definition:            
            #self.logger.error(f"未定義的指令碼: {cmd_code}")
            #self.logger.error(f"封包內容: {binascii.hexlify(frame).decode('ascii')}")
            result = {
                "序列號": decoded["seq"],
                "號誌控制器ID": decoded["addr"],
                "欄位長度": decoded["len"],
                "指令編號": cmd_code,
                "原始封包": binascii.hexlify(frame).decode('ascii'),
                "接收時間": datetime.datetime.now().isoformat()
            }
            
            
            return result
        
        # 解析封包
        return self._parse_by_definition(definition, header, payload, cmd_code, frame)
    
    
    def _parse_by_definition(self, definition, header, 
                            payload, cmd_code, frame):
        """根據定義解析封包 - 統一處理所有字段"""
        # 基礎字段
        result = {
            "序列號": header["序列號"],
            "號誌控制器ID": header["addr"],
            "欄位長度": header["len"],
            "指令編號": cmd_code,
            "指令": definition.get("name", ""),
            "回覆類型": definition.get("reply_type", ""),
            "needs_ack": definition.get("needs_ack", False),
            "原始封包": binascii.hexlify(frame).decode('ascii'),
            "接收時間": datetime.datetime.now().isoformat()
        }
        
        # 解析payload字段
        if "fields" in definition:
            result = self.field_parser.parse_fields(
                payload, definition["fields"], result
            )     
        return result
    
class UnifiedFieldParser:
    """統一字段解析器"""
    
    def __init__(self):
        self.definitions = PacketDefinition
    
    def parse_fields(self, payload, fields, result):
        """解析payload字段（統一處理）"""
        current_index = 0  # 當前 PAYLOAD 索引位置
        
        for field in fields:
            field_name = field["name"]
            field_type = field.get("type", "uint8")
            field_index = field.get("index")
            
            
            # 計算實際索引位置
            if field_index is None:
                actual_index = current_index
            else:
                # 固定索引
                actual_index = field_index
            
            # 解析字段值
            value = self._parse_field_by_type(payload, field, actual_index, result)
            
            if value is not None:
                # 應用映射（如果有）
                if "mapping" in field:
                    mapping = field["mapping"]
                    processed_value = mapping.get(value, f"未知(0x{value:02X})")
                else:
                    processed_value = value
                
                #應用後處理（如果有）
                if "post_process" in field:
                    result[field_name] = field["post_process"](processed_value, result)
                else:
                    result[field_name] = processed_value
            else:
                result[field_name] = None
            
            # 更新當前索引（用於下一個字段）
            if field_index != "dynamic" and field_index is not None:
                current_index = self._calculate_next_index(
                    actual_index, field_type, field, value, result
                )
        
        return result
    
    def _parse_field_by_type(self, payload, field, 
                            index, result):
        """根據字段類型解析"""
        field_type = field["type"]
        
        if field_type == "uint8":
            return self._parse_uint8(payload, index)
        elif field_type == "uint16":
            endian = field.get("endian", "big")
            return self._parse_uint16(payload, index, endian)
        elif field_type == "list":
            return self._parse_list(payload, field, index, result)
        elif field_type == "struct_list":
            return self._parse_struct_list(payload, field, index, result)
        else:
            return None
    
    def _parse_uint8(self, payload, index):
        """解析 uint8"""
        if index >= len(payload):
            return None
        return payload[index]
    
    def _parse_uint16(self, payload, index, endian="big"):
        """解析 uint16"""
        if index + 1 >= len(payload):
            return None
        return int.from_bytes(payload[index:index+2], endian)
    
    def _parse_list(self, payload, field, index, result):
        """解析列表字段"""
        count = result.get(field.get("count_from", ""), 0)
        item_type = field.get("item_type", "uint8")
        items = []
        
        type_def = PacketDefinition().get_field_type(field_type=item_type)
        if not type_def:
            return items
        
        item_size = type_def["size"]
        for i in range(count):
            item_index = index + i * item_size
            if item_index + item_size <= len(payload):
                if item_type == "uint16":
                    endian = field.get("endian", "big")
                    items.append(self._parse_uint16(payload, item_index, endian))
                else:
                    items.append(self._parse_uint8(payload, item_index))
        
        return items
    
    def _parse_struct_list(self, payload, field, index, result):
        """解析結構體列表字段"""
        count = result.get(field.get("count_from", ""), 0)
        item_fields = field.get("item_fields", [])
        items = []
        
        current_index = index
        for i in range(count):
            item = {}
            for item_field in item_fields:
                field_type = item_field["type"]
                field_name = item_field["name"]
                
                if field_type == "uint8":
                    value = self._parse_uint8(payload, current_index)
                    current_index += 1
                elif field_type == "uint16":
                    endian = item_field.get("endian", "big")
                    value = self._parse_uint16(payload, current_index, endian)
                    current_index += 2
                else:
                    value = None
                
                item[field_name] = value if value is not None else 0
            
            items.append(item)
        
        return items
    
    
    def _calculate_next_index(self, current_index, field_type, 
                             field, value, result):
        """計算下一個字段的索引位置"""
        if field_type == "uint8":
            return current_index + 1
        elif field_type == "uint16":
            return current_index + 2
        elif field_type == "list":
            count = result.get(field.get("count_from", ""), 0)
            item_type = field.get("item_type", "uint8")
            item_size = 1 if item_type == "uint8" else 2
            return current_index + count * item_size
        elif field_type == "struct_list":
            count = result.get(field.get("count_from", ""), 0)
            item_fields = field.get("item_fields", [])
            item_size = sum(1 if f["type"] == "uint8" else 2 for f in item_fields)
            return current_index + count * item_size
        else:
            return current_index + 1


