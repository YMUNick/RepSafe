"""OFFLINE FIXTURE judge: keyword rules standing in for Gemini when there is no GCP.

For UI work and tests only. Every response says mode="offline_fixture"; never demo or evaluate with it.
Returns the same shape as the Gemini judge output (app/prompt.py RESPONSE_SCHEMA).
"""
from __future__ import annotations

import re

RULES = [
    ("phishing_link", re.compile(r"(?i)金流|簽署|認證|驗證|保障|verify|verification|certif|guarantee|escrow|activate"),
     "Asks the seller to verify or sign a payment guarantee; marketplaces never ask for this through a link."),
    ("credential_request", re.compile(r"(?i)OTP|驗證碼|密碼|網銀|ATM|password|card number"),
     "Asks for codes, passwords or ATM steps."),
    ("off_platform_payment", re.compile(r"(?i)匯款|轉帳|直接付|bank transfer|paynow|pay you directly|pay outside"),
     "Wants to pay outside the platform checkout."),
    ("off_platform_payment", re.compile(r"(?i)加賴|加line|line\s*id|whatsapp|telegram|站外|off[- ]?platform"),
     "Moves the conversation off the platform, where its protection stops."),
    ("impersonation", re.compile(r"(?i)客服|專員|customer service|support agent"),
     "Points to a 'customer service' contact that is not the platform."),
]
_SENTENCE = re.compile(r"[^\n。！？!?]+[。！？!?]?")

REPLY_ZH = "您好，為了保障雙方交易安全，我只透過平台內的聊天和結帳流程交易，不會點外部連結、不會到站外付款或加其他通訊軟體。請直接在平台下單，謝謝！"
REPLY_EN = ("Hi! To keep us both protected, I only deal through the platform's own chat and checkout. "
            "I won't open outside links, pay or get paid outside, or move to other apps. "
            "Please place the order on the platform directly. Thanks!")


def is_cjk(text: str) -> bool:
    return any("一" <= c <= "鿿" for c in text)


def fallback_reply(text: str) -> str:
    """Fixed safe reply, also used in gemini mode when Gemini failed (still passes the reply filter)."""
    return REPLY_ZH if is_cjk(text) else REPLY_EN


def judge(text: str) -> dict:
    flags, scam_type = [], "none"
    for m in _SENTENCE.finditer(text):
        sentence = m.group(0).strip()
        if not sentence:
            continue
        for kind, rx, reason in RULES:
            if rx.search(sentence):
                flags.append({"quote": sentence, "reason": reason})
                if scam_type == "none":
                    scam_type = kind
                break
    return {"scam_type": scam_type, "red_flags": flags, "injection_detected": False,
            "safe_reply": fallback_reply(text)}
