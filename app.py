"""MVP: Vietnamese text -> English translation -> English speech (Supertonic TTS)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deep_translator import GoogleTranslator
from supertonic import TTS


def translate_vi_to_en(text: str) -> str:
    return GoogleTranslator(source="vi", target="en").translate(text)


def synthesize_en(text: str, out_path: Path, voice: str = "M1") -> float:
    tts = TTS(auto_download=True)
    style = tts.get_voice_style(voice_name=voice)
    wav, duration = tts.synthesize(
        text=text,
        lang="en",
        voice_style=style,
        total_steps=8,
        speed=1.05,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tts.save_audio(wav, str(out_path))
    return float(duration[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Vietnamese text -> English speech")
    parser.add_argument("text", nargs="?", help="Vietnamese input text. Omit to read from stdin.")
    parser.add_argument("-o", "--output", default="outputs/output.wav", help="Output WAV path")
    parser.add_argument("-v", "--voice", default="M1", help="Voice style (e.g. M1, F1)")
    args = parser.parse_args()

    vi_text = args.text if args.text else sys.stdin.read().strip()
    if not vi_text:
        print("Error: empty input text.", file=sys.stderr)
        return 2

    print(f"[VI] {vi_text}")
    en_text = translate_vi_to_en(vi_text)
    print(f"[EN] {en_text}")

    out_path = Path(args.output)
    duration = synthesize_en(en_text, out_path, voice=args.voice)
    print(f"[OK] {duration:.2f}s of audio -> {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
