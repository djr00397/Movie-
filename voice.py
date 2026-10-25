import os, re, subprocess, urllib.request
import numpy as np, soundfile as sf
import config as C

SR = 24000
_K = None
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def kokoro():
    global _K
    if _K is None:
        from kokoro_onnx import Kokoro
        d = os.path.join(C.ROOT, "models")
        os.makedirs(d, exist_ok=True)
        for fn in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
            p = os.path.join(d, fn)
            if not os.path.exists(p):
                print("downloading", fn)
                urllib.request.urlretrieve(BASE + fn, p)
        _K = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    return _K


def speakable(t):
    t = re.sub(r"\$(\d[\d,\.]*)\s*(trillion|billion|million|thousand)?", lambda m: f"{m.group(1)} {m.group(2) or ''} dollars".replace("  ", " "), t)
    t = t.replace("%", " percent").replace("&", " and ").replace("S and P", "S and P")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def speak(text):
    s, _ = kokoro().create(speakable(text), voice=C.VOICE, speed=1.0, lang="en-us")
    return np.asarray(s, dtype=np.float32)


def split_sent(p):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", p.strip()) if s.strip()]


def tempo(a, f):
    sf.write(os.path.join(C.WORK, "t_in.wav"), a, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(C.WORK, "t_in.wav"),
                    "-filter:a", f"atempo={f:.4f}", os.path.join(C.WORK, "t_out.wav")], check=True)
    b, _ = sf.read(os.path.join(C.WORK, "t_out.wav"), dtype="float32")
    return b if b.ndim == 1 else b[:, 0]


def narrate(script, mode):
    chunks = [np.zeros(int(0.35 * SR), dtype=np.float32)]
    pos = len(chunks[0])
    units = []
    for si, sec in enumerate(script["sections"]):
        paras = [p for p in sec["text"].split("\n\n") if p.strip()]
        for pi, p in enumerate(paras):
            sents = split_sent(p)
            for k, s in enumerate(sents):
                a = speak(s)
                start = pos / SR
                chunks.append(a)
                pos += len(a)
                last_s = k == len(sents) - 1
                gap = int((0.7 if (last_s and pi == len(paras) - 1) else 0.45 if last_s else 0.16) * SR)
                chunks.append(np.zeros(gap, dtype=np.float32))
                pos += gap
                units.append({"text": s, "start": start, "end": (pos - gap) / SR, "sec": si})
        print("voiced section", si + 1, "/", len(script["sections"]))
    audio = np.concatenate(chunks)
    dur = len(audio) / SR
    f = 1.0
    if mode == "long" and (dur < C.LONG_MIN or dur > C.LONG_MAX):
        f = min(1.18, max(0.88, dur / (17.0 * 60)))
    elif mode == "short" and dur > C.SHORT_MAX:
        f = min(1.25, dur / (C.SHORT_MAX - 1.5))
    if abs(f - 1) > 0.01:
        audio = tempo(audio, f)
        for u in units:
            u["start"] /= f
            u["end"] /= f
        print(f"tempo x{f:.3f}: {dur:.0f}s -> {len(audio) / SR:.0f}s")
    audio = audio / (np.abs(audio).max() + 1e-9) * 0.92
    return audio.astype(np.float32), units


# ---------- procedural background music + sound effects (no downloads, no copyright) ----------
def music(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
    out = np.zeros(n)
    seg = 8.0
    for i in range(int(dur // seg) + 1):
        a, b = int(i * seg * SR), min(n, int((i + 1) * seg * SR))
        if b <= a:
            continue
        tt = t[a:b]
        env = np.clip(np.minimum(tt - tt[0], tt[-1] - tt) / 1.5, 0, 1)
        for note in chords[i % 4]:
            fr = 440 * 2 ** ((note - 69) / 12)
            out[a:b] += env * (np.sin(2 * np.pi * fr * tt) + 0.3 * np.sin(4 * np.pi * fr * tt))
    out /= (np.abs(out).max() + 1e-9)
    return (out * (0.85 + 0.15 * np.sin(2 * np.pi * 0.1 * t))).astype(np.float32)


def sfx(kind):
    if kind == "whoosh":
        d = 0.55
        t = np.arange(int(d * SR)) / SR
        env = np.sin(np.pi * t / d) ** 2
        ch = np.sin(2 * np.pi * (300 * t + 2200 * t ** 2 / d))
        return (np.random.randn(len(t)) * ch * env * 0.25).astype(np.float32)
    d = 0.12
    t = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * 620 * t) * np.exp(-t * 35) * 0.5).astype(np.float32)


def mix(voice, events, out_path):
    n = len(voice) + int(0.8 * SR)
    out = np.zeros(n, dtype=np.float32)
    out[:len(voice)] += voice
    out += 0.055 * music(n / SR)[:n]
    cache = {}
    for t, kind in events:
        w = cache.setdefault(kind, sfx(kind))
        a = int(t * SR)
        if a < n:
            e = min(n, a + len(w))
            out[a:e] += w[:e - a] * 0.7
    out /= max(1.0, np.abs(out).max() / 0.95)
    fade = int(0.6 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    sf.write(out_path, out, SR)
    return n / SR
