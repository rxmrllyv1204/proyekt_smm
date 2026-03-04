
import database
from sqlalchemy.orm import Session

def migrate_ids():
    db = database.SessionLocal()
    try:
        users = db.query(database.User).order_by(database.User.id.desc()).all()
        for user in users:
            if user.id < 10000:
                old_id = user.id
                new_id = 10000 + old_id
                
                # Update foreign keys first
                db.query(database.Order).filter(database.Order.user_id == old_id).update({"user_id": new_id})
                db.query(database.PaymentRequest).filter(database.PaymentRequest.user_id == old_id).update({"user_id": new_id})
                
                # Update user ID
                # Since we are changing PK, it's a bit tricky with some ORMs, but SQLite allows it.
                user.id = new_id
                print(f"Migrated User {old_id} -> {new_id}")
        
        db.commit()
        print("Migration complete.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_ids()
