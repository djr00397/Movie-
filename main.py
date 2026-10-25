import os, sys, shutil, traceback
import config as C, art, sources as S, llm_script as L, voice as V, video, thumb, upload


def mmss(sec):
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def main():
    mode = os.environ.get("MODE", "long")
    print("MODE:", mode)
    art.ensure_fonts()
    yt = upload.youtube()          # fail fast: check the YouTube login BEFORE the long work starts
    print("YouTube login OK")
    hist = S.load_hist()
    items = S.gather()
    topic = S.pick_topic(items, hist)
    print("TOPIC:", topic["title"], "| keys:", topic["keys"])
    ev = S.build_evidence(topic)

    script = L.write_long(topic, ev) if mode == "long" else L.write_short(topic, ev)
    voice, units = V.narrate(script, mode)
    dur = len(voice) / V.SR + 0.8
    print(f"narration {len(voice) / V.SR / 60:.1f} min")

    chapters = []
    if mode == "long":
        seen = set()
        for u in units:
            if u["sec"] not in seen:
                seen.add(u["sec"])
                chapters.append((mmss(u["start"] if u["sec"] else 0), script["sections"][u["sec"]]["title"]))
    seo = L.make_seo(topic, script, ev, mode, chapters)
    print("TITLE:", seo["title"], "| thumb:", seo["thumb_text"])

    W, H = C.LONG_SIZE if mode == "long" else C.SHORT_SIZE
    scenes, sfx_events = video.plan(units, script, ev, mode, dur)
    words = video.words_timeline(units)
    audio_path = os.path.join(C.WORK, "final.wav")
    V.mix(voice, sfx_events, audio_path)
    out = os.path.join(C.WORK, f"{mode}.mp4")
    video.render(scenes, words, voice, ev, audio_path, out, W, H, mode, dur, seo["thumb_text"])
    th = thumb.make(seo["thumb_text"], ev, os.path.join(C.WORK, "thumb.jpg"))
    vid = upload.upload(out, th, seo, mode, yt)
    S.save_hist(topic, mode, vid)
    shutil.rmtree(C.WORK, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
