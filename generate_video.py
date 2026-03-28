#!/usr/bin/env python3
"""
禅園 西梅田 ─ 四月「宗伝唐茶」造里 季節感動画生成スクリプト
全シーン画像背景 + Ken Burns効果 + テキストオーバーレイ
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import glob
import os

# ===== 設定 =====
OUTPUT_PATH = "/home/user/0328Zenen-Nishiumeda/output_seasonal_tsukuri.mp4"
CANVAS_W, CANVAS_H = 1080, 1350  # 4:5 Instagram最適比率
FPS = 30

# 色定義
WHITE = (255, 255, 255)
CREAM = (250, 248, 245)
GOLD = (200, 175, 120)
SOFT_PINK = (220, 190, 190)

# フォントキャッシュ
_font_cache = {}

# ===== ユーティリティ =====

def load_image(path, target_w=CANVAS_W, target_h=CANVAS_H):
    """画像を読み込み、カバーフィットでリサイズ"""
    img = Image.open(path).convert("RGB")
    src_ratio = img.width / img.height
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return img


def load_image_large(path, scale=1.3):
    """Ken Burns用に大きめに読み込む"""
    return load_image(path, int(CANVAS_W * scale), int(CANVAS_H * scale))


def pil_to_cv2(pil_img):
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def ease_in_out(t):
    return t * t * (3 - 2 * t)


def get_font(font_size):
    """フォントを取得（キャッシュ付き）"""
    if font_size in _font_cache:
        return _font_cache[font_size]
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    ]
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                pass
    if font is None:
        import subprocess
        result = subprocess.run(["fc-list", ":lang=ja", "-f", "%{file}\n"],
                                capture_output=True, text=True)
        for fp in result.stdout.strip().split("\n"):
            if fp and os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except:
                    pass
    if font is None:
        font = ImageFont.load_default()
    _font_cache[font_size] = font
    return font


def draw_text_centered(img, text, center_x, y, font_size=36, color=(255, 255, 255), alpha=255):
    """テキストを中央揃えで描画"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = get_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = center_x - text_w // 2
    r, g, b = color
    draw.text((x, y), text, font=font, fill=(r, g, b, alpha))
    img_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(img_rgba, overlay)
    return composite.convert("RGB")


def add_dark_overlay(img, opacity=0.5):
    """画像に暗いオーバーレイを追加"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, int(255 * opacity)))
    img_rgba = img.convert("RGBA")
    return Image.alpha_composite(img_rgba, overlay).convert("RGB")


def add_gradient_overlay(img, direction="bottom", height_ratio=0.4, max_alpha=200):
    """グラデーションオーバーレイを追加"""
    overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    grad_h = int(CANVAS_H * height_ratio)

    if direction == "bottom":
        for y in range(CANVAS_H - grad_h, CANVAS_H):
            a = int(max_alpha * ((y - (CANVAS_H - grad_h)) / grad_h))
            draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, a))
    elif direction == "top":
        for y in range(0, grad_h):
            a = int(max_alpha * (1 - y / grad_h))
            draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, a))
    elif direction == "full":
        for y in range(CANVAS_H):
            a = int(max_alpha * 0.6)
            draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, a))

    frame_rgba = img.convert("RGBA")
    return Image.alpha_composite(frame_rgba, overlay).convert("RGB")


def ken_burns(img, progress, zoom_start=1.0, zoom_end=1.15, pan_x=0, pan_y=0):
    """Ken Burns効果"""
    t = ease_in_out(progress)
    zoom = zoom_start + (zoom_end - zoom_start) * t
    w, h = img.size
    new_w = int(w / zoom)
    new_h = int(h / zoom)
    cx = w // 2 + int(pan_x * t)
    cy = h // 2 + int(pan_y * t)
    left = max(0, cx - new_w // 2)
    top = max(0, cy - new_h // 2)
    right = min(w, left + new_w)
    bottom = min(h, top + new_h)
    cropped = img.crop((left, top, right, bottom))
    return cropped.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)


def crossfade(img_from, img_to, t):
    """2枚の画像をクロスフェード"""
    return Image.blend(img_from, img_to, t)


def draw_decorative_line(img, y, margin_ratio=0.15, color=GOLD, alpha=255):
    """装飾ラインを描画"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    margin = int(CANVAS_W * margin_ratio)
    r, g, b = color
    draw.line([(margin, y), (CANVAS_W - margin, y)], fill=(r, g, b, alpha), width=1)
    img_rgba = img.convert("RGBA")
    return Image.alpha_composite(img_rgba, overlay).convert("RGB")


# ===== シーン定義 =====

def scene_opening(writer, sakura_img, duration_sec=3.5):
    """オープニング: 桜画像をぼかした背景 + タイトル"""
    total_frames = int(duration_sec * FPS)
    sakura_large = load_image_large(sakura_img, scale=1.2)

    for i in range(total_frames):
        t = i / total_frames

        # 桜画像をぼかして背景に
        frame_img = ken_burns(sakura_large, t, zoom_start=1.1, zoom_end=1.0, pan_x=0, pan_y=-20)
        frame_img = frame_img.filter(ImageFilter.GaussianBlur(radius=6))
        frame_img = add_dark_overlay(frame_img, opacity=0.55)

        # フェードイン
        if t < 0.15:
            fade = ease_in_out(t / 0.15)
            dark = add_dark_overlay(frame_img, opacity=1.0 - fade)
            frame_img = dark

        # 装飾ライン
        line_alpha = int(255 * ease_in_out(min(t * 2.5, 1.0)))
        cy = CANVAS_H // 2
        frame_img = draw_decorative_line(frame_img, cy - 120, alpha=line_alpha)
        frame_img = draw_decorative_line(frame_img, cy + 140, alpha=line_alpha)

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.2) / 0.5)))
        if text_alpha > 0:
            frame_img = draw_text_centered(frame_img, "卯 月", CANVAS_W // 2, cy - 80,
                                           font_size=68, color=GOLD, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "─  旬 を 、 味 わ う  ─",
                                           CANVAS_W // 2, cy + 20,
                                           font_size=32, color=CREAM, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "禅 園  西 梅 田",
                                           CANVAS_W // 2, cy + 80,
                                           font_size=24, color=SOFT_PINK, alpha=int(text_alpha * 0.7))

        writer.write(pil_to_cv2(frame_img))


def scene_sakura(writer, sakura_img, duration_sec=3.5):
    """桜のシーン: 季節のあしらい（クリア表示）"""
    total_frames = int(duration_sec * FPS)
    sakura_large = load_image_large(sakura_img, scale=1.3)

    for i in range(total_frames):
        t = i / total_frames

        frame_img = ken_burns(sakura_large, t, zoom_start=1.2, zoom_end=1.0, pan_x=0, pan_y=-30)

        # フェードイン
        if t < 0.15:
            fade = ease_in_out(t / 0.15)
            blurred = frame_img.filter(ImageFilter.GaussianBlur(radius=8))
            dark = add_dark_overlay(blurred, opacity=0.5)
            frame_img = Image.blend(dark, frame_img, fade)

        # 下部グラデーション
        frame_img = add_gradient_overlay(frame_img, "bottom", 0.25, 180)

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.25) / 0.5)))
        if text_alpha > 0:
            frame_img = draw_text_centered(frame_img, "春 の 息 吹 を 感 じ て",
                                           CANVAS_W // 2, CANVAS_H - 180,
                                           font_size=30, color=CREAM, alpha=text_alpha)

        writer.write(pil_to_cv2(frame_img))


def scene_tsukuri_side(writer, tsukuri_img, sakura_img, duration_sec=4.5):
    """造里 横アングル: クロスフェードで桜から遷移"""
    total_frames = int(duration_sec * FPS)
    tsukuri_large = load_image_large(tsukuri_img, scale=1.25)
    sakura_large = load_image_large(sakura_img, scale=1.3)

    for i in range(total_frames):
        t = i / total_frames

        frame_img = ken_burns(tsukuri_large, t, zoom_start=1.15, zoom_end=1.05, pan_x=-40, pan_y=0)

        # クロスフェードイン（桜 → 造里）
        if t < 0.15:
            fade = ease_in_out(t / 0.15)
            sakura_frame = ken_burns(sakura_large, 0.9 + t * 0.5,
                                     zoom_start=1.0, zoom_end=0.95, pan_x=0, pan_y=-30)
            frame_img = crossfade(sakura_frame, frame_img, fade)

        # 上部グラデーション
        frame_img = add_gradient_overlay(frame_img, "top", 0.2, 180)

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.2) / 0.4)))
        if text_alpha > 0:
            frame_img = draw_text_centered(frame_img, "御 献 立「 宗 伝 唐 茶 」",
                                           CANVAS_W // 2, 55,
                                           font_size=30, color=GOLD, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "造  里",
                                           CANVAS_W // 2, 105,
                                           font_size=46, color=WHITE, alpha=text_alpha)

        writer.write(pil_to_cv2(frame_img))


def scene_tsukuri_top(writer, tsukuri_top_img, tsukuri_side_img, duration_sec=4.5):
    """造里 真上アングル: クロスフェードで横→俯瞰"""
    total_frames = int(duration_sec * FPS)
    top_large = load_image_large(tsukuri_top_img, scale=1.25)
    side_large = load_image_large(tsukuri_side_img, scale=1.25)

    for i in range(total_frames):
        t = i / total_frames

        frame_img = ken_burns(top_large, t, zoom_start=1.0, zoom_end=1.18, pan_x=10, pan_y=15)

        # クロスフェードイン（横 → 俯瞰）
        if t < 0.15:
            fade = ease_in_out(t / 0.15)
            side_frame = ken_burns(side_large, 0.9 + t * 0.5,
                                    zoom_start=1.05, zoom_end=1.0, pan_x=-40, pan_y=0)
            frame_img = crossfade(side_frame, frame_img, fade)

        # 下部グラデーション
        frame_img = add_gradient_overlay(frame_img, "bottom", 0.3, 200)

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.3) / 0.4)))
        if text_alpha > 0:
            frame_img = draw_text_centered(frame_img, "その日、最も旬を迎えた魚介を",
                                           CANVAS_W // 2, CANVAS_H - 230,
                                           font_size=26, color=CREAM, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "料理長が見極め、丁寧にお仕立て",
                                           CANVAS_W // 2, CANVAS_H - 180,
                                           font_size=26, color=CREAM, alpha=text_alpha)

        writer.write(pil_to_cv2(frame_img))


def scene_ending(writer, tsukuri_top_img, sakura_img, duration_sec=4.0):
    """エンディング: 造里俯瞰をぼかした背景 + 店舗情報"""
    total_frames = int(duration_sec * FPS)
    top_large = load_image_large(tsukuri_top_img, scale=1.2)
    sakura_large = load_image_large(sakura_img, scale=1.2)

    for i in range(total_frames):
        t = i / total_frames

        # 造里俯瞰と桜をブレンドしてぼかし背景
        bg1 = ken_burns(top_large, t, zoom_start=1.1, zoom_end=1.05, pan_x=5, pan_y=5)
        bg2 = ken_burns(sakura_large, t, zoom_start=1.05, zoom_end=1.0, pan_x=0, pan_y=-10)
        frame_img = Image.blend(bg1, bg2, 0.35)
        frame_img = frame_img.filter(ImageFilter.GaussianBlur(radius=8))
        frame_img = add_dark_overlay(frame_img, opacity=0.5)

        # クロスフェードイン
        if t < 0.12:
            fade = ease_in_out(t / 0.12)
            prev = ken_burns(top_large, 0.95, zoom_start=1.0, zoom_end=1.18, pan_x=10, pan_y=15)
            prev = add_gradient_overlay(prev, "bottom", 0.3, 200)
            frame_img = crossfade(prev, frame_img, fade)

        cy = CANVAS_H // 2

        # 装飾ライン
        line_alpha = int(255 * ease_in_out(min(t * 3, 1.0)))
        frame_img = draw_decorative_line(frame_img, cy - 140, margin_ratio=0.2, alpha=line_alpha)
        frame_img = draw_decorative_line(frame_img, cy + 170, margin_ratio=0.2, alpha=line_alpha)

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.1) / 0.45)))
        if text_alpha > 0:
            frame_img = draw_text_centered(frame_img, "禅  園", CANVAS_W // 2, cy - 100,
                                           font_size=60, color=GOLD, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "西 梅 田", CANVAS_W // 2, cy - 20,
                                           font_size=32, color=CREAM, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "移ろう季節を、お箸の先から。",
                                           CANVAS_W // 2, cy + 40,
                                           font_size=28, color=SOFT_PINK, alpha=text_alpha)
            frame_img = draw_text_centered(frame_img, "四 月 の 御 献 立",
                                           CANVAS_W // 2, cy + 100,
                                           font_size=24, color=CREAM, alpha=int(text_alpha * 0.7))

        # フェードアウト
        if t > 0.85:
            fade_out = ease_in_out((1 - t) / 0.15)
            dark = add_dark_overlay(frame_img, opacity=1.0 - fade_out)
            frame_img = dark

        writer.write(pil_to_cv2(frame_img))


# ===== メイン =====

def main():
    base = "/home/user/0328Zenen-Nishiumeda"

    tsukuri_side = os.path.join(base, "3Z7A4062.jpg")
    tsukuri_top = os.path.join(base, "3Z7A4064.jpg")

    sakura_candidates = glob.glob(os.path.join(base, "*あしらい*")) + \
                        glob.glob(os.path.join(base, "*季節*"))
    sakura_path = sakura_candidates[0] if sakura_candidates else None

    print(f"造里（横）: {tsukuri_side}")
    print(f"造里（上）: {tsukuri_top}")
    print(f"桜あしらい: {sakura_path}")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, FPS, (CANVAS_W, CANVAS_H))

    if not writer.isOpened():
        print("ERROR: VideoWriter を開けませんでした")
        return

    print("\n--- 動画生成開始（全シーン画像背景版） ---")

    print("Scene 1/5: オープニング（桜ぼかし背景）...")
    scene_opening(writer, sakura_path, 3.5)

    print("Scene 2/5: 桜のあしらい...")
    scene_sakura(writer, sakura_path, 3.5)

    print("Scene 3/5: 造里（横アングル）...")
    scene_tsukuri_side(writer, tsukuri_side, sakura_path, 4.5)

    print("Scene 4/5: 造里（真上アングル）...")
    scene_tsukuri_top(writer, tsukuri_top, tsukuri_side, 4.5)

    print("Scene 5/5: エンディング（造里+桜ぼかし背景）...")
    scene_ending(writer, tsukuri_top, sakura_path, 4.0)

    writer.release()

    total_sec = 3.5 + 3.5 + 4.5 + 4.5 + 4.0
    print(f"\n完成: {OUTPUT_PATH}")
    print(f"解像度: {CANVAS_W}x{CANVAS_H} / FPS: {FPS}")
    print(f"長さ: 約{total_sec}秒")


if __name__ == "__main__":
    main()
