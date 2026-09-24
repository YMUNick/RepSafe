"""Three-state verdict card. The ONLY place that decides red / amber / grey.

    red    at least one red flag from any source (a tool, the injection guard, or Gemini)
    grey   no red flag, and something did not finish: Gemini / Web Risk failed, timed out, hit quota,
           returned output outside the schema, a link was not checked, or the rate limit was hit
    amber  no red flag AND every step finished. Means "no red flags found", never "safe".

Order matters: red beats grey. A punycode Shopee look-alike stays red even when Web Risk is out of quota,
otherwise a failure would turn a caught scam into a miss (grey counts as a miss in the eval).
A failure can never produce amber. There is deliberately no green / "safe" state.
"""
from __future__ import annotations

RED, AMBER, GREY = "red", "amber", "grey"

# Problem codes (also returned to the client so the grey card can say why, without any message content)
PROBLEMS = {
    "gemini_timeout", "gemini_error", "gemini_quota", "gemini_bad_output", "gemini_unavailable",
    "reputation_error", "reputation_skipped", "rate_limited", "internal_error",
}


def decide(red_flags: list, problems: list[str]) -> str:
    """Any problem code at all (known or not) rules out amber."""
    if red_flags:
        return RED
    if problems:
        return GREY
    return AMBER
