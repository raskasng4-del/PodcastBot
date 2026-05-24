import os
import subprocess
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

# ⚙️ إعدادات النظام
change_settings({"IMAGEMAGICK_BINARY": r"/usr/bin/convert"})

# 🔑 المفاتيح (من متغيرات البيئة)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PAGE_ID = os.environ.get("FB_PAGE_ID", "")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "")

image_path = "abdo.png"
# 🛠️ تم التعديل هنا باش GitHub يلقى الفيديوهات
save_path = "output"
os.makedirs(save_path, exist_ok=True)

groq_client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def generate_ai_description(title, index):
    prompt = f"اكتب وصف مشوق وجذاب جدا بالدارجة المغربية للحلقة رقم ({index}) من '{title}'. الوصف يجب أن يثير الفضول ويجعل المتابع يرغب في مشاهدة الفيديو. في النهاية، أضف 4 هاشتاغات مناسبة للفيسبوك. لا تكتب أي مقدمات أو شروحات، أعطني الوصف والهاشتاغات مباشرة."
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "أنت صانع محتوى مغربي محترف وكاتب نصوص إبداعي لمقاطع البودكاست على فيسبوك."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-70b-8192",
            temperature=0.7,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"تتمة {title} - شنو وقع فهاد الحلقة؟ 🤔\n\nالحلقة ({index})\n\n#قصص_واقعية #بودكاست_مغربي"

def process_podcast_fast(url, title, index):
    try:
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': f'raw_{index}.%(ext)s', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}], 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        os.system(f"ffmpeg -i raw_{index}.mp3 -af 'volume=1.5, atempo=1.07, asetrate=48000*0.96,aresample=48000, highpass=f=80, lowpass=f=7500' -y enhanced_{index}.mp3 > /dev/null 2>&1")
        audio = AudioFileClip(f"enhanced_{index}.mp3")

        bg = ImageClip(image_path).set_duration(audio.duration)
        bg = bg.resize(lambda t: 0.97 + 0.06 * t / audio.duration)

        video_text = f"{title} | الحلقة ({index})"
        reshaped_text = arabic_reshaper.reshape(video_text)
        bidi_text = get_display(reshaped_text)

        font_path = '/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf'
        txt_shadow = TextClip(bidi_text, fontsize=45, color='black', font=font_path,
                              method='caption', size=(bg.w*0.8, None))
        txt_shadow = txt_shadow.set_duration(audio.duration).set_position(('center', 'bottom'))

        txt = TextClip(bidi_text, fontsize=45, color='white', font=font_path,
                       bg_color='rgba(0,0,0,0.6)', method='caption', size=(bg.w*0.8, None))
        txt = txt.set_duration(audio.duration).set_position(('center', 'bottom'))

        # موجات الصوت
        try:
            subprocess.run([
                'ffmpeg', '-i', f"enhanced_{index}.mp3",
                '-filter_complex',
                f"color=c=black@0:s=1280x120:r=24,format=rgba[bg];"
                f"[0:a]showwaves=s=1280x120:mode=cline:rate=24:colors=#e94560[waves];"
                f"[bg][waves]overlay=format=auto,format=rgba",
                '-an', '-c:v', 'png', '-y', f"wave_{index}.mp4"
            ], capture_output=True, timeout=600)
            if os.path.exists(f"wave_{index}.mp4"):
                wave_clip = VideoFileClip(f"wave_{index}.mp4", has_mask=True).set_duration(audio.duration).set_position(('center', 'bottom'))
                clips = [bg, txt_shadow, txt, wave_clip]
            else:
                clips = [bg, txt_shadow, txt]
        except Exception:
            clips = [bg, txt_shadow, txt]

        video = CompositeVideoClip(clips).set_audio(audio)
        video = video.fadein(1).fadeout(1)
        final_output = os.path.join(save_path, f"Abdo_Samir_Pro_{index}.mp4")

        video.write_videofile(final_output, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)

        ai_description = generate_ai_description(title, index)
        
        fb_url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/videos"
        with open(final_output, 'rb') as f:
            payload = {'description': ai_description, 'access_token': FB_ACCESS_TOKEN, 'published': 'true'}
            res = requests.post(fb_url, data=payload, files={'source': f}).json()
            
        audio.close()
        video.close()
        os.remove(f"raw_{index}.mp3")
        os.remove(f"enhanced_{index}.mp3")

        if "id" in res:
            return f"✅ الحلقة {index} تنشرات بنجاح! ID: {res['id']}"
        else:
            return f"❌ الحلقة {index} فيها مشكل مع فيسبوك: {res}"

    except Exception as e:
        return f"❌ خطأ فالحلقة {index}: {str(e)}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "مرحبا بيك أ المعلم! 🎬\nصيفط ليا القصة كاملة بحال هكا:\n\nاسم القصة\n1 | رابط\n2 | رابط")

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
                links.append((parts[0].strip(), parts[1].strip()))
        
        if not links:
            bot.reply_to(message, "⚠️ مالقيت حتى رابط مقاد.")
            return

        bot.reply_to(message, f"🎬 توصلت بالقصة: '{title}'. غنبدا الخدمة دابا! ☕")

        for index, url in links:
            bot.send_message(message.chat.id, f"⏳ كنبدا دابا فالحلقة ({index})...")
            result_msg = process_podcast_fast(url, title, index)
            bot.send_message(message.chat.id, result_msg)
            
        bot.send_message(message.chat.id, f"✨ ساليت القصة ديال '{title}' كاملة!")

    except Exception as e:
        bot.reply_to(message, f"❌ كاين شي مشكل: {e}")

if __name__ == "__main__":
    bot.polling(non_stop=True)
