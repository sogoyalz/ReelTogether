"""Explicit offline experiment; refuses insufficient or synthetic training data."""
import json
from app.db.session import SessionLocal
from app.services.model_training import train_and_save_box_office_model

if __name__ == "__main__":
    try:
        with SessionLocal() as db:
            artifact = train_and_save_box_office_model(db)
        print(json.dumps(artifact, indent=2))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
