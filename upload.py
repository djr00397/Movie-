import os, time, datetime as dt
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import config as C


def youtube():
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"])
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def next_slot(mode):
    """Next publish slot (UTC) at least 12 minutes from now. Returns None if the job is too late."""
    slots = C.LONG_SLOTS_UTC if mode == "long" else C.SHORT_SLOTS_UTC
    now = dt.datetime.now(dt.timezone.utc)
    cands = []
    for day in (0, 1):
        for h in slots:
            c = (now + dt.timedelta(days=day)).replace(hour=h, minute=0, second=0, microsecond=0)
            if c > now + dt.timedelta(minutes=12):
                cands.append(c)
    return min(cands) if cands else None


def upload(path, thumb, seo, mode, yt=None):
    yt = yt or youtube()
    slot = next_slot(mode)
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "embeddable": True, "publicStatsViewable": True}
    # Scheduled publishing: the video goes live exactly at the slot (06:00/18:00 or 00:00/12:00 Bangladesh time)
    if slot and slot - dt.datetime.now(dt.timezone.utc) < dt.timedelta(hours=6):
        status.update(privacyStatus="private", publishAt=slot.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        print("scheduled for", slot)
    body = {"snippet": {"title": seo["title"][:100], "description": seo["description"], "tags": seo["tags"][:30],
                        "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"}, "status": status}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(path, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4"))
    resp, tries = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"upload {st.progress() * 100:.0f}%", flush=True)
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tries < 8:
                tries += 1
                time.sleep(2 ** tries)
                continue
            raise
    vid = resp["id"]
    print("uploaded video id:", vid)
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
        print("thumbnail set")
    except Exception as ex:
        print("thumbnail failed (needs the 'youtube' scope and a phone-verified channel):", str(ex)[:150])
    return vid
