"""Tool 2: link extraction + impersonation check. Test domains are made up; nothing is ever opened."""
import pytest

from app.tools.domain_check import check_text, check_url, extract_urls

CYRILLIC_O = "о"  # looks exactly like Latin "o"


def codes(url):
    return {f.code for f in check_url(url).findings}


# ---------------------------------------------------------------- extraction
def test_extracts_scheme_and_bare_links_in_chinese_text():
    text = "你好，請點https://shopee-tw.com/verify 完成簽署，或到shopee-tw.net驗證。"
    assert extract_urls(text) == ["https://shopee-tw.com/verify", "shopee-tw.net"]


def test_emails_filenames_and_abbreviations_are_not_links():
    assert extract_urls("mail me at abc@gmail.com, see photo.jpg, Mr.Smith said e.g. ok") == []


def test_fullwidth_dot_is_read_as_a_dot():
    assert extract_urls("去 shopee。tw 下單") == ["shopee.tw"]


def test_duplicates_removed():
    assert extract_urls("bit.ly/abc and again bit.ly/abc") == ["bit.ly/abc"]


# ---------------------------------------------------------------- official = no red flag (false-positive guard)
@pytest.mark.parametrize("url", [
    "https://shopee.tw/product/123/456",
    "https://mall.shopee.tw/abc",
    "shopee.sg/item-i.1.2",
    "https://www.carousell.sg/p/iphone-123",
    "https://www.ruten.com.tw/item/show?123",
])
def test_official_links_have_no_findings(url):
    info = check_url(url)
    assert info.official and info.findings == []


def test_unrelated_domain_is_not_official_and_not_flagged():
    info = check_url("https://www.google.com/maps")
    assert not info.official and info.findings == []


# ---------------------------------------------------------------- impersonation
@pytest.mark.parametrize("url,code", [
    ("https://shopee-tw.com/verify", "brand_impersonation"),       # brand + dash
    ("shopeetw-pay.net/login", "brand_impersonation"),
    ("https://sh0pee.tw/guarantee", "brand_impersonation"),        # digit look-alike
    ("https://shoppee.tw/login", "lookalike_domain"),              # one letter added
    ("https://shopee.tw.verify-pay.com/x", "brand_impersonation"),  # brand as subdomain
    ("https://carouse11.sg/pay", "brand_impersonation"),
    ("https://carousel.sg/pay", "lookalike_domain"),
    ("https://rutem.com.tw/pay", "lookalike_domain"),
    ("https://shopee.tv/pay", "brand_impersonation"),              # right name, wrong TLD
])
def test_impersonation_detected(url, code):
    assert code in codes(url)


def test_punycode_is_decoded_and_flagged():
    fake = f"sh{CYRILLIC_O}pee.tw"
    puny = fake.encode("idna").decode()
    assert puny.startswith("xn--")
    info = check_url(f"https://{puny}/verify")
    assert info.host == fake                      # decoded back to what the seller would read
    assert info.host_ascii == puny
    assert {"idn_domain", "brand_impersonation"} <= {f.code for f in info.findings}
    assert not info.official


def test_unicode_lookalike_written_directly_is_flagged():
    assert {"idn_domain", "brand_impersonation"} <= codes(f"https://sh{CYRILLIC_O}pee.tw/verify")


def test_userinfo_trick_uses_real_host():
    info = check_url("https://shopee.tw@evil-pay.com/login")
    assert info.host == "evil-pay.com" and "userinfo_trick" in {f.code for f in info.findings}


# ---------------------------------------------------------------- short links: flagged, never expanded
@pytest.mark.parametrize("url", ["https://bit.ly/3abcXYZ", "reurl.cc/abc12", "https://shp.ee/xyz", "lihi1.cc/AbC"])
def test_short_links_are_red_flags(url):
    assert codes(url) == {"short_link"}


def test_check_text_end_to_end():
    infos = check_text("買家：這是我的訂單 https://shopee.tw/order/1 ，另外請到 bit.ly/x1y2z3 簽署金流")
    assert [i.official for i in infos] == [True, False]
    assert infos[1].findings[0].code == "short_link"
