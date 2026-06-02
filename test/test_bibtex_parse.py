import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.main import _parse_bibtex_fields, _parse_bibtex_authors

bib = r"""@inproceedings{zhu-etal-2026-teams,
    title = "Teams of {LLM} Agents can Exploit Zero-Day Vulnerabilities",
    author = "Zhu, Yuxuan  and
      Kellermann, Antony  and
      Gupta, Akul  and
      Li, Philip  and
      Fang, Richard  and
      Bindu, Rohan  and
      Kang, Daniel",
    year = "2026",
    url = "https://aclanthology.org/2026.eacl-long.2/",
    doi = "10.18653/v1/2026.eacl-long.2",
}"""

fields = _parse_bibtex_fields(bib)
print("Parsed fields:")
for k, v in fields.items():
    print(f"  {k}: {v!r}")

assert fields.get("title") == "Teams of LLM Agents can Exploit Zero-Day Vulnerabilities", f"title mismatch: {fields.get('title')}"
assert fields.get("year") == "2026", f"year mismatch: {fields.get('year')}"
assert fields.get("url") == "https://aclanthology.org/2026.eacl-long.2/", f"url mismatch: {fields.get('url')}"
assert "Zhu" in fields.get("author", ""), f"author missing Zhu: {fields.get('author')}"
print("\nAll assertions passed!")
