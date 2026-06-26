import pytest
from datetime import date

import database
from database import (
    init_db,
    init_settings,
    add_client,
    register_purchase,
    get_client_by_id,
    get_all_clients_enriched,
    search_clients,
    get_client_history,
    get_dashboard_kpis,
    get_monthly_purchase_history,
    get_top_clients_by_points,
    claim_milestone_reward,
    get_setting,
    set_setting,
    get_program_rules,
    add_bulletin_update,
    get_bulletin_updates,
    update_bulletin_update,
    delete_bulletin_update,
    reset_client_data,
)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets its own isolated in-file SQLite database."""
    path = tmp_path / "test_isopor.db"
    monkeypatch.setattr(database, "DB_PATH", path)
    init_db()
    init_settings()


# ─────────────────────────── CLIENT CRUD ───────────────────────────

class TestAddClient:
    def test_returns_positive_id(self):
        cid = add_client("Ana Paula", "11987654321")
        assert cid > 0

    def test_sequential_ids_are_unique(self):
        id1 = add_client("Ana", "11111111111")
        id2 = add_client("Bruno", "22222222222")
        assert id1 != id2

    def test_duplicate_phone_raises(self):
        add_client("Ana", "11111111111")
        with pytest.raises(Exception):
            add_client("Outro Nome", "11111111111")

    def test_name_is_stripped(self):
        cid = add_client("  Carlos  ", "33333333333")
        client = get_client_by_id(cid)
        assert client["name"] == "Carlos"

    def test_phone_is_stripped(self):
        cid = add_client("Daniela", "  44444444444  ")
        client = get_client_by_id(cid)
        assert client["phone"] == "44444444444"


class TestGetClientById:
    def test_existing_client_returned(self):
        cid = add_client("Eduardo", "55555555555")
        client = get_client_by_id(cid)
        assert client is not None
        assert client["name"] == "Eduardo"
        assert client["id"] == cid

    def test_nonexistent_returns_none(self):
        assert get_client_by_id(99999) is None

    def test_new_client_has_zero_points(self):
        cid = add_client("Felipe", "66666666666")
        client = get_client_by_id(cid)
        assert client["current_points"] == 0

    def test_new_client_has_zero_spent(self):
        cid = add_client("Gabriela", "77777777777")
        client = get_client_by_id(cid)
        assert client["total_spent"] == 0.0

    def test_new_client_has_zero_packages_bought(self):
        cid = add_client("Henrique", "88888888888")
        client = get_client_by_id(cid)
        assert client["total_packages_bought"] == 0

    def test_new_client_has_no_milestone(self):
        cid = add_client("Isabela", "99999999999")
        client = get_client_by_id(cid)
        assert client["has_milestone_500"] is False


class TestSearchClients:
    def test_search_by_full_name(self):
        add_client("Fernanda Lima", "10000000001")
        results = search_clients("Fernanda Lima")
        assert len(results) == 1

    def test_search_by_partial_name(self):
        add_client("João Pedro Souza", "10000000002")
        results = search_clients("Pedro")
        assert len(results) == 1

    def test_search_by_phone_fragment(self):
        add_client("Karen", "10000000003")
        results = search_clients("10000000003")
        assert len(results) >= 1

    def test_search_case_insensitive(self):
        add_client("Laura", "10000000004")
        assert len(search_clients("laura")) == 1
        assert len(search_clients("LAURA")) == 1

    def test_no_match_returns_empty(self):
        assert search_clients("xyzxyzxyz_não_existe") == []

    def test_multiple_matches(self):
        add_client("Marcos Silva", "10000000005")
        add_client("Maria Silva", "10000000006")
        results = search_clients("Silva")
        assert len(results) == 2


class TestGetAllClientsEnriched:
    def test_empty_db_returns_empty_list(self):
        assert get_all_clients_enriched() == []

    def test_returns_all_clients(self):
        add_client("Alice", "20000000001")
        add_client("Bob", "20000000002")
        assert len(get_all_clients_enriched()) == 2

    def test_sorted_alphabetically_by_name(self):
        add_client("Zé", "20000000009")
        add_client("Ana", "20000000010")
        clients = get_all_clients_enriched()
        assert clients[0]["name"] == "Ana"
        assert clients[1]["name"] == "Zé"

    def test_enriched_with_stats_fields(self):
        add_client("Nathalia", "20000000011")
        client = get_all_clients_enriched()[0]
        for field in ("current_points", "total_spent", "total_packages_bought", "has_milestone_500"):
            assert field in client


# ─────────────────────────── PURCHASES ───────────────────────────

class TestRegisterPurchase:
    def test_one_package_equals_one_point(self):
        cid = add_client("Otávio", "30000000001")
        result = register_purchase(cid, 38.0, package_quantity=1)
        assert result["final_points"] == 1

    def test_ten_packages_equals_ten_points(self):
        cid = add_client("Paula", "30000000002")
        result = register_purchase(cid, 380.0, package_quantity=10)
        assert result["final_points"] == 10
        assert result["package_quantity"] == 10

    def test_zero_packages_yields_zero_points(self):
        cid = add_client("Roberto", "30000000003")
        result = register_purchase(cid, 380.0, package_quantity=0)
        assert result["final_points"] == 0

    def test_negative_quantity_treated_as_zero(self):
        cid = add_client("Sofia", "30000000004")
        result = register_purchase(cid, 100.0, package_quantity=-5)
        assert result["package_quantity"] == 0
        assert result["final_points"] == 0

    def test_points_accumulate_across_purchases(self):
        cid = add_client("Tiago", "30000000005")
        register_purchase(cid, 380.0, package_quantity=10)
        register_purchase(cid, 760.0, package_quantity=20)
        client = get_client_by_id(cid)
        assert client["current_points"] == 30
        assert client["total_packages_bought"] == 30

    def test_total_spent_accumulates(self):
        cid = add_client("Ursula", "30000000006")
        register_purchase(cid, 500.0, package_quantity=5)
        register_purchase(cid, 300.0, package_quantity=3)
        client = get_client_by_id(cid)
        assert client["total_spent"] == 800.0

    def test_amount_recorded_correctly(self):
        cid = add_client("Vera", "30000000007")
        result = register_purchase(cid, 1234.56, package_quantity=5)
        assert result["amount"] == 1234.56

    def test_custom_date_recorded(self):
        cid = add_client("Walter", "30000000008")
        past = date(2025, 1, 15)
        result = register_purchase(cid, 100.0, purchase_date=past, package_quantity=3)
        assert result["date"] == "2025-01-15"

    def test_monthly_spent_only_counts_current_month(self):
        cid = add_client("Ximena", "30000000009")
        today = date.today()
        register_purchase(cid, 200.0, purchase_date=today, package_quantity=5)
        register_purchase(cid, 100.0, purchase_date=date(2020, 1, 1), package_quantity=3)
        client = get_client_by_id(cid, today=today)
        assert client["monthly_spent"] == 200.0


# ─────────────────────────── MILESTONE REWARD ───────────────────────────

class TestClaimMilestoneReward:
    def test_first_claim_succeeds(self):
        cid = add_client("Yago", "40000000001")
        result = claim_milestone_reward(cid)
        assert result["milestone"] == "500_pacotes"

    def test_default_reward_choice_is_cafeteira(self):
        cid = add_client("Zara", "40000000002")
        result = claim_milestone_reward(cid)
        assert result["reward_choice"] == "cafeteira"

    def test_duplicate_claim_raises_value_error(self):
        cid = add_client("Alex", "40000000003")
        claim_milestone_reward(cid)
        with pytest.raises(ValueError, match="já recebeu"):
            claim_milestone_reward(cid)

    def test_sets_has_milestone_flag_on_client(self):
        cid = add_client("Beatriz", "40000000004")
        claim_milestone_reward(cid, reward_description="Cafeteira")
        client = get_client_by_id(cid)
        assert client["has_milestone_500"] is True
        assert client["milestone_500_desc"] == "Cafeteira"

    def test_custom_reward_description_stored(self):
        cid = add_client("César", "40000000005")
        claim_milestone_reward(cid, reward_description="Liquidificador")
        client = get_client_by_id(cid)
        assert client["milestone_500_desc"] == "Liquidificador"

    def test_different_clients_are_independent(self):
        cid1 = add_client("Diego", "40000000006")
        cid2 = add_client("Elena", "40000000007")
        claim_milestone_reward(cid1)
        c2 = get_client_by_id(cid2)
        assert c2["has_milestone_500"] is False


# ─────────────────────────── HISTORY ───────────────────────────

class TestGetClientHistory:
    def test_empty_history(self):
        cid = add_client("Fábio", "50000000001")
        assert get_client_history(cid) == []

    def test_purchase_appears_with_correct_type(self):
        cid = add_client("Gisele", "50000000002")
        register_purchase(cid, 380.0, package_quantity=10)
        history = get_client_history(cid)
        assert len(history) == 1
        assert history[0]["type"] == "purchase"
        assert history[0]["points"] == 10

    def test_milestone_appears_in_history(self):
        cid = add_client("Hélio", "50000000003")
        claim_milestone_reward(cid)
        history = get_client_history(cid)
        types = [h["type"] for h in history]
        assert "milestone_reward" in types

    def test_multiple_purchases_all_present(self):
        cid = add_client("Ingrid", "50000000004")
        register_purchase(cid, 100.0, package_quantity=3)
        register_purchase(cid, 200.0, package_quantity=5)
        assert len(get_client_history(cid)) == 2

    def test_sorted_most_recent_first(self):
        cid = add_client("Júlio", "50000000005")
        register_purchase(cid, 100.0, purchase_date=date(2025, 1, 1), package_quantity=3)
        register_purchase(cid, 200.0, purchase_date=date(2025, 6, 1), package_quantity=5)
        history = get_client_history(cid)
        assert history[0]["date"] >= history[1]["date"]

    def test_history_contains_amount_field(self):
        cid = add_client("Kátia", "50000000006")
        register_purchase(cid, 750.0, package_quantity=20)
        history = get_client_history(cid)
        assert history[0]["amount"] == 750.0


# ─────────────────────────── DASHBOARD KPIs ───────────────────────────

class TestGetDashboardKpis:
    def test_no_clients(self):
        kpis = get_dashboard_kpis()
        assert kpis["total_clients"] == 0
        assert kpis["points_today"] == 0

    def test_total_client_count(self):
        add_client("Laura", "60000000001")
        add_client("Marcos", "60000000002")
        assert get_dashboard_kpis()["total_clients"] == 2

    def test_points_today_only_counts_todays_purchases(self):
        cid = add_client("Nadia", "60000000003")
        today = date.today()
        register_purchase(cid, 380.0, purchase_date=today, package_quantity=10)
        register_purchase(cid, 100.0, purchase_date=date(2020, 1, 1), package_quantity=5)
        kpis = get_dashboard_kpis(today=today)
        assert kpis["points_today"] == 10

    def test_volume_this_month(self):
        cid = add_client("Oswaldo", "60000000004")
        register_purchase(cid, 500.0, purchase_date=date.today(), package_quantity=5)
        kpis = get_dashboard_kpis(today=date.today())
        assert kpis["volume_month"] == 500.0

    def test_circulating_points_equals_total_earned(self):
        cid = add_client("Patrícia", "60000000005")
        register_purchase(cid, 380.0, package_quantity=10)
        register_purchase(cid, 760.0, package_quantity=20)
        kpis = get_dashboard_kpis()
        assert kpis["circulating_points"] == 30


# ─────────────────────────── MONTHLY HISTORY ───────────────────────────

class TestGetMonthlyPurchaseHistory:
    def test_empty_db_returns_empty(self):
        assert get_monthly_purchase_history() == []

    def test_purchase_appears_in_correct_month(self):
        cid = add_client("Quirino", "70000000001")
        register_purchase(cid, 380.0, purchase_date=date(2026, 3, 15), package_quantity=10)
        history = get_monthly_purchase_history(months_back=12)
        assert any(h["month"] == "2026-03" for h in history)

    def test_aggregates_volume_per_month(self):
        cid = add_client("Regina", "70000000002")
        register_purchase(cid, 200.0, purchase_date=date(2026, 3, 1), package_quantity=5)
        register_purchase(cid, 300.0, purchase_date=date(2026, 3, 15), package_quantity=8)
        history = get_monthly_purchase_history(months_back=12)
        march = next(h for h in history if h["month"] == "2026-03")
        assert march["volume"] == 500.0
        assert march["num_purchases"] == 2


# ─────────────────────────── TOP CLIENTS ───────────────────────────

class TestGetTopClientsByPoints:
    def test_empty_db(self):
        assert get_top_clients_by_points() == []

    def test_ordered_by_points_desc(self):
        cid1 = add_client("Sandro", "80000000001")
        cid2 = add_client("Tatiane", "80000000002")
        register_purchase(cid1, 100.0, package_quantity=5)
        register_purchase(cid2, 100.0, package_quantity=20)
        top = get_top_clients_by_points()
        assert top[0]["id"] == cid2
        assert top[1]["id"] == cid1

    def test_limit_respected(self):
        for i in range(5):
            cid = add_client(f"Cliente {i}", f"9000000000{i}")
            register_purchase(cid, 100.0, package_quantity=i + 1)
        top = get_top_clients_by_points(limit=3)
        assert len(top) == 3


# ─────────────────────────── SETTINGS ───────────────────────────

class TestSettings:
    def test_get_existing_default_setting(self):
        assert get_setting("milestone_reward") == "Cafeteira"

    def test_get_missing_key_returns_default(self):
        assert get_setting("nonexistent_key", default="fallback") == "fallback"

    def test_set_and_get_new_setting(self):
        set_setting("my_custom_key", "my_value")
        assert get_setting("my_custom_key") == "my_value"

    def test_update_existing_setting(self):
        set_setting("milestone_reward", "Liquidificador")
        assert get_setting("milestone_reward") == "Liquidificador"

    def test_program_rules_returns_required_keys(self):
        rules = get_program_rules()
        assert "milestone_packages_threshold" in rules
        assert "milestone_reward" in rules

    def test_milestone_threshold_is_integer(self):
        rules = get_program_rules()
        assert isinstance(rules["milestone_packages_threshold"], int)

    def test_default_threshold_is_500(self):
        rules = get_program_rules()
        assert rules["milestone_packages_threshold"] == 500


# ─────────────────────────── BULLETIN ───────────────────────────

class TestBulletinBoard:
    def test_add_and_retrieve_update(self):
        bid = add_bulletin_update("Título", "Conteúdo")
        updates = get_bulletin_updates()
        assert any(u["id"] == bid for u in updates)

    def test_client_view_hides_private_updates(self):
        add_bulletin_update("Público", "Visível", show_to_clients=True)
        add_bulletin_update("Privado", "Oculto", show_to_clients=False)
        public = get_bulletin_updates(client_view=True)
        assert all(u["show_to_clients"] == 1 for u in public)

    def test_inactive_excluded_from_active_only_query(self):
        add_bulletin_update("Ativo", "X", is_active=True)
        bid2 = add_bulletin_update("Inativo", "Y", is_active=False)
        active = get_bulletin_updates(active_only=True)
        assert not any(u["id"] == bid2 for u in active)

    def test_update_changes_title_and_content(self):
        bid = add_bulletin_update("Antigo", "Conteúdo antigo")
        update_bulletin_update(bid, "Novo", "Conteúdo novo")
        updated = next(u for u in get_bulletin_updates() if u["id"] == bid)
        assert updated["title"] == "Novo"
        assert updated["content"] == "Conteúdo novo"

    def test_delete_removes_update(self):
        bid = add_bulletin_update("Para deletar", "Conteúdo")
        delete_bulletin_update(bid)
        assert not any(u["id"] == bid for u in get_bulletin_updates())

    def test_multiple_updates_stored(self):
        add_bulletin_update("Um", "Conteúdo 1")
        add_bulletin_update("Dois", "Conteúdo 2")
        assert len(get_bulletin_updates()) == 2


# ─────────────────────────── RESET ───────────────────────────

class TestResetClientData:
    def test_clears_all_clients(self):
        add_client("Alice", "99000000001")
        add_client("Bob", "99000000002")
        reset_client_data()
        assert get_all_clients_enriched() == []

    def test_clears_purchase_history(self):
        cid = add_client("Carol", "99000000003")
        register_purchase(cid, 100.0, package_quantity=5)
        reset_client_data()
        assert get_all_clients_enriched() == []

    def test_settings_preserved_after_reset(self):
        set_setting("program_name", "Meu Programa Customizado")
        reset_client_data(keep_settings=True)
        assert get_setting("program_name") == "Meu Programa Customizado"
