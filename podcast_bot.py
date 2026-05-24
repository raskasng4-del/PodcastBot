import os
import sys
import time
import json
import subprocess
import logging
from typing import Optional
from dataclasses import dataclass
import requests
import yt_dlp
from PIL import Image as PILImage
PILImage.ANTIALIAS = PILImage.LANCZOS
from moviepy.editor import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
log = logging.getLogger("PodcastBot")

@dataclass
class Config:
    page_id: str = ""
    access_token: str = ""
    bg_image_path: str = "abdo.png"
    output_dir: str = "output"
    retry_count: int = 3
    audio_volume: float = 1.5
    audio_speed: float = 1.07
    pitch_shift: float = 0.96
    eq_highpass: int = 80
    eq_lowpass: int = 7500
    fps: int = 24
    video_bitrate: str = "500k"
    audio_bitrate: str = "96k"
    state_file: str = "processed.txt"
    max_part_duration: int = 1800 
    show_waveform: bool = True
    waveform_color: str = "#e94560"
    waveform_height: int = 120
    cookies_file: str = ""

def make_waveform(audio_path: str, index: int, config: Config) -> Optional[str]:
    tmp_dir = "temp"
    os.makedirs(tmp_dir, exist_ok=True)
    out = f'{tmp_dir}/wave_{index}.mp4'
    try:
        subprocess.run([
            'ffmpeg', '-i', audio_path,
            '-filter_complex',
            f"color=c=black@0:s=1280x{config.waveform_height}:r=25,format=rgba[bg];"
            f"[0:a]showwaves=s=1280x{config.waveform_height}:mode=cline:rate=25:colors={config.waveform_color}[waves];"
            f"[bg][waves]overlay=format=auto,format=rgba",
            '-an', '-c:v', 'png', '-y', out
        ], capture_output=True, timeout=600)
        if os.path.exists(out): return out
    except: pass
    return None

def create_video(audio_path: str, index: int, config: Config) -> Optional[str]:
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        if duration < 1: return None

        bg = ImageClip(config.bg_image_path).set_duration(duration)
        bg = bg.resize(lambda t: 0.97 + 0.06 * t / duration)
        clips = [bg]

        if config.show_waveform:
            wave_path = make_waveform(audio_path, index, config)
            if wave_path:
                wave_clip = (VideoFileClip(wave_path, has_mask=True)
                             .set_duration(duration)
                             .set_position(('center', 'bottom')))
                clips.append(wave_clip)

        video = CompositeVideoClip(clips).set_audio(audio)
        os.makedirs(config.output_dir, exist_ok=True)
        output_path = os.path.join(config.output_dir, f"Abdo_Samir_Pro_{index}.mp4")
        
        video.write_videofile(
            output_path, fps=config.fps,
            codec="libx264", audio_codec="aac",
            preset="medium", bitrate=config.video_bitrate,
            audio_bitrate=config.audio_bitrate,
            threads=2, verbose=False, logger=None
        )
        audio.close()
        video.close()
        if os.path.exists(output_path): return output_path
    except Exception as e:
        log.error(f"❌ خطأ فيديو {index}: {e}")
    return None

def upload_to_facebook(video_path: str, index: int, config: Config, custom_desc: str = None) -> Optional[str]:
    final_desc = custom_desc if custom_desc else "قصص واقعية وحصرية 🔥\n\n#قصص_واقعية #بودكاست_مغربي"
    description = f"{final_desc}\n\nالحلقة ({index})"
    
    for attempt in range(1, config.retry_count + 1):
        try:
            with open(video_path, 'rb') as f:
                data = {'description': description, 'access_token': config.access_token, 'published': 'true'}
                files = {'source': (f'video_{index}.mp4', f, 'video/mp4')}
                r = requests.post(f"https://graph.facebook.com/v22.0/{config.page_id}/videos", data=data, files=files)
                result = r.json()
                if "id" in result:
                    log.info(f"✅ الحلقة {index} منشورة! ID: {result['id']}")
                    return result['id']
                else:
                    log.warning(f"⚠️ مشكل مع فيسبوك: {result}")
        except Exception as e:
            log.warning(f"⚠️ خطأ رفع: {e}")
        time.sleep(10)
    return None

def load_processed_ids(state_file: str) -> set:
    if not os.path.exists(state_file): return set()
    with open(state_file) as f:
        return {line.strip() for line in f if line.strip()}

def save_processed_id(state_file: str, video_id: str):
    with open(state_file, 'a') as f: f.write(f"{video_id}\n")

def fetch_youtube_videos(channel_url: str, max_results: int = 5) -> list:
    try:
        cmd = ['yt-dlp', '--flat-playlist', '--dump-json', '--playlist-end', str(max_results), channel_url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        videos = []
        for line in result.stdout.strip().split('\n'):
            if line:
                d = json.loads(line)
                videos.append({'id': d['id'], 'title': d.get('title', ''), 'duration': d.get('duration', 0), 'url': d.get('webpage_url', f"https://youtube.com/watch?v={d['id']}")})
        return videos
    except: return []

def process_youtube_video(video: dict, episode_start: int, config: Config) -> list:
    tmp_dir = "temp"
    os.makedirs(tmp_dir, exist_ok=True)
    vid, url = video['id'], video['url']
    
    log.info(f"🎬 كنجبدو المعلومات ديال الفيديو...")
    original_description = ""
    duration = video.get('duration', 0)
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best', 
            'outtmpl': f'{tmp_dir}/yt_{vid}.%(ext)s', 
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}], 
            'quiet': True,
            'cookiefile': config.cookies_file if config.cookies_file and os.path.exists(config.cookies_file) else None,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            original_description = info.get('description', '')
            if duration == 0:
                duration = info.get('duration', 1800)
                
        audio_path = f'{tmp_dir}/yt_{vid}.mp3'
    except Exception as e:
        log.error(f"❌ فشل تحميل {url}: {e}")
        return []
    
    num_parts = max(1, int(duration / config.max_part_duration) + (1 if duration % config.max_part_duration > 60 else 0))
    log.info(f"⏱️ الفيديو غيتقسم لـ {num_parts} أجزاء")
    
    results = []
    for part in range(num_parts):
        ep_num = episode_start + part
        part_audio = f'{tmp_dir}/part_{vid}_{part}.mp3'
        enhanced = f'{tmp_dir}/enh_{vid}_{part}.mp3'
        try:
            subprocess.run(['ffmpeg', '-i', audio_path, '-ss', str(part * config.max_part_duration), '-t', str(config.max_part_duration), '-y', part_audio], capture_output=True)
            filters = f"volume={config.audio_volume},atempo={config.audio_speed},asetrate=48000*{config.pitch_shift},aresample=48000,highpass=f={config.eq_highpass},lowpass=f={config.eq_lowpass}"
            subprocess.run(['ffmpeg', '-i', part_audio, '-af', filters, '-y', enhanced], capture_output=True)
            
            video_output = create_video(enhanced, ep_num, config)
            if video_output:
                fb_id = upload_to_facebook(video_output, ep_num, config, custom_desc=original_description)
                if fb_id:
                    save_processed_id(config.state_file, f"{vid}:{part}")
                    results.append(ep_num)
        except Exception as e: 
            log.error(f"❌ خطأ فالمونتاج: {e}")
    return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="رابط واحد")
    parser.add_argument("--cookies", help="ملف كوكيز")
    args = parser.parse_args()

    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_ACCESS_TOKEN")
    yt_channel = os.environ.get("YOUTUBE_CHANNEL")
    
    if not token or not page_id:
        log.error("❌ الأسرار غير موجودة!")
        sys.exit(1)
        
    config = Config(
        page_id=page_id,
        access_token=token,
        max_part_duration=1800,
        cookies_file=args.cookies or ""
    )
    
    if args.url:
        log.info(f"🎯 غنخدمو على هاد الرابط: {args.url}")
        process_youtube_video({'id': 'test_vid', 'url': args.url, 'duration': 0}, 1, config)
    elif yt_channel:
        processed = load_processed_ids(config.state_file)
        videos = fetch_youtube_videos(yt_channel)
        new_videos = [v for v in videos if f"{v['id']}:0" not in processed and not any(p.startswith(v['id']) for p in processed)]
        
        if not new_videos:
            log.info("✅ لا توجد فيديوهات جديدة.")
            sys.exit(0)
            
        episode_num = 1
        for v in reversed(new_videos):
            results = process_youtube_video(v, episode_num, config)
            episode_num += len(results)
