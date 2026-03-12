"""QC validation for a generated slide image using Gemini vision + Levenshtein."""

from creation_studio.graphs.utils.gemini_utils import call_gemini_vision

_QC_PROMPT = """\
Examine this carousel slide image and return ONLY a JSON object with these fields:
{
  "transcribed_headline": "<exact text you see as the headline>",
  "hex_codes_visible": <true if any #XXXXXX hex color codes appear in the image, else false>,
  "logo_in_top_left": <true if a logo/brand mark is clearly in the top-left area, else false>,
  "readability_score": <integer 1-5 where 5=perfectly readable, 1=unreadable>
}
No markdown, no explanation — only the JSON object.\
"""


def _levenshtein_similarity(s1: str, s2: str) -> float:
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if s1[i - 1] == s2[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return 1.0 - dp[n] / max(m, n)


def validate_slide(image_base64: str, expected_headline: str) -> tuple[bool, list[str]]:
    """Run QC on a generated slide image.

    Returns (passed: bool, issues: list[str]).
    """
    try:
        result = call_gemini_vision(_QC_PROMPT, image_base64, "image/png")
    except Exception as e:
        return False, [f"QC vision call failed: {e}"]

    issues: list[str] = []

    transcribed = result.get("transcribed_headline", "")
    similarity = _levenshtein_similarity(
        expected_headline.lower().strip(),
        transcribed.lower().strip(),
    )
    if similarity < 0.85:
        issues.append(
            f"Headline mismatch (similarity={similarity:.2f}): "
            f"expected '{expected_headline}', got '{transcribed}'"
        )

    if result.get("hex_codes_visible", False):
        issues.append("Hex color codes are visible in the image — remove them")

    if not result.get("logo_in_top_left", False):
        issues.append("Logo not found in top-left corner — place the provided logo there")

    readability = result.get("readability_score", 0)
    if isinstance(readability, (int, float)) and readability < 3:
        issues.append(f"Readability score too low ({readability}/5) — improve text contrast and size")

    return len(issues) == 0, issues
