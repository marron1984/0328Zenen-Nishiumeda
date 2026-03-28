#!/usr/bin/env python3
"""
禅園 西梅田 ─ 四月「宗伝唐茶」造里 季節感動画生成スクリプト
Ken Burns効果 + テキストオーバーレイ + トランジション付きMP4を生成
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import glob
import os

# ===== 設定 =====
OUTPUT_PATH = "/home/user/0328Zenen-Nishiumeda/output_seasonal_tsukuri.mp4"
CANVAS_W, CANVAS_H = 1080, 1350  # 4:5 Instagram最適比率
FPS = 30

# 色定義
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CREAM = (250, 248, 245)
GOLD = (200, 175, 120)
DARK_GREEN = (92, 122, 61)
SOFT_PINK = (220, 190, 190)

# ===== ユーティリティ =====

def load_image(path, target_w=CANVAS_W, target_h=CANVAS_H):
    """画像を読み込み、カバーフィットでリサイズ"""
    img = Image.open(path).convert("RGB")
    # Cover fit
    src_ratio = img.width / img.height
    tgt_ratio = target_w / target_h
    if src_ratio > tgt_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return img


def pil_to_cv2(pil_img):
    """PIL -> OpenCV (BGR)"""
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_img):
    """OpenCV (BGR) -> PIL"""
    return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))


def ease_in_out(t):
    """スムーズなイージング"""
    return t * t * (3 - 2 * t)


def draw_text_pil(img, text, position, font_size=36, color=(255, 255, 255), alpha=255):
    """PIL画像にテキストを描画（日本語対応）"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # フォント（システムフォントを探索）
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
        # フォールバック: 利用可能なフォントを検索
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

    r, g, b = color
    draw.text(position, text, font=font, fill=(r, g, b, alpha))

    img_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(img_rgba, overlay)
    return composite.convert("RGB")


def ken_burns(img, progress, zoom_start=1.0, zoom_end=1.15, pan_x=0, pan_y=0):
    """Ken Burns効果（ゆっくりズーム＋パン）"""
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


def create_frame(base_img, overlays=None):
    """最終フレームを作成"""
    frame = base_img.copy()
    return pil_to_cv2(frame)


# ===== シーン定義 =====

def scene_opening(writer, duration_sec=3.0):
    """オープニング: 黒背景からフェードイン、タイトル表示"""
    total_frames = int(duration_sec * FPS)
    for i in range(total_frames):
        t = i / total_frames

        img = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)

        # 上部の装飾ライン
        draw = ImageDraw.Draw(img)
        line_alpha = int(255 * ease_in_out(min(t * 2, 1.0)))
        line_y = CANVAS_H // 3
        line_color = tuple(int(c * ease_in_out(min(t * 2, 1.0))) for c in GOLD)
        margin = int(CANVAS_W * 0.15)
        draw.line([(margin, line_y), (CANVAS_W - margin, line_y)], fill=line_color, width=1)

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.2) / 0.6)))
        if text_alpha > 0:
            # 「卯月」
            img = draw_text_pil(img, "卯 月", (CANVAS_W // 2 - 80, line_y + 50),
                                font_size=64, color=GOLD, alpha=text_alpha)
            # サブタイトル
            img = draw_text_pil(img, "─  旬 を 、 味 わ う  ─", (CANVAS_W // 2 - 180, line_y + 150),
                                font_size=32, color=CREAM, alpha=text_alpha)

        # 下部ライン
        draw2 = ImageDraw.Draw(img)
        line_y2 = line_y + 250
        draw2.line([(margin, line_y2), (CANVAS_W - margin, line_y2)], fill=line_color, width=1)

        writer.write(pil_to_cv2(img))


def scene_sakura(writer, sakura_img, duration_sec=3.5):
    """桜のシーン: 季節のあしらい"""
    total_frames = int(duration_sec * FPS)
    # 桜画像を大きめに読み込み（Ken Burns用）
    sakura_large = load_image_large(sakura_img, scale=1.3)

    for i in range(total_frames):
        t = i / total_frames

        # Ken Burns: ゆっくりズームアウト
        frame_img = ken_burns(sakura_large, t, zoom_start=1.2, zoom_end=1.0, pan_x=0, pan_y=-30)

        # フェードイン
        if t < 0.15:
            fade = ease_in_out(t / 0.15)
            black = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
            frame_img = Image.blend(black, frame_img, fade)

        # 下部グラデーション
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(CANVAS_H - 300, CANVAS_H):
            alpha = int(180 * ((y - (CANVAS_H - 300)) / 300))
            draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, alpha))
        frame_rgba = frame_img.convert("RGBA")
        frame_img = Image.alpha_composite(frame_rgba, overlay).convert("RGB")

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.25) / 0.5)))
        if text_alpha > 0:
            frame_img = draw_text_pil(frame_img, "春 の 息 吹 を 感 じ て",
                                      (CANVAS_W // 2 - 200, CANVAS_H - 200),
                                      font_size=30, color=CREAM, alpha=text_alpha)

        writer.write(pil_to_cv2(frame_img))


def scene_tsukuri_side(writer, tsukuri_img, duration_sec=4.5):
    """造里 横アングル: メイン料理のお披露目"""
    total_frames = int(duration_sec * FPS)
    tsukuri_large = load_image_large(tsukuri_img, scale=1.25)

    for i in range(total_frames):
        t = i / total_frames

        # Ken Burns: 右から左へゆっくりパン + 微ズーム
        frame_img = ken_burns(tsukuri_large, t, zoom_start=1.15, zoom_end=1.05, pan_x=-40, pan_y=0)

        # フェードイン
        if t < 0.12:
            fade = ease_in_out(t / 0.12)
            black = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
            frame_img = Image.blend(black, frame_img, fade)

        # 上部グラデーション
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(0, 250):
            alpha = int(160 * (1 - y / 250))
            draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, alpha))
        frame_rgba = frame_img.convert("RGBA")
        frame_img = Image.alpha_composite(frame_rgba, overlay).convert("RGB")

        # テキスト（上部）
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.2) / 0.4)))
        if text_alpha > 0:
            frame_img = draw_text_pil(frame_img, "御 献 立 「 宗 伝 唐 茶 」",
                                      (CANVAS_W // 2 - 210, 60),
                                      font_size=30, color=GOLD, alpha=text_alpha)
            frame_img = draw_text_pil(frame_img, "造  里",
                                      (CANVAS_W // 2 - 55, 110),
                                      font_size=44, color=WHITE, alpha=text_alpha)

        writer.write(pil_to_cv2(frame_img))


def scene_tsukuri_top(writer, tsukuri_top_img, duration_sec=4.5):
    """造里 真上アングル: ディテール"""
    total_frames = int(duration_sec * FPS)
    tsukuri_large = load_image_large(tsukuri_top_img, scale=1.25)

    for i in range(total_frames):
        t = i / total_frames

        # Ken Burns: ゆっくりズームイン
        frame_img = ken_burns(tsukuri_large, t, zoom_start=1.0, zoom_end=1.18, pan_x=10, pan_y=15)

        # クロスフェードイン
        if t < 0.15:
            fade = ease_in_out(t / 0.15)
            black = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
            frame_img = Image.blend(black, frame_img, fade)

        # 下部グラデーション
        overlay = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for y in range(CANVAS_H - 350, CANVAS_H):
            alpha = int(200 * ((y - (CANVAS_H - 350)) / 350))
            draw.line([(0, y), (CANVAS_W, y)], fill=(0, 0, 0, alpha))
        frame_rgba = frame_img.convert("RGBA")
        frame_img = Image.alpha_composite(frame_rgba, overlay).convert("RGB")

        # テキスト
        text_alpha = int(255 * ease_in_out(max(0, (t - 0.3) / 0.4)))
        if text_alpha > 0:
            frame_img = draw_text_pil(frame_img, "その日、最も旬を迎えた魚介を",
                                      (CANVAS_W // 2 - 250, CANVAS_H - 250),
                                      font_size=26, color=CREAM, alpha=text_alpha)
            frame_img = draw_text_pil(frame_img, "料理長が見極め、丁寧にお仕立て",
                                      (CANVAS_W // 2 - 250, CANVAS_H - 200),
                                      font_size=26, color=CREAM, alpha=text_alpha)

        # フェードアウト
        if t > 0.88:
            fade_out = ease_in_out((1 - t) / 0.12)
            black = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
            frame_img = Image.blend(black, frame_img, fade_out)

        writer.write(pil_to_cv2(frame_img))


def scene_ending(writer, duration_sec=3.5):
    """エンディング: 店舗情報"""
    total_frames = int(duration_sec * FPS)
    for i in range(total_frames):
        t = i / total_frames

        img = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
        draw = ImageDraw.Draw(img)

        # 装飾ライン（上）
        line_alpha = ease_in_out(min(t * 3, 1.0))
        line_color = tuple(int(c * line_alpha) for c in GOLD)
        margin = int(CANVAS_W * 0.2)
        cy = CANVAS_H // 2
        draw.line([(margin, cy - 160), (CANVAS_W - margin, cy - 160)], fill=line_color, width=1)
        draw.line([(margin, cy + 160), (CANVAS_W - margin, cy + 160)], fill=line_color, width=1)

        text_alpha = int(255 * ease_in_out(max(0, (t - 0.1) / 0.5)))
        if text_alpha > 0:
            img = draw_text_pil(img, "禅  園", (CANVAS_W // 2 - 80, cy - 120),
                                font_size=56, color=GOLD, alpha=text_alpha)
            img = draw_text_pil(img, "西 梅 田", (CANVAS_W // 2 - 60, cy - 45),
                                font_size=32, color=CREAM, alpha=text_alpha)
            img = draw_text_pil(img, "移ろう季節を、お箸の先から。",
                                (CANVAS_W // 2 - 210, cy + 30),
                                font_size=28, color=SOFT_PINK, alpha=text_alpha)
            img = draw_text_pil(img, "四 月 の 御 献 立",
                                (CANVAS_W // 2 - 120, cy + 90),
                                font_size=26, color=CREAM, alpha=int(text_alpha * 0.7))

        # フェードアウト
        if t > 0.85:
            fade_out = ease_in_out((1 - t) / 0.15)
            black = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
            img = Image.blend(black, img, fade_out)

        writer.write(pil_to_cv2(img))


def load_image_large(path, scale=1.3):
    """Ken Burns用に大きめに読み込む"""
    target_w = int(CANVAS_W * scale)
    target_h = int(CANVAS_H * scale)
    return load_image(path, target_w, target_h)


# ===== メイン =====

def main():
    base = "/home/user/0328Zenen-Nishiumeda"

    # 画像パス
    tsukuri_side = os.path.join(base, "3Z7A4062.jpg")
    tsukuri_top = os.path.join(base, "3Z7A4064.jpg")

    # 季節のあしらい画像を探す
    sakura_candidates = glob.glob(os.path.join(base, "*あしらい*")) + \
                        glob.glob(os.path.join(base, "*季節*"))
    sakura_path = sakura_candidates[0] if sakura_candidates else None

    print(f"造里（横）: {tsukuri_side}")
    print(f"造里（上）: {tsukuri_top}")
    print(f"桜あしらい: {sakura_path}")

    # VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(OUTPUT_PATH, fourcc, FPS, (CANVAS_W, CANVAS_H))

    if not writer.isOpened():
        print("ERROR: VideoWriter を開けませんでした")
        return

    print("\n--- 動画生成開始 ---")

    # シーン1: オープニング（3秒）
    print("Scene 1/5: オープニング...")
    scene_opening(writer, 3.0)

    # シーン2: 桜のあしらい（3.5秒）
    if sakura_path:
        print("Scene 2/5: 桜のあしらい...")
        scene_sakura(writer, sakura_path, 3.5)

    # シーン3: 造里 横アングル（4.5秒）
    print("Scene 3/5: 造里（横アングル）...")
    scene_tsukuri_side(writer, tsukuri_side, 4.5)

    # シーン4: 造里 真上アングル（4.5秒）
    print("Scene 4/5: 造里（真上アングル）...")
    scene_tsukuri_top(writer, tsukuri_top, 4.5)

    # シーン5: エンディング（3.5秒）
    print("Scene 5/5: エンディング...")
    scene_ending(writer, 3.5)

    writer.release()
    print(f"\n完成: {OUTPUT_PATH}")
    print(f"解像度: {CANVAS_W}x{CANVAS_H}")
    print(f"FPS: {FPS}")
    total_sec = 3.0 + 3.5 + 4.5 + 4.5 + 3.5
    print(f"長さ: 約{total_sec}秒")


if __name__ == "__main__":
    main()
