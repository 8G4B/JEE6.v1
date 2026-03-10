import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def gambling_service():
    with patch("src.repositories.UserBalanceRepository.UserBalanceRepository"), \
         patch("src.repositories.JackpotRepository.JackpotRepository"), \
         patch("src.repositories.CooldownRepository.CooldownRepository"):
        from src.services.GamblingService import GamblingService
        GamblingService._instance = None
        service = GamblingService()
        service.user_balance_repo = MagicMock()
        service.jackpot_repo = MagicMock()
        service.cooldown_repo = MagicMock()
        yield service
        GamblingService._instance = None


class TestValidateBet:
    def test_none_bet_returns_error(self, gambling_service):
        result = gambling_service.validate_bet(None)
        assert result is not None

    def test_below_min_bet_returns_error(self, gambling_service):
        result = gambling_service.validate_bet(1)
        assert result is not None

    def test_valid_bet_returns_none(self, gambling_service):
        result = gambling_service.validate_bet(1000)
        assert result is None

    def test_above_max_bet_returns_error(self, gambling_service):
        result = gambling_service.validate_bet(999_999_999_999_999)
        assert result is not None


class TestCalculateTax:
    def test_income_tax_zero_for_small_amount(self, gambling_service):
        tax = gambling_service.calculate_income_tax(0)
        assert tax == 0

    def test_securities_tax_minimum_rate(self, gambling_service):
        tax = gambling_service.calculate_securities_transaction_tax(1_000_000)
        assert tax == int(1_000_000 * 0.005)

    def test_gift_tax_minimum_rate(self, gambling_service):
        tax = gambling_service.calculate_gift_tax(1_000_000)
        assert tax == int(1_000_000 * 0.05)

    def test_calculate_tax_routes_to_securities(self, gambling_service):
        for game in ["coin", "dice", "blackjack", "baccarat", "indian_poker"]:
            tax = gambling_service.calculate_tax(1_000_000, tax_type=game)
            expected = gambling_service.calculate_securities_transaction_tax(1_000_000)
            assert tax == expected, f"{game} tax mismatch"

    def test_calculate_tax_routes_to_gift(self, gambling_service):
        tax = gambling_service.calculate_tax(1_000_000, tax_type="gift")
        expected = gambling_service.calculate_gift_tax(1_000_000)
        assert tax == expected

    def test_calculate_tax_default_income(self, gambling_service):
        tax = gambling_service.calculate_tax(1_000_000, tax_type="income")
        expected = gambling_service.calculate_income_tax(1_000_000)
        assert tax == expected


class TestCalculateHandValue:
    def test_number_cards(self, gambling_service):
        assert gambling_service.calculate_hand_value(["2", "3"]) == 5

    def test_face_cards_worth_ten(self, gambling_service):
        assert gambling_service.calculate_hand_value(["J", "Q", "K"]) == 30

    def test_ace_as_eleven(self, gambling_service):
        assert gambling_service.calculate_hand_value(["A", "9"]) == 20

    def test_ace_reduces_to_one_when_bust(self, gambling_service):
        assert gambling_service.calculate_hand_value(["A", "K", "5"]) == 16

    def test_blackjack_hand(self, gambling_service):
        assert gambling_service.calculate_hand_value(["A", "K"]) == 21


class TestCalculateBaccaratValue:
    def test_baccarat_mod_ten(self, gambling_service):
        assert gambling_service.calculate_baccarat_value(["7", "8"]) == 5  # 15 % 10

    def test_face_cards_worth_zero(self, gambling_service):
        assert gambling_service.calculate_baccarat_value(["J", "Q"]) == 0

    def test_ace_worth_one(self, gambling_service):
        assert gambling_service.calculate_baccarat_value(["A", "9"]) == 0  # 10 % 10
