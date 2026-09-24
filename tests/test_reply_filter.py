"""Safe-reply filter: the copied reply must never carry a link or an account (PRD F8, 100% gate)."""
import pytest

from app.reply_filter import REMOVED, filter_reply
from app.tools.domain_check import extract_urls

ORIGINAL = ("您好，您的賣場未簽署金流保障，請點 https://shopee-tw.com/verify 驗證，"
            "或加 LINE ID: scam888，匯款到 812-1234-5678901，有問題打 0912 345 678，信箱 help@shopee-tw.com")


@pytest.mark.parametrize("reply", [
    "好的，請到 https://shopee-tw.com/verify 我再確認",
    "請改到 shopee-tw.com 下單",
    "我們改用 xn--shpee-8ve.tw 吧",
    "請寄信到 help@shopee-tw.com",
    "我的 LINE ID: scam888",
    "請加 @scam888",
    "我會匯到 812-1234-5678901",
    "電話 0912 345 678",
    "Visit www.example-pay.net or http://1.2.3.4/login",
])
def test_links_and_accounts_removed(reply):
    out, n = filter_reply(reply, ORIGINAL)
    assert n >= 1 and REMOVED in out
    assert extract_urls(out) == []
    for secret in ("shopee-tw.com", "scam888", "5678901", "345 678", "help@", "xn--", "example-pay", "1.2.3.4"):
        assert secret not in out


def test_clean_reply_unchanged():
    reply = "您好，為了雙方安全，我只透過平台內的聊天和結帳流程交易，請直接在平台下單，謝謝！"
    assert filter_reply(reply, ORIGINAL) == (reply, 0)


def test_english_clean_reply_unchanged():
    reply = "Hi! I only deal through the platform's own checkout. Please order there. Thanks!"
    assert filter_reply(reply, "pay me at bit.ly/abc") == (reply, 0)


def test_original_secret_removed_even_without_pattern():
    # a short account-like token the generic patterns would not catch, taken from the buyer's message
    out, n = filter_reply("OK, I will send it to acct 7788abc", "my account: 7788abc")
    assert "7788abc" not in out and n >= 1


def test_empty_reply():
    assert filter_reply("", ORIGINAL) == ("", 0)
