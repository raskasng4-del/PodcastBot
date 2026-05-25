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

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
change_settings({"IMAGEMAGICK_BINARY": r"/usr/bin/convert"})

GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
PAGE_ID         = os.environ.get("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")
PO_TOKEN        = os.environ.get("PO_TOKEN", "")

image_path = "abdo.png"
save_path  = "output"
os.makedirs(save_path, exist_ok=True)
groq_client = Groq(api_key=GROQ_API_KEY)


def download_audio(url, index):
    base = {
        'format': 'bestaudio/best',
        'outtmpl': f'raw_{index}.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': False,
    }

    # بناء إعدادات PO Token لو كاين
    po_opts = {}
    if PO_TOKEN:
        logging.info("🔑 غنستعملو PO Token")
        po_opts = {
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'po_token': [f'web+{PO_TOKEN}'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
            },
        }

    attempts = [
        # 1: PO Token لو كاين — الأقوى
        {**base, **po_opts} if PO_TOKEN else None,

        # 2: iOS بدون كوكيز — كيخدم أحياناً
        {
            **base,
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

        # 3: mweb — mobile web
        {
            **base,
            'extractor_args': {'youtube': {'player_client': ['mweb']}},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1',
            },
        },

        # 4: android
        {
            **base,
            'extractor_args': {'youtube': {'player_client': ['android']}},
            'http_headers': {
                'User-Agent': 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
            },
        },
    ]

    # حذف None من اللائحة
    attempts = [a for a in attempts if a is not None]

    for i, opts in enumerate(attempts, 1):
        try:
            client = opts.get('extractor_args', {}).get('youtube', {}).get('player_client', ['unknown'])
            logging.info(f"🎯 محاولة {i}/{len(attempts)} — client: {client}")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)

            raw_file = f"raw_{index}.mp3"
            if not os.path.exists(raw_file):
                for ext in ['webm', 'opus', 'm4a', 'wav', 'ogg']:
                    alt = f"raw_{index}.{ext}"
                    if os.path.exists(alt):
                        os.rename(alt, raw_file)
                        break

            if os.path.exists(raw_file):
                logging.info(f"✅ تم تحميل الصوت: {raw_file}")
                return raw_file

        except Exception:
            logging.error(f"❌ المحاولة {i} فشلت:\n{traceback.format_exc()}")

    raise Exception("❌ فشل تحميل الصوت بجميع الطرق")


def generate_ai_description(title, index):
    try:
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "أنت صانع محتوى مغربي محترف لمقاطع البودكاست على فيسبوك."},
                {"role": "user", "content": f"اكتب وصف مشوق بالدارجة المغربية للحلقة ({index}) من '{title}'. أضف 4 هاشتاغات. بدون مقدمات."}
            ],
            model="llama3-70b-8192",
            temperature=0.7,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"❌ Groq: {e}")
        return f"الحلقة ({index}) من {title} 🎙️\n\n#بودكاست_مغربي #قصص_واقعية"


def process_episode(url, title, index):
    raw_file = enhanced_file = wave_file = None
    enhanced_file = f"enhanced_{index}.mp3"
    wave_file     = f"wave_{index}.mp4"

    try:
        raw_file = download_audio(url, index)

        os.system(f"ffmpeg -i {raw_file} -af 'volume=1.5,atempo=1.07,asetrate=48000*0.96,aresample=48000,highpass=f=80,lowpass=f=7500' -y {enhanced_file} 2>/dev/null")
        if not os.path.exists(enhanced_file):
            os.rename(raw_file, enhanced_file); raw_file = None

        audio = AudioFileClip(enhanced_file)
        bg    = ImageClip(image_path).set_duration(audio.duration)
        bg    = bg.resize(lambda t: 0.97 + 0.06 * t / audio.duration)

        bidi_text = get_display(arabic_reshaper.reshape(f"{title} | الحلقة ({index})"))
        font_path = '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf'

        txt_shadow = TextClip(bidi_text, fontsize=45, color='black', font=font_path, method='caption', size=(bg.w*0.8, None)).set_duration(audio.duration).set_position(('center','bottom'))
        txt        = TextClip(bidi_text, fontsize=45, color='white', font=font_path, bg_color='rgba(0,0,0,0.6)', method='caption', size=(bg.w*0.8, None)).set_duration(audio.duration).set_position(('center','bottom'))

        clips = [bg, txt_shadow, txt]
        try:
            subprocess.run(['ffmpeg','-i',enhanced_file,'-filter_complex',
                "color=c=black@0:s=1280x120:r=24,format=rgba[bg];[0:a]showwaves=s=1280x120:mode=cline:rate=24:colors=#e94560[waves];[bg][waves]overlay=format=auto,format=rgba",
                '-an','-c:v','png','-y',wave_file], capture_output=True, timeout=600)
            if os.path.exists(wave_file):
                clips.append(VideoFileClip(wave_file, has_mask=True).set_duration(audio.duration).set_position(('center','bottom')))
        except Exception as e:
            logging.warning(f"⚠️ موجات الصوت: {e}")

        video        = CompositeVideoClip(clips).set_audio(audio).fadein(1).fadeout(1)
        final_output = os.path.join(save_path, f"Abdo_Samir_Pro_{index}.mp4")
        video.write_videofile(final_output, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)

        desc   = generate_ai_description(title, index)
        fb_url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/videos"
        with open(final_output, 'rb') as f:
            res = requests.post(fb_url, data={'description': desc, 'access_token': FB_ACCESS_TOKEN, 'published': 'true'}, files={'source': f}).json()

        audio.close(); video.close()
        for tmp in [raw_file, enhanced_file, wave_file]:
            if tmp and os.path.exists(tmp): os.remove(tmp)

        if "id" in res:
            return True, f"✅ الحلقة {index} تنشرات! ID: {res['id']}"
        return False, f"❌ فيسبوك: {res}"

    except Exception as e:
        logging.error(f"❌ خطأ:\n{traceback.format_exc()}")
        for tmp in [raw_file, enhanced_file, wave_file]:
            if tmp and os.path.exists(tmp):
                try: os.remove(tmp)
                except: pass
        return False, f"❌ خطأ: {str(e)}"


def get_channel_videos(channel_url, max_videos=3):
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'playlistend': max_videos}) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            return [(str(i+1), f"https://www.youtube.com/watch?v={e['id']}", e.get('title', f'حلقة {i+1}'))
                    for i, e in enumerate(info.get('entries', []))]
    except Exception:
        logging.error(traceback.format_exc())
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url',   type=str, default=None)
    parser.add_argument('--title', type=str, default='بودكاست عبدو سمير')
    parser.add_argument('--index', type=str, default='1')
    args = parser.parse_args()

    if args.url:
        logging.info(f"🎯 غنخدمو على: {args.url}")
        ok, msg = process_episode(args.url, args.title, args.index)
        print(msg)
        sys.exit(0 if ok else 1)
    else:
        channel = os.environ.get("YOUTUBE_CHANNEL", "")
        if not channel:
            logging.error("❌ ما حطيتيش YOUTUBE_CHANNEL!")
            sys.exit(1)
        videos  = get_channel_videos(channel)
        success = 0
        for index, url, title in videos:
            ok, msg = process_episode(url, title, index)
            print(msg)
            if ok: success += 1
        sys.exit(0 if success > 0 else 1)


if __name__ == "__main__":
    main()
