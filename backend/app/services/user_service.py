from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.models import User
from app.schemas import schemas

class UserService:
    @staticmethod
    def create_user(db: Session, user: schemas.UserCreate) -> User:
        db_user = User(**user.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_name(db: Session, name: str) -> Optional[User]:
        return db.query(User).filter(User.name == name).first()
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_data: schemas.UserBase) -> Optional[User]:
        db_user = UserService.get_user(db, user_id)
        if db_user:
            for key, value in user_data.model_dump().items():
                setattr(db_user, key, value)
            db.commit()
            db.refresh(db_user)
        return db_user
    
    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        db_user = UserService.get_user(db, user_id)
        if db_user:
            db.delete(db_user)
            db.commit()
            return True
        return False 