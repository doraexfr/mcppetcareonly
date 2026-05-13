"""
Integration test fixtures.

Requires the docker-compose stack to be running:
    cd mcp-server/docker && docker compose up -d

All fixtures are session-scoped: DB and S3 are seeded once,
cleaned up at the end of the session.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import AsyncGenerator, Generator

import asyncpg
import boto3
import httpx
import pytest
import pytest_asyncio
from botocore.exceptions import ClientError

# ── Connection parameters (override via env vars if needed) ──────────────────
BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8000")
PG_DSN = os.getenv(
    "TEST_PG_DSN",
    "postgresql://petcare-admin:supersecret@localhost:5432/petcare",
)
MINIO_ENDPOINT = os.getenv("TEST_MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("TEST_MINIO_ACCESS_KEY", "petcare")
MINIO_SECRET_KEY = os.getenv("TEST_MINIO_SECRET_KEY", "petcare123")
MINIO_BUCKET = os.getenv("TEST_MINIO_BUCKET", "petcare-private")
AUTH_PASSWORD = os.getenv("AUTH_DEMO_PASSWORD", "petcare-demo-password")

# ── Fixed test-data identifiers ───────────────────────────────────────────────
TEST_USER_ID = "test-user-integration-001"
TEST_PET_NAME = "IntegrationDog"
TEST_DOCUMENT_CUSTOM_NAME = "integration-vaccine-cert"
TEST_DOCUMENT_OBJECT_KEY = f"pets/integration/test-doc.txt"
TEST_DOCUMENT_CONTENT = b"Vaccine: Rabies\nDate: 2025-01-15\nVet: Dr. Ivanov"
TEST_CLINIC_NAME = "Integration Vet Clinic"
TEST_CLINIC_CITY = "Integrationville"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
    )


# ── DB seeding ────────────────────────────────────────────────────────────────

async def _seed_db() -> dict:
    """Insert all test rows; return their generated IDs."""
    conn = await asyncpg.connect(PG_DSN)
    try:
        # Ensure lookup rows exist
        animal_type_id = await conn.fetchval(
            """
            INSERT INTO animals_types (animal_name)
            VALUES ('Dog')
            ON CONFLICT (animal_name) DO UPDATE SET animal_name = EXCLUDED.animal_name
            RETURNING id
            """
        )
        animal_breed_id = await conn.fetchval(
            """
            INSERT INTO animals_breeds (animal_breed)
            VALUES ('Labrador')
            ON CONFLICT (animal_breed) DO UPDATE SET animal_breed = EXCLUDED.animal_breed
            RETURNING id
            """
        )
        doc_type_id = await conn.fetchval(
            """
            INSERT INTO documents_types (document_type)
            VALUES ('Vaccination')
            ON CONFLICT (document_type) DO UPDATE SET document_type = EXCLUDED.document_type
            RETURNING document_type_id
            """
        )

        # Pet
        pet_id = await conn.fetchval(
            """
            INSERT INTO pets_info
                (user_id, pet_name, animal_type_id, animal_breed_id,
                 pet_date_of_birth, pedigree, pet_weight, pet_is_sterylyzed)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING pet_id
            """,
            TEST_USER_ID, TEST_PET_NAME, animal_type_id, animal_breed_id,
            date(2020, 6, 15), "RKF-123456", 28.5, False,
        )

        # Document pointing at the S3 object we'll upload
        doc_id = await conn.fetchval(
            """
            INSERT INTO pet_documents
                (pet_id, custom_name, object_key, content_type,
                 size_bytes, document_type_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING document_id
            """,
            pet_id, TEST_DOCUMENT_CUSTOM_NAME, TEST_DOCUMENT_OBJECT_KEY,
            "text/plain", len(TEST_DOCUMENT_CONTENT), doc_type_id,
        )

        # Clinic — open 09:00-18:00, inside Moscow coords
        clinic_id = await conn.fetchval(
            """
            INSERT INTO vet_clinics
                (vet_name, vet_city, vet_streets, vet_building_number,
                 vet_lat, vet_lon, vet_working_hours, vet_is_24_7,
                 vet_phone, vet_website, vet_status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'active')
            RETURNING vet_id
            """,
            TEST_CLINIC_NAME, TEST_CLINIC_CITY,
            "Integration Street", "1",
            55.7558, 37.6176,  # Moscow-ish coordinates
            "09:00-18:00", False,
            "+7-999-000-00-01", "https://integration-vet.example.com",
        )

        return {
            "pet_id": pet_id,
            "doc_id": doc_id,
            "clinic_id": clinic_id,
        }
    finally:
        await conn.close()


async def _cleanup_db(ids: dict) -> None:
    conn = await asyncpg.connect(PG_DSN)
    try:
        await conn.execute("DELETE FROM pet_documents WHERE document_id = $1", ids["doc_id"])
        await conn.execute("DELETE FROM pets_info WHERE pet_id = $1", ids["pet_id"])
        await conn.execute("DELETE FROM vet_clinics WHERE vet_id = $1", ids["clinic_id"])
    finally:
        await conn.close()


# ── S3 seeding ────────────────────────────────────────────────────────────────

def _seed_s3() -> None:
    s3 = _make_s3_client()
    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=MINIO_BUCKET)
    # Upload test document
    s3.put_object(
        Bucket=MINIO_BUCKET,
        Key=TEST_DOCUMENT_OBJECT_KEY,
        Body=TEST_DOCUMENT_CONTENT,
        ContentType="text/plain",
    )


def _cleanup_s3() -> None:
    s3 = _make_s3_client()
    try:
        s3.delete_object(Bucket=MINIO_BUCKET, Key=TEST_DOCUMENT_OBJECT_KEY)
    except ClientError:
        pass


# ── Session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for all async session-scoped fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def seed_data() -> AsyncGenerator[dict, None]:
    """Seed DB and S3 once for the whole session; clean up afterwards."""
    _seed_s3()
    ids = await _seed_db()
    yield ids
    await _cleanup_db(ids)
    _cleanup_s3()


@pytest_asyncio.fixture(scope="session")
async def auth_token(seed_data) -> str:
    """Obtain a JWT from the running server (validates /auth/login end-to-end)."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        response = await client.post(
            "/auth/login",
            json={"user_id": TEST_USER_ID, "password": AUTH_PASSWORD},
        )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["data"]["access_token"]


@pytest_asyncio.fixture(scope="session")
async def client(auth_token) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Authenticated httpx client for the whole session."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    async with httpx.AsyncClient(
        base_url=BASE_URL, headers=headers, timeout=10
    ) as http_client:
        yield http_client
