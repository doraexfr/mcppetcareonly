"""Юнит-тесты: PetsService + calculate_age."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.services.pets_service import PetsService, calculate_age
from tests.unit.conftest import (
    make_pet_details_row,
    make_pet_short_row,
    mock_pets_repo,
)


# ── calculate_age ─────────────────────────────────────────────────────────────

class TestCalculateAge:
    def test_birthday_today_is_zero(self):
        assert calculate_age(date.today()) == 0

    def test_born_five_years_ago(self):
        today = date.today()
        birth = date(today.year - 5, today.month, today.day)
        assert calculate_age(birth) == 5

    def test_birthday_tomorrow_is_one_less(self):
        """Если день рождения завтра — год ещё не наступил."""
        today = date.today()
        try:
            birth = date(today.year - 3, today.month, today.day + 1)
        except ValueError:
            # 31 декабря → завтра 1 января следующего года
            birth = date(today.year - 3 + 1, 1, 1)
        assert calculate_age(birth) == 2

    def test_none_returns_none(self):
        assert calculate_age(None) is None

    def test_year_2000(self):
        age = calculate_age(date(2000, 1, 1))
        assert age >= 25


# ── PetsService.get_pet_details ───────────────────────────────────────────────

class TestPetsServiceGetDetails:
    @pytest.mark.asyncio
    async def test_returns_mapped_fields(self):
        row = make_pet_details_row(pet_name="Rex", animal_breed="Husky", weight=30.0)
        service = PetsService(mock_pets_repo(details_row=row))

        result = await service.get_pet_details(pet_id=1, user_id="user-1")

        assert result["pet_name"] == "Rex"
        assert result["animal_breed"] == "Husky"
        assert result["pet_weight"] == 30.0
        assert isinstance(result["age"], int)

    @pytest.mark.asyncio
    async def test_age_calculated_from_birth_date(self):
        row = make_pet_details_row(birth_date=date(2020, 1, 1))
        service = PetsService(mock_pets_repo(details_row=row))

        result = await service.get_pet_details(pet_id=1, user_id="user-1")

        assert result["age"] >= 4

    @pytest.mark.asyncio
    async def test_none_birth_date_gives_none_age(self):
        row = make_pet_details_row()
        row["pet_date_of_birth"] = None
        service = PetsService(mock_pets_repo(details_row=row))

        result = await service.get_pet_details(pet_id=1, user_id="user-1")

        assert result["age"] is None

    @pytest.mark.asyncio
    async def test_pet_not_found_raises_not_found(self):
        """Питомца нет вообще — NotFoundError."""
        repo = mock_pets_repo(details_row=None, owner_id=None)
        service = PetsService(repo)

        with pytest.raises(NotFoundError):
            await service.get_pet_details(pet_id=999, user_id="user-1")

    @pytest.mark.asyncio
    async def test_pet_belongs_to_other_user_raises_forbidden(self):
        """Питомец есть, но владелец другой — ForbiddenError."""
        repo = mock_pets_repo(details_row=None, owner_id="other-user")
        service = PetsService(repo)

        with pytest.raises(ForbiddenError):
            await service.get_pet_details(pet_id=1, user_id="user-1")

    @pytest.mark.asyncio
    async def test_raw_db_fields_not_leaked(self):
        """В ответе нет сырых полей БД вроде user_id и pet_id."""
        row = make_pet_details_row()
        service = PetsService(mock_pets_repo(details_row=row))

        result = await service.get_pet_details(pet_id=1, user_id="user-1")

        assert "user_id" not in result
        assert "pet_id" not in result
        assert "pet_date_of_birth" not in result


# ── PetsService.get_pet_short_info ────────────────────────────────────────────

class TestPetsServiceGetShortInfo:
    @pytest.mark.asyncio
    async def test_returns_type_and_breed(self):
        row = make_pet_short_row(animal_type="Cat", animal_breed="Siamese")
        service = PetsService(mock_pets_repo(short_row=row))

        result = await service.get_pet_short_info(pet_id=1, user_id="user-1")

        assert result["animal_type"] == "Cat"
        assert result["animal_breed"] == "Siamese"

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        repo = mock_pets_repo(short_row=None, owner_id=None)
        service = PetsService(repo)

        with pytest.raises(NotFoundError):
            await service.get_pet_short_info(pet_id=999, user_id="user-1")

    @pytest.mark.asyncio
    async def test_calls_correct_repo_method(self):
        row = make_pet_short_row()
        repo = mock_pets_repo(short_row=row)
        service = PetsService(repo)

        await service.get_pet_short_info(pet_id=7, user_id="user-abc")

        repo.get_pet_short_info.assert_awaited_once_with(7, "user-abc")
