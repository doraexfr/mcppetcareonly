"""Юнит-тесты: ClinicsService, haversine_km, is_open_at."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.core.exceptions import NotFoundError
from app.services.clinics_service import ClinicsService, haversine_km, is_open_at
from tests.unit.conftest import make_clinic_row, mock_clinics_repo


# ── haversine_km ──────────────────────────────────────────────────────────────

class TestHaversineKm:
    def test_same_point_is_zero(self):
        assert haversine_km(55.7, 37.6, 55.7, 37.6) == pytest.approx(0.0, abs=1e-6)

    def test_moscow_to_spb_approx_634km(self):
        # Москва → Санкт-Петербург ≈ 634 км
        dist = haversine_km(55.7558, 37.6176, 59.9343, 30.3351)
        assert 620 < dist < 650

    def test_symmetry(self):
        d1 = haversine_km(55.7, 37.6, 48.8, 2.35)
        d2 = haversine_km(48.8, 2.35, 55.7, 37.6)
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_returns_float(self):
        result = haversine_km(0.0, 0.0, 1.0, 1.0)
        assert isinstance(result, float)


# ── is_open_at ────────────────────────────────────────────────────────────────

class TestIsOpenAt:
    def test_inside_hours(self):
        assert is_open_at("09:00-18:00", datetime(2026, 5, 8, 12, 0)) is True

    def test_before_opening(self):
        assert is_open_at("09:00-18:00", datetime(2026, 5, 8, 8, 59)) is False

    def test_after_closing(self):
        assert is_open_at("09:00-18:00", datetime(2026, 5, 8, 18, 1)) is False

    def test_exactly_at_open(self):
        assert is_open_at("09:00-18:00", datetime(2026, 5, 8, 9, 0)) is True

    def test_exactly_at_close(self):
        assert is_open_at("09:00-18:00", datetime(2026, 5, 8, 18, 0)) is True

    def test_overnight_open_after_midnight(self):
        # 22:00–06:00, проверяем 01:00 — должно быть открыто
        assert is_open_at("22:00-06:00", datetime(2026, 5, 8, 1, 0)) is True

    def test_overnight_closed_midday(self):
        assert is_open_at("22:00-06:00", datetime(2026, 5, 8, 12, 0)) is False

    def test_none_hours_is_closed(self):
        assert is_open_at(None, datetime(2026, 5, 8, 12, 0)) is False

    def test_empty_string_is_closed(self):
        assert is_open_at("", datetime(2026, 5, 8, 12, 0)) is False

    def test_multiple_intervals_comma_separated(self):
        # Обед-перерыв: 09:00-13:00, 14:00-18:00
        assert is_open_at("09:00-13:00,14:00-18:00", datetime(2026, 5, 8, 10, 0)) is True
        assert is_open_at("09:00-13:00,14:00-18:00", datetime(2026, 5, 8, 13, 30)) is False
        assert is_open_at("09:00-13:00,14:00-18:00", datetime(2026, 5, 8, 15, 0)) is True

    def test_multiple_intervals_semicolon_separated(self):
        assert is_open_at("09:00-13:00;14:00-18:00", datetime(2026, 5, 8, 16, 0)) is True


# ── ClinicsService.search_vet_clinics_by_city ─────────────────────────────────

class TestSearchByCity:
    @pytest.mark.asyncio
    async def test_returns_clinics_from_repo(self):
        clinics = [make_clinic_row(vet_city="Moscow"), make_clinic_row(vet_id=2, vet_city="Moscow")]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.search_vet_clinics_by_city("Moscow")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_empty_city_returns_empty(self):
        service = ClinicsService(mock_clinics_repo(clinics=[]))

        result = await service.search_vet_clinics_by_city("Nowhere")

        assert result == []

    @pytest.mark.asyncio
    async def test_passes_city_to_repo(self):
        repo = mock_clinics_repo(clinics=[])
        service = ClinicsService(repo)

        await service.search_vet_clinics_by_city("Kazan")

        repo.search_by_city.assert_awaited_once_with("Kazan")


# ── ClinicsService.search_vet_clinics_by_location ────────────────────────────

class TestSearchByLocation:
    @pytest.mark.asyncio
    async def test_clinic_inside_radius_included(self):
        # Клиника на тех же координатах — расстояние ~0 км
        clinics = [make_clinic_row(vet_lat=55.7558, vet_lon=37.6176)]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.search_vet_clinics_by_location(55.7558, 37.6176, radius_km=5.0)

        assert len(result) == 1
        assert result[0]["distance_km"] < 0.01

    @pytest.mark.asyncio
    async def test_clinic_outside_radius_excluded(self):
        # Клиника во Владивостоке — >6000 км от Москвы
        clinics = [make_clinic_row(vet_lat=43.1155, vet_lon=131.8855)]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.search_vet_clinics_by_location(55.7558, 37.6176, radius_km=100.0)

        assert result == []

    @pytest.mark.asyncio
    async def test_results_sorted_by_distance(self):
        clinics = [
            make_clinic_row(vet_id=1, vet_lat=55.800, vet_lon=37.600),  # ~5 км
            make_clinic_row(vet_id=2, vet_lat=55.756, vet_lon=37.618),  # ~0.1 км
            make_clinic_row(vet_id=3, vet_lat=55.830, vet_lon=37.550),  # ~8 км
        ]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.search_vet_clinics_by_location(55.7558, 37.6176, radius_km=50.0)

        distances = [r["distance_km"] for r in result]
        assert distances == sorted(distances)

    @pytest.mark.asyncio
    async def test_clinic_without_coords_skipped(self):
        clinics = [
            make_clinic_row(vet_id=1, vet_lat=55.7558, vet_lon=37.6176),
            {**make_clinic_row(vet_id=2), "vet_lat": None, "vet_lon": None},
        ]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.search_vet_clinics_by_location(55.7558, 37.6176, radius_km=50.0)

        assert all(r.get("vet_lat") is not None for r in result)


# ── ClinicsService.filter_available_vet_clinics ───────────────────────────────

class TestFilterAvailable:
    @pytest.mark.asyncio
    async def test_open_clinic_included(self):
        clinics = [make_clinic_row(working_hours="09:00-18:00")]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.filter_available_vet_clinics(
            current_datetime=datetime(2026, 5, 8, 12, 0),
            vet_city="Moscow",
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_closed_clinic_excluded(self):
        clinics = [make_clinic_row(working_hours="09:00-18:00")]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.filter_available_vet_clinics(
            current_datetime=datetime(2026, 5, 8, 23, 0),
            vet_city="Moscow",
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_24_7_clinic_always_included(self):
        clinics = [make_clinic_row(is_24_7=True, working_hours=None)]
        service = ClinicsService(mock_clinics_repo(clinics=clinics))

        result = await service.filter_available_vet_clinics(
            current_datetime=datetime(2026, 5, 8, 3, 0),  # глубокая ночь
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_location_filter_takes_priority_over_city(self):
        """Если переданы координаты — используется поиск по геолокации, не по городу."""
        repo = mock_clinics_repo(clinics=[])
        service = ClinicsService(repo)

        await service.filter_available_vet_clinics(
            current_datetime=datetime(2026, 5, 8, 12, 0),
            vet_city="Moscow",
            user_lat=55.7558,
            user_lon=37.6176,
            radius_km=5.0,
        )

        repo.list_active.assert_awaited_once()
        repo.search_by_city.assert_not_awaited()


# ── ClinicsService.get_vet_contacts_by_address ───────────────────────────────

class TestGetVetContacts:
    @pytest.mark.asyncio
    async def test_returns_phone_and_website(self):
        clinic = make_clinic_row(vet_phone="+7-999-111-22-33", vet_website="https://vet.ru")
        service = ClinicsService(mock_clinics_repo(single_clinic=clinic))

        result = await service.get_vet_contacts_by_address(vet_id=1)

        assert result == {"vet_phone": "+7-999-111-22-33", "vet_website": "https://vet.ru"}

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        service = ClinicsService(mock_clinics_repo(single_clinic=None))

        with pytest.raises(NotFoundError):
            await service.get_vet_contacts_by_address(vet_id=999)


# ── ClinicsService.get_vet_location_by_name ──────────────────────────────────

class TestGetVetLocation:
    @pytest.mark.asyncio
    async def test_returns_location_dict(self):
        clinic = make_clinic_row()
        service = ClinicsService(mock_clinics_repo(single_clinic=clinic))

        result = await service.get_vet_location_by_name("City Vet", "Moscow")

        assert result["vet_lat"] == pytest.approx(55.7558)

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        service = ClinicsService(mock_clinics_repo(single_clinic=None))

        with pytest.raises(NotFoundError):
            await service.get_vet_location_by_name("NoSuchClinic", "NoCity")
