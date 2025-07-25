import os
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
try:
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    if not cred_path:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY_PATH environment variable not set.")

    # Ensure the path is absolute or relative to the script's directory
    full_cred_path = os.path.join(os.path.dirname(__file__), cred_path)

    cred = credentials.Certificate(full_cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    db = None # Set db to None if initialization fails, so main can check

def get_content(collection_name: str, document_id: str):
    """Fetches a document from a specified Firestore collection (synchronous)."""
    if db is None:
        print("Firestore DB is not initialized. Cannot fetch content.")
        return None, None

    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get() # Synchronous call
        if doc.exists:
            return doc_ref, doc.to_dict()
        else:
            print(f"Document {document_id} not found in collection {collection_name}.")
            return doc_ref, None
    except Exception as e:
        print(f"Error fetching document {document_id} from {collection_name}: {e}")
        return None, None