# conver-listen

English-conversation practice tools on top of [Supertonic](https://github.com/supertone-inc/supertonic) (on-device TTS) and Anthropic Claude.

Three things in one repo:

| Component | What it does |
|---|---|
| **`chat-ui/tutor.py`** | Gradio web UI. Type in Vietnamese or English → Claude Haiku replies in English → Supertonic speaks the reply. Conversations are persisted to a local SQLite database. |
| **`app.py`** | CLI. Vietnamese text → Google Translate → English → Supertonic WAV. |
| **`.claude/skills/conver-listen/`** | Project-local Claude Code skill. Ask Claude for a dialogue on any topic → it writes a self-contained `outputs/{slug}/{slug}.py` + plays the generated WAV. |

---

## Prerequisites

- Python 3.10–3.12
- [`uv`](https://docs.astral.sh/uv/) (package manager)
- An audio player on `$PATH` — `paplay` / `aplay` / `ffplay` (already standard on most Linux desktops)
- `ANTHROPIC_API_KEY` (only required for `chat-ui/tutor.py`)

First run will auto-download the Supertonic ONNX weights (~260 MB) from Hugging Face.

## Setup

```bash
git clone git@github.com:ngocp-0847/conver-listen.git
cd conver-listen
uv sync
cp .env.example .env       # then paste your real ANTHROPIC_API_KEY
```

## Run

### Gradio chatbot (English tutor)
```bash
uv run python chat-ui/tutor.py
# open http://127.0.0.1:7860
```
Type freely in Vietnamese or English. Claude replies in short, learner-friendly English; the reply autoplays via Supertonic.

Every turn is appended to `chat-ui/conversations.db`:

| column | meaning |
|---|---|
| `session_id` | one id per Gradio tab/state |
| `turn_index` | 0-based position within the session |
| `user_message` | what you typed |
| `assistant_message` | Claude's English reply |
| `audio_path` | absolute path to the generated WAV |
| `created_at` | UTC timestamp |

Inspect from the shell:
```bash
sqlite3 chat-ui/conversations.db "SELECT turn_index, user_message, assistant_message FROM turns ORDER BY id DESC LIMIT 5;"
```

### CLI translator → speech
```bash
uv run python app.py "Xin chào, hôm nay trời đẹp."
# writes outputs/output.wav
```

## The Claude skill

`.claude/skills/conver-listen/SKILL.md` is a project-local Claude Code skill named `conversation-tts`. When you open Claude Code inside this directory and say something like:

> tôi muốn nghe 1 đoạn hội thoại về phỏng vấn senior developer

…Claude will:

1. Pick a slug (`senior-developer-interview`).
2. Generate a 10–14 turn English dialogue with two speakers.
3. Write `outputs/{slug}/{slug}.py` — a runnable Python file containing the dialogue + Supertonic synthesis logic.
4. Run it to produce `outputs/{slug}/{slug}.wav`.
5. Play the WAV via `paplay`.

Replay any generated dialogue:
```bash
paplay outputs/<slug>/<slug>.wav
```

The skill only activates when Claude Code is invoked from this folder — it is project-local, not user-global.

## Layout

```
conver-listen/
├── .claude/skills/conver-listen/SKILL.md  # the skill
├── chat-ui/
│   ├── tutor.py                           # Gradio + Claude + Supertonic + SQLite
│   ├── conversations.db                   # SQLite store (gitignored)
│   └── outputs/                           # per-turn WAVs (gitignored)
├── app.py                                 # CLI Vi -> En speech
├── outputs/                               # skill-generated dialogues
│   └── <slug>/<slug>.py + <slug>.wav
├── pyproject.toml
├── uv.lock
└── .env.example
```

## Notes

- Generated `*.wav` files are gitignored — regenerate them by running the scripts.
- `chat-ui/conversations.db` is gitignored too; delete it to start fresh.
- The `.venv/` directory is gitignored. Use `uv sync` to rebuild it.
- `chat-ui/tutor.py` requires `ANTHROPIC_API_KEY`; `app.py` does not.

## License

MIT for the code in this repo. Supertonic itself is OpenRAIL-M — see [supertone-inc/supertonic](https://github.com/supertone-inc/supertonic) for upstream terms.
