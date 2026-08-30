from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import current_user_id
from app.database.connection import get_db
from app.repositories.database_repository import DatabaseRepository
from app.schemas.database import DatabaseCreate, DatabaseResponse
from app.services.database_service import DatabaseService

router = APIRouter(prefix="/databases", tags=["databases"])


def get_database_service(db: Session = Depends(get_db)) -> DatabaseService:
    return DatabaseService(DatabaseRepository(db))


@router.post("", response_model=DatabaseResponse)
def create_database(
    payload: DatabaseCreate,
    user_id: str = Depends(current_user_id),
    database_service: DatabaseService = Depends(get_database_service),
) -> DatabaseResponse:
    database = database_service.add(user_id, payload.name, payload.url)
    return DatabaseResponse(id=database.id, owner_id=database.owner_id, name=database.name, url=database.url)