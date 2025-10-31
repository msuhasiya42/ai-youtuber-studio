from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db, Base, engine
from app.models.models import Channel, Video


router = APIRouter()


class ConnectRequest(BaseModel):
    channel_url: str | None = None
    google_oauth: bool = False


@router.post("/connect")
def connect_channel(payload: ConnectRequest, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=engine)
    # Very simplified: extract channel id from URL as last path segment
    if not payload.channel_url and not payload.google_oauth:
        raise HTTPException(status_code=400, detail="Provide channel_url or use google_oauth")

    yt_channel_id = "mock_channel_id"
    ch = Channel(
        youtube_channel_id=yt_channel_id,
        name="Mock Channel",
        avatar_url="https://placehold.co/96x96",
        subscribers=123456,
        verified=True,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    # seed some videos
    for i in range(1, 7):
        v = Video(
            channel_id=ch.id,
            youtube_video_id=f"mockvid{i}",
            title=f"Sample Video {i}",
            thumbnail_url="https://placehold.co/320x180",
            duration_seconds=480 + i,
            views=1000 * i,
            likes=100 * i,
            ctr=3.5 + i,
        )
        db.add(v)
    db.commit()
    return {"channel_id": ch.id}


@router.get("/me")
def get_my_channel(db: Session = Depends(get_db)):
    ch = db.query(Channel).order_by(Channel.id.desc()).first()
    if not ch:
        return {"channel": None}
    top_videos = (
        db.query(Video)
        .filter(Video.channel_id == ch.id)
        .order_by(Video.views.desc())
        .limit(3)
        .all()
    )
    return {"channel": {
        "id": ch.id,
        "name": ch.name,
        "avatar_url": ch.avatar_url,
        "subscribers": ch.subscribers,
        "verified": ch.verified,
    }, "top_videos": [
        {"id": v.id, "title": v.title, "thumbnail_url": v.thumbnail_url, "views": v.views, "likes": v.likes, "ctr": v.ctr}
        for v in top_videos
    ]}


