from typing import List, Dict, Any, Optional
import logging

# It's assumed that backend_common.auth.db is initialized and available
# when these functions are called within the test environment.
# The setup_dev_environment fixture in conftest.py should ensure
# GOOGLE_APPLICATION_CREDENTIALS is set, allowing db to initialize correctly.
from backend_common.auth import db as firestore_db # Use an alias to avoid confusion if 'db' is used locally

logger = logging.getLogger(__name__)

async def seed_firestore_document(collection_path: str, document_id: str, data: Dict[str, Any]) -> None:
    """
    Creates or overwrites a document in Firestore.

    Args:
        collection_path: Path to the Firestore collection.
        document_id: ID of the document.
        data: Data to store in the document.
    """
    try:
        doc_ref = firestore_db.collection(collection_path).document(document_id)
        await doc_ref.set(data)
        logger.info(f"Successfully seeded document: {collection_path}/{document_id}")
    except Exception as e:
        logger.error(f"Error seeding document {collection_path}/{document_id}: {e}")
        # Depending on test needs, you might want to raise the exception
        # raise

async def get_firestore_document(collection_path: str, document_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a document from Firestore.

    Args:
        collection_path: Path to the Firestore collection.
        document_id: ID of the document.

    Returns:
        The document data as a dictionary if found, otherwise None.
    """
    try:
        doc_ref_snapshot = await firestore_db.collection(collection_path).document(document_id).get()
        if doc_ref_snapshot.exists:
            return doc_ref_snapshot.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error getting document {collection_path}/{document_id}: {e}")
        # raise
        return None

async def cleanup_firestore_document(collection_path: str, document_id: str) -> None:
    """
    Deletes a document from Firestore. Does not fail if the document doesn't exist.

    Args:
        collection_path: Path to the Firestore collection.
        document_id: ID of the document to delete.
    """
    try:
        await firestore_db.collection(collection_path).document(document_id).delete()
        logger.info(f"Successfully requested deletion for document: {collection_path}/{document_id} (if it existed)")
    except Exception as e:
        logger.error(f"Error deleting document {collection_path}/{document_id}: {e}")
        # raise

async def cleanup_firestore_documents(collection_path: str, document_ids: List[str]) -> None:
    """
    Deletes multiple documents from a Firestore collection.
    Firestore Admin SDK does not directly support batched deletes in the same way
    as client SDKs (e.g. for web/mobile) or batched writes.
    Iterative deletion is standard for admin operations unless using bulk writers for very large scale.

    Args:
        collection_path: Path to the Firestore collection.
        document_ids: List of IDs of the documents to delete.
    """
    # Firestore Admin SDK's `delete()` is idempotent. No need to check for existence.
    # For batched deletes with Admin SDK, one typically uses a BulkWriter for very large
    # numbers of operations. For typical test cleanup scenarios, iterating is fine.
    # If performance becomes an issue with many documents, a BulkWriter could be implemented.
    
    # As of firebase-admin SDK version used in backend_common.auth (firestore_async),
    # direct batched deletes like client SDKs (writeBatch.delete()) are not available on `db` (AsyncClient).
    # The `db` object is an AsyncClient for Firestore.
    # We will iterate and delete.
    
    deleted_count = 0
    errors_count = 0
    
    for doc_id in document_ids:
        try:
            await firestore_db.collection(collection_path).document(doc_id).delete()
            deleted_count +=1
        except Exception as e:
            errors_count +=1
            logger.error(f"Error deleting document {collection_path}/{doc_id}: {e}")
            # Decide if one error should stop all, or continue. For cleanup, usually continue.

    logger.info(f"Requested deletion for {deleted_count} documents from {collection_path}. Encountered {errors_count} errors.")


