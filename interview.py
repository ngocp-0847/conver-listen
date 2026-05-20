"""Generate a senior-developer interview dialogue, synthesize with Supertonic, save WAV."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
from supertonic import TTS

OUTPUT = Path(__file__).parent / "outputs" / "interview.wav"
SAMPLE_RATE = 44100
PAUSE_MS = 350  # silence between turns

INTERVIEWER_VOICE = "M1"
CANDIDATE_VOICE = "F1"

DIALOGUE: list[tuple[str, str]] = [
    ("interviewer", "Hi, thanks for coming in today. To start, could you walk me through your background as a senior developer?"),
    ("candidate",   "Sure. I have around nine years of experience, mostly in backend systems. The last four years I've been leading a small team building payment infrastructure on AWS, mainly Python and Go."),
    ("interviewer", "Great. Tell me about a system you designed end to end. What were the hardest trade-offs?"),
    ("candidate",   "We replaced a monolith with an event-driven service for transaction processing. The hardest trade-off was consistency. We picked eventual consistency with idempotent consumers to scale writes, but it pushed real complexity to the client side and to our reconciliation jobs."),
    ("interviewer", "How did you handle failures in that event-driven flow?"),
    ("candidate",   "Three layers. Retries with exponential backoff at the consumer, a dead-letter queue for poison messages, and a daily reconciliation job that compares the event log to the source of truth. We also added structured tracing so on-call could follow a single transaction across services."),
    ("interviewer", "Nice. Shifting gears, how do you mentor more junior engineers on your team?"),
    ("candidate",   "I focus on code review as a teaching moment, not a gate. I leave comments that explain why, not just what. I also pair on hard problems for the first thirty minutes, then let them drive. It builds confidence without slowing them down."),
    ("interviewer", "Last question. What's a technical decision you regret, and what did you learn from it?"),
    ("candidate",   "Early on I picked a NoSQL store for data that turned out to be highly relational. We paid for that for years in awkward joins at the application layer. The lesson was simple. Match the data model to the access patterns, not to the hype."),
    ("interviewer", "That's a great answer. Thanks for your time. We'll be in touch within the week."),
    ("candidate",   "Thank you. I really enjoyed the conversation."),
]


def main() -> None:
    print("[init] Loading Supertonic...", flush=True)
    tts = TTS(auto_download=True)
    styles = {
        "interviewer": tts.get_voice_style(voice_name=INTERVIEWER_VOICE),
        "candidate":   tts.get_voice_style(voice_name=CANDIDATE_VOICE),
    }

    pause_samples = int(SAMPLE_RATE * PAUSE_MS / 1000)
    silence = np.zeros((1, pause_samples), dtype=np.float32)

    chunks: list[np.ndarray] = []
    for i, (speaker, line) in enumerate(DIALOGUE, 1):
        print(f"[{i:02d}/{len(DIALOGUE)}] {speaker}: {line[:60]}{'...' if len(line) > 60 else ''}", flush=True)
        wav, _dur = tts.synthesize(
            text=line,
            lang="en",
            voice_style=styles[speaker],
            total_steps=8,
            speed=1.05,
        )
        if wav.ndim == 1:
            wav = wav.reshape(1, -1)
        chunks.append(wav.astype(np.float32))
        chunks.append(silence)

    full = np.concatenate(chunks, axis=1)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(OUTPUT), full.squeeze(), SAMPLE_RATE, subtype="PCM_16")

    total_sec = full.shape[1] / SAMPLE_RATE
    print(f"\n[done] {total_sec:.1f}s -> {OUTPUT}")


if __name__ == "__main__":
    main()
