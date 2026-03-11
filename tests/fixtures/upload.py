import pytest
from typing import Optional

from app.v2.type_util.upload import (PrepareUploadRequest, CompleteUploadRequest, MultipartStartRequest,
                                     MultipartCompleteRequest, MultipartGetPartUrlRequest, MultipartAbortRequest,
                                     PartInfo)


@pytest.fixture
def make_prepare_upload_request(test_collection):
    """Factory fixture for creating PrepareUploadRequest objects."""
    def _make_prepare_upload_request(collection_name: str = test_collection["short_name"], file_name: str = "test_file",
                                     file_size_bytes: int = 1, checksum: str = "mock_checksum",
                                     collection_path: Optional[str] = None, content_type: str = "application/octet-stream"):
        return PrepareUploadRequest(collection_name=collection_name, 
                                    file_name=file_name,
                                    file_size_bytes=file_size_bytes,
                                    checksum=checksum,
                                    collection_path=collection_path,
                                    content_type=content_type)
    return _make_prepare_upload_request


@pytest.fixture
def make_multipart_start_request(test_collection):
    """Factory fixture for creating MultipartStartRequest objects."""
    def _make_multipart_start_request(collection_name: str = test_collection["short_name"], file_name: str = "test_file",
                                     final_file_size_bytes: int = 1, checksum: str = "mock_checksum",
                                     collection_path: Optional[str] = None, content_type: str = "application/octet-stream"):
        return MultipartStartRequest(collection_name=collection_name, 
                                    file_name=file_name,
                                    final_file_size_bytes=final_file_size_bytes,
                                    checksum=checksum,
                                    collection_path=collection_path,
                                    content_type=content_type)
    return _make_multipart_start_request


@pytest.fixture
def make_multipart_complete_request(test_collection):
    """Factory fixture for creating MulipartCompleteRequest objects."""
    def _make_multipart_complete_request(file_id, upload_id, parts, file_name="test_file", collection_name=test_collection["short_name"], collection_path=None, content_type="application/octet-stream", checksum="mock_checksum", final_file_size=1):
        return MultipartCompleteRequest(file_id=file_id, upload_id=upload_id, parts=parts, file_name=file_name, collection_name=collection_name, collection_path=collection_path, content_type=content_type, checksum=checksum, final_file_size=final_file_size)
    return _make_multipart_complete_request
