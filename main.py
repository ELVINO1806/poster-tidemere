
"""TIDEMERE - a travel poster for a place that isn't there.

Draws one 1024x1024 travel poster with a hand-built rasteriser:
2x supersampling into an RGB buffer, box downsample, PNG encoded
with zlib + struct. Standard library only.

The scene: a small town the sea visits twice a day. A lighthouse-
clocktower stands on a rock in a turquoise lagoon at dusk; stilt
houses with lit windows line the curving shore; lanterns are strung
between poles; two small boats ride the shimmering water. The only
text in the image is the name TIDEMERE, set large in the sky.
"""

import math
import os
import random
import struct
import zlib

SS = 2                 # supersample factor
FW = 1024              # final image size
W = FW * SS            # buffer size
buf = bytearray(W * W * 3)

CREAM = (255, 243, 213)
AMBER = (255, 178, 84)
DARKTEAL = (16, 48, 56)


def _span(sy, xa, xb, color):
    if xb < xa or sy < 0 or sy >= W:
        return
    xa = max(0, xa)
    xb = min(W - 1, xb)
    if xb < xa:
        return
    off = (sy * W + xa) * 3
    buf[off:off + (xb - xa + 1) * 3] = bytes(color) * (xb - xa + 1)


def _blend_px(sx, sy, color, a):
    if sx < 0 or sy < 0 or sx >= W or sy >= W or a <= 0.0:
        return
    i = (sy * W + sx) * 3
    ia = 1.0 - a
    buf[i] = int(buf[i] * ia + color[0] * a)
    buf[i + 1] = int(buf[i + 1] * ia + color[1] * a)
    buf[i + 2] = int(buf[i + 2] * ia + color[2] * a)


def rect(x0, y0, x1, y1, color):
    for sy in range(int(y0 * SS), int(y1 * SS)):
        _span(sy, int(x0 * SS), int(x1 * SS) - 1, color)


def _sample_stops(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for k in range(len(stops) - 1):
        p0, c0 = stops[k]
        p1, c1 = stops[k + 1]
        if t <= p1:
            f = (t - p0) / max(1e-9, (p1 - p0))
            return (int(c0[0] + (c1[0] - c0[0]) * f),
                    int(c0[1] + (c1[1] - c0[1]) * f),
                    int(c0[2] + (c1[2] - c0[2]) * f))
    return stops[-1][1]


def vgrad(y0, y1, stops):
    sy0 = int(y0 * SS)
    sy1 = int(y1 * SS)
    for sy in range(sy0, sy1):
        t = ((sy / SS) - y0) / max(1e-9, (y1 - y0))
        _span(sy, 0, W - 1, _sample_stops(stops, t))


def disc(cx, cy, r, color):
    cx2 = cx * SS
    cy2 = cy * SS
    r2 = r * SS
    for sy in range(int(cy2 - r2), int(cy2 + r2) + 1):
        dy = sy - cy2
        half = math.sqrt(max(0.0, r2 * r2 - dy * dy))
        _span(sy, int(cx2 - half), int(cx2 + half), color)


def glow(cx, cy, r, color, strength):
    cx2 = cx * SS
    cy2 = cy * SS
    r2 = r * SS
    rr = r2 * r2
    for sy in range(int(cy2 - r2), int(cy2 + r2) + 1):
        for sx in range(int(cx2 - r2), int(cx2 + r2) + 1):
            d2 = (sx - cx2) * (sx - cx2) + (sy - cy2) * (sy - cy2)
            if d2 < rr:
                d = math.sqrt(d2) / r2
                _blend_px(sx, sy, color, strength * (1.0 - d) * (1.0 - d))


def poly(pts, color, alpha=1.0):
    P = [(x * SS, y * SS) for (x, y) in pts]
    ys = [p[1] for p in P]
    y0 = max(0, int(min(ys)))
    y1 = min(W - 1, int(max(ys)))
    edges = [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]
    for sy in range(y0, y1 + 1):
        yc = sy + 0.5
        xs = []
        for (ax, ay), (bx, by) in edges:
            if (ay <= yc < by) or (by <= yc < ay):
                xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa = max(0, int(xs[i]))
            xb = min(W - 1, int(xs[i + 1]))
            if xb < xa:
                continue
            if alpha >= 1.0:
                _span(sy, xa, xb, color)
            else:
                for sx in range(xa, xb + 1):
                    _blend_px(sx, sy, color, alpha)


def seg(x0, y0, x1, y1, width, color):
    dist = math.hypot((x1 - x0) * SS, (y1 - y0) * SS)
    steps = max(2, int(dist / 2.5))
    for i in range(steps + 1):
        t = i / steps
        disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, width / 2.0, color)


def hline(x, y, length, color, alpha, thick=2.2):
    sx0 = int(x * SS)
    sx1 = int((x + length) * SS)
    sy0 = int((y - thick / 2.0) * SS)
    sy1 = int((y + thick / 2.0) * SS)
    for sy in range(sy0, sy1 + 1):
        for sx in range(sx0, sx1 + 1):
            _blend_px(sx, sy, color, alpha)


# ---------------------------------------------------------------- glyphs
# Each glyph is a list of strokes; a stroke is a list of (x, y) points in a
# unit box (x right, y down, cap height 1). Drawn squeezed to GW of the
# letter height so the advance can be tighter than the box.

def _bowl(x0, ymid, rx, ry, n=14):
    pts = []
    for k in range(n + 1):
        a = -math.pi / 2 + math.pi * k / n
        pts.append((x0 + rx * math.cos(a), ymid + ry * math.sin(a)))
    return pts


GLYPHS = {
    "T": [[(0.02, 0.0), (0.98, 0.0)], [(0.5, 0.0), (0.5, 1.0)]],
    "I": [[(0.5, 0.0), (0.5, 1.0)], [(0.18, 0.0), (0.82, 0.0)],
          [(0.18, 1.0), (0.82, 1.0)]],
    "D": [[(0.06, 0.0), (0.06, 1.0)], _bowl(0.06, 0.5, 0.88, 0.5)],
    "E": [[(0.06, 0.0), (0.06, 1.0)], [(0.06, 0.0), (0.92, 0.0)],
          [(0.06, 0.5), (0.78, 0.5)], [(0.06, 1.0), (0.92, 1.0)]],
    "M": [[(0.04, 1.0), (0.04, 0.0), (0.5, 0.6), (0.96, 0.0), (0.96, 1.0)]],
    "R": [[(0.06, 0.0), (0.06, 1.0)], _bowl(0.06, 0.26, 0.84, 0.26),
          [(0.42, 0.5), (0.94, 1.0)]],
}
GW = 0.72  # glyph width as a fraction of letter height


def draw_glyph(ch, ox, oy, h, sw, color):
    for stroke in GLYPHS[ch]:
        pts = [(ox + px * GW * h, oy + py * h) for (px, py) in stroke]
        for i in range(len(pts) - 1):
            seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], sw, color)


def draw_word(word, top, h, sw, color, tracking=16.0, dy=0.0):
    adv = 0.80 * h + tracking
    total = adv * len(word) - tracking
    x = (FW - total) / 2.0
    for ch in word:
        draw_glyph(ch, x, top + dy, h, sw, color)
        x += adv


# ---------------------------------------------------------------- scene

def ridge(base, amp1, amp2, phase, ybot, color):
    pts = []
    for x in range(0, FW + 1, 32):
        y = base + amp1 * math.sin(x * 0.011 + phase) \
            + amp2 * math.sin(x * 0.027 + phase * 1.7)
        pts.append((float(x), y))
    pts.append((float(FW), float(ybot)))
    pts.append((0.0, float(ybot)))
    poly(pts, color)


def house(x, base, w, h, body, roof):
    seg(x + 5, base, x + 3, base + 24, 4, DARKTEAL)
    seg(x + w - 5, base, x + w - 3, base + 24, 4, DARKTEAL)
    rect(x, base - h, x + w, base, body)
    rh = h * 0.52
    poly([(x - 5, base - h), (x + w + 5, base - h),
          (x + w / 2.0, base - h - rh)], roof)
    wx = x + w / 2.0
    rect(wx - 6, base - h + 9, wx + 6, base - h + 22, (40, 58, 68))
    rect(wx - 4, base - h + 11, wx + 4, base - h + 20, AMBER)
    glow(wx, base - h + 15, 17, (255, 180, 90), 0.40)
    hline(wx - 7, base + 31, 14, (255, 180, 90), 0.16, 2.5)
    hline(wx - 5, base + 43, 10, (255, 180, 90), 0.09, 2.5)


def boat(cx, cy, s):
    poly([(cx - 58 * s, cy), (cx + 58 * s, cy), (cx + 34 * s, cy + 24 * s),
          (cx - 30 * s, cy + 24 * s)], (12, 46, 56))
    poly([(cx + 4 * s, cy - 50 * s), (cx + 4 * s, cy - 6 * s),
          (cx + 32 * s, cy - 6 * s)], (240, 232, 205))
    seg(cx, cy, cx, cy - 54 * s, 4, (12, 46, 56))
    disc(cx, cy - 58 * s, 4.5, AMBER)
    glow(cx, cy - 58 * s, 17 * s, (255, 180, 90), 0.5)
    for i in range(6):
        hline(cx - 10 * s, cy + 32 * s + i * 8, 20 * s,
              (255, 180, 90), 0.13 - i * 0.017, 2.4)


def bird(x, y, s):
    c = (74, 54, 58)
    seg(x - s, y, x, y - s * 0.5, 3, c)
    seg(x, y - s * 0.5, x + s, y, 3, c)


def draw():
    rnd = random.Random(20261121)

    # sky: coral to peach
    vgrad(0, 580, [(0.0, (247, 116, 88)), (0.45, (255, 150, 102)),
                   (0.8, (255, 190, 128)), (1.0, (255, 213, 158))])

    # low sun with a soft glow
    glow(322, 472, 195, (255, 196, 120), 0.38)
    disc(322, 472, 74, (255, 228, 168))

    # the name, set into the sky; a warm offset copy gives a print shadow
    draw_word("TIDEMERE", 54, 118, 16, (206, 92, 70), dy=5.0)
    draw_word("TIDEMERE", 54, 118, 16, CREAM)

    # layered headlands behind the lagoon
    ridge(498, 24, 11, 0.4, 572, (99, 172, 166))
    ridge(530, 20, 9, 2.1, 578, (52, 130, 132))

    # the lagoon
    vgrad(556, FW, [(0.0, (58, 164, 158)), (0.35, (34, 128, 132)),
                    (1.0, (8, 62, 84))])

    # the lighthouse beam, sweeping right across sky and water
    lamp = (610, 330)
    poly([(618, 328), (1018, 272), (1018, 420), (618, 346)],
         (255, 240, 200), alpha=0.10)
    poly([(618, 331), (1018, 300), (1018, 398), (618, 343)],
         (255, 240, 200), alpha=0.14)
    poly([(618, 333), (1018, 322), (1018, 378), (618, 341)],
         (255, 240, 200), alpha=0.19)

    # the rock
    poly([(512, 606), (700, 606), (668, 548), (612, 528), (556, 544),
          (528, 574)], (26, 62, 72))
    poly([(556, 544), (612, 528), (668, 548), (638, 568), (584, 568)],
         (38, 80, 90))

    # the lighthouse-clocktower
    poly([(564, 574), (656, 574), (640, 354), (580, 354)], (246, 240, 226))
    poly([(610, 574), (656, 574), (640, 354), (610, 354)], (228, 218, 198))
    half452 = 46 - (574 - 452) * (16.0 / 220.0)
    half466 = 46 - (574 - 466) * (16.0 / 220.0)
    poly([(610 - half452, 452), (610 + half452, 452), (610 + half466, 466),
          (610 - half466, 466)], (198, 62, 52))
    rect(572, 346, 648, 356, (40, 60, 70))                    # gallery
    rect(578, 312, 642, 348, (38, 58, 68))                    # lamp room
    poly([(570, 312), (650, 312), (610, 264)], (198, 62, 52))  # roof
    seg(610, 264, 610, 248, 4, (40, 58, 68))
    disc(610, 245, 4.5, (198, 62, 52))
    disc(lamp[0], lamp[1], 12, (255, 196, 92))
    glow(lamp[0], lamp[1], 48, (255, 190, 100), 0.5)
    disc(610, 428, 23, (40, 58, 68))                          # clock
    disc(610, 428, 20, (250, 244, 220))
    seg(610, 428, 610, 411, 4, (40, 50, 60))
    seg(610, 428, 621, 437, 4, (40, 50, 60))
    disc(610, 428, 3, (40, 50, 60))
    rect(596, 475, 624, 505, (40, 58, 68))                    # lit window
    rect(599, 478, 621, 502, AMBER)
    glow(610, 490, 30, (255, 180, 90), 0.45)
    rect(599, 536, 621, 574, (40, 58, 68))                    # door

    # the town: stilt houses along both curving shores
    poly([(0, 604), (110, 590), (250, 594), (390, 610), (428, 636),
          (428, 664), (0, 668)], (24, 66, 74))
    poly([(1024, 600), (900, 588), (790, 596), (716, 620), (700, 646),
          (700, 668), (1024, 664)], (24, 66, 74))
    house(52, 606, 64, 46, (233, 214, 178), (176, 74, 60))
    house(140, 600, 54, 40, (240, 226, 196), (38, 96, 104))
    house(218, 602, 70, 50, (226, 204, 168), (176, 74, 60))
    house(312, 612, 56, 42, (238, 220, 186), (38, 96, 104))
    house(742, 610, 58, 44, (233, 214, 178), (176, 74, 60))
    house(824, 600, 66, 48, (240, 226, 196), (38, 96, 104))
    house(916, 606, 60, 42, (226, 204, 168), (176, 74, 60))

    # lanterns strung between two poles on the left shore
    seg(168, 598, 168, 516, 5, DARKTEAL)
    seg(322, 606, 322, 524, 5, DARKTEAL)
    ctrl = (245, 570)
    prev = (168.0, 516.0)
    lantern_ts = (0.14, 0.32, 0.5, 0.68, 0.86)
    lantern_pts = []
    for k in range(1, 25):
        t = k / 24.0
        bx = (1 - t) ** 2 * 168 + 2 * (1 - t) * t * ctrl[0] + t * t * 322
        by = (1 - t) ** 2 * 516 + 2 * (1 - t) * t * ctrl[1] + t * t * 524
        seg(prev[0], prev[1], bx, by, 2, DARKTEAL)
        prev = (bx, by)
    for t in lantern_ts:
        bx = (1 - t) ** 2 * 168 + 2 * (1 - t) * t * ctrl[0] + t * t * 322
        by = (1 - t) ** 2 * 516 + 2 * (1 - t) * t * ctrl[1] + t * t * 524
        lantern_pts.append((bx, by))
    for (bx, by) in lantern_pts:
        disc(bx, by, 4, (255, 190, 95))
        glow(bx, by, 15, (255, 180, 90), 0.5)

    # reflections: the tower, the sun path, general shimmer
    for i in range(42):
        y = 612 + i * 8.5
        cx = 610 + math.sin(y * 0.045) * 9
        wdt = max(12.0, 36 - i * 0.45)
        hline(cx - wdt / 2, y, wdt, (238, 232, 205), 0.085, 2.6)
    for i in range(8):
        y = 606 + i * 7
        hline(599 + math.sin(y * 0.06) * 5, y, 22, (205, 90, 75), 0.07, 2.4)
    for i in range(26):
        y = 586 + i * 7 + rnd.uniform(-2, 2)
        cx = 322 + rnd.uniform(-26, 26)
        ln = rnd.uniform(14, 44)
        hline(cx - ln / 2, y, ln, (255, 214, 150), 0.10, 2.4)
    for i in range(280):
        y = 596 + (rnd.random() ** 1.25) * 410
        x = rnd.uniform(4, 990)
        ln = rnd.uniform(8, 40)
        hline(x, y, ln, (150, 224, 212), rnd.uniform(0.04, 0.12), 2.2)

    # three small boats with lanterns
    boat(252, 806, 1.0)
    boat(792, 892, 0.78)
    boat(884, 812, 1.12)

    # warm reflections under the town's lit windows and lanterns
    for i in range(16):
        y = 640 + i * 9.5
        for cx0 in (84, 167, 253, 340, 771, 857, 946):
            cx = cx0 + math.sin(y * 0.05 + cx0) * 6
            hline(cx - 9, y, 18, (255, 190, 110), 0.05, 2.4)

    # foreground: dock posts and a sagging rope at the lower left

    # foreground: dock posts and a sagging rope at the lower left
    rect(16, 792, 206, 806, (10, 40, 50))
    rect(34, 788, 72, FW, (9, 38, 48))
    rect(28, 780, 78, 796, (9, 38, 48))
    rect(158, 856, 188, FW, (9, 38, 48))
    rect(152, 849, 194, 863, (9, 38, 48))
    ctrl = (113, 840)
    prev = (53.0, 796.0)
    for k in range(1, 21):
        t = k / 20.0
        bx = (1 - t) ** 2 * 53 + 2 * (1 - t) * t * ctrl[0] + t * t * 173
        by = (1 - t) ** 2 * 796 + 2 * (1 - t) * t * ctrl[1] + t * t * 857
        seg(prev[0], prev[1], bx, by, 7, (7, 32, 42))
        prev = (bx, by)
    seg(113, 830, 113, 840, 3, (7, 32, 42))
    disc(113, 846, 5, (255, 190, 95))
    glow(113, 846, 18, (255, 180, 90), 0.5)

    # birds over the water
    bird(168, 252, 13)
    bird(228, 222, 10)
    bird(852, 238, 12)
    bird(905, 205, 9)
    bird(120, 300, 9)

    # a thin cream frame, like a printed poster's border
    rect(20, 20, 1004, 26, CREAM)
    rect(20, 998, 1004, 1004, CREAM)
    rect(20, 20, 26, 1004, CREAM)
    rect(998, 20, 1004, 1004, CREAM)


# ---------------------------------------------------------------- output

def downsample():
    out = bytearray(FW * FW * 3)
    for oy in range(FW):
        sy = oy * SS
        row0 = (sy * W) * 3
        row1 = ((sy + 1) * W) * 3
        orow = (oy * FW) * 3
        for ox in range(FW):
            sx3 = ox * SS * 3
            i0 = row0 + sx3
            i1 = row1 + sx3
            o = orow + ox * 3
            out[o] = (buf[i0] + buf[i0 + 3] + buf[i1] + buf[i1 + 3] + 2) // 4
            out[o + 1] = (buf[i0 + 1] + buf[i0 + 4] + buf[i1 + 1]
                          + buf[i1 + 4] + 2) // 4
            out[o + 2] = (buf[i0 + 2] + buf[i0 + 5] + buf[i1 + 2]
                          + buf[i1 + 5] + 2) // 4
    return out


def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, w, h, rgb):
    stride = w * 3
    raw = bytearray()
    for y in range(h):
        row = rgb[y * stride:(y + 1) * stride]
        filt = bytearray(stride)
        for i in range(stride):
            left = row[i - 3] if i >= 3 else 0
            filt[i] = (row[i] - left) & 0xFF
        raw.append(1)
        raw += filt
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    draw()
    img = downsample()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    write_png(path, FW, FW, img)
    print("wrote", path)


if __name__ == "__main__":
    main()
