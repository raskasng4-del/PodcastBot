# ============================================================
# 🚀 PODCAST ABDO BOT V2 - النسخة المحلية (بدون كولاب)
# ============================================================

import os
import sys
import time
import json
import subprocess
import logging
import re
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum

import requests
import yt_dlp
from PIL import Image as PILImage
PILImage.ANTIALIAS = PILImage.LANCZOS
from moviepy.editor import *
from moviepy.config import change_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger("PodcastBot")


class URLType(Enum):
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    UNKNOWN = "unknown"


@dataclass
class Config:
    story_title: str = "قصة حمزة"
    description: str = "💔 حبيتها وبغيت نتزوج بيها… ولكن الحقيقة صدمتني 😱 | قصة حمزة"
    page_id: str = ""
    access_token: str = ""
    bg_image_path: str = ""  # مسار صورة الخلفية المحلية
    output_dir: str = "output"
    font_path: str = ""  # سيتم تعيينه تلقائياً
    
    intro_audio: str = ""
    outro_audio: str = ""
    watermark_image: str = ""
    publish_now: bool = True
    publish_time: Optional[str] = None
    parallel: bool = True
    max_workers: int = 3
    retry_count: int = 3
    skip_existing: bool = True
    audio_volume: float = 1.5
    audio_speed: float = 1.07
    pitch_shift: float = 0.96
    eq_highpass: int = 80
    eq_lowpass: int = 7500
    text_size: int = 45
    fps: int = 24
    fade_duration: float = 1.0


@dataclass
class EpisodeResult:
    index: int
    url: str
    success: bool
    facebook_id: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0
    output_path: Optional[str] = None


# ============================================================
# 🔧 تجهيز البيئة المحلية
# ============================================================

def setup_environment():
    """تثبيت المتطلبات محلياً"""
    
    # إيجاد خط عربي - نبحث في مسارات معروفة
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoKufiArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf",
        "/usr/share/fonts/google-noto-vf/NotoNaskhArabic[wght].ttf",
        "/usr/share/fonts/truetype/cairo/Cairo-Bold.ttf",
        "/usr/share/fonts/opentype/cairo/Cairo-Bold.otf",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "Cairo-Bold.ttf"),
        "Cairo-Bold.ttf",
        os.path.expanduser("~/.fonts/Cairo-Bold.ttf"),
        "/usr/share/fonts/truetype/hosny-amiri/Amiri-Bold.ttf",
        "/usr/share/fonts/truetype/hosny-amiri/Amiri-Regular.ttf",
    ]
    
    font_found = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_found = fp
            log.info(f"✅ تم العثور على الخط: {font_found}")
            break
    
    if not font_found:
        try:
            result = subprocess.run(
                ['fc-match', '-v', 'sans:lang=ar'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                if 'file:' in line:
                    path = line.split('"')[1] if '"' in line else ''
                    if path and os.path.exists(path):
                        font_found = path
                        log.info(f"✅ تم العثور على خط عربي: {font_found}")
                        break
        except Exception:
            pass
    
    if not font_found:
        log.warning("⚠️ لم نجد خط عربي. راح نستخدم Arial (قد لا يعمل)")
        font_found = None
    
    return font_found


def detect_url_type(url: str) -> URLType:
    if not url: return URLType.UNKNOWN
    if re.search(r'facebook\.com/(reel|watch|share|video)|fb\.watch', url):
        return URLType.FACEBOOK
    if 'youtu.be' in url or 'youtube.com' in url:
        return URLType.YOUTUBE
    if 'tiktok.com' in url:
        return URLType.TIKTOK
    if 'instagram.com' in url:
        return URLType.INSTAGRAM
    return URLType.UNKNOWN


def validate_token(page_id: str, token: str) -> Tuple[bool, str]:
    try:
        r = requests.get(
            f"https://graph.facebook.com/v18.0/{page_id}",
            params={"access_token": token, "fields": "name"},
            timeout=15
        )
        if r.status_code == 200:
            return True, f"✅ التوكن صالح - الصفحة: {r.json().get('name', 'غير معروفة')}"
        else:
            return False, f"❌ التوكن غير صالح: {r.json().get('error', {}).get('message', '')}"
    except Exception as e:
        return False, f"❌ فشل الاتصال: {e}"


def download_audio(url: str, index: int) -> Optional[str]:
    tmp_dir = "temp"
    os.makedirs(tmp_dir, exist_ok=True)
    output = f'{tmp_dir}/raw_{index}.%(ext)s'
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    for attempt in range(3):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            
            mp3 = f'{tmp_dir}/raw_{index}.mp3'
            if os.path.exists(mp3) and os.path.getsize(mp3) > 1000:
                return mp3
            
            time.sleep(2)
        except Exception as e:
            log.warning(f"⚠️ فشل التحميل (محاولة {attempt + 1}): {e}")
            time.sleep(3)
    
    return None


def process_audio(input_path: str, index: int, config: Config) -> Optional[str]:
    tmp_dir = "temp"
    os.makedirs(tmp_dir, exist_ok=True)
    output = f'{tmp_dir}/enhanced_{index}.mp3'
    
    filters = []
    if config.audio_volume != 1.0:
        filters.append(f"volume={config.audio_volume}")
    if config.audio_speed != 1.0:
        filters.append(f"atempo={config.audio_speed}")
    # تغيير البيتش لتفادي الكوبريت
    if config.pitch_shift != 1.0:
        filters.append(f"asetrate=48000*{config.pitch_shift},aresample=48000")
    # فلترة الترددات للكوبريت
    filters.append(f"highpass=f={config.eq_highpass},lowpass=f={config.eq_lowpass}")
    
    filter_str = ','.join(filters) if filters else None
    
    try:
        if filter_str:
            subprocess.run(
                ['ffmpeg', '-i', input_path, '-af', filter_str, '-y', output],
                capture_output=True, timeout=300
            )
        else:
            shutil.copy(input_path, output)
        
        if os.path.exists(output) and os.path.getsize(output) > 1000:
            return output
    except subprocess.TimeoutExpired:
        log.error(f"❌ Timeout في معالجة الصوت {index}")
    except Exception as e:
        log.error(f"❌ خطأ في معالجة الصوت {index}: {e}")
    
    return None


def create_video(audio_path: str, index: int, config: Config) -> Optional[str]:
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        if duration < 1:
            audio.close()
            return None

        bg = ImageClip(config.bg_image_path).set_duration(duration)
        # زووم متطور: يبدا مقرب شويا ويفتح مع الوقت
        bg = bg.resize(lambda t: 0.97 + 0.06 * t / duration)
        
        clips = [bg]
        
        if config.watermark_image and os.path.exists(config.watermark_image):
            try:
                wm = (ImageClip(config.watermark_image)
                      .resize(height=60)
                      .set_duration(duration)
                      .set_position(('right', 'bottom'))
                      .set_opacity(0.7))
                clips.append(wm)
            except Exception:
                pass

        video_text = f"{config.story_title} | الحلقة ({index})"
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            video_text = get_display(arabic_reshaper.reshape(video_text))
        except Exception:
            pass

        # ظل النص
        txt_shadow = TextClip(
            video_text,
            fontsize=config.text_size,
            color='black',
            font=config.font_path or 'Arial',
            method='caption',
            size=(bg.w * 0.8, None)
        ).set_duration(duration).set_position(lambda t: ('center', 'center'))

        # النص الرئيسي
        txt = TextClip(
            video_text,
            fontsize=config.text_size,
            color='white',
            font=config.font_path or 'Arial',
            bg_color='rgba(0,0,0,0.6)',
            method='caption',
            size=(bg.w * 0.8, None)
        ).set_duration(duration).set_position(('center', 'center'))

        clips.extend([txt_shadow, txt])

        if config.intro_audio and os.path.exists(config.intro_audio):
            try:
                intro = AudioFileClip(config.intro_audio)
                if intro.duration > 0:
                    audio = CompositeAudioClip([intro, audio.set_start(0)])
                    audio = audio.set_duration(max(intro.duration, duration))
            except Exception as e:
                log.warning(f"⚠️ فشل إضافة المقدمة: {e}")

        video = CompositeVideoClip(clips).set_audio(audio)
        video = video.fadein(config.fade_duration).fadeout(config.fade_duration)
        
        os.makedirs(config.output_dir, exist_ok=True)
        output_path = os.path.join(config.output_dir, f"Abdo_Samir_Pro_{index}.mp4")
        
        video.write_videofile(
            output_path, fps=config.fps,
            codec="libx264", audio_codec="aac",
            preset="medium", bitrate="3000k",
            threads=2, verbose=False, logger=None
        )
        
        audio.close()
        video.close()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
            return output_path
        
    except Exception as e:
        log.error(f"❌ خطأ في إنشاء الفيديو {index}: {e}")
    
    return None


def upload_to_facebook(video_path: str, index: int, config: Config) -> Optional[str]:
    description = f"{config.description}\n\nالحلقة ({index})"
    
    for attempt in range(1, config.retry_count + 1):
        try:
            size_mb = os.path.getsize(video_path) / 1024 / 1024
            log.info(f"📤 رفع الحلقة {index} ({size_mb:.1f} MB) - محاولة {attempt}")
            
            with open(video_path, 'rb') as f:
                data = {
                    'description': description,
                    'access_token': config.access_token,
                    'published': 'true' if config.publish_now else 'false',
                }
                if config.publish_time and not config.publish_now:
                    data['scheduled_publish_time'] = str(int(
                        datetime.fromisoformat(config.publish_time).timestamp()
                    ))
                
                files = {'source': (f'video_{index}.mp4', f, 'video/mp4')}
                r = requests.post(
                    f"https://graph-video.facebook.com/v18.0/{config.page_id}/videos",
                    data=data, files=files, timeout=600
                )
                result = r.json()
                
                if "id" in result:
                    log.info(f"✅ الحلقة {index} منشورة! ID: {result['id']}")
                    return result['id']
                else:
                    err = result.get('error', {}).get('message', str(result))
                    if 'token' in err.lower():
                        break
                    log.warning(f"⚠️ فشل: {err}")
                    
        except Exception as e:
            log.warning(f"⚠️ خطأ (محاولة {attempt}): {e}")
        
        if attempt < config.retry_count:
            time.sleep(attempt * 10)
    
    return None


def process_episode(url: str, index: int, config: Config) -> EpisodeResult:
    start = time.time()
    result = EpisodeResult(index=index, url=url, success=False)
    
    output_path = os.path.join(config.output_dir, f"Abdo_Samir_Pro_{index}.mp4")
    if config.skip_existing and os.path.exists(output_path):
        log.info(f"⏭️ الحلقة {index} موجودة مسبقاً")
        result.success = True
        result.output_path = output_path
        return result
    
    log.info(f"\n{'='*40}\n🎬 الحلقة ({index})\n{'='*40}")
    
    audio_raw = download_audio(url, index)
    if not audio_raw:
        result.error = "فشل تحميل الصوت"
        return result
    
    audio_proc = process_audio(audio_raw, index, config)
    if not audio_proc:
        result.error = "فشل معالجة الصوت"
        try: os.remove(audio_raw)
        except: pass
        return result
    
    video_path = create_video(audio_proc, index, config)
    
    # تنظيف
    for f in [audio_raw, audio_proc]:
        try: os.remove(f)
        except: pass
    
    if not video_path:
        result.error = "فشل إنشاء الفيديو"
        return result
    
    result.output_path = video_path
    
    fb_id = upload_to_facebook(video_path, index, config)
    if fb_id:
        result.success = True
        result.facebook_id = fb_id
    else:
        result.error = "فشل الرفع"
    
    result.duration = time.time() - start
    status = '✅' if result.success else '❌'
    log.info(f"{status} الحلقة {index}: {result.duration:.1f} ثانية")
    
    return result


# ============================================================
# 🚀 التشغيل
# ============================================================

def run_bot(config: Config, urls: List[str]):
    log.info(f"\n{'='*50}")
    log.info(f"🚀 PODCAST ABDO BOT V2 (محلي)")
    log.info(f"📖 {config.story_title}")
    log.info(f"🔗 {len([u for u in urls if u.strip()])} حلقة")
    log.info(f"{'='*50}\n")
    
    if not os.path.exists(config.bg_image_path):
        log.error(f"❌ صورة الخلفية غير موجودة: {config.bg_image_path}")
        return
    
    if not config.page_id or not config.access_token:
        log.error("❌ يجب تعيين Page ID و Access Token في config")
        return
    
    valid, msg = validate_token(config.page_id, config.access_token)
    log.info(msg)
    if not valid:
        return
    
    valid_urls = [u.strip() for u in urls if u.strip()]
    if not valid_urls:
        log.warning("⚠️ لا توجد روابط")
        return
    
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    
    results = []
    total_start = time.time()
    
    if config.parallel and len(valid_urls) > 1:
        log.info(f"⚡ معالجة متوازية ({config.max_workers})")
        with ThreadPoolExecutor(max_workers=config.max_workers) as ex:
            futures = {ex.submit(process_episode, u, i+1, config): (u, i+1) for i, u in enumerate(valid_urls)}
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    _, idx = futures[f]
                    log.error(f"❌ خطأ في الحلقة {idx}: {e}")
                    results.append(EpisodeResult(index=idx, url=_, success=False, error=str(e)))
    else:
        for i, u in enumerate(valid_urls):
            results.append(process_episode(u, i+1, config))
    
    # تقرير
    ok = sum(1 for r in results if r.success)
    ko = sum(1 for r in results if not r.success)
    log.info(f"\n{'='*50}")
    log.info(f"📊 التقرير النهائي")
    log.info(f"✅ {ok}/{len(results)} | ❌ {ko}")
    log.info(f"⏱️ {time.time() - total_start:.1f} ثانية")
    log.info(f"📁 {config.output_dir}")
    
    if ko:
        log.info("\n❌ الفاشلة:")
        for r in results:
            if not r.success:
                log.info(f"  - حلقة {r.index}: {r.error}")
    
    if ok:
        log.info("\n✅ المنشورة:")
        for r in results:
            if r.success and r.facebook_id:
                log.info(f"  - حلقة {r.index}: https://web.facebook.com/{config.page_id}/videos/{r.facebook_id}")
    
    log.info("\n✨ انتهى!")


# ============================================================
# ⚙️ الإعدادات
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Podcast Abdo Bot")
    parser.add_argument("--url", help="رابط واحد للمعالجة")
    parser.add_argument("--urls", nargs="+", help="قائمة روابط")
    parser.add_argument("--index", type=int, default=1, help="رقم الحلقة")
    parser.add_argument("--story", help="عنوان القصة")
    parser.add_argument("--desc", help="وصف القصة")
    parser.add_argument("--bg", help="مسار صورة الخلفية")
    parser.add_argument("--output", help="مجلد الإخراج")
    parser.add_argument("--page-id", help="Facebook Page ID")
    parser.add_argument("--token", help="Facebook Access Token")
    args = parser.parse_args()
    
    font = setup_environment()
    
    page_id = args.page_id or os.environ.get("FB_PAGE_ID") or "1179824185206026"
    token = args.token or os.environ.get("FB_ACCESS_TOKEN") or ""
    
    if not token:
        log.error("❌ يجب تعيين Access Token via --token أو متغير FB_ACCESS_TOKEN")
        sys.exit(1)
    
    config = Config(
        story_title=args.story or "قصة حمزة",
        description=args.desc or "💔 حبيتها وبغيت نتزوج بيها… ولكن الحقيقة صدمتني 😱 | قصة حمزة",
        page_id=page_id,
        access_token=token,
        bg_image_path=args.bg or "background.png",
        output_dir=args.output or "output",
        font_path=font,
        parallel=False,
        max_workers=1,
    )
    
    if args.url:
        run_bot(config, [args.url])
    elif args.urls:
        run_bot(config, args.urls)
    else:
        raw_urls = [
            "", "", "", "", "", "", "",
            "https://web.facebook.com/share/v/1Gp4Ub4XKd/",
            "https://web.facebook.com/share/v/1GCXYziuYc/",
            "https://web.facebook.com/share/v/1GdxZ8eCh4/",
            "", "", "", "", "",
        ]
        run_bot(config, raw_urls)
