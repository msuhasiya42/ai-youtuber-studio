"""
Unified storage client supporting both AWS S3 and MinIO.
Automatically switches based on STORAGE_TYPE environment variable.
"""
import os
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
from typing import Optional


class StorageClient:
    """
    Unified client for object storage supporting both AWS S3 and MinIO.

    Environment Variables:
        STORAGE_TYPE: 's3', 'aws', or 'minio' (default: 's3')

        For AWS S3:
            AWS_ACCESS_KEY_ID: AWS access key
            AWS_SECRET_ACCESS_KEY: AWS secret key
            AWS_S3_BUCKET: Bucket name
            AWS_REGION: AWS region (default: 'us-east-1')

        For MinIO:
            MINIO_ENDPOINT: MinIO endpoint (default: 'localhost:9000')
            MINIO_ACCESS_KEY: MinIO access key (default: 'minioadmin')
            MINIO_SECRET_KEY: MinIO secret key (default: 'minioadmin')
            MINIO_BUCKET: Bucket name (default: 'youtube-data')
            MINIO_SECURE: Use HTTPS (default: 'false')
    """

    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "s3").lower()

        if self.storage_type in ("s3", "aws"):
            self._init_aws_s3()
        elif self.storage_type == "minio":
            self._init_minio()
        else:
            raise ValueError(f"Invalid STORAGE_TYPE: {self.storage_type}. Use 's3', 'aws', or 'minio'")

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _init_aws_s3(self):
        """Initialize AWS S3 client"""
        self.bucket_name = os.getenv("AWS_S3_BUCKET")
        if not self.bucket_name:
            raise ValueError("AWS_S3_BUCKET environment variable is required for S3 storage")

        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Create S3 client using boto3
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=self.region
        )

        print(f"✓ Initialized AWS S3 client (bucket: {self.bucket_name}, region: {self.region})")

    def _init_minio(self):
        """Initialize MinIO client using boto3"""
        self.bucket_name = os.getenv("MINIO_BUCKET", "youtube-data")
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.region = "us-east-1"  # MinIO doesn't use regions, but boto3 requires it

        # Create boto3 client configured for MinIO
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f"{'https' if secure else 'http'}://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region,
            config=boto3.session.Config(signature_version='s3v4')
        )

        print(f"✓ Initialized MinIO client (bucket: {self.bucket_name}, endpoint: {endpoint})")

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"✓ Bucket exists: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.storage_type in ("s3", "aws") and self.region != "us-east-1":
                        # AWS S3 requires LocationConstraint for regions other than us-east-1
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    else:
                        # us-east-1 or MinIO
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    print(f"✓ Created bucket: {self.bucket_name}")
                except ClientError as create_error:
                    print(f"✗ Error creating bucket: {create_error}")
                    raise
            elif error_code == '403':
                # Bucket exists but we don't have permission
                print(f"⚠ Bucket exists but access denied: {self.bucket_name}")
            else:
                print(f"✗ Error checking bucket: {e}")
                raise

    def upload_file(self, file_path: str, object_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Upload a file to storage.

        Args:
            file_path: Local file path to upload
            object_name: Object name in bucket (S3 key)
            content_type: MIME type of the file

        Returns:
            S3 key of the uploaded file
        """
        try:
            extra_args = {'ContentType': content_type}
            self.s3_client.upload_file(file_path, self.bucket_name, object_name, ExtraArgs=extra_args)
            print(f"✓ Uploaded {file_path} → s3://{self.bucket_name}/{object_name}")
            return object_name
        except ClientError as e:
            print(f"✗ Error uploading file: {e}")
            raise

    def upload_bytes(self, data: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
        """
        Upload bytes data to storage.

        Args:
            data: Bytes data to upload
            object_name: Object name in bucket (S3 key)
            content_type: MIME type of the data

        Returns:
            S3 key of the uploaded data
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=data,
                ContentType=content_type
            )
            print(f"✓ Uploaded {len(data)} bytes → s3://{self.bucket_name}/{object_name}")
            return object_name
        except ClientError as e:
            print(f"✗ Error uploading bytes: {e}")
            raise

    def download_file(self, object_name: str, file_path: str) -> str:
        """
        Download a file from storage.

        Args:
            object_name: Object name in bucket (S3 key)
            file_path: Local file path to save to

        Returns:
            Local file path
        """
        try:
            self.s3_client.download_file(self.bucket_name, object_name, file_path)
            print(f"✓ Downloaded s3://{self.bucket_name}/{object_name} → {file_path}")
            return file_path
        except ClientError as e:
            print(f"✗ Error downloading file: {e}")
            raise

    def get_object(self, object_name: str) -> bytes:
        """
        Get object data as bytes.

        Args:
            object_name: Object name in bucket (S3 key)

        Returns:
            Object data as bytes
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_name)
            data = response['Body'].read()
            print(f"✓ Retrieved {len(data)} bytes from s3://{self.bucket_name}/{object_name}")
            return data
        except ClientError as e:
            print(f"✗ Error getting object: {e}")
            raise

    def delete_object(self, object_name: str):
        """Delete an object from storage"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            print(f"✓ Deleted s3://{self.bucket_name}/{object_name}")
        except ClientError as e:
            print(f"✗ Error deleting object: {e}")
            raise

    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access to an object.

        Args:
            object_name: Object name in bucket (S3 key)
            expires_seconds: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expires_seconds
            )
            print(f"✓ Generated presigned URL for {object_name} (expires in {expires_seconds}s)")
            return url
        except ClientError as e:
            print(f"✗ Error generating presigned URL: {e}")
            raise

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        List objects in the bucket.

        Args:
            prefix: Filter by prefix (e.g., 'audio/' for all audio files)
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            objects = [obj['Key'] for obj in response['Contents']]
            print(f"✓ Listed {len(objects)} objects with prefix '{prefix}'")
            return objects
        except ClientError as e:
            print(f"✗ Error listing objects: {e}")
            raise


# Singleton instance
_storage_client = None


def get_storage_client() -> StorageClient:
    """Get or create storage client singleton"""
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
