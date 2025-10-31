from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Video

router = APIRouter()


@router.get("")
def top_performers(db: Session = Depends(get_db)):
    vids = db.query(Video).order_by(Video.views.desc()).limit(5).all()
    # Placeholder insights
    insights = {
        "drivers": ["Engaging hooks", "Clear thumbnails"],
        "patterns": ["8-10 minute length", "Actionable titles"],
        "suggestions": ["Try A/B testing titles", "Experiment with first 15s hook"],
    }
    return {
        "videos": [
            {"id": v.id, "title": v.title, "views": v.views, "likes": v.likes, "ctr": v.ctr}
            for v in vids
        ],
        "insights": insights,
    }


