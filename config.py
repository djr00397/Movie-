import os

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "work")
ASSETS = os.path.join(ROOT, "assets")
HIST = os.path.join(ROOT, "history")
for _d in (WORK, ASSETS, HIST):
    os.makedirs(_d, exist_ok=True)

# Local AI models (CPU, GGUF, downloaded free from Hugging Face)
MAIN_MODEL = ("bartowski/Qwen2.5-7B-Instruct-GGUF", "Qwen2.5-7B-Instruct-Q4_K_M.gguf")
FAST_MODEL = ("bartowski/Qwen2.5-3B-Instruct-GGUF", "Qwen2.5-3B-Instruct-Q4_K_M.gguf")

VOICE = "am_michael"          # Kokoro English voice
FPS = 24
LONG_SIZE = (1280, 720)
SHORT_SIZE = (1080, 1920)
LONG_MIN, LONG_MAX = 15.4 * 60, 19.3 * 60   # seconds (video will be 15-20 min)
SHORT_MAX = 57.0
N_CHAPTERS = 7
HOOK_WORDS, CHAPTER_WORDS, CONCL_WORDS = 120, 310, 220
LONG_MIN_WORDS = 2450
SHORT_WORDS = 120

# Publish slots (UTC hours). 06:00/18:00 Bangladesh time = 00:00/12:00 UTC (shorts)
# 00:00/12:00 Bangladesh time = 18:00/06:00 UTC (long videos)
LONG_SLOTS_UTC = [6, 18]
SHORT_SLOTS_UTC = [0, 12]

OUTLETS = ["cnbc", "marketwatch", "yahoo", "investing.com", "seeking alpha", "reuters", "bloomberg",
           "forbes", "wikipedia", "fred", "google", "bbc", "guardian", "new york times", "nytimes",
           "wall street journal", "wsj", "fortune", "business insider", "cointelegraph", "coindesk",
           "financial times", "associated press", "axios", "cnn", "fox business", "barron"]

STYLE = """You are the narrator of a popular English finance-explainer YouTube channel. Voice and structure:
- Open with a gripping hook: a surprising fact, a bold question, or a 'what if'. Never start with 'Hello' or 'Welcome'.
- Speak directly to the viewer ('you'), like a smart friend explaining over coffee. Mix short punchy sentences with longer ones.
- Build a story: the problem, the context, how it actually works, the numbers, who wins, who loses, what could happen next.
- Explain every jargon word the first time in plain language, with an everyday analogy.
- Use rhetorical questions and transitions such as 'But here is the twist', 'Now think about this', 'So what does this mean for you?'.
- Be factual and balanced. Present evidence. Never promise returns and never tell people to buy or sell anything.
- Write only spoken narration: no headings, no bullet points, no markdown, no stage directions, no emojis, no URLs, and never name websites, newspapers or news outlets."""
