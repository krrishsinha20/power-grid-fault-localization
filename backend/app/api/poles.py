from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.pole import Pole
from app.models.transformer import Transformer


router = APIRouter(
    prefix="/poles",
    tags=["Poles"]
)


@router.get("")
def list_poles(
    transformer_id: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):

    query = db.query(Pole)

    if transformer_id:

        transformer = (
            db.query(Transformer)
            .filter(Transformer.transformer_id == transformer_id)
            .first()
        )

        if transformer:
            query = query.filter(Pole.transformer_id == transformer.id)
        else:
            return []

    poles = query.limit(limit).all()

    return [
        {
            "pole_id": pole.pole_id,
            "parent_pole_id": (
                db.get(Pole, pole.parent_pole_id).pole_id
                if pole.parent_pole_id else None
            ),
            "transformer_id": pole.transformer.transformer_id,
            "latitude": pole.latitude,
            "longitude": pole.longitude,
            "pincode": pole.pincode,
            "energized": pole.energized,
            "active": pole.active,
        }
        for pole in poles
    ]