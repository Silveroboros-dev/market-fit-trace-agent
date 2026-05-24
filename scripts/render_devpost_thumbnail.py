from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "devpost-thumbnail-market-fit-v3.png"
LEGACY_OUT = ROOT / "docs" / "assets" / "devpost-thumbnail.png"
WIDTH = 1200
HEIGHT = 800
SCALE = 2


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Avenir.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def s(value: int) -> int:
    return value * SCALE


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: tuple[int, int, int],
    spacing: int = 8,
) -> None:
    draw.multiline_text(
        (s(xy[0]), s(xy[1])),
        text,
        font=font(s(size)),
        fill=fill,
        spacing=s(spacing),
    )


def draw_gradient_text(
    img: Image.Image,
    xy: tuple[int, int],
    text: str,
    size: int,
    start: tuple[int, int, int],
    mid: tuple[int, int, int],
    end: tuple[int, int, int],
) -> None:
    text_font = font(s(size))
    x = s(xy[0])
    y = s(xy[1])
    mask = Image.new("L", img.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((x, y), text, font=text_font, fill=255)
    bbox = mask.getbbox()
    if not bbox:
        return

    gradient = Image.new("RGB", img.size, (255, 255, 255))
    pixels = gradient.load()
    left, top, right, bottom = bbox
    width = max(1, right - left)
    for px in range(left, right):
        t = (px - left) / width
        if t < 0.5:
            local = t / 0.5
            color = tuple(int(start[i] + (mid[i] - start[i]) * local) for i in range(3))
        else:
            local = (t - 0.5) / 0.5
            color = tuple(int(mid[i] + (end[i] - mid[i]) * local) for i in range(3))
        for py in range(top, bottom):
            pixels[px, py] = color

    img.paste(gradient, (0, 0), mask)


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    outline: tuple[int, int, int] | tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(
        tuple(s(v) for v in box),
        radius=s(radius),
        fill=fill,
        outline=outline,
        width=s(width),
    )


def line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    width: int = 1,
) -> None:
    draw.line([(s(x), s(y)) for x, y in points], fill=fill, width=s(width))


def pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    text_fill: tuple[int, int, int],
) -> None:
    text_font = font(s(size))
    width = int(draw.textlength(text, font=text_font) / SCALE) + 34
    height = size + 22
    x, y = xy
    rounded(draw, (x, y, x + width, y + height), height // 2, fill, outline, 1)
    draw.text((s(x + 17), s(y + 10)), text, font=text_font, fill=text_fill)


def main() -> None:
    img = Image.new("RGB", (s(WIDTH), s(HEIGHT)), "#fbfaf7")
    draw = ImageDraw.Draw(img, "RGBA")

    ink = (34, 35, 40)
    muted = (84, 86, 93)
    paper = (255, 255, 252)
    red = (229, 56, 56)
    purple = (180, 54, 169)
    blue = (92, 66, 224)
    green = (78, 139, 103)
    brass = (168, 128, 48)

    # Quiet paper texture and a sparse grid: clean first read, ledger detail close up.
    draw.rectangle((0, 0, s(WIDTH), s(HEIGHT)), fill=(251, 250, 247, 255))
    for x in range(88, 1120, 86):
        line(draw, [(x, 358), (x, 722)], (210, 207, 198, 76), 1)
    for y in range(390, 724, 56):
        line(draw, [(70, y), (1134, y)], (210, 207, 198, 76), 1)

    draw_text(draw, (64, 54), "Market Fit Trace", 64, ink)
    draw_gradient_text(img, (64, 128), "weak proxy audit", 58, red, purple, blue)
    draw = ImageDraw.Draw(img, "RGBA")

    draw_text(
        draw,
        (742, 62),
        "Prediction-market\nmatches need evidence,\nnot adjacency.",
        33,
        ink,
        spacing=4,
    )

    line(draw, [(66, 235), (1134, 235)], (34, 35, 40, 120), 1)
    draw_text(draw, (66, 268), "Gemini proposal -> deterministic fit check", 39, ink)
    draw_text(
        draw,
        (66, 324),
        "Gemini drafts the market thesis. Phoenix traces and deterministic evals "
        "catch the weak proxy.",
        22,
        muted,
    )

    # A wide audit rail, deliberately different from the earlier card thumbnail.
    rail_y = 510
    line(draw, [(116, rail_y), (1038, rail_y)], (34, 35, 40, 145), 2)
    stages = [
        (116, "THESIS", "pasted source", red),
        (346, "CLAIM", "Gemini draft", purple),
        (576, "FIT", "deterministic eval", blue),
        (806, "VERDICT", "human ledger", green),
        (1036, "TRACE", "Phoenix MCP", brass),
    ]
    for x, label, caption, color in stages:
        draw.ellipse((s(x - 18), s(rail_y - 18), s(x + 18), s(rail_y + 18)), fill=(*color, 255))
        draw.ellipse(
            (s(x - 28), s(rail_y - 28), s(x + 28), s(rail_y + 28)),
            outline=(*color, 130),
            width=s(2),
        )
        draw_text(draw, (x - 44, rail_y + 48), label, 16, ink)
        draw_text(draw, (x - 58, rail_y + 76), caption, 15, muted)

    # The failure marker is the actual product moment.
    rounded(draw, (494, 410, 720, 466), 28, (255, 241, 239, 255), (*red, 220), 2)
    draw_text(draw, (526, 424), "WEAK PROXY", 24, red)
    line(draw, [(607, 466), (607, 490)], (*red, 180), 2)

    # Small trace evidence panel, more like an annotation than a UI card.
    rounded(draw, (760, 392, 1084, 458), 8, (*paper, 245), (34, 35, 40, 85), 1)
    draw_text(draw, (784, 407), "eval.false_strong_recommendation = true", 19, ink)
    rounded(draw, (760, 468, 1084, 534), 8, (*paper, 245), (34, 35, 40, 85), 1)
    draw_text(draw, (784, 483), "second_run.fit_class = weak_proxy", 19, ink)

    # Authored markers: enough personal visual texture without borrowing organizer branding.
    for cx, cy, label, color in [
        (82, 706, "01", red),
        (128, 662, "02", purple),
        (174, 706, "03", blue),
    ]:
        draw.ellipse(
            (s(cx - 19), s(cy - 19), s(cx + 19), s(cy + 19)),
            outline=(*color, 220),
            width=s(2),
        )
        tw = draw.textlength(label, font=font(s(12)))
        draw.text((s(cx) - tw / 2, s(cy - 7)), label, font=font(s(12)), fill=(*color, 240))

    line(draw, [(66, 742), (1134, 742)], (34, 35, 40, 110), 1)
    draw_text(draw, (66, 756), "trace-linked prediction-market audit", 17, muted)
    draw_text(draw, (824, 756), "OpenInference / Phoenix trace loop", 17, muted)

    img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    img.save(LEGACY_OUT, optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()
