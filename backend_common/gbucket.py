import time
import logging
from google.cloud import storage
from google.oauth2 import service_account


logger = logging.getLogger(__name__)


def get_google_cloud_bucket_conn(bucket_name: str, cred_path: str):
    """Setup Google Cloud Storage client"""
    credentials = service_account.Credentials.from_service_account_file(cred_path)
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    return bucket


def upload_file_to_google_cloud_bucket(file, bucket_name, bucket_path, cred_path):
    """Upload file to google bucket"""
    bucket = get_google_cloud_bucket_conn(bucket_name, cred_path)
    blob = bucket.blob(f"{bucket_path}/{time.time()}-{file.filename}")
    blob.upload_from_file(file.file, content_type=file.content_type)
    # blob.make_public()
    return blob.public_url


def upload_file_to_google_cloud_bucket(file, bucket_name, bucket_path, cred_path):
    """Upload file to google bucket"""
    bucket = get_google_cloud_bucket_conn(bucket_name, cred_path)
    blob = bucket.blob(f"{bucket_path}/{time.time()}-{file.filename}")
    blob.upload_from_file(file.file, content_type=file.content_type)
    # blob.make_public()
    return blob.public_url


def delete_file_from_google_cloud_bucket(
    file_path: str, bucket_name: str, cred_path: str
):
    """Delete a file from a Google Cloud Storage bucket"""
    try:
        # Get the bucket connection
        bucket = get_google_cloud_bucket_conn(bucket_name, cred_path)
        blob = bucket.blob(file_path)
        blob.delete()

        return f"File {file_path} deleted successfully from bucket {bucket_name}."

    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise e
