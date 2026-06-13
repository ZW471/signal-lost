"""
Pixel-art avatar generator for Signal Lost characters.

Produces 64x64 RGBA PNG portraits for every named character, drawn
procedurally as chunky cyberpunk pixel art. Re-run to regenerate:

    uv run assets/characters/_generate.py

Output: assets/characters/<id>.png  (+ _contact_sheet.png preview)
"""
import os
from PIL import Image, ImageDraw

SIZE = 64
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- color utils
def hx(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3)) + (255,)


def shade(c, f):
    """Multiply RGB by factor f (keep alpha)."""
    return (max(0, min(255, int(c[0] * f))),
            max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))),
            c[3] if len(c) > 3 else 255)


# ---------------------------------------------------------------- primitives
def canvas(bg_top, bg_bot):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        d.line([(0, y), (SIZE, y)], fill=lerp(bg_top, bg_bot, y / (SIZE - 1)))
    return img, d


def rfill(d, x0, y0, x1, y1, color, r=0):
    """Filled rect with chamfered (45deg) corners for a blocky-rounded look."""
    for y in range(y0, y1 + 1):
        dy = min(y - y0, y1 - y)
        inset = max(0, r - dy)
        d.line([(x0 + inset, y), (x1 - inset, y)], fill=color)


def dot(d, x, y, color, s=1):
    d.rectangle([x, y, x + s - 1, y + s - 1], fill=color)


def vignette_scanlines(img):
    """Add a gentle corner vignette + 1px frame (kept crisp, no scanlines)."""
    d = ImageDraw.Draw(img, "RGBA")
    # vignette (gentle)
    for y in range(SIZE):
        for x in range(SIZE):
            dx = (x - 31.5) / 31.5
            dy = (y - 31.5) / 31.5
            v = dx * dx + dy * dy
            if v > 0.92:
                a = int(min(80, (v - 0.92) * 180))
                px = img.getpixel((x, y))
                img.putpixel((x, y), lerp(px, (0, 0, 0, 255), a / 255)[:3] + (255,))
    # frame
    d.rectangle([0, 0, SIZE - 1, SIZE - 1], outline=(0, 0, 0, 255))
    return img


# ---------------------------------------------------------------- face builder
def base_face(d, skin, hair, eye, collar, *,
              head=(18, 12, 45, 44), neck=True,
              eye_y=24, eye_glow=False, mouth=True, mouth_y=37,
              brow=True, shadow=0.72):
    x0, y0, x1, y1 = head
    cx = (x0 + x1) // 2
    # shoulders / collar
    rfill(d, 6, 46, 57, 63, shade(collar, 0.8), r=4)
    rfill(d, 9, 48, 54, 63, collar, r=3)
    # neck
    if neck:
        rfill(d, cx - 4, 41, cx + 3, 49, shade(skin, 0.82), r=1)
    # head
    rfill(d, x0, y0, x1, y1, skin, r=6)
    # cheek/jaw shading (right side)
    rfill(d, x1 - 6, y0 + 6, x1, y1 - 4, shade(skin, shadow), r=4)
    # brows
    if brow:
        d.line([(x0 + 5, eye_y - 4), (cx - 3, eye_y - 5)], fill=shade(hair, 0.85))
        d.line([(cx + 3, eye_y - 5), (x1 - 5, eye_y - 4)], fill=shade(hair, 0.85))
    # eyes
    if eye_glow:
        for ex in (x0 + 7, x1 - 9):
            dot(d, ex, eye_y, eye, 4)
            dot(d, ex + 1, eye_y, lerp(eye, (255, 255, 255), 0.6), 1)
    else:
        for ex in (x0 + 6, x1 - 9):
            dot(d, ex, eye_y, (245, 245, 245, 255), 4)      # sclera
            dot(d, ex + 1, eye_y, eye, 2)                    # iris
            dot(d, ex + 1, eye_y, shade(eye, 0.4), 1)        # pupil
    # nose
    d.line([(cx, eye_y + 3), (cx, eye_y + 8)], fill=shade(skin, 0.78))
    dot(d, cx, eye_y + 9, shade(skin, 0.7), 1)
    # mouth
    if mouth:
        d.line([(cx - 4, mouth_y), (cx + 4, mouth_y)], fill=shade(skin, 0.62))
    return cx


# ---------------------------------------------------------------- characters
def make_player():
    img, d = canvas(hx("#0d1b2a"), hx("#1b263b"))
    skin, hair, eye, collar = hx("#c79a72"), hx("#3a2a22"), hx("#6ad0ff"), hx("#454852")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24)
    # tousled short hair
    rfill(d, 17, 8, 46, 18, hair, r=6)
    rfill(d, 16, 14, 21, 30, hair, r=3)
    rfill(d, 43, 14, 47, 30, hair, r=3)
    for x in range(19, 45, 3):
        dot(d, x, 9, shade(hair, 1.25), 1)
    # scar across right cheek
    d.line([(40, 26), (43, 33)], fill=shade(skin, 1.18))
    # old-gen temple implant (left), glowing cyan node + traces
    dot(d, 17, 22, hx("#1b3a4a"), 4)
    dot(d, 18, 23, hx("#6ad0ff"), 2)
    d.line([(20, 24), (24, 27)], fill=shade(eye, 0.8))
    d.line([(17, 26), (17, 31)], fill=shade(eye, 0.8))
    return vignette_scanlines(img)


def make_mira():
    img, d = canvas(hx("#0a0f1f"), hx("#16233d"))
    skin, hair, eye, collar = hx("#b9835f"), hx("#15110f"), hx("#2a1d16"), hx("#1d2b45")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24)
    # short, uneven black hair
    rfill(d, 16, 7, 47, 19, hair, r=6)
    rfill(d, 15, 12, 20, 28, hair, r=3)
    rfill(d, 44, 12, 48, 27, hair, r=3)
    # uneven, knife-cut fringe
    for x, h in [(20, 17), (24, 19), (28, 16), (32, 18), (36, 17), (40, 19)]:
        d.line([(x, 16), (x, h)], fill=hair)
    # high jacket collar
    rfill(d, 8, 50, 55, 63, shade(collar, 1.15), r=3)
    d.line([(cx - 6, 49), (cx, 56)], fill=shade(collar, 0.7))
    d.line([(cx + 6, 49), (cx, 56)], fill=shade(collar, 0.7))
    # thin scar on left cheek
    d.line([(22, 28), (23, 33)], fill=shade(skin, 1.2))
    # silver ear pendant (Listener symbol)
    dot(d, 16, 31, hx("#cfd6dd"), 2)
    dot(d, 16, 33, hx("#9aa3ad"), 1)
    return vignette_scanlines(img)


def make_ghost():
    img, d = canvas(hx("#05060a"), hx("#0a0b14"))
    led = hx("#2ea8ff")
    mask, hood = hx("#0c0d12"), hx("#111219")
    # hood
    rfill(d, 12, 6, 51, 46, hood, r=8)
    rfill(d, 6, 40, 57, 63, shade(hood, 0.85), r=5)
    # matte mask face (no skin, no features)
    rfill(d, 19, 13, 44, 45, mask, r=7)
    rfill(d, 39, 18, 44, 42, shade(mask, 0.7), r=4)   # side shadow
    # single LED strip across eye-line, pulsing
    rfill(d, 21, 25, 42, 28, shade(led, 0.35), r=1)   # housing
    rfill(d, 22, 26, 41, 27, led, r=0)
    for x in range(23, 41, 4):
        dot(d, x, 26, lerp(led, (255, 255, 255), 0.7), 2)
    # faint glow bleed below strip
    d.line([(24, 29), (39, 29)], fill=shade(led, 0.4))
    return vignette_scanlines(img)


def make_orin():
    img, d = canvas(hx("#1a1a1d"), hx("#2c2c33"))
    skin, hair, eye, collar = hx("#cdb6a1"), hx("#c9ccd1"), hx("#5b6b78"), hx("#202128")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24, shadow=0.78)
    # silver hair swept back
    rfill(d, 17, 8, 46, 17, hair, r=6)
    rfill(d, 16, 13, 20, 26, hair, r=3)
    rfill(d, 43, 13, 47, 26, hair, r=3)
    for x in range(19, 45, 2):                          # swept-back strands
        d.line([(x, 9), (x + 2, 13)], fill=shade(hair, 1.1))
    # sharp charcoal suit + white shirt + tie
    rfill(d, 6, 46, 57, 63, hx("#15151a"), r=4)
    rfill(d, 28, 48, 35, 63, hx("#d9dde2"), r=0)       # shirt
    rfill(d, 30, 50, 33, 63, hx("#2a3340"), r=0)       # tie
    d.line([(28, 49), (24, 63)], fill=hx("#0c0c10"))   # lapel L
    d.line([(35, 49), (39, 63)], fill=hx("#0c0c10"))   # lapel R
    # silver NEXUS pin on lapel
    dot(d, 22, 53, hx("#dfe4ea"), 2)
    dot(d, 22, 53, hx("#9aa6f0"), 1)
    return vignette_scanlines(img)


def make_patch():
    img, d = canvas(hx("#07120c"), hx("#0e2618"))
    skin, hair, eye, collar = hx("#cfe6d8"), hx("#6b6f68"), hx("#bfeede"), hx("#3a3128")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, shadow=0.8)
    # hollow cheeks
    rfill(d, 20, 33, 24, 40, shade(skin, 0.82), r=2)
    rfill(d, 39, 33, 43, 40, shade(skin, 0.82), r=2)
    # long matted hair
    rfill(d, 15, 6, 48, 20, hair, r=6)
    rfill(d, 14, 14, 19, 46, hair, r=3)
    rfill(d, 44, 14, 49, 46, hair, r=3)
    for x in (15, 17, 46, 48):                          # stringy strands
        d.line([(x, 20), (x, 47)], fill=shade(hair, 0.8))
    # objects strung in hair: lens, barrette, data-chip beads
    dot(d, 15, 30, hx("#e0a32a"), 2)    # cracked amber lens
    dot(d, 17, 38, hx("#c64b4b"), 2)    # red child's barrette
    dot(d, 47, 28, hx("#3fd07a"), 2)    # nexus data chip (green)
    dot(d, 46, 40, hx("#7bb0d6"), 1)    # bit of wire/glass
    # bioluminescent freckles
    for fx, fy in [(26, 30), (38, 31), (32, 41), (24, 28), (40, 38)]:
        dot(d, fx, fy, hx("#7dffba"), 1)
    return vignette_scanlines(img)


def make_lian():
    img, d = canvas(hx("#160a14"), hx("#241420"))
    skin, hair, collar = hx("#d8b489"), hx("#1a1714"), hx("#1f7a5a")
    eye = hx("#3a2c20")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, shadow=0.78)
    # hair worn up in a bun, silver-streaked
    rfill(d, 17, 7, 46, 16, hair, r=6)
    rfill(d, 16, 12, 20, 24, hair, r=3)
    rfill(d, 43, 12, 47, 24, hair, r=3)
    rfill(d, 27, 3, 36, 9, hair, r=3)                  # top bun
    for x in (22, 28, 34, 40):                          # silver streaks
        d.line([(x, 9), (x, 14)], fill=hx("#b8bcc0"))
    dot(d, 31, 5, hx("#b8bcc0"), 1)
    # jade silk collar with gold trim
    rfill(d, 8, 49, 55, 63, collar, r=4)
    d.line([(8, 50), (55, 50)], fill=hx("#d8b24a"))    # gold trim
    d.line([(cx, 51), (cx, 63)], fill=shade(collar, 0.7))
    # jade earrings
    dot(d, 17, 33, hx("#2fae7e"), 2)
    dot(d, 46, 33, hx("#2fae7e"), 2)
    return vignette_scanlines(img)


def make_echo():
    img, d = canvas(hx("#050714"), hx("#0a0f24"))
    glow = hx("#7fdfff")
    # floating data motes
    for mx, my in [(10, 14), (52, 20), (14, 48), (50, 46), (8, 32), (56, 36)]:
        dot(d, mx, my, shade(glow, 0.5), 1)
    # translucent shifting head outline (glitch-displaced rows)
    head = [(20, 12, 44, 44)]
    x0, y0, x1, y1 = head[0]
    import math
    rows = {}
    for y in range(y0, y1 + 1):
        off = int(2.5 * math.sin(y * 0.7))             # deterministic waver
        rows[y] = off
    # body fill (cyan, brighter toward center)
    for y in range(y0, y1 + 1):
        dy = min(y - y0, y1 - y)
        inset = max(0, 6 - dy)
        off = rows[y]
        f = 0.28 + 0.22 * (dy / 8 if dy < 8 else 1)
        d.line([(x0 + inset + off, y), (x1 - inset + off, y)],
               fill=shade(glow, f))
    # RGB-split glitch edges
    for y in range(y0, y1 + 1, 2):
        off = rows[y]
        d.point((x0 + max(0, 6 - min(y - y0, y1 - y)) + off - 1, y), fill=hx("#ff4d6d"))
        d.point((x1 - max(0, 6 - min(y - y0, y1 - y)) + off + 1, y), fill=hx("#4dffd6"))
    # bright glitch scan-bands
    for by in (20, 27, 34):
        d.line([(x0 - 2 + rows[by], by), (x1 + 2 + rows[by], by)], fill=shade(glow, 0.9))
    # two bright eye-glints
    dot(d, 27 + rows[26], 26, lerp(glow, (255, 255, 255), 0.8), 2)
    dot(d, 37 + rows[26], 26, lerp(glow, (255, 255, 255), 0.8), 2)
    return vignette_scanlines(img)


def make_architect():
    img, d = canvas(hx("#14110c"), hx("#1d1812"))
    skin, hair, eye, collar = hx("#bdb6a8"), hx("#e4e2dc"), hx("#7d8a8f"), hx("#2a2620")
    # faint monitor glow + equation flecks behind
    for ex, ey in [(8, 12), (54, 16), (10, 50), (52, 48)]:
        dot(d, ex, ey, hx("#2c4a4a"), 1)
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, shadow=0.7)
    # gaunt: deep eye sockets + sunken cheeks
    rfill(d, 22, 27, 28, 31, shade(skin, 0.65), r=1)
    rfill(d, 36, 27, 42, 31, shade(skin, 0.65), r=1)
    rfill(d, 20, 34, 24, 41, shade(skin, 0.72), r=2)
    rfill(d, 39, 34, 43, 41, shade(skin, 0.72), r=2)
    # thin wispy white hair (receding)
    rfill(d, 19, 9, 44, 15, hair, r=5)
    rfill(d, 17, 13, 21, 28, hair, r=2)
    rfill(d, 43, 13, 47, 28, hair, r=2)
    for x in range(20, 44, 3):
        d.line([(x, 9), (x, 7)], fill=shade(hair, 0.9))
    # stained worn collar
    d.line([(14, 52), (28, 49)], fill=shade(collar, 1.3))
    # faint cyan monitor reflection in eyes
    dot(d, 26, 25, hx("#4fd0d0"), 1)
    dot(d, 37, 25, hx("#4fd0d0"), 1)
    return vignette_scanlines(img)


# ---------------------------------------------------------------- generic archetypes
# Faction / role avatars used as fallbacks for dynamically-spawned NPCs.
def make_nexus_sentinel():
    img, d = canvas(hx("#18141a"), hx("#241016"))
    helm, visor = hx("#2a2d33"), hx("#e23b4b")
    # shoulder armor plates
    rfill(d, 5, 47, 58, 63, hx("#15161b"), r=4)
    rfill(d, 7, 49, 22, 63, shade(helm, 0.8), r=2)
    rfill(d, 41, 49, 56, 63, shade(helm, 0.8), r=2)
    d.line([(31, 49), (31, 63)], fill=hx("#0c0c10"))
    # angular helmet
    rfill(d, 17, 9, 46, 45, helm, r=5)
    rfill(d, 40, 14, 46, 42, shade(helm, 0.72), r=3)   # side shadow
    rfill(d, 20, 8, 43, 12, shade(helm, 1.2), r=3)     # crown highlight
    # red visor strip
    rfill(d, 19, 23, 44, 29, shade(visor, 0.35), r=1)
    rfill(d, 20, 24, 43, 27, visor, r=0)
    for x in range(22, 42, 5):
        dot(d, x, 25, lerp(visor, (255, 255, 255), 0.7), 2)
    # breather grille
    for x in range(28, 36, 2):
        d.line([(x, 34), (x, 39)], fill=shade(helm, 0.6))
    # red NEXUS pin on shoulder
    dot(d, 11, 53, hx("#e23b4b"), 2)
    return vignette_scanlines(img)


def make_nexus_staff():
    img, d = canvas(hx("#1a1a1d"), hx("#2a2a30"))
    skin, hair, eye, collar = hx("#cdb29a"), hx("#2c2622"), hx("#5b6b78"), hx("#202128")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24)
    # neat side-part hair
    rfill(d, 17, 8, 46, 17, hair, r=6)
    rfill(d, 16, 13, 20, 25, hair, r=3)
    rfill(d, 43, 13, 47, 25, hair, r=3)
    d.line([(24, 9), (24, 16)], fill=shade(hair, 0.7))   # part
    # blazer + shirt
    rfill(d, 6, 46, 57, 63, hx("#23242b"), r=4)
    rfill(d, 28, 48, 35, 63, hx("#d9dde2"), r=0)
    d.line([(28, 49), (24, 63)], fill=hx("#15151a"))
    d.line([(35, 49), (39, 63)], fill=hx("#15151a"))
    # ID badge + earpiece
    dot(d, 22, 54, hx("#3fa0c0"), 2)
    dot(d, 22, 56, hx("#d9dde2"), 1)
    dot(d, 47, 27, hx("#8ad0ff"), 1)                     # earpiece glow
    return vignette_scanlines(img)


def make_listener():
    img, d = canvas(hx("#0c1420"), hx("#16202e"))
    skin, hair, eye, collar = hx("#bd9c7c"), hx("#1d1a17"), hx("#3a4658"), hx("#22303f")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, shadow=0.78)
    # hood
    rfill(d, 13, 7, 50, 44, hx("#1a2735"), r=8)
    rfill(d, 6, 41, 57, 63, hx("#16212d"), r=5)
    rfill(d, 19, 13, 44, 45, skin, r=6)                  # face inside hood
    rfill(d, 39, 18, 44, 42, shade(skin, 0.78), r=4)
    # re-draw eyes over face (base_face eyes were under hood box)
    for ex in (26, 36):
        dot(d, ex, 25, (240, 240, 240, 255), 4)
        dot(d, ex + 1, 25, eye, 2)
        dot(d, ex + 1, 25, shade(eye, 0.4), 1)
    d.line([(cx, 28), (cx, 33)], fill=shade(skin, 0.78))
    d.line([(cx - 4, 38), (cx + 4, 38)], fill=shade(skin, 0.62))
    # ear pendant (Listener symbol) prominent on hood edge
    dot(d, 16, 33, hx("#cfd6dd"), 2)
    dot(d, 15, 35, hx("#9aa3ad"), 1)
    dot(d, 17, 35, hx("#9aa3ad"), 1)
    return vignette_scanlines(img)


def make_purist():
    img, d = canvas(hx("#1c1e22"), hx("#2b2e34"))
    skin, hair, eye, collar = hx("#d8cfc4"), hx("#3a342e"), hx("#7a6a58"), hx("#d7d9dc")
    cx = base_face(d, skin, hair, eye, collar, eye_y=23, mouth=False, shadow=0.82)
    # severe cropped hair
    rfill(d, 18, 9, 45, 15, hair, r=4)
    rfill(d, 17, 12, 20, 20, hair, r=2)
    rfill(d, 43, 12, 46, 20, hair, r=2)
    # high white ascetic collar
    rfill(d, 8, 49, 55, 63, hx("#e6e8ea"), r=4)
    rfill(d, 26, 49, 37, 58, shade(collar, 0.92), r=2)
    # white surgical half-mask over nose+mouth
    rfill(d, 24, 30, 39, 41, hx("#eef0f2"), r=3)
    d.line([(24, 33), (39, 33)], fill=shade((230, 232, 234, 255), 0.85))
    d.line([(24, 30), (20, 27)], fill=hx("#cfd2d6"))     # ear loop
    d.line([(39, 30), (43, 27)], fill=hx("#cfd2d6"))
    # red purist cross on collar
    dot(d, 31, 53, hx("#c43a3a"), 1)
    d.line([(31, 52), (31, 55)], fill=hx("#c43a3a"))
    d.line([(30, 53), (32, 53)], fill=hx("#c43a3a"))
    return vignette_scanlines(img)


def make_red_circuit():
    img, d = canvas(hx("#1a0c0e"), hx("#2a1014"))
    skin, hair, eye, collar = hx("#b98668"), hx("#141013"), hx("#d94b4b"), hx("#2a1216")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24, eye_glow=True, shadow=0.7)
    # mohawk, red-tipped
    rfill(d, 28, 4, 35, 16, hair, r=2)
    for y in range(4, 9):
        dot(d, 31, y, hx("#d94b4b"), 2)
    rfill(d, 18, 12, 46, 16, hair, r=3)                  # shaved sides stubble
    # red collar / jacket
    rfill(d, 6, 47, 57, 63, hx("#1f0c0f"), r=4)
    d.line([(8, 50), (55, 50)], fill=hx("#7a1f24"))
    # chrome cheek implant + scar
    rfill(d, 38, 30, 43, 35, hx("#9aa0a8"), r=1)
    for y in range(31, 35):
        dot(d, 40, y, hx("#cfd6dd"), 1)
    d.line([(22, 22), (24, 30)], fill=shade(skin, 1.2))  # scar over brow
    # red circuit-line tattoo on left cheek
    d.line([(21, 33), (24, 33)], fill=hx("#d94b4b"))
    d.line([(24, 33), (24, 37)], fill=hx("#d94b4b"))
    return vignette_scanlines(img)


def make_sprawl_vendor():
    img, d = canvas(hx("#1a1410"), hx("#281e14"))
    skin, hair, eye, collar = hx("#c08a5e"), hx("#1e1813"), hx("#3a2a1e"), hx("#6a4a2e")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, mouth=False, shadow=0.78)
    # head bandana
    rfill(d, 16, 9, 47, 18, hx("#9a3b3b"), r=5)
    d.line([(16, 13), (47, 13)], fill=shade((150, 60, 60, 255), 0.75))
    dot(d, 16, 15, hx("#9a3b3b"), 2)                     # knot
    rfill(d, 16, 18, 20, 26, hair, r=2)                  # hair peeking
    rfill(d, 43, 18, 47, 26, hair, r=2)
    # warm smile
    rfill(d, 27, 37, 36, 39, shade(skin, 0.6), r=1)
    d.line([(26, 36), (28, 38)], fill=shade(skin, 0.6))
    d.line([(37, 36), (35, 38)], fill=shade(skin, 0.6))
    # apron / steam
    rfill(d, 9, 49, 54, 63, hx("#cbb89a"), r=3)
    for x in (24, 31, 38):
        for y in (44, 46):
            dot(d, x, y, hx("#5a6a6a"), 1)
    return vignette_scanlines(img)


def make_street_kid():
    img, d = canvas(hx("#10131a"), hx("#1a1f28"))
    skin, hair, eye, collar = hx("#c2926a"), hx("#241c16"), hx("#3a2a1e"), hx("#2e3640")
    cx = base_face(d, skin, hair, eye, collar, head=(20, 16, 43, 44),
                   eye_y=27, mouth_y=38, shadow=0.78)
    # bigger childlike eyes (overdraw)
    for ex in (24, 36):
        dot(d, ex, 26, (245, 245, 245, 255), 5)
        dot(d, ex + 1, 27, eye, 2)
        dot(d, ex + 1, 27, shade(eye, 0.35), 1)
        dot(d, ex + 1, 26, (255, 255, 255, 255), 1)     # catchlight
    # hood up
    rfill(d, 14, 9, 49, 24, hx("#262d37"), r=8)
    rfill(d, 6, 44, 57, 63, hx("#222831"), r=5)
    rfill(d, 22, 16, 41, 24, hair, r=4)                  # messy fringe
    for x in range(23, 41, 3):
        dot(d, x, 17, shade(hair, 1.2), 1)
    # smudge on cheek
    dot(d, 39, 36, shade(skin, 0.6), 2)
    return vignette_scanlines(img)


def make_neon_dealer():
    img, d = canvas(hx("#14081a"), hx("#1e0a24"))
    skin, hair, collar = hx("#bd8d6a"), hx("#181018"), hx("#241030")
    cx = base_face(d, skin, hair, hx("#000000"), collar, eye_y=24, shadow=0.72)
    # slicked hair w/ magenta sheen
    rfill(d, 17, 8, 46, 16, hair, r=6)
    rfill(d, 16, 13, 20, 24, hair, r=3)
    rfill(d, 43, 13, 47, 24, hair, r=3)
    for x in range(20, 44, 3):
        d.line([(x, 9), (x + 2, 13)], fill=hx("#c23bd0"))
    # reflective shades (cover eyes)
    rfill(d, 20, 22, 43, 28, hx("#0a0a10"), r=2)
    rfill(d, 21, 23, 30, 27, hx("#2ad0d0"), r=1)         # cyan lens
    rfill(d, 33, 23, 42, 27, hx("#d03bb0"), r=1)         # magenta lens
    d.line([(30, 24), (33, 24)], fill=hx("#0a0a10"))     # bridge
    # smirk
    d.line([(28, 37), (35, 37)], fill=shade(skin, 0.6))
    d.line([(35, 37), (37, 35)], fill=shade(skin, 0.6))
    # neon collar trim
    rfill(d, 6, 47, 57, 63, hx("#1a0c22"), r=4)
    d.line([(8, 50), (55, 50)], fill=hx("#2ad0d0"))
    return vignette_scanlines(img)


def make_scavenger():
    img, d = canvas(hx("#14110c"), hx("#1e1a12"))
    skin, hair, eye, collar = hx("#b58a64"), hx("#2a2018"), hx("#3a2c1e"), hx("#3a3026")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24, mouth=False, shadow=0.72)
    # matted hair
    rfill(d, 16, 8, 47, 18, hair, r=6)
    rfill(d, 15, 14, 20, 30, hair, r=3)
    rfill(d, 43, 14, 48, 30, hair, r=3)
    # goggles pushed up on forehead
    rfill(d, 19, 16, 44, 21, hx("#2a2620"), r=2)
    dot(d, 23, 18, hx("#7a8a6a"), 3)
    dot(d, 38, 18, hx("#7a8a6a"), 3)
    d.line([(31, 18), (33, 18)], fill=hx("#15120c"))
    # dust mask over nose/mouth
    rfill(d, 24, 31, 39, 41, hx("#6a5f4e"), r=3)
    d.line([(24, 31), (20, 28)], fill=hx("#4a4236"))
    d.line([(39, 31), (43, 28)], fill=hx("#4a4236"))
    dot(d, 31, 36, hx("#3a342a"), 2)                     # filter
    # grime
    dot(d, 22, 28, shade(skin, 0.6), 2)
    return vignette_scanlines(img)


def make_fragment_touched():
    img, d = canvas(hx("#07120c"), hx("#0d2417"))
    skin, hair, eye, collar = hx("#cfe6da"), hx("#5f6a64"), hx("#9dffce"), hx("#2a322c")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, eye_glow=True, shadow=0.85)
    # wispy hair
    rfill(d, 17, 8, 46, 17, hair, r=6)
    rfill(d, 16, 13, 19, 32, hair, r=2)
    rfill(d, 44, 13, 47, 32, hair, r=2)
    for x in range(20, 44, 4):
        d.line([(x, 9), (x, 7)], fill=shade(hair, 1.2))
    # bioluminescent veins / freckles
    for fx, fy in [(25, 30), (38, 31), (31, 40), (23, 35), (40, 36), (31, 21)]:
        dot(d, fx, fy, hx("#7dffba"), 1)
    d.line([(20, 33), (22, 38)], fill=shade((125, 255, 186, 255), 0.7))
    # vacant glow halo
    dot(d, 31, 12, hx("#3fd07a"), 1)
    return vignette_scanlines(img)


def make_chrome_elite():
    img, d = canvas(hx("#100a16"), hx("#1c1424"))
    skin, hair, eye, collar = hx("#d8b48c"), hx("#1a1612"), hx("#3a2c20"), hx("#2a2030")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, shadow=0.78)
    # sleek styled hair
    rfill(d, 17, 7, 46, 16, hair, r=6)
    rfill(d, 16, 12, 20, 26, hair, r=3)
    rfill(d, 43, 12, 47, 26, hair, r=3)
    for x in range(20, 44, 3):
        d.line([(x, 8), (x + 2, 12)], fill=shade(hair, 1.3))
    # luxe collar w/ gold trim
    rfill(d, 8, 48, 55, 63, hx("#2a2030"), r=4)
    d.line([(8, 50), (55, 50)], fill=hx("#d8b24a"))
    d.line([(cx, 51), (cx, 63)], fill=hx("#d8b24a"))
    # gold earrings + brooch
    dot(d, 17, 33, hx("#e6c24a"), 2)
    dot(d, 46, 33, hx("#e6c24a"), 2)
    dot(d, 24, 53, hx("#e6c24a"), 1)
    return vignette_scanlines(img)


def make_fixer():
    img, d = canvas(hx("#160e08"), hx("#221608"))
    skin, hair, eye, collar = hx("#b98a5e"), hx("#15110c"), hx("#3a2a1a"), hx("#1c160e")
    cx = base_face(d, skin, hair, eye, collar, eye_y=24, mouth=False, shadow=0.7)
    # slicked-back hair
    rfill(d, 17, 8, 46, 15, hair, r=6)
    rfill(d, 16, 12, 20, 23, hair, r=3)
    rfill(d, 43, 12, 47, 23, hair, r=3)
    for x in range(20, 44, 3):
        d.line([(x, 9), (x + 3, 13)], fill=shade(hair, 1.25))
    # goatee
    rfill(d, 28, 38, 35, 43, hair, r=2)
    d.line([(28, 33), (28, 38)], fill=hair)
    d.line([(35, 33), (35, 38)], fill=hair)
    # confident smirk + gold tooth glint
    d.line([(28, 37), (35, 37)], fill=shade(skin, 0.55))
    dot(d, 33, 37, hx("#e6c24a"), 1)
    # gold earring + collar trim
    dot(d, 46, 31, hx("#e6c24a"), 2)
    rfill(d, 6, 47, 57, 63, hx("#1c160e"), r=4)
    d.line([(8, 50), (55, 50)], fill=hx("#a8842e"))
    return vignette_scanlines(img)


def make_civilian():
    img, d = canvas(hx("#14161c"), hx("#20242c"))
    skin, hair, eye, collar = hx("#c2966c"), hx("#332a22"), hx("#3a2c20"), hx("#3a4048")
    cx = base_face(d, skin, hair, eye, collar, eye_y=25, shadow=0.76)
    rfill(d, 17, 8, 46, 18, hair, r=6)
    rfill(d, 16, 13, 20, 28, hair, r=3)
    rfill(d, 43, 13, 47, 28, hair, r=3)
    return vignette_scanlines(img)


def make_unknown():
    img, d = canvas(hx("#0e0f14"), hx("#16181f"))
    sil = hx("#2c303a")
    # featureless silhouette
    rfill(d, 6, 47, 57, 63, sil, r=5)
    rfill(d, 19, 13, 44, 45, sil, r=7)
    rfill(d, 28, 41, 35, 47, sil, r=1)                   # neck
    # glowing "?" cyan
    q = hx("#46c8d2")
    d.line([(28, 24), (35, 24)], fill=q)
    d.line([(35, 24), (35, 29)], fill=q)
    d.line([(35, 29), (31, 30)], fill=q)
    d.line([(31, 30), (31, 33)], fill=q)
    dot(d, 31, 36, q, 2)
    return vignette_scanlines(img)


CHARACTERS = {
    "player": ("Player (Amnesiac)", make_player),
    "mira": ("Mira", make_mira),
    "ghost": ("Ghost", make_ghost),
    "orin": ("Director Orin", make_orin),
    "patch": ("Patch", make_patch),
    "lian": ("Senator Lian", make_lian),
    "echo": ("Echo", make_echo),
    "architect": ("The Architect / Shen Wei", make_architect),
}

# Generic faction / role avatars (fallbacks for dynamically-spawned NPCs).
GENERICS = {
    "nexus_sentinel": ("NEXUS Sentinel", make_nexus_sentinel),
    "nexus_staff": ("NEXUS Staff", make_nexus_staff),
    "listener": ("Listener", make_listener),
    "purist": ("Purist", make_purist),
    "red_circuit": ("Red Circuit", make_red_circuit),
    "sprawl_vendor": ("Sprawl Vendor", make_sprawl_vendor),
    "street_kid": ("Street Kid", make_street_kid),
    "neon_dealer": ("Neon Row Dealer", make_neon_dealer),
    "scavenger": ("Undercroft Scavenger", make_scavenger),
    "fragment_touched": ("Fragment-Touched", make_fragment_touched),
    "chrome_elite": ("Chrome Heights Elite", make_chrome_elite),
    "fixer": ("Fixer", make_fixer),
    "civilian": ("Civilian", make_civilian),
    "unknown": ("Unknown", make_unknown),
}


def _render(registry):
    made = []
    for cid, (name, fn) in registry.items():
        img = fn()
        img.save(os.path.join(HERE, f"{cid}.png"))
        made.append((cid, name, img))
        print(f"  {cid:18s} -> {cid}.png  ({name})")
    return made


def _contact_sheet(made, path):
    scale, cols = 4, len(made)
    cw = SIZE * scale
    sheet = Image.new("RGBA", (cw * cols, cw + 4), (12, 12, 18, 255))
    for i, (_cid, _name, img) in enumerate(made):
        sheet.paste(img.resize((cw, cw), Image.NEAREST), (i * cw, 2))
    sheet.save(path)


def main():
    import json
    print("Named characters:")
    named = _render(CHARACTERS)
    print("\nGeneric archetypes:")
    generic = _render(GENERICS)

    _contact_sheet(named, os.path.join(HERE, "_contact_sheet.png"))
    _contact_sheet(generic, os.path.join(HERE, "_contact_generic.png"))

    manifest = {
        "size": SIZE,
        "named": [cid for cid in CHARACTERS],
        "generic": [cid for cid in GENERICS],
    }
    with open(os.path.join(HERE, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nGenerated {len(named)} named + {len(generic)} generic avatars, "
          f"manifest.json, and 2 contact sheets in assets/characters/")


if __name__ == "__main__":
    main()
