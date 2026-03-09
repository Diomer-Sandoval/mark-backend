import json
import os

import firebase_admin
from firebase_admin import credentials, firestore


def _get_db():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if cred_json:
            cred = credentials.Certificate(json.loads(cred_json))
        else:
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
    return firestore.client()


def create_creation(creation_uuid: str, data: dict) -> None:
    db = _get_db()
    db.collection("creations").document(creation_uuid).set(data)


def create_generation(creation_uuid: str, generation_uuid: str, data: dict) -> None:
    db = _get_db()
    (
        db.collection("creations")
        .document(creation_uuid)
        .collection("generations")
        .document(generation_uuid)
        .set(data)
    )


def update_creation(creation_uuid: str, data: dict) -> None:
    db = _get_db()
    db.collection("creations").document(creation_uuid).update(data)
