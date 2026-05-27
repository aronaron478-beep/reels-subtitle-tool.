import streamlit as st
import tempfile
import os
import re
from datetime import timedelta
from pathlib import Path

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🎬 Reels Subtitle Burner",
    page_icon="🎬",
    layout="centered",
)

# ─────────────────────────────────────────────
# Custom CSS – dark cinematic theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0d0d0d;
    color: #e8e8e0;
}
.stApp { background-color: #0d0d0d; }

h1 { font-size: 2.4rem; font-weight: 800; letter-spacing: -1px; color: #f0e040; }
h2, h3 { color: #e8e8e0; }

.block-container { padding-top: 2.5rem; max-width: 780px; }

.stFileUploader > label { color: #aaa; font-size: 0.85rem; }
.stFileUploader > div { border: 1px dashed #333; border-radius: 10px; background: #161616; }

.stSlider > div > div > div { background: #f0e040; }

.stButton > button {
    background: #f0e040;
    color: #0d0d0d;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    border: none;
    border-radius: 6px;
    padding: 0.6rem 2rem;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity .2s;
}
.stButton > button:hover { opacity: .85; }

.stSelectbox > div > div { background: #161616; border: 1px solid #2a2a2a; border-radius: 8px; }
.stColorPicker > div { background: #161616; }

div[data-testid="stMetricValue"] { color: #f0e040; }

.info-box {
    background: #161616;
    border-left: 3px solid #f0e040;
    padding: 1rem 1.2rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    color: #999;
}
.section-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #555;
    margin: 1.8rem 0 0.6rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("# 🎬 Reels Subtitle Burner")
st.markdown("הלבשת כתוביות (Burn-in) על סרטוני ריילס — תמיכה מלאה בעברית ו-UTF-8")

st.markdown('<div class="info-box">⚡ כל העיבוד מתבצע בשרת. הסרטון הסופי ישמר ב-MP4 ויהיה זמין להורדה ישירה.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SRT parser (pure Python, no extra deps)
# ─────────────────────────────────────────────
def parse_srt(content: str):
    """Parse SRT file content into list of (start_sec, end_sec, text) tuples."""
    pattern = re.compile(
        r'\d+\s*\n'
        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n'
        r'([\s\S]*?)(?=\n\d+\s*\n|\Z)',
        re.MULTILINE
    )

    def tc_to_sec(tc: str) -> float:
        tc = tc.replace(',', '.')
        h, m, rest = tc.split(':')
        s, ms = rest.split('.')
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    subtitles = []
    for m in pattern.finditer(content):
        start = tc_to_sec(m.group(1))
        end   = tc_to_sec(m.group(2))
        text  = m.group(3).strip()
        if text:
            subtitles.append((start, end, text))
    return subtitles


# ─────────────────────────────────────────────
# Upload section
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">📁 העלאת קבצים</p>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    video_file = st.file_uploader("קובץ וידאו (MP4)", type=["mp4", "mov", "avi"])
with col2:
    srt_file = st.file_uploader("קובץ כתוביות (SRT)", type=["srt"])

# ─────────────────────────────────────────────
# Design settings
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">🎨 הגדרות עיצוב</p>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)
with col_a:
    font_size = st.slider("גודל פונט", min_value=20, max_value=100, value=52, step=2)
with col_b:
    font_color = st.color_picker("צבע טקסט", value="#FFFFFF")

col_c, col_d = st.columns(2)
with col_c:
    position = st.selectbox(
        "מיקום כתוביות",
        options=["תחתית", "מרכז", "חלק עליון"],
        index=0
    )
with col_d:
    stroke_color = st.color_picker("צבע מסגרת (stroke)", value="#000000")

stroke_width = st.slider("עובי מסגרת", min_value=0, max_value=6, value=2)

# Font path – user can point to any TTF on the server / uploaded font
st.markdown('<p class="section-title">🔤 פונט (TTF)</p>', unsafe_allow_html=True)
font_upload = st.file_uploader("העלה קובץ פונט TTF (אופציונלי)", type=["ttf", "otf"])
custom_font_path_input = st.text_input(
    "או הכנס נתיב מקומי לקובץ פונט TTF",
    placeholder="/path/to/your/font.ttf"
)

# ─────────────────────────────────────────────
# Process button
# ─────────────────────────────────────────────
st.markdown('<p class="section-title">⚙️ עיבוד</p>', unsafe_allow_html=True)
process_btn = st.button("🚀 צור סרטון עם כתוביות")

if process_btn:
    if not video_file:
        st.error("❌ נא להעלות קובץ וידאו.")
    elif not srt_file:
        st.error("❌ נא להעלות קובץ SRT.")
    else:
        with st.spinner("⏳ מעבד את הסרטון... (עשוי לקחת מספר דקות)"):
            try:
                # Lazy import to avoid crash if moviepy not installed yet
                from moviepy.editor import VideoFileClip, CompositeVideoClip
                from moviepy.video.tools.subtitles import SubtitlesClip
                from PIL import Image, ImageDraw, ImageFont
                import numpy as np

                # ── Save uploaded files to temp dir ──────────────────
                tmp_dir = tempfile.mkdtemp()
                video_path = os.path.join(tmp_dir, "input.mp4")
                output_path = os.path.join(tmp_dir, "output.mp4")

                with open(video_path, "wb") as f:
                    f.write(video_file.read())

                srt_content = srt_file.read().decode("utf-8-sig")  # handle BOM
                subtitles_data = parse_srt(srt_content)

                if not subtitles_data:
                    st.error("❌ לא נמצאו כתוביות בקובץ SRT. בדוק את הפורמט.")
                    st.stop()

                # ── Resolve font path ────────────────────────────────
                font_path = None

                if font_upload is not None:
                    font_path = os.path.join(tmp_dir, font_upload.name)
                    with open(font_path, "wb") as f:
                        f.write(font_upload.read())
                elif custom_font_path_input.strip():
                    fp = custom_font_path_input.strip()
                    if os.path.isfile(fp):
                        font_path = fp
                    else:
                        st.warning(f"⚠️ נתיב הפונט '{fp}' לא נמצא. נשתמש בפונט ברירת מחדל.")

                # ── Load video ───────────────────────────────────────
                clip = VideoFileClip(video_path)
                W, H = clip.size

                # ── Helper: hex → RGB tuple ──────────────────────────
                def hex_to_rgb(hex_str: str):
                    hex_str = hex_str.lstrip('#')
                    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

                txt_rgb    = hex_to_rgb(font_color)
                stroke_rgb = hex_to_rgb(stroke_color)

                # ── Position mapping ─────────────────────────────────
                position_map = {
                    "תחתית":      ("center", H * 0.88),
                    "מרכז":       ("center", H * 0.50),
                    "חלק עליון":  ("center", H * 0.10),
                }
                sub_x, sub_y = position_map[position]

                # ── Frame maker using Pillow ─────────────────────────
                def make_frame(text: str):
                    """Return RGBA numpy array for a single subtitle frame."""
                    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)

                    try:
                        if font_path:
                            font = ImageFont.truetype(font_path, font_size)
                        else:
                            font = ImageFont.load_default()
                    except Exception:
                        font = ImageFont.load_default()

                    # Measure text
                    bbox = draw.textbbox((0, 0), text, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]

                    # Center X
                    x = (W - tw) // 2

                    # Y depends on position
                    if position == "תחתית":
                        y = int(H * 0.88) - th
                    elif position == "מרכז":
                        y = int(H * 0.50) - th // 2
                    else:  # עליון
                        y = int(H * 0.10)

                    # Draw stroke
                    if stroke_width > 0:
                        sw = stroke_width
                        for dx in range(-sw, sw + 1):
                            for dy in range(-sw, sw + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((x + dx, y + dy), text, font=font,
                                              fill=(*stroke_rgb, 255))

                    # Draw text
                    draw.text((x, y), text, font=font, fill=(*txt_rgb, 255))

                    return np.array(img)

                # ── Build subtitle clips ─────────────────────────────
                from moviepy.editor import ImageClip

                sub_clips = []
                for (start, end, text) in subtitles_data:
                    duration = end - start
                    if duration <= 0:
                        continue
                    frame = make_frame(text)
                    ic = (ImageClip(frame, ismask=False)
                          .set_start(start)
                          .set_duration(duration))
                    sub_clips.append(ic)

                # ── Composite & export ───────────────────────────────
                final = CompositeVideoClip([clip] + sub_clips)

                final.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=clip.fps,
                    preset="fast",
                    logger=None,
                )

                clip.close()
                final.close()

                # ── Serve download ───────────────────────────────────
                with open(output_path, "rb") as f:
                    video_bytes = f.read()

                st.success("✅ הסרטון מוכן להורדה!")
                st.download_button(
                    label="⬇️ הורד סרטון עם כתוביות",
                    data=video_bytes,
                    file_name="reels_with_subtitles.mp4",
                    mime="video/mp4",
                )

            except ImportError as e:
                st.error(f"❌ ספרייה חסרה: {e}\nהרץ: pip install -r requirements.txt")
            except Exception as e:
                st.error(f"❌ שגיאה בעיבוד: {e}")
                st.exception(e)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="color:#444;font-size:0.75rem;font-family:\'Space Mono\',monospace;text-align:center;">'
    'Reels Subtitle Burner · Powered by MoviePy + Pillow · UTF-8 / Hebrew ready'
    '</p>',
    unsafe_allow_html=True
)
