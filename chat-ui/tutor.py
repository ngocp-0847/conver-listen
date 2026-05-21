"""English conversation tutor.

User types Vietnamese or English -> Claude Haiku replies in English ->
Supertonic synthesizes English speech -> Gradio plays it in the browser.

Every turn is persisted to a local SQLite database.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit(
        "Set ANTHROPIC_API_KEY in your environment or in .env before launching."
    )

import anthropic
import gradio as gr
from supertonic import TTS

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
DB_PATH = BASE_DIR / "conversations.db"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLAUDE_MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = (
    "You are a friendly English conversation tutor. "
    "Always reply in English, even if the user writes Vietnamese. "
    "Keep replies short — 1 to 3 sentences in natural, learner-friendly English. "
    "If the user's English has a clear mistake, gently correct it in one short clause before continuing. "
    "End most turns with a simple follow-up question to keep the conversation going."
)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                audio_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON turns(session_id, turn_index)"
        )


def save_turn(
    session_id: str,
    turn_index: int,
    user_message: str,
    assistant_message: str,
    audio_path: str | None,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO turns (session_id, turn_index, user_message, assistant_message, audio_path) VALUES (?, ?, ?, ?, ?)",
            (session_id, turn_index, user_message, assistant_message, audio_path),
        )


init_db()
print(f"[startup] SQLite ready at {DB_PATH}", flush=True)

print("[startup] Loading Supertonic TTS (first run downloads ~260MB)...", flush=True)
TTS_ENGINE = TTS(auto_download=True)
VOICE_STYLE = TTS_ENGINE.get_voice_style(voice_name="M1")
print("[startup] TTS ready.", flush=True)

CLAUDE = anthropic.Anthropic()


def synth_to_file(text: str) -> str:
    wav, _duration = TTS_ENGINE.synthesize(
        text=text,
        lang="en",
        voice_style=VOICE_STYLE,
        total_steps=8,
        speed=1.05,
    )
    out_path = OUTPUT_DIR / f"turn_{uuid.uuid4().hex}.wav"
    TTS_ENGINE.save_audio(wav, str(out_path))
    return str(out_path)


def call_claude(messages: list[dict]) -> str:
    response = CLAUDE.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def respond(
    user_msg: str,
    history: list[dict],
    session_id: str,
    anth_history: list[dict],
):
    user_msg = (user_msg or "").strip()
    if not user_msg:
        return history, None, session_id, anth_history, ""

    if not session_id:
        session_id = uuid.uuid4().hex

    try:
        next_anth = anth_history + [{"role": "user", "content": user_msg}]
        reply = call_claude(next_anth)
        wav_path = synth_to_file(reply)
        next_anth = next_anth + [{"role": "assistant", "content": reply}]
        next_history = history + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": reply},
        ]
        turn_index = len(anth_history) // 2
        save_turn(session_id, turn_index, user_msg, reply, wav_path)
        return next_history, wav_path, session_id, next_anth, ""
    except Exception as exc:  # noqa: BLE001 — surface any failure to the chat
        err = f"[Error: {type(exc).__name__}: {exc}]"
        next_history = history + [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": err},
        ]
        return next_history, None, session_id, anth_history, ""


with gr.Blocks(title="English Conversation Tutor") as demo:
    gr.Markdown(
        "# English Conversation Tutor\n"
        "Type in **English or Vietnamese**. The bot replies in English (Claude Haiku) "
        "and speaks the reply with **Supertonic** TTS. Conversations are saved locally to SQLite."
    )
    chatbot = gr.Chatbot(height=420, label="Conversation")
    audio = gr.Audio(autoplay=True, type="filepath", label="Bot voice", interactive=False)
    box = gr.Textbox(
        placeholder="Hỏi bằng tiếng Việt hoặc English...",
        label="Your message",
        autofocus=True,
    )
    session_state = gr.State("")
    hist_state = gr.State([])

    box.submit(
        respond,
        [box, chatbot, session_state, hist_state],
        [chatbot, audio, session_state, hist_state, box],
    )


if __name__ == "__main__":
    demo.launch()
