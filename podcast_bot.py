import os
import sys
import argparse
import subprocess
import logging
import traceback
import yt_dlp
import requests
from PIL import Image as PILImage
PILImage.ANTIALIAS = PILImage.LANCZOS
from moviepy.editor import *
from moviepy.config import change_settings
import arabic_reshaper
from bidi.algorithm import get_display
from groq import Groq

# ⚙️ إعدادات اللوغ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

# ⚙️ إعدادات النظام
change_settings({"IMAGEMAGICK_BINARY": r"/usr/bin/convert"})

# 🔑 المفاتيح من متغيرات البيئة
GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
PAGE_ID         = os.environ.get("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")

image_path = "abdo.png"
save_path  = "output"
os.makedirs(save_path, exist_ok=True)

groq_client = Groq(api_key=GROQ_API_KEY)


# ─────────────────────────────────────────────
# تحميل الصوت — بدون كوكيز، بمحاولتين
# ─────────────────────────────────────────────
def download_audio(url, index, cookiefile=None):
    base_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'raw_{index}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'no_warnings': False,
    }

    if cookiefile and os.path.exists(cookiefile) and os.path.getsize(cookiefile) > 10:
        base_opts['cookiefile'] = cookiefile
        logging.info(f"🍪 غنستعملو الكوكيز: {cookiefile}")

    attempts = [
        {
            **base_opts,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios'],
                    'player_skip': ['webpage', 'configs'],
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
            },
        },
        {
            **base_opts,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web_creator'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
            },
        },
        {
            **base_opts,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
            },
        },
    ]

    for i, opts in enumerate(attempts, 1):
        try:
            logging.info(f"🎯 محاولة {i}/3 لتحميل: {url}")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)

            raw_file = f"raw_{index}.mp3"
            if not os.path.exists(raw_file):
                for ext in ['webm', 'opus', 'm4a', 'wav', 'ogg']:
                    alt = f"raw_{index}.{ext}"
                    if os.path.exists(alt):
                        logging.info(f"🔄 تحويل {alt} → {raw_file}")
                        os.rename(alt, raw_file)
                        break

            if os.path.exists(raw_file):
                logging.info(f"✅ تم تحميل الصوت بنجاح: {raw_file}")
                return raw_file
            else:
                logging.warning(f"⚠️ المحاولة {i} — الملف ما وجدش بعد التحميل")

        except Exception:
            logging.error(f"❌ المحاولة {i} فشلت:\n{traceback.format_exc()}")

    raise Exception("❌ فشل تحميل الصوت بجميع الطرق الثلاث")


# ─────────────────────────────────────────────
# توليد الوصف بـ AI
# ─────────────────────────────────────────────
def generate_ai_description(title, index):
    prompt = (
        f"اكتب وصف مشوق وجذاب جدا بالدارجة المغربية للحلقة رقم ({index}) من '{title}'. "
        f"الوصف يجب أن يثير الفضول ويجعل المتابع يرغب في مشاهدة الفيديو. "
        f"في النهاية، أضف 4 هاشتاغات مناسبة للفيسبوك. "
        f"لا تكتب أي مقدمات أو شروحات، أعطني الوصف والهاشتاغات مباشرة."
    )
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "أنت صانع محتوى مغربي محترف وكاتب نصوص إبداعي لمقاطع البودكاست على فيسبوك."
                },
                {"role": "user", "content": prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.7,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"❌ خطأ في Groq: {e}")
        return f"تتمة {title} - شنو وقع فهاد الحلقة؟ 🤔\n\nالحلقة ({index})\n\n#قصص_واقعية #بودكاست_مغربي"


# ─────────────────────────────────────────────
# معالجة حلقة واحدة
# ─────────────────────────────────────────────
def process_episode(url, title, index, cookiefile=None):
    raw_file      = None
    enhanced_file = f"enhanced_{index}.mp3"
    wave_file     = f"wave_{index}.mp4"

    try:
        # 1️⃣ تحميل الصوت
        raw_file = download_audio(url, index, cookiefile)

        # 2️⃣ تحسين الصوت
        logging.info(f"🎵 تحسين الصوت للحلقة {index}...")
        ret = os.system(
            f"ffmpeg -i {raw_file} "
            f"-af 'volume=1.5,atempo=1.07,asetrate=48000*0.96,aresample=48000,"
            f"highpass=f=80,lowpass=f=7500' "
            f"-y {enhanced_file} 2>/dev/null"
        )
        if ret != 0 or not os.path.exists(enhanced_file):
            logging.warning("⚠️ فشل تحسين الصوت، غنستعملو الأصلي")
            os.rename(raw_file, enhanced_file)
            raw_file = None

        audio = AudioFileClip(enhanced_file)

        # 3️⃣ الخلفية
        bg = ImageClip(image_path).set_duration(audio.duration)
        bg = bg.resize(lambda t: 0.97 + 0.06 * t / audio.duration)

        # 4️⃣ النص العربي
        video_text    = f"{title} | الحلقة ({index})"
        reshaped_text = arabic_reshaper.reshape(video_text)
        bidi_text     = get_display(reshaped_text)
        font_path     = '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf'

        txt_shadow = TextClip(
            bidi_text, fontsize=45, color='black', font=font_path,
            method='caption', size=(bg.w * 0.8, None)
        ).set_duration(audio.duration).set_position(('center', 'bottom'))

        txt = TextClip(
            bidi_text, fontsize=45, color='white', font=font_path,
            bg_color='rgba(0,0,0,0.6)', method='caption', size=(bg.w * 0.8, None)
        ).set_duration(audio.duration).set_position(('center', 'bottom'))

        # 5️⃣ موجات الصوت
        clips = [bg, txt_shadow, txt]
        try:
            subprocess.run([
                'ffmpeg', '-i', enhanced_file,
                '-filter_complex',
                "color=c=black@0:s=1280x120:r=24,format=rgba[bg];"
                "[0:a]showwaves=s=1280x120:mode=cline:rate=24:colors=#e94560[waves];"
                "[bg][waves]overlay=format=auto,format=rgba",
                '-an', '-c:v', 'png', '-y', wave_file
            ], capture_output=True, timeout=600)

            if os.path.exists(wave_file):
                wave_clip = VideoFileClip(wave_file, has_mask=True) \
                    .set_duration(audio.duration) \
                    .set_position(('center', 'bottom'))
                clips.append(wave_clip)
                logging.info("✅ موجات الصوت تضافت")
        except Exception as e:
            logging.warning(f"⚠️ موجات الصوت فشلات: {e}")

        # 6️⃣ تجميع الفيديو
        logging.info(f"🎬 كنجمع الفيديو للحلقة {index}...")
        video        = CompositeVideoClip(clips).set_audio(audio)
        video        = video.fadein(1).fadeout(1)
        final_output = os.path.join(save_path, f"Abdo_Samir_Pro_{index}.mp4")

        video.write_videofile(
            final_output, fps=24,
            codec="libx264", audio_codec="aac",
            verbose=False, logger=None
        )
        logging.info(f"✅ الفيديو تجمع: {final_output}")

        # 7️⃣ وصف AI
        ai_description = generate_ai_description(title, index)

        # 8️⃣ النشر على فيسبوك
        logging.info("📤 كننشر على فيسبوك...")
        fb_url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/videos"
        with open(final_output, 'rb') as f:
            payload = {
                'description': ai_description,
                'access_token': FB_ACCESS_TOKEN,
                'published': 'true'
            }
            res = requests.post(fb_url, data=payload, files={'source': f}).json()

        # 9️⃣ تنظيف
        audio.close()
        video.close()
        for tmp in [raw_file, enhanced_file, wave_file]:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)

        if "id" in res:
            logging.info(f"✅ الحلقة {index} تنشرات! ID: {res['id']}")
            return True, f"✅ الحلقة {index} تنشرات بنجاح! ID: {res['id']}"
        else:
            logging.error(f"❌ فيسبوك رجع: {res}")
            return False, f"❌ مشكل مع فيسبوك: {res}"

    except Exception as e:
        logging.error(f"❌ خطأ فالحلقة {index}:\n{traceback.format_exc()}")
        for tmp in [raw_file, enhanced_file, wave_file]:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        return False, f"❌ خطأ فالحلقة {index}: {str(e)}"


# ─────────────────────────────────────────────
# جلب آخر فيديوهات القناة
# ─────────────────────────────────────────────
def get_channel_videos(channel_url, max_videos=5):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': max_videos,
        'extractor_args': {'youtube': {'player_client': ['ios']}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get('entries', [])
            videos = []
            for i, entry in enumerate(entries, 1):
                vid_url = f"https://www.youtube.com/watch?v={entry['id']}"
                vid_title = entry.get('title', f'حلقة {i}')
                videos.append((str(i), vid_url, vid_title))
            return videos
    except Exception:
        logging.error(f"❌ فشل جلب قناة:\n{traceback.format_exc()}")
        return []


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Podcast Bot')
    parser.add_argument('--url',     type=str, default=None,
                        help='رابط فيديو يوتيوب للتجربة')
    parser.add_argument('--cookies', type=str, default=None,
                        help='مسار ملف الكوكيز')
    parser.add_argument('--title',   type=str, default='بودكاست عبدو سمير',
                        help='اسم البودكاست')
    parser.add_argument('--index',   type=str, default='1',
                        help='رقم الحلقة')
    args = parser.parse_args()

    if args.url:
        # ── وضع التجربة: رابط واحد مباشر
        logging.info(f"🎯 غنخدمو على هاد الرابط: {args.url}")
        logging.info("🎬 كنجبدو المعلومات ديال الفيديو...")
        ok, msg = process_episode(
            url=args.url,
            title=args.title,
            index=args.index,
            cookiefile=args.cookies
        )
        print(msg)
        sys.exit(0 if ok else 1)

    else:
        # ── وضع تلقائي: جلب القناة
        channel = os.environ.get("YOUTUBE_CHANNEL", "")
        if not channel:
            logging.error("❌ ما حطيتيش YOUTUBE_CHANNEL فالـ secrets!")
            sys.exit(1)

        logging.info(f"🔍 كنجبدو فيديوهات القناة: {channel}")
        videos = get_channel_videos(channel, max_videos=3)

        if not videos:
            logging.error("❌ ما لقيناش حتى فيديو فالقناة")
            sys.exit(1)

        success_count = 0
        for index, url, title in videos:
            logging.info(f"\n{'='*50}")
            logging.info(f"📹 الحلقة {index}: {title}")
            ok, msg = process_episode(
                url=url,
                title=title,
                index=index,
                cookiefile=args.cookies
            )
            print(msg)
            if ok:
                success_count += 1

        logging.info(f"\n✨ انتهت الخدمة: {success_count}/{len(videos)} تنشرات بنجاح")
        sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    main()
