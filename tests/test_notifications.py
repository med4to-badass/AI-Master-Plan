import pytest

from notifications import format_phone_for_whatsapp, build_whatsapp_url


class TestFormatPhoneForWhatsapp:
    def test_none_returns_empty(self):
        assert format_phone_for_whatsapp(None) == ""

    def test_empty_string_returns_empty(self):
        assert format_phone_for_whatsapp("") == ""

    def test_whitespace_only_returns_empty(self):
        assert format_phone_for_whatsapp("   ") == ""

    def test_10_digit_landline(self):
        # Area code + 8-digit number (no leading 9)
        result = format_phone_for_whatsapp("1133334444")
        assert result == "551133334444"

    def test_11_digit_mobile(self):
        # Area code + 9-digit mobile (with leading 9)
        result = format_phone_for_whatsapp("11987654321")
        assert result == "5511987654321"

    def test_already_has_country_code_passes_through(self):
        result = format_phone_for_whatsapp("5511987654321")
        assert result == "5511987654321"

    def test_formatted_mobile_with_punctuation(self):
        result = format_phone_for_whatsapp("(11) 98765-4321")
        assert result == "5511987654321"

    def test_formatted_landline_with_punctuation(self):
        result = format_phone_for_whatsapp("(11) 3333-4444")
        assert result == "551133334444"

    def test_strips_all_non_digit_characters(self):
        result = format_phone_for_whatsapp("+55 (21) 96543-2109")
        assert result.isdigit()
        assert result.startswith("55")

    def test_only_digits_in_result(self):
        result = format_phone_for_whatsapp("(85) 99876-5432")
        assert result.isdigit()

    def test_country_code_prepended_only_once(self):
        result = format_phone_for_whatsapp("11987654321")
        assert not result.startswith("5555")


class TestBuildWhatsappUrl:
    def test_returns_wa_me_url(self):
        url = build_whatsapp_url("11987654321", "Olá!")
        assert url.startswith("https://wa.me/")

    def test_phone_normalized_in_url(self):
        url = build_whatsapp_url("11987654321", "Oi")
        assert "5511987654321" in url

    def test_message_appended_as_text_param(self):
        url = build_whatsapp_url("11987654321", "Teste")
        assert "?text=" in url

    def test_spaces_are_encoded(self):
        url = build_whatsapp_url("11987654321", "Olá mundo")
        assert " " not in url

    def test_accented_chars_are_encoded(self):
        url = build_whatsapp_url("11987654321", "café")
        # 'é' percent-encoded: %C3%A9
        assert "%C3%A9" in url

    def test_ampersand_encoded(self):
        url = build_whatsapp_url("11987654321", "R$ 38 & mais")
        text_part = url.split("?text=")[1]
        assert "&" not in text_part
        assert "%26" in text_part

    def test_empty_phone_no_number_in_url(self):
        url = build_whatsapp_url("", "Mensagem")
        assert url.startswith("https://wa.me/?text=")

    def test_formatted_phone_input(self):
        url = build_whatsapp_url("(11) 98765-4321", "Oi")
        assert "5511987654321" in url
