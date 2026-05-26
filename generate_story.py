#!/usr/bin/env python3
"""
Generate story videos using Remotion.
- Fetches French book from Gutenberg
- Splits into ~30min parts
- Generates edge-tts narration
- Writes props JSON with line timing
- Calls Remotion render
"""
import os, sys, json, re, asyncio, subprocess, tempfile, textwrap, math, html
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "french-flow", "bot"))
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).parent
AUDIO_DIR = PROJECT_ROOT / "public" / "audio"
OUTPUT_DIR = PROJECT_ROOT / "out"
PROGRESS_FILE = PROJECT_ROOT / "story_progress.json"
MAX_WORDS_PER_PART = 4500
VOICES = ["fr-FR-VivienneMultilingualNeural", "fr-FR-RemyMultilingualNeural"]

GUTENBERG_SEARCH = "https://www.gutenberg.org/ebooks/search/?query={query}&submit_search=Go"
GUTENBERG_BOOK_URL = "https://www.gutenberg.org/ebooks/{id}"
GUTENBERG_TEXT = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        return json.load(open(PROGRESS_FILE))
    return {"current_book": None, "current_part": 0, "finished_books": [], "last_date": None}

def save_progress(p):
    json.dump(p, open(PROGRESS_FILE, "w"), indent=2, ensure_ascii=False)

async def generate_tts(text, outpath, voice_idx=0):
    voice = VOICES[voice_idx % len(VOICES)]
    proc = await asyncio.create_subprocess_exec(
        "edge-tts", "--voice", voice, "--text", text,
        "--write-media", str(outpath),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return os.path.exists(outpath) and os.path.getsize(outpath) > 0

def get_audio_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try: return float(r.stdout.strip())
    except: return 0

def extract_story_text(raw):
    text = re.sub(r'(?i).*?\*\*\* START OF (THIS PROJECT GUTENBERG|THE PROJECT GUTENBERG).*?\*\*\*', '', raw, count=1, flags=re.DOTALL)
    text = re.sub(r'(?i)\*\*\* END OF (THIS PROJECT GUTENBERG|THE PROJECT GUTENBERG).*', '', text, flags=re.DOTALL)
    lines = []
    for line in text.split('\n'):
        s = line.strip()
        if not s:
            if lines and lines[-1] != '':
                lines.append('')
        elif re.match(r'^(Produced by|Transcribed by|Language:|Release Date:|\[Illustration)', s, re.I):
            continue
        else:
            lines.append(s)
    return '\n'.join(lines).strip()

async def fetch_book(book_id, finished_ids):
    import aiohttp
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for attempt in range(30):
            queries = ["fr", "french", "français", "conte", "nouvelle", "roman", "littérature"]
            query = queries[attempt % len(queries)]
            async with session.get(GUTENBERG_SEARCH.format(query=query)) as resp:
                html_text = await resp.text()
            soup = BeautifulSoup(html_text, "lxml")
            ids = set()
            for link in soup.select("li.booklink a[href*='/ebooks/']"):
                m = re.search(r'/ebooks/(\d+)', link.get("href", ""))
                if m: ids.add(int(m.group(1)))
            if not ids: continue
            avail = [bid for bid in ids if bid not in finished_ids]
            if not avail: continue
            bid = random.choice(avail)
            async with session.get(GUTENBERG_BOOK_URL.format(id=bid)) as dr:
                dh = await dr.text()
            ds = BeautifulSoup(dh, "lxml")
            te = ds.select_one("h1")
            title = te.get_text(strip=True) if te else f"Book {bid}"
            async with session.get(GUTENBERG_TEXT.format(id=bid)) as tr:
                if tr.status != 200: continue
                raw = await tr.text(errors="replace")
            text = extract_story_text(raw)
            if not text or len(text) < 500: continue
            words = text.split()
            parts = max(1, math.ceil(len(words) / MAX_WORDS_PER_PART))
            return {"id": bid, "title": title, "text": text, "total_parts": parts}
    return None

def text_to_lines(text, width=38):
    paragraphs = text.split('\n')
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if re.match(r'^[A-Z\sÀ-ÖØ-Ý]{4,}$', p) and len(p) < 70:
            result.append({"text": p.strip(), "isHeading": True})
        else:
            wrapped = textwrap.wrap(p, width=width)
            for w in wrapped:
                result.append({"text": w, "isHeading": False})
    return result

async def generate_part(book, part_num):
    words = book["text"].split()
    start = (part_num - 1) * MAX_WORDS_PER_PART
    end = min(start + MAX_WORDS_PER_PART, len(words))
    part_text = ' '.join(words[start:end])
    lines = text_to_lines(part_text)
    safe_name = re.sub(r'[^a-z0-9]+', '_', book["title"].lower())[:40]
    audio_path = AUDIO_DIR / f"story_{book['id']}_p{part_num}.mp3"

    print(f"📖 '{book['title']}' — Part {part_num}/{book['total_parts']}")
    print(f"   {len(part_text.split())} words, {len(lines)} lines")

    # Generate full audio for the part
    print(f"🔊 Generating TTS ({len(part_text)} chars)...")
    ok = await generate_tts(part_text, audio_path, part_num)
    if not ok:
        print("❌ TTS failed"); return None

    dur = get_audio_duration(audio_path)
    print(f"⏱️  Audio: {dur:.0f}s ({dur/60:.1f} min)")

    if dur < 60:
        print("⚠️  Too short"); return None

    # Write props JSON for Remotion
    rel_audio = f"audio/story_{book['id']}_p{part_num}.mp3"
    bg_music = "audio/bg-music.mp3"
    bg_path = AUDIO_DIR / "bg-music.mp3"
    has_bg = os.path.exists(bg_path)

    props = {
        "title": f"{book['title']} — Partie {part_num}",
        "lines": lines,
        "audioSrc": rel_audio,
        "bgMusicSrc": "audio/bg-music.mp3" if has_bg else None,
    }

    props_json = json.dumps(props)
    props_file = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    )
    props_file.write(props_json)
    props_file.close()

    output_path = OUTPUT_DIR / f"story_{book['id']}_p{part_num}.mp4"

    print(f"🎬 Rendering with Remotion...")
    result = subprocess.run(
        ["npx", "remotion", "render", "Story", str(output_path),
         "--props", props_file.name, "--overwrite",
         "--concurrency", "2"],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True, timeout=7200,
        env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=4096"},
    )
    os.unlink(props_file.name)

    if result.returncode == 0 and os.path.exists(output_path):
        size = os.path.getsize(output_path) / (1024*1024)
        print(f"✅ Video: {output_path.name} ({size:.1f} MB)")
        return output_path
    else:
        err = result.stderr[-500:]
        print(f"❌ Render failed: {err}")
        return None

async def publish_to_facebook(video_path, title, part_num, total_parts, page_id, access_token):
    if not page_id or not access_token:
        print("  ⚠️ No FB credentials"); return False
    import aiohttp
    desc = (
        f"🇫🇷 Histoire du jour - French Flow 📖\n\n"
        f"{title}\nPartie {part_num}/{total_parts}\n\n"
        f"#FrenchFlow #HistoireDuJour #ApprendreLeFrançais"
    )
    async with aiohttp.ClientSession() as session:
        with open(video_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('source', f, filename='story.mp4', content_type='video/mp4')
            data.add_field('description', desc)
            data.add_field('access_token', access_token)
            async with session.post(f'https://graph.facebook.com/v22.0/{page_id}/videos', data=data) as resp:
                r = await resp.json()
                if r.get('id'): print(f"  ✅ Published ID: {r['id']}"); return True
                print(f"  ❌ FB error: {r}"); return False

async def main():
    import random
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_ACCESS_TOKEN")
    progress = load_progress()

    print("🤖 French Flow Story — Remotion Edition")

    needs_new = (
        progress["current_book"] is None or
        progress["current_part"] >= progress["current_book"]["total_parts"]
    )

    if needs_new:
        finished = [b["id"] for b in progress.get("finished_books", [])]
        book = await fetch_book(None, finished)
        if not book: print("❌ No books"); return
        progress["current_book"] = {"id": book["id"], "title": book["title"], "total_parts": book["total_parts"]}
        progress["current_part"] = 0
        progress["book_text"] = book["text"]
    else:
        book = {**progress["current_book"], "text": progress.get("book_text", "")}
        if not book.get("text"):
            print("❌ Book text missing"); return

    part_num = progress["current_part"] + 1
    print(f"📚 {progress['current_book']['title']} — Part {part_num}/{book['total_parts']}")

    video_path = await generate_part(book, part_num)

    if video_path:
        pub_ok = await publish_to_facebook(
            video_path, book["title"], part_num, book["total_parts"],
            page_id, access_token
        )
        if pub_ok:
            progress["current_part"] += 1
            progress["last_date"] = str(__import__("datetime").date.today())
            if progress["current_part"] >= book["total_parts"]:
                progress.setdefault("finished_books", []).append(progress["current_book"])
                progress["current_book"] = None
                progress.pop("book_text", None)
            save_progress(progress)
    print("✨ Done!")

if __name__ == "__main__":
    asyncio.run(main())
