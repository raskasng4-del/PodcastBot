#!/usr/bin/env python3
import json, os, sys, asyncio, subprocess, tempfile, shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(PROJECT_ROOT, "public", "audio")
EDGE_TTS = "edge-tts"

FRENCH_ARTICLES = {
    "trompette": "une", "piano": "un", "guitare": "une", "violon": "un",
    "batterie": "une", "flûte": "une", "saxophone": "un", "harpe": "une",
    "accordéon": "un", "clarinette": "une", "contrebasse": "une",
    "triangle": "un", "cymbale": "une", "orgue": "un", "violoncelle": "un",
    "banjo": "un", "xylophone": "un", "tambour": "un", "maracas": "une",
    "castagnettes": "une", "harmonica": "un", "basse": "une",
    "synthétiseur": "un", "piano à queue": "un",
}

VOICES = ["fr-FR-VivienneMultilingualNeural", "fr-FR-RemyMultilingualNeural"]

def get_article(name):
    name_lower = name.lower().strip()
    if name_lower in FRENCH_ARTICLES:
        return FRENCH_ARTICLES[name_lower]
    if name_lower.endswith("e") or name_lower.endswith("ion"):
        return "une"
    return "un"

async def generate_tts(text, outpath, voice_idx=0):
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    voice = VOICES[voice_idx % len(VOICES)]
    proc = await asyncio.create_subprocess_exec(
        "edge-tts", "--voice", voice, "--text", text,
        "--write-media", outpath,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if not os.path.exists(outpath) or os.path.getsize(outpath) == 0:
        print(f"  ❌ TTS failed for: {text[:40]}")
        return False
    print(f"  🔊 Generated: {os.path.basename(outpath)} ({voice})")
    return True

async def generate_quiz_video(item, output_path):
    name = item.get("name", item.get("objectName", ""))
    image_url = item.get("image_url", item.get("imageUrl", ""))
    article = item.get("article", get_article(name))
    safe_name = name.lower().replace(" ", "_").replace("'", "_")
    os.makedirs(AUDIO_DIR, exist_ok=True)

    question_text = "Qu'est-ce que c'est ?"
    answer_text = f"C'est {article} {name}."

    q_audio = os.path.join(AUDIO_DIR, f"q_{safe_name}.mp3")
    a_audio = os.path.join(AUDIO_DIR, f"a_{safe_name}.mp3")

    voice_idx = hash(name) % len(VOICES)
    ok = await generate_tts(question_text, q_audio, voice_idx)
    ok = await generate_tts(answer_text, a_audio, voice_idx + 1) and ok

    if not ok:
        print("❌ Audio generation failed")
        return False

    props = {
        "imageUrl": image_url,
        "objectName": name,
        "objectArticle": article,
        "questionAudio": f"audio/q_{safe_name}.mp3",
        "answerAudio": f"audio/a_{safe_name}.mp3",
    }

    props_json = json.dumps(props).replace('"', '\\"')
    fps = 30
    total_frames = int(fps * 8.5)

    cmd = (
        f'npx remotion render Quiz "{output_path}" '
        f'--props=\'{json.dumps(props)}\' --overwrite'
    )

    print(f"🎬 Rendering quiz: {name}")
    result = subprocess.run(
        cmd, shell=True, cwd=PROJECT_ROOT,
        capture_output=True, text=True,
        timeout=180,
        env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=2048"},
    )

    if result.returncode == 0 and os.path.exists(output_path):
        print(f"✅ Quiz video saved: {output_path}")
        return True
    else:
        err = result.stderr[-500:]
        print(f"❌ Render failed for '{name}': {err}")
        # Clean up failed output
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate vocabulary quiz videos")
    parser.add_argument("--input", help="JSON file with items (list of {name, image_url})")
    parser.add_argument("--name", help="Single object name")
    parser.add_argument("--image", help="Single image URL")
    parser.add_argument("--article", help="Article (un/une), auto-detected if omitted")
    parser.add_argument("--output", default="out/quiz.mp4", help="Output path")
    parser.add_argument("--batch", action="store_true", help="Generate all items from input file")

    args = parser.parse_args()

    if args.batch and args.input:
        with open(args.input) as f:
            items = json.load(f)
        os.makedirs(os.path.join(PROJECT_ROOT, "out", "quiz"), exist_ok=True)
        success = 0
        fail = 0
        for i, item in enumerate(items):
            out = os.path.join(PROJECT_ROOT, "out", "quiz",
                f"quiz_{item['name'].lower().replace(' ', '_')}.mp4")
            if await generate_quiz_video(item, out):
                success += 1
            else:
                fail += 1
            print()
        print(f"✅ Batch done: {success} succeeded, {fail} failed")
    elif args.name and args.image:
        item = {
            "name": args.name,
            "image_url": args.image,
            "article": args.article or get_article(args.name),
        }
        os.makedirs(os.path.dirname(os.path.join(PROJECT_ROOT, args.output)), exist_ok=True)
        await generate_quiz_video(item, os.path.join(PROJECT_ROOT, args.output))
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
