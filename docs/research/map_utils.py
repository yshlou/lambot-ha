"""SLAM 地图 RLE 解码与 PNG 渲染（v3.3.0，格式已破解）。

格式（逆向自 APK RLEUtil.kt，字节码验证）：
  data[0..2] = "RLE" 魔数
  data[3]    = escape 转义字节（自适应可变）
  data[4]    = 切换标记 b11（初始候选）
  data[5..8] = 输出总长度（小端 4 字节）
  data[9..]  = RLE 流：
    escape <len> <value>  -> 输出 len 个 value
    escape 0x00 <X>        -> 输出 1 个字面 escape 字节；若 X == b11 则切换
                             escape=X（不输出）、b11=旧 escape，i 推进 3
    其他字节               -> 输出 1 个像素

值语义（逆向自 map_view/n.java）：
  0 = 未知（不画/深灰），1..127 = 空闲（白），128..255 = 障碍（深色）

行序：数据第 0 行是地图最底行，渲染时需上下翻转。
"""
from __future__ import annotations

import base64
import struct
import zlib


def decode_rle(raw: bytes, dim_x: int, dim_y: int) -> list[int]:
    """按官方 RLEUtil 算法解码地图数据。"""
    if len(raw) < 9 or raw[:3] != b"RLE":
        return []
    escape = raw[3]
    b11 = raw[4]
    total = int.from_bytes(raw[5:9], "little")
    if total != dim_x * dim_y:
        total = dim_x * dim_y
    out = bytearray()
    i = 9
    n = len(raw)
    while i < n and len(out) < total:
        b = raw[i]
        runlen = 1
        if b == escape:
            if i + 1 < n and raw[i + 1] == 0:
                if i + 2 < n and b11 == raw[i + 2]:
                    # 切换 escape，不输出
                    b11 = escape
                    escape = raw[i + 2]
                    i += 3
                    continue
                # 输出 1 个字面 escape 字节
                i += 2
                b = escape
            else:
                if i + 2 >= n:
                    break
                runlen = raw[i + 1]
                b = raw[i + 2]
                i += 3
        else:
            i += 1
        out.extend([b] * runlen)
    px = list(out[:total])
    if len(px) < total:
        px.extend([0] * (total - len(px)))
    return px


def render_png(px: list[int], dim_x: int, dim_y: int) -> bytes:
    """渲染灰度 PNG。0=未知(深灰)，1..127=空闲(白)，128..255=障碍(黑)。"""
    rows = bytearray()
    for y in range(dim_y):
        rows.append(0)
        src_row = dim_y - 1 - y  # 数据第 0 行是最底行，翻转
        for x in range(dim_x):
            v = px[src_row * dim_x + x]
            if v == 0:
                g = 40
            elif v <= 127:
                g = 255
            else:
                g = 0
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
    if not px:
        return None
    png = render_png(px, dx, dy)
    return png, dx, dy