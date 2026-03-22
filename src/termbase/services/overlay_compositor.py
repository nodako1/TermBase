from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from termbase.errors import OverlayCompositionError
from termbase.models import AppConfig, ImagePrompt, OverlayCompositeAsset


FONT_CANDIDATES = (
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
)


def compose_overlays(
    config: AppConfig,
    image_prompts: list[ImagePrompt],
    run_directory: Path,
) -> list[OverlayCompositeAsset]:
    output_directory = run_directory / "images" / "composited"
    assets: list[OverlayCompositeAsset] = []

    for prompt in image_prompts:
        base_image_path = run_directory / "images" / f"{prompt.filename_prefix}.png"
        output_path = output_directory / f"{prompt.filename_prefix}.png"
        if not base_image_path.exists():
            raise OverlayCompositionError(f"base image not found for overlay composition: {base_image_path}")
        _compose_single_image(config, base_image_path, output_path, prompt)
        assets.append(
            OverlayCompositeAsset(
                scene_id=prompt.scene_id,
                title=prompt.title,
                base_image_path=base_image_path,
                output_path=output_path,
                speech_bubble_text=prompt.speech_bubble.text,
                graph_type=prompt.graph_overlay.graph_type if prompt.graph_overlay else None,
            )
        )

    return assets


def _compose_single_image(config: AppConfig, base_image_path: Path, output_path: Path, prompt: ImagePrompt) -> None:
    try:
        base_image = Image.open(base_image_path).convert("RGBA")
    except OSError as exc:
        raise OverlayCompositionError(f"failed to open base image: {exc}") from exc

    canvas = base_image.copy()
    bubble_layer = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    graph_layer = Image.new("RGBA", canvas.size, (255, 255, 255, 0))

    _draw_speech_bubble(config, bubble_layer, prompt)
    if prompt.graph_overlay is not None:
        _draw_graph_panel(config, graph_layer, prompt)

    composited = Image.alpha_composite(canvas, graph_layer)
    composited = Image.alpha_composite(composited, bubble_layer)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        composited.save(output_path)
    except OSError as exc:
        raise OverlayCompositionError(f"failed to save composited image: {exc}") from exc


def _draw_speech_bubble(config: AppConfig, layer: Image.Image, prompt: ImagePrompt) -> None:
    draw = ImageDraw.Draw(layer)
    width, height = layer.size
    bubble_width = int(width * 0.42)
    font = _load_font(config, int(width * 0.035))
    lines = _wrap_text(prompt.speech_bubble.text, 14)
    line_height = int(font.size * 1.35)
    bubble_height = max(int(height * 0.14), line_height * len(lines) + int(height * 0.05))
    margin_x = int(width * 0.05)
    margin_y = int(height * 0.04)

    if prompt.speech_bubble.placement == "top-left":
        left = margin_x
    else:
        left = width - margin_x - bubble_width
    top = margin_y
    right = left + bubble_width
    bottom = top + bubble_height

    draw.rounded_rectangle((left, top, right, bottom), radius=28, fill=(255, 255, 255, 236), outline=(30, 30, 30, 255), width=4)
    tail_base_x = left + 60 if prompt.speech_bubble.placement == "top-left" else right - 60
    tail_points = [(tail_base_x, bottom - 4), (tail_base_x + 24, bottom + 34), (tail_base_x + 58, bottom - 4)]
    if prompt.speech_bubble.placement != "top-left":
        tail_points = [(tail_base_x, bottom - 4), (tail_base_x - 24, bottom + 34), (tail_base_x - 58, bottom - 4)]
    draw.polygon(tail_points, fill=(255, 255, 255, 236), outline=(30, 30, 30, 255))

    current_y = top + int(height * 0.022)
    for line in lines:
        text_width = draw.textbbox((0, 0), line, font=font)[2]
        text_x = left + (bubble_width - text_width) / 2
        draw.text((text_x, current_y), line, fill=(20, 20, 20, 255), font=font)
        current_y += line_height


def _draw_graph_panel(config: AppConfig, layer: Image.Image, prompt: ImagePrompt) -> None:
    if prompt.graph_overlay is None:
        return

    draw = ImageDraw.Draw(layer)
    width, height = layer.size
    panel_margin_x = int(width * 0.06)
    panel_height = int(height * 0.26)
    panel_top = height - panel_height - int(height * 0.04)
    panel_rect = (panel_margin_x, panel_top, width - panel_margin_x, panel_top + panel_height)
    title_font = _load_font(config, int(width * 0.028))
    label_font = _load_font(config, int(width * 0.022))

    draw.rounded_rectangle(panel_rect, radius=30, fill=(247, 250, 255, 230), outline=(70, 110, 160, 255), width=4)
    title = _truncate_for_panel(prompt.graph_overlay.source_excerpt, 24)
    draw.text((panel_rect[0] + 26, panel_rect[1] + 18), title, fill=(32, 56, 88, 255), font=title_font)

    if prompt.graph_overlay.graph_type == "flowchart":
        _draw_flowchart(draw, panel_rect, label_font)
    elif prompt.graph_overlay.graph_type == "mapping-diagram":
        _draw_mapping_diagram(draw, panel_rect, label_font)
    elif prompt.graph_overlay.graph_type == "comparison-chart":
        _draw_comparison_chart(draw, panel_rect, label_font)
    else:
        _draw_sequence_diagram(draw, panel_rect, label_font)


def _draw_flowchart(draw: ImageDraw.ImageDraw, panel_rect: tuple[int, int, int, int], font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    labels = ["名前を見る", "DNSに聞く", "行き先へ接続"]
    left, top, right, bottom = panel_rect
    content_top = top + 64
    box_width = int((right - left) * 0.62)
    box_height = 34
    box_left = left + int((right - left - box_width) / 2)
    positions = [content_top, content_top + 52, content_top + 104]
    for index, label in enumerate(labels):
        box_top = positions[index]
        box = (box_left, box_top, box_left + box_width, box_top + box_height)
        draw.rounded_rectangle(box, radius=16, fill=(255, 255, 255, 255), outline=(70, 110, 160, 255), width=3)
        _draw_centered_text(draw, box, label, font, fill=(30, 45, 68, 255))
        if index < len(labels) - 1:
            mid_x = box_left + box_width / 2
            draw.line((mid_x, box_top + box_height, mid_x, positions[index + 1]), fill=(70, 110, 160, 255), width=4)
            draw.polygon([(mid_x - 8, positions[index + 1] - 10), (mid_x + 8, positions[index + 1] - 10), (mid_x, positions[index + 1] + 2)], fill=(70, 110, 160, 255))


def _draw_mapping_diagram(draw: ImageDraw.ImageDraw, panel_rect: tuple[int, int, int, int], font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    left, top, right, bottom = panel_rect
    content_top = top + 78
    box_width = int((right - left) * 0.28)
    box_height = 58
    left_box = (left + 34, content_top, left + 34 + box_width, content_top + box_height)
    right_box = (right - 34 - box_width, content_top, right - 34, content_top + box_height)
    draw.rounded_rectangle(left_box, radius=18, fill=(255, 255, 255, 255), outline=(70, 110, 160, 255), width=3)
    draw.rounded_rectangle(right_box, radius=18, fill=(255, 255, 255, 255), outline=(70, 110, 160, 255), width=3)
    _draw_centered_text(draw, left_box, "名前", font, fill=(30, 45, 68, 255))
    _draw_centered_text(draw, right_box, "IP/住所", font, fill=(30, 45, 68, 255))
    mid_y = content_top + box_height / 2
    draw.line((left_box[2] + 18, mid_y, right_box[0] - 18, mid_y), fill=(70, 110, 160, 255), width=4)
    draw.polygon([(right_box[0] - 26, mid_y - 10), (right_box[0] - 26, mid_y + 10), (right_box[0] - 10, mid_y)], fill=(70, 110, 160, 255))


def _draw_comparison_chart(draw: ImageDraw.ImageDraw, panel_rect: tuple[int, int, int, int], font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    left, top, right, bottom = panel_rect
    content_top = top + 76
    half_width = int((right - left - 84) / 2)
    left_box = (left + 28, content_top, left + 28 + half_width, bottom - 24)
    right_box = (left_box[2] + 28, content_top, right - 28, bottom - 24)
    draw.rounded_rectangle(left_box, radius=18, fill=(255, 255, 255, 255), outline=(70, 110, 160, 255), width=3)
    draw.rounded_rectangle(right_box, radius=18, fill=(255, 255, 255, 255), outline=(70, 110, 160, 255), width=3)
    _draw_centered_text(draw, (left_box[0], left_box[1] + 8, left_box[2], left_box[1] + 38), "身近なたとえ", font, fill=(30, 45, 68, 255))
    _draw_centered_text(draw, (right_box[0], right_box[1] + 8, right_box[2], right_box[1] + 38), "ITの役割", font, fill=(30, 45, 68, 255))
    _draw_centered_text(draw, (left_box[0], left_box[1] + 48, left_box[2], left_box[3]), "電話帳\n案内役", font, fill=(70, 110, 160, 255))
    _draw_centered_text(draw, (right_box[0], right_box[1] + 48, right_box[2], right_box[3]), "名前検索\n行き先特定", font, fill=(70, 110, 160, 255))


def _draw_sequence_diagram(draw: ImageDraw.ImageDraw, panel_rect: tuple[int, int, int, int], font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    left, top, right, bottom = panel_rect
    labels = ["入力", "確認", "変換", "接続"]
    y = top + 110
    x_positions = _evenly_spaced(left + 50, right - 50, len(labels))
    for index, label in enumerate(labels):
        center_x = x_positions[index]
        draw.ellipse((center_x - 28, y - 28, center_x + 28, y + 28), fill=(255, 255, 255, 255), outline=(70, 110, 160, 255), width=3)
        _draw_centered_text(draw, (center_x - 28, y - 18, center_x + 28, y + 18), label, font, fill=(30, 45, 68, 255))
        if index < len(labels) - 1:
            next_x = x_positions[index + 1]
            draw.line((center_x + 28, y, next_x - 28, y), fill=(70, 110, 160, 255), width=4)
            draw.polygon([(next_x - 36, y - 8), (next_x - 36, y + 8), (next_x - 24, y)], fill=(70, 110, 160, 255))


def _load_font(config: AppConfig, size: int):
    if config.overlay_font_path:
        try:
            return ImageFont.truetype(str(config.overlay_font_path), size=size)
        except OSError as exc:
            raise OverlayCompositionError(f"failed to load overlay font: {exc}") from exc

    for candidate in FONT_CANDIDATES:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return ImageFont.truetype(str(candidate_path), size=size)
    return ImageFont.load_default()


def _wrap_text(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in text:
        current += character
        if len(current) >= max_chars:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines or [text]


def _truncate_for_panel(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    text: str,
    font,
    fill: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = rect
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=4, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = left + (right - left - text_width) / 2
    y = top + (bottom - top - text_height) / 2
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=4, align="center")


def _evenly_spaced(start: int, end: int, count: int) -> list[int]:
    if count == 1:
        return [int((start + end) / 2)]
    step = (end - start) / (count - 1)
    return [int(start + step * index) for index in range(count)]