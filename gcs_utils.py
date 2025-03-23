import os
import logging
from google.cloud import storage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_directory_from_gcs(gcs_directory, local_directory, bucket_name):
    """Download all files from a GCS directory to a local directory."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=gcs_directory)
        
        file_count = 0
        for blob in blobs:
            if not blob.name.endswith("/"):  # Avoid directory blobs
                relative_path = os.path.relpath(blob.name, gcs_directory)
                local_file_path = os.path.join(local_directory, relative_path)
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                blob.download_to_filename(local_file_path)
                file_count += 1
                logger.info(f"Downloaded {blob.name} to {local_file_path}")
        
        logger.info(f"Downloaded {file_count} files from GCS")
        return file_count
    except Exception as e:
        logger.error(f"Error downloading from GCS: {str(e)}")
        return 0

def upload_directory_to_gcs(local_directory, bucket_name, gcs_directory):
    """Upload all files in a local directory to a GCS directory."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        file_count = 0
        for root, _, files in os.walk(local_directory):
            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(local_file_path, local_directory)
                blob = bucket.blob(os.path.join(gcs_directory, relative_path))
                blob.upload_from_filename(local_file_path)
                file_count += 1
                logger.info(f"Uploaded {local_file_path} to gs://{bucket_name}/{gcs_directory}/{relative_path}")
        
        logger.info(f"Uploaded {file_count} files to GCS")
        return file_count
    except Exception as e:
        logger.error(f"Error uploading to GCS: {str(e)}")
        return 0