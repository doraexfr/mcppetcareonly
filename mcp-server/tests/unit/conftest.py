import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date

@pytest.fixture
def mock_pet_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value={
        "pet_id": "p_123",
        "pet_name": "Barsik",
        "pet_date_of_birth": date(2020, 5, 15),
        "pet_weight": 4.5
    })
    repo.list_by_owner = AsyncMock(return_value=[
        {"pet_id": "p_123", "pet_name": "Barsik"},
        {"pet_id": "p_456", "pet_name": "Sharik"}
    ])
    return repo

@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    client.upload_file = AsyncMock(return_value={
        "url": "https://s3.mock/petcare/test-doc.pdf"
    })
    client.delete_object = AsyncMock(return_value=None)
    return client

@pytest.fixture
def mock_clinic_repo():
    repo = MagicMock()
    repo.find_nearby = AsyncMock(return_value=[
        {
            "vet_id": "c_001",
            "vet_name": "Test Vet Clinic",
            "vet_working_hours": "09:00-18:00",
            "vet_lat": 55.7558,
            "vet_lon": 37.6173
        }
    ])
    return repo
