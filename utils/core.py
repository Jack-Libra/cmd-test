import struct
import logging

DLE = 0xAA
STX = 0xBB
ETX = 0xCC
ACK = 0xDD
NAK = 0xEE

def _u8(x: int) -> int:
    if not (0 <= x <= 0xFF):
        raise ValueError(f"u8 range error: {x}")
    return x

def _u16(x: int) -> int:
    if not (0 <= x <= 0xFFFF):
        raise ValueError(f"u16 range error: {x}")
    return x

def xor_checksum(data: bytes) -> int:
    """XOR 校驗和"""
    result = 0
    for b in data:
        result ^= b
    return result & 0xFF

def stuff_info(info: bytes) -> bytes:
    """INFO 轉義：0xAA -> 0xAA 0xAA"""
    out = bytearray()
    for b in info:
        out.append(b)
        if b == 0xAA:
            out.append(0xAA)
    return bytes(out)

def restore_info(stuffed: bytes) -> bytes:
    """INFO 還原：0xAA 0xAA -> 0xAA"""
    out = bytearray()
    i, n = 0, len(stuffed)
    while i < n:
        b = stuffed[i]
        if b == 0xAA and i+1 < n and stuffed[i+1] == 0xAA:
            out.append(0xAA)
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)

class MessageFrame:
    """訊息框：DLE STX SEQ ADDR(2) LEN(2) INFO DLE ETX CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int, info: bytes) -> bytes:
        stuffed = stuff_info(info)
        length = 1+1+1+2+2+len(stuffed)+1+1
        hdr = struct.pack(">BBBHH", DLE, STX, _u8(seq), _u16(addr), _u16(length))
        tail = struct.pack(">BB", DLE, ETX)
        cks = xor_checksum(hdr + stuffed + tail)
        return hdr + stuffed + tail + struct.pack(">B", cks)
    
    @staticmethod
    def decode(frame: bytes) -> dict:
        if not frame or frame[0] != DLE or frame[1] != STX:
            raise ValueError("非訊息框")
        if xor_checksum(frame[:-1]) != frame[-1]:
            raise ValueError("校驗和錯誤")
        if frame[-3] != DLE or frame[-2] != ETX:
            print(frame.hex().upper())
            raise ValueError("尾端格式錯誤")
        
        seq = frame[2]
        addr = int.from_bytes(frame[3:5], 'big')
        stuffed_info = frame[7:-3]
        info = restore_info(stuffed_info)
        
        return {"seq": seq, "addr": addr, "info": info}

class Ack:
    """ACK 框：DLE ACK SEQ ADDR(2) LEN(2) CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int) -> bytes:
        hdr = struct.pack(">BBBHH", DLE, ACK, _u8(seq), _u16(addr), 8)
        cks = xor_checksum(hdr)
        return hdr + struct.pack(">B", cks)

    @staticmethod
    def decode(frame: bytes) -> dict:
        if not frame or frame[0] != DLE or frame[1] != ACK:
            raise ValueError("非 ACK 框")
        if xor_checksum(frame[:-1]) != frame[-1]:
            raise ValueError("校驗和錯誤")
        seq = frame[2]
        addr = int.from_bytes(frame[3:5], 'big')
        return {"seq": seq, "addr": addr}

class Nak:
    """NAK 框：DLE NAK SEQ ADDR(2) LEN(2) ERR CKS"""
    
    @staticmethod
    def encode(seq: int, addr: int, err: int) -> bytes:
        hdr = struct.pack(">BBBHHB", DLE, NAK, _u8(seq), _u16(addr), 9, _u8(err))
        cks = xor_checksum(hdr)
        return hdr + struct.pack(">B", cks)

  