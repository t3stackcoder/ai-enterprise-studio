"""
MinIO integration tests using CQRS

Tests MinIO S3-compatible storage through CQRS mediator.
Validates file upload, download, and bucket operations.
"""

import os
import sys
from pathlib import Path

# Add libs to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "libs"))

import io
from dataclasses import dataclass
from uuid import uuid4

import pytest
from buildingblocks.cqrs import ICommand, ICommandHandler, IQuery, IQueryHandler


# ============================================================================
# Commands
# ============================================================================


@dataclass
class UploadFileCommand(ICommand):
    """Upload a file to MinIO bucket"""

    bucket_name: str
    object_name: str
    data: bytes
    content_type: str = "application/octet-stream"


@dataclass
class DeleteFileCommand(ICommand):
    """Delete a file from MinIO bucket"""

    bucket_name: str
    object_name: str


# ============================================================================
# Queries
# ============================================================================


@dataclass
class DownloadFileQuery(IQuery[bytes]):
    """Download a file from MinIO bucket"""

    bucket_name: str
    object_name: str


@dataclass
class ListFilesQuery(IQuery[list[str]]):
    """List files in MinIO bucket"""

    bucket_name: str
    prefix: str = ""


# ============================================================================
# Handlers
# ============================================================================


class UploadFileHandler(ICommandHandler):
    """Handler for uploading files to MinIO"""

    def __init__(self, minio_client):
        self.minio = minio_client

    async def handle(self, command: UploadFileCommand) -> None:
        data_stream = io.BytesIO(command.data)
        self.minio.put_object(
            bucket_name=command.bucket_name,
            object_name=command.object_name,
            data=data_stream,
            length=len(command.data),
            content_type=command.content_type,
        )


class DeleteFileHandler(ICommandHandler):
    """Handler for deleting files from MinIO"""

    def __init__(self, minio_client):
        self.minio = minio_client

    async def handle(self, command: DeleteFileCommand) -> None:
        self.minio.remove_object(
            bucket_name=command.bucket_name, object_name=command.object_name
        )


class DownloadFileHandler(IQueryHandler):
    """Handler for downloading files from MinIO"""

    def __init__(self, minio_client):
        self.minio = minio_client

    async def handle(self, query: DownloadFileQuery) -> bytes:
        response = self.minio.get_object(
            bucket_name=query.bucket_name, object_name=query.object_name
        )
        data = response.read()
        response.close()
        response.release_conn()
        return data


class ListFilesHandler(IQueryHandler):
    """Handler for listing files in MinIO bucket"""

    def __init__(self, minio_client):
        self.minio = minio_client

    async def handle(self, query: ListFilesQuery) -> list[str]:
        objects = self.minio.list_objects(
            bucket_name=query.bucket_name, prefix=query.prefix, recursive=True
        )
        return [obj.object_name for obj in objects]


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.minio
@pytest.mark.asyncio
async def test_upload_and_download_file(minio_clean, mediator):
    """
    Test uploading and downloading a file to/from MinIO via CQRS.
    
    Flow:
    1. Upload file to test bucket
    2. Download the same file
    3. Verify content matches
    """
    # Register handlers
    mediator.register_command_handler(UploadFileCommand, UploadFileHandler(minio_clean))
    mediator.register_query_handler(DownloadFileQuery, DownloadFileHandler(minio_clean))

    # Upload file
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    object_name = f"test/{uuid4().hex[:8]}/test_file.txt"
    test_data = b"Hello from MinIO integration test!"

    await mediator.send_command(
        UploadFileCommand(
            bucket_name=test_bucket,
            object_name=object_name,
            data=test_data,
            content_type="text/plain",
        )
    )

    # Download file
    downloaded_data = await mediator.send_query(
        DownloadFileQuery(bucket_name=test_bucket, object_name=object_name)
    )

    # Verify
    assert downloaded_data == test_data
    print(f"✅ Uploaded and downloaded file from MinIO: {object_name}")


@pytest.mark.integration
@pytest.mark.minio
@pytest.mark.asyncio
async def test_list_files_in_bucket(minio_clean, mediator):
    """
    Test listing files in a MinIO bucket via CQRS.
    """
    # Register handlers
    mediator.register_command_handler(UploadFileCommand, UploadFileHandler(minio_clean))
    mediator.register_query_handler(ListFilesQuery, ListFilesHandler(minio_clean))

    # Upload multiple files
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    test_prefix = f"test_list/{uuid4().hex[:8]}"

    file_names = ["file1.txt", "file2.txt", "file3.txt"]
    for file_name in file_names:
        object_name = f"{test_prefix}/{file_name}"
        await mediator.send_command(
            UploadFileCommand(
                bucket_name=test_bucket,
                object_name=object_name,
                data=b"test content",
            )
        )

    # List files
    files = await mediator.send_query(
        ListFilesQuery(bucket_name=test_bucket, prefix=test_prefix)
    )

    # Verify all files are listed
    assert len(files) == 3
    for file_name in file_names:
        assert any(file_name in f for f in files)

    print(f"✅ Listed {len(files)} files from MinIO bucket with prefix: {test_prefix}")


@pytest.mark.integration
@pytest.mark.minio
@pytest.mark.asyncio
async def test_delete_file(minio_clean, mediator):
    """
    Test deleting a file from MinIO via CQRS.
    """
    # Register handlers
    mediator.register_command_handler(UploadFileCommand, UploadFileHandler(minio_clean))
    mediator.register_command_handler(DeleteFileCommand, DeleteFileHandler(minio_clean))
    mediator.register_query_handler(ListFilesQuery, ListFilesHandler(minio_clean))

    # Upload file
    test_bucket = os.getenv("MINIO_TEST_BUCKET", "test-artifacts")
    object_name = f"test_delete/{uuid4().hex[:8]}/file_to_delete.txt"

    await mediator.send_command(
        UploadFileCommand(
            bucket_name=test_bucket, object_name=object_name, data=b"delete me"
        )
    )

    # Verify file exists
    files = await mediator.send_query(
        ListFilesQuery(bucket_name=test_bucket, prefix="test_delete")
    )
    assert any(object_name in f for f in files)

    # Delete file
    await mediator.send_command(
        DeleteFileCommand(bucket_name=test_bucket, object_name=object_name)
    )

    # Verify file is gone
    files = await mediator.send_query(
        ListFilesQuery(bucket_name=test_bucket, prefix="test_delete")
    )
    assert not any(object_name in f for f in files)

    print(f"✅ Deleted file from MinIO: {object_name}")
