"""SLAM 地图 RLE 解码与 PNG 渲染。

注意：RLE 格式尚未完全破解（数据为多层结构，像素流仅占前段），
decode_map_payload 暂未被调用，保留供后续研究使用。
"""
from __future__ import annotations

import base64
import struct
import zlib


def decode_rle(raw: bytes, dim_x: int, dim_y: int) -> list[int]:
    """解码 SLAMTEC RLE 地图（当前实现为实验性，格式待确认）。

    格式：魔数 "RLE" + 头部 + 像素流；
    像素流：高 bit(0x80) 标记 run（值=b&0x7f，后跟长度-1），否则单字节像素。
    """
    total = dim_x * dim_y
    px: list[int] = []
    i = 3
    n = len(raw)
    while i < n and len(px) < total:
        b = raw[i]
        if b & 0x80:
            v = b & 0x7f
            if i + 1 >= n:
                break
            cnt = raw[i + 1] + 1
            px.extend([v] * cnt)
            i += 2
        else:
            px.append(b)
            i += 1
    if len(px) < total:
        px.extend([0] * (total - len(px)))
    return px[:total]


def render_png(px: list[int], dim_x: int, dim_y: int) -> bytes:
    """把像素渲染成灰度 PNG。1=空闲(白)，0=未知(深灰)，高值=障碍(黑)。"""
    rows = bytearray()
    for y in range(dim_y):
        rows.append(0)
        for x in range(dim_x):
            v = px[y * dim_x + x]
            if v == 1:
                g = 255
            elif v == 0:
                g = 60
            elif v >= 100:
                g = 0
            else:
                g = max(0, 200 - v * 2)
            rows.append(g)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", dim_x, dim_y, 8, 0, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(rows)))
        + chunk(b"IEND", b"")
    )
    return png


def decode_map_payload(p: dict) -> tuple[bytes, int, int] | None:
    """从消息 payload 提取并解码地图 PNG。返回 (png, dim_x, dim_y) 或 None。"""
    md = p.get("map_data")
    if not md:
        return None
    try:
        raw = base64.b64decode(md)
    except Exception:
        return None
    dx = int(p.get("dimension_x", 0))
    dy = int(p.get("dimension_y", 0))
    if dx <= 0 or dy <= 0:
        return None
    px = decode_rle(raw, dx, dy)
    png = render_png(px, dx, dy)
    return png, dx, dy