import os
import subprocess
import logging
import traceback
import yt_dlp
import requests
import telebot
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

# 🔑 المفاتيح (من متغيرات البيئة)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PAGE_ID = os.environ.get("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")

image_path = "abdo.png"
save_path = "output"
os.makedirs(save_path, exist_ok=True)

groq_client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def download_audio(url, index):
    """تحميل الصوت من YouTube بدون كوكيز"""

    # الطريقة 1: iOS client
    ydl_opts_ios = {
        'format': 'bestaudio/best',
        'outtmpl': f'raw_{index}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'no_warnings': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
        },
    }

    # الطريقة 2: web_creator client كـ fallback
    ydl_opts_web = {
        'format': 'bestaudio/best',
        'outtmpl': f'raw_{index}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['web_creator'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        },
    }

    for attempt, opts in enumerate([ydl_opts_ios, ydl_opts_web], start=1):
        try:
            logging.info(f"🎯 محاولة {attempt} لتحميل: {url}")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)

            # البحث على الملف المحمل
            raw_file = f"raw_{index}.mp3"
            if not os.path.exists(raw_file):
                for ext in ['webm', 'opus', 'm4a', 'wav', 'ogg']:
                    alt = f"raw_{index}.{ext}"
                    if os.path.exists(alt):
                        logging.info(f"🔄 تحويل {alt} إلى {raw_file}")
                        os.rename(alt, raw_file)
                        break

            if os.path.exists(raw_file):
                logging.info(f"✅ تم تحميل الصوت: {raw_file}")
                return raw_file
            else:
                logging.warning(f"⚠️ المحاولة {attempt} فشلت - الملف ما وجدش")

        except Exception as e:
            logging.error(f"❌ المحاولة {attempt} فشلت: {traceback.format_exc()}")

    raise Exception("❌ فشل تحميل الصوت بجميع الطرق")


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


def process_podcast_fast(url, title, index):
    raw_file = None
    enhanced_file = f"enhanced_{index}.mp3"
    wave_file = f"wave_{index}.mp4"

    try:
        # 1️⃣ تحميل الصوت
        raw_file = download_audio(url, index)

        # 2️⃣ تحسين الصوت
        logging.info(f"🎵 تحسين الصوت للحلقة {index}...")
        os.system(
            f"ffmpeg -i {raw_file} "
            f"-af 'volume=1.5,atempo=1.07,asetrate=48000*0.96,aresample=48000,"
            f"highpass=f=80,lowpass=f=7500' "
            f"-y {enhanced_file} > /dev/null 2>&1"
        )

        if not os.path.exists(enhanced_file):
            logging.warning("⚠️ فشل تحسين الصوت، غنستعمل الأصلي")
            os.rename(raw_file, enhanced_file)
            raw_file = None

        audio = AudioFileClip(enhanced_file)

        # 3️⃣ الخلفية مع تكبير تدريجي
        bg = ImageClip(image_path).set_duration(audio.duration)
        bg = bg.resize(lambda t: 0.97 + 0.06 * t / audio.duration)

        # 4️⃣ النص العربي
        video_text = f"{title} | الحلقة ({index})"
        reshaped_text = arabic_reshaper.reshape(video_text)
        bidi_text = get_display(reshaped_text)

        font_path = '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf'

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
                f"color=c=black@0:s=1280x120:r=24,format=rgba[bg];"
                f"[0:a]showwaves=s=1280x120:mode=cline:rate=24:colors=#e94560[waves];"
                f"[bg][waves]overlay=format=auto,format=rgba",
                '-an', '-c:v', 'png', '-y', wave_file
            ], capture_output=True, timeout=600)

            if os.path.exists(wave_file):
                wave_clip = VideoFileClip(wave_file, has_mask=True)\
                    .set_duration(audio.duration)\
                    .set_position(('center', 'bottom'))
                clips.append(wave_clip)
                logging.info("✅ موجات الصوت تضافت")
        except Exception as e:
            logging.warning(f"⚠️ موجات الصوت فشلات: {e}")

        # 6️⃣ تجميع الفيديو
        logging.info(f"🎬 كنجمع الفيديو للحلقة {index}...")
        video = CompositeVideoClip(clips).set_audio(audio)
        video = video.fadein(1).fadeout(1)
        final_output = os.path.join(save_path, f"Abdo_Samir_Pro_{index}.mp4")

        video.write_videofile(
            final_output, fps=24,
            codec="libx264", audio_codec="aac",
            verbose=False, logger=None
        )
        logging.info(f"✅ الفيديو تجمع: {final_output}")

        # 7️⃣ توليد الوصف بالـ AI
        ai_description = generate_ai_description(title, index)

        # 8️⃣ النشر على فيسبوك
        logging.info(f"📤 كننشر على فيسبوك...")
        fb_url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/videos"
        with open(final_output, 'rb') as f:
            payload = {
                'description': ai_description,
                'access_token': FB_ACCESS_TOKEN,
                'published': 'true'
            }
            res = requests.post(fb_url, data=payload, files={'source': f}).json()

        # 9️⃣ تنظيف الملفات المؤقتة
        audio.close()
        video.close()
        for tmp in [raw_file, enhanced_file, wave_file]:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
                logging.info(f"🗑️ حذفنا: {tmp}")

        if "id" in res:
            return f"✅ الحلقة {index} تنشرات بنجاح! ID: {res['id']}"
        else:
            return f"❌ الحلقة {index} فيها مشكل مع فيسبوك: {res}"

    except Exception as e:
        logging.error(f"❌ خطأ فالحلقة {index}:\n{traceback.format_exc()}")
        # تنظيف في حالة الخطأ
        for tmp in [raw_file, enhanced_file, wave_file]:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except:
                    pass
        return f"❌ خطأ فالحلقة {index}: {str(e)}"


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "مرحبا بيك أ المعلم! 🎬\n"
        "صيفط ليا القصة كاملة بحال هكا:\n\n"
        "اسم القصة\n"
        "1 | رابط\n"
        "2 | رابط"
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        lines = message.text.strip().split('\n')
        if len(lines) < 2:
            bot.reply_to(message, "⚠️ الشكل ديال الرسالة غالط.")
            return

        title = lines[0].strip()
        links = []
        for line in lines[1:]:
            if '|' in line:
                parts = line.split('|', 1)
                idx = parts[0].strip()
                url = parts[1].strip()
                links.append((idx, url))

        if not links:
            bot.reply_to(message, "⚠️ مالقيت حتى رابط مقاد.")
            return

        bot.reply_to(message, f"🎬 توصلت بالقصة: '{title}'. غنبدا الخدمة دابا! ☕")

        for index, url in links:
            logging.info(f"🎯 غنخدمو على هاد الرابط: {url}")
            bot.send_message(message.chat.id, f"⏳ كنبدا دابا فالحلقة ({index})...")
            result_msg = process_podcast_fast(url, title, index)
            bot.send_message(message.chat.id, result_msg)

        bot.send_message(message.chat.id, f"✨ ساليت القصة ديال '{title}' كاملة!")

    except Exception as e:
        logging.error(f"❌ خطأ في handle_message: {traceback.format_exc()}")
        bot.reply_to(message, f"❌ كاين شي مشكل: {e}")


if __name__ == "__main__":
    logging.info("🤖 البوت بدا...")
    bot.polling(non_stop=True)
