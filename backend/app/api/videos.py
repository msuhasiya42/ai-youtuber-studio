from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import Video, Idea, Script


router = APIRouter()


@router.get("")
def list_videos(page: int = 1, page_size: int = 6, db: Session = Depends(get_db)):
    q = db.query(Video).order_by(Video.id.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": v.id,
                "title": v.title,
                "thumbnail_url": v.thumbnail_url,
                "views": v.views,
                "likes": v.likes,
                "ctr": v.ctr,
            }
            for v in items
        ],
    }


@router.get("/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404)
    idea = db.query(Idea).filter(Idea.video_id == v.id).order_by(Idea.id.desc()).first()
    scripts = db.query(Script).join(Idea, Script.idea_id == Idea.id).filter(Idea.video_id == v.id).all()
    return {
        "id": v.id,
        "title": v.title,
        "thumbnail_url": v.thumbnail_url,
        "transcript_s3_key": v.transcript_s3_key,
        "summary": idea.summary if idea else None,
        "ideas": idea.ideas_json if idea else None,
        "scripts": [
            {"id": s.id, "content_md": s.content_md, "tone": s.tone, "minutes": s.minutes}
            for s in scripts
        ],
    }


class ScriptRequest(BaseModel):
    idea_id: int
    tone: str | None = None
    minutes: int | None = 8


@router.post("/script")
def create_script(payload: ScriptRequest, db: Session = Depends(get_db)):
    s = Script(idea_id=payload.idea_id, content_md="# Draft Script\n\n...", tone=payload.tone, minutes=payload.minutes)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id}


