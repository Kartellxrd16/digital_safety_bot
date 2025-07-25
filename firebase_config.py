import os
import firebase_admin
from firebase_admin import credentials, firestore
import json # Import json module to parse string content

# Initialize Firebase Admin SDK
db = None # Initialize db as None
try:
    # --- Try to initialize from environment variable (preferred for cloud deployment) ---
    firebase_config_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_CONFIG")
    if firebase_config_json_str:
        try:
            cred_dict = json.loads(firebase_config_json_str)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase Admin SDK initialized successfully from environment variable (JSON string).")
        except json.JSONDecodeError as e:
            print(f"Error decoding Firebase service account JSON from FIREBASE_SERVICE_ACCOUNT_CONFIG: {e}")
            print("Falling back to file path method for Firebase initialization.")
            # Continue to the file path method below if decoding fails

    # --- Fallback: Initialize from a file path (for local or Render's Secret Files) ---
    if db is None: # Only try file path if not already initialized from JSON string
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
        if not cred_path:
            print("FIREBASE_SERVICE_ACCOUNT_KEY_PATH environment variable not set. Cannot initialize Firebase from file path.")
        else:
            if not os.path.isabs(cred_path):
                full_cred_path = os.path.join(os.path.dirname(__file__), cred_path)
            else:
                full_cred_path = cred_path

            if os.path.exists(full_cred_path):
                cred = credentials.Certificate(full_cred_path)
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("Firebase Admin SDK initialized successfully from file path.")
            else:
                print(f"Firebase service account file not found at: {full_cred_path}")
                print("Firebase Admin SDK initialization failed from file path.")

except Exception as e:
    print(f"Generic error initializing Firebase Admin SDK: {e}")
    db = None # Ensure db is None if any error occurs

# Check again if db is still None after all attempts
if db is None:
    print("Warning: Firestore DB client could not be initialized. Database operations will fail.")


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