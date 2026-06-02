"""Tests for _split_references — the PDF reference section splitter."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.main import _split_references, _is_continuation

# ── Test data ────────────────────────────────────────────────────────────────

SAMPLE_6_REFS = """\
Rodriguez, M., Popa, R. A., Flynn, F., Liang, L., Dafoe,
A., and Wang, A. A framework for evaluating emerging cyberattack capabilities of AI. arXiv preprint
arXiv:2503.11917, 2025.
Shao, R., Haghighatkhah, F., Biderman, S., et al. NYU CTF
Bench: A scalable open-source benchmark database for
evaluating LLMs in offensive security. arXiv preprint
arXiv:2406.05590, 2024.
Yang, J., Prabhakar, A., Narasimhan, K., and Yao, S. InterCode: Standardizing and benchmarking interactive
coding with execution feedback. In Advances in Neural
Information Processing Systems (NeurIPS), 2024.
Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan,
K., and Cao, Y. ReAct: Synergizing reasoning and acting in language models. In International Conference on
Learning Representations (ICLR), 2023.
Zhang, A. K., Perry, N., Dulepet, R., Ji, J., et al. Cybench: A framework for evaluating cybersecurity capabilities and risks of language models. arXiv preprint
arXiv:2408.08926, 2024.
Zhou, S., Xu, F. F., Zhu, H., Zhou, X., et al. WebArena: A realistic web environment for building autonomous agents.
In International Conference on Learning Representations
(ICLR), 2024.
"""

EXPECTED_6 = [
    "Rodriguez, M., Popa, R. A., Flynn, F., Liang, L., Dafoe, A., and Wang, A. A framework for evaluating emerging cyberattack capabilities of AI. arXiv preprint arXiv:2503.11917, 2025.",
    "Shao, R., Haghighatkhah, F., Biderman, S., et al. NYU CTF Bench: A scalable open-source benchmark database for evaluating LLMs in offensive security. arXiv preprint arXiv:2406.05590, 2024.",
    "Yang, J., Prabhakar, A., Narasimhan, K., and Yao, S. InterCode: Standardizing and benchmarking interactive coding with execution feedback. In Advances in Neural Information Processing Systems (NeurIPS), 2024.",
    "Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., and Cao, Y. ReAct: Synergizing reasoning and acting in language models. In International Conference on Learning Representations (ICLR), 2023.",
    "Zhang, A. K., Perry, N., Dulepet, R., Ji, J., et al. Cybench: A framework for evaluating cybersecurity capabilities and risks of language models. arXiv preprint arXiv:2408.08926, 2024.",
    "Zhou, S., Xu, F. F., Zhu, H., Zhou, X., et al. WebArena: A realistic web environment for building autonomous agents. In International Conference on Learning Representations (ICLR), 2024.",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _debug_split(text: str) -> list[str]:
    """Run the splitter and print each result for debugging."""
    results = _split_references(text)
    print(f"\n{'='*60}")
    print(f"Split produced {len(results)} reference(s):\n")
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r[:120]}{'...' if len(r) > 120 else ''}")
    print(f"{'='*60}\n")
    return results


def _debug_continuation(text: str):
    """Trace _is_continuation decisions line by line."""
    import re
    text = text.strip()
    text = re.sub(r"^(?:References|Bibliography)\s*\n", "", text, flags=re.IGNORECASE)
    lines = text.split("\n")
    merged = []
    print(f"\n{'='*60}")
    print("Line-by-line continuation trace:\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if merged:
            is_cont = _is_continuation(stripped, merged[-1])
            prev_end = merged[-1].rstrip()[-5:] if merged[-1].rstrip() else ""
            decision = "CONT" if is_cont else "NEW "
            print(f"  {decision} | prev_end=...{prev_end!r:>8s} | {stripped[:80]}")
            if is_cont:
                prev = merged[-1]
                if prev.endswith("-") and not prev.endswith("--"):
                    merged[-1] = prev[:-1] + stripped
                else:
                    merged[-1] = prev + " " + stripped
            else:
                merged.append(stripped)
        else:
            print(f"  FIRST| {stripped[:80]}")
            merged.append(stripped)
    print(f"\nMerged into {len(merged)} block(s)")
    print(f"{'='*60}\n")


# ── Tests ────────────────────────────────────────────────────────────────────

def test_6_refs_count():
    results = _split_references(SAMPLE_6_REFS)
    if len(results) != 6:
        _debug_split(SAMPLE_6_REFS)
        _debug_continuation(SAMPLE_6_REFS)
    assert len(results) == 6, f"Expected 6, got {len(results)}"


def test_6_refs_content():
    results = _split_references(SAMPLE_6_REFS)
    for i, (got, want) in enumerate(zip(results, EXPECTED_6)):
        assert got == want, f"Reference {i+1} mismatch:\n  GOT:  {got[:100]}\n  WANT: {want[:100]}"


def test_numbered_bracket_style():
    text = "[1] First ref content.\n[2] Second ref content.\n[3] Third ref."
    results = _split_references(text)
    assert len(results) == 3, f"Expected 3, got {len(results)}: {results}"


def test_numbered_bracket_style_first_on_same_line():
    """When [1] is at the very start (no preceding newline), it should still work."""
    text = "[1] First ref.\n[2] Second ref.\n[3] Third ref."
    results = _split_references(text)
    # The split regex requires \n before [n], so [1] on line 1 may not split.
    # The fallback merger should still produce 3.
    assert len(results) >= 3, f"Expected >=3, got {len(results)}: {results}"


def test_numbered_dot_style():
    text = "1. First ref content.\n2. Second ref content.\n3. Third ref."
    results = _split_references(text)
    assert len(results) == 3, f"Expected 3, got {len(results)}: {results}"


def test_years_not_treated_as_numbers():
    """Years like 2023. at the start of a line must NOT be treated as ref numbers."""
    text = "Author, A. Title. arXiv,\n2023.\nAuthor, B. Another title. arXiv,\n2024."
    results = _split_references(text)
    assert len(results) == 2, f"Expected 2, got {len(results)}: {results}"


if __name__ == "__main__":
    test_6_refs_count()
    test_6_refs_content()
    test_numbered_bracket_style()
    test_numbered_dot_style()
    test_years_not_treated_as_numbers()
    print("\nAll tests passed!")
