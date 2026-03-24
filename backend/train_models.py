from __future__ import annotations

import json

from app.services.ai_foundation import ensure_ai_foundation
from app.db.session import SessionLocal
from app.services.bootstrap import initialize_database, seed_database_if_empty
from app.services.model_training import BOX_OFFICE_ARTIFACT, train_and_save_box_office_model


def main() -> None:
    initialize_database()
    with SessionLocal() as db:
        seed_database_if_empty(db)
        ensure_ai_foundation(db)
        artifact = train_and_save_box_office_model(db)

    print("Saved trained model artifact:")
    print(BOX_OFFICE_ARTIFACT)
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
