import pytest

from utils import (
    create_welcome_purchase_message,
    create_redemption_message,
    create_monthly_summary_message,
    create_milestone_reward_message,
    create_promotional_message,
)


class TestCreateWelcomePurchaseMessage:
    def test_contains_first_name(self):
        msg = create_welcome_purchase_message("João Silva", 500.0, 14, 30, 0)
        assert "João" in msg
        assert "Silva" not in msg

    def test_single_name(self):
        msg = create_welcome_purchase_message("Ana", 100.0, 3, 10, 0)
        assert "Ana" in msg

    def test_empty_name_falls_back_to_parceiro(self):
        msg = create_welcome_purchase_message("", 100.0, 3, 3, 0)
        assert "Parceiro" in msg

    def test_points_earned_shown(self):
        msg = create_welcome_purchase_message("Maria", 380.0, 10, 10, 0)
        assert "+10" in msg or "10" in msg

    def test_current_points_shown(self):
        msg = create_welcome_purchase_message("Carlos", 380.0, 5, 25, 0)
        assert "25" in msg

    def test_with_client_link_includes_url(self):
        msg = create_welcome_purchase_message(
            "Daniela", 100.0, 3, 3, 0, "http://localhost:8501/?view=cliente&id=1"
        )
        assert "http://localhost:8501" in msg

    def test_without_client_link_no_url(self):
        msg = create_welcome_purchase_message("Eduardo", 100.0, 3, 3, 0, "")
        assert "http" not in msg

    def test_returns_string(self):
        msg = create_welcome_purchase_message("Felipe", 500.0, 10, 10, 0)
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestCreateRedemptionMessage:
    def test_singular_package_word(self):
        msg = create_redemption_message("Ana Paula", 1, 10, 40)
        assert "pacote" in msg
        # exactly singular, not plural
        assert msg.count("pacotes") == 0

    def test_plural_packages_word(self):
        msg = create_redemption_message("Bruno", 3, 30, 20)
        assert "pacotes" in msg

    def test_first_name_only(self):
        msg = create_redemption_message("João Pedro Souza", 1, 10, 30)
        assert "João" in msg
        assert "Pedro" not in msg

    def test_points_deducted_shown(self):
        msg = create_redemption_message("Carla", 2, 20, 30)
        assert "20" in msg

    def test_remaining_points_shown(self):
        msg = create_redemption_message("Daniela", 1, 10, 75)
        assert "75" in msg

    def test_package_count_shown(self):
        msg = create_redemption_message("Eduardo", 5, 50, 100)
        assert "5" in msg

    def test_returns_string(self):
        msg = create_redemption_message("Felipe", 1, 10, 0)
        assert isinstance(msg, str)


class TestCreateMonthlySummaryMessage:
    def test_contains_first_name(self):
        msg = create_monthly_summary_message("Gabriela Lima", 760.0, 20)
        assert "Gabriela" in msg
        assert "Lima" not in msg

    def test_contains_points(self):
        msg = create_monthly_summary_message("Henrique", 380.0, 10)
        assert "10" in msg

    def test_currency_formatted_brl(self):
        msg = create_monthly_summary_message("Isabela", 1234.56, 32)
        assert "R$" in msg

    def test_zero_spent(self):
        msg = create_monthly_summary_message("João", 0.0, 0)
        assert "R$ 0,00" in msg

    def test_returns_string(self):
        msg = create_monthly_summary_message("Karen", 100.0, 3)
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestCreateMilestoneRewardMessage:
    def test_contains_first_name(self):
        msg = create_milestone_reward_message("Gabriela Ferreira")
        assert "Gabriela" in msg
        assert "Ferreira" not in msg

    def test_contains_default_reward(self):
        msg = create_milestone_reward_message("Henrique")
        assert "Cafeteira" in msg

    def test_empty_name_falls_back_to_parceiro(self):
        msg = create_milestone_reward_message("")
        assert "Parceiro" in msg

    def test_custom_reward_shown(self):
        msg = create_milestone_reward_message("Isabela", "Voucher R$200")
        assert "Voucher" in msg

    def test_500_pontos_mentioned(self):
        msg = create_milestone_reward_message("Laura")
        assert "500" in msg

    def test_returns_string(self):
        msg = create_milestone_reward_message("Marcos")
        assert isinstance(msg, str)


class TestCreatePromotionalMessage:
    def test_returns_non_empty_string(self):
        msg = create_promotional_message()
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_mentions_program_or_brand(self):
        msg = create_promotional_message()
        assert "Isopor" in msg or "IsoSoluções" in msg

    def test_consistent_output(self):
        assert create_promotional_message() == create_promotional_message()
