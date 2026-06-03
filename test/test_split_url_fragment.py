"""Test that URL fragments like '08.' on their own line don't trigger numbered splitting."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.main import _split_references

TEXT = """Google. OSS-Fuzz: Continuous Fuzzing for Open Source Software. https://github.com/g
oogle/oss-fuzz. Accessed: 2025-05-10.
Google AI Team. Start building with gemini 2.5 flash. https://developers.googleblog.
com/en/start-building-with-gemini-25-flash/. Accessed: 2025-05-10.
Wenbo Guo, Yujin Potter, Tianneng Shi, Zhun Wang, Andy Zhang, and Dawn Song. Frontier ai's
impact on the cybersecurity landscape, 2025. URL https://arxiv.org/abs/2504.054
08.
Diane Hosfelt. Implications of Rewriting a Browser Component in Rust. https://hacks.mo
zilla.org/2019/02/rewriting-a-browser-component-in-rust/, February
2019. Mozilla Hacks blog. Accessed: 2025-11-27.
Naman Jain, Jaskirat Singh, Manish Shetty, Liang Zheng, Koushik Sen, and Ion Stoica. R2e-gym:
Procedural environments and hybrid verifiers for scaling open-weights swe agents. arXiv preprint
arXiv:2504.07164, 2025.
Carlos E Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, and Karthik R
Narasimhan. SWE-bench: Can language models resolve real-world github issues? In International
Conference on Learning Representations (ICLR), 2024. URL https://openreview.net/f
orum?id=VTF8yNQM66.
Brandon N Keller, Benjamin S Meyers, and Andrew Meneely. What happens when we fuzz?
investigating oss-fuzz bug history. In International Conference on Mining Software Repositories
(MSR), pp. 207-217. IEEE, 2023.
Kimi Team, Tongtong Bai, Yifan Bai, Yiping Bao, SH Cai, Yuan Cao, Y Charles, HS Che,
Cheng Chen, Guanduo Chen, et al. Kimi k2. 5: Visual agentic intelligence. arXiv preprint
arXiv:2602.02276, 2026.
George Klees, Andrew Ruef, Benji Cooper, Shiyi Wei, and Michael Hicks. Evaluating fuzz testing.
In Conference on Computer and Communications Security (CCS), 2018.
Tom Lane and Independent JPEG Group. libjpeg is a free software library written for jpeg image
compression. http://www.ijg.org/. Accessed: 2025-09-15.
Hwiwon Lee, Ziqi Zhang, Hanxiao Lu, and Lingming Zhang. Sec-bench: Automated benchmarking
of llm agents on real-world software security tasks. In Neural Information Processing Systems
(NeurIPS), 2025.
Aixin Liu, Bei Feng, Bing Xue, Bingxuan Wang, Bochao Wu, Chengda Lu, Chenggang Zhao,
Chengqi Deng, Chenyu Zhang, Chong Ruan, et al. Deepseek-v3 technical report. arXiv preprint
arXiv:2412.19437, 2024.
LLVM. Clang: a C language family frontend for LLVM. https://clang.llvm.org/, a.
Accessed: 2025-09-15.
LLVM. Undefinedbehaviorsanitizer - clang documentation. https://clang.llvm.org/d
ocs/UndefinedBehaviorSanitizer.html, b. Accessed: 2025-05-10.
Xiang Mei, Pulkit Singh Singaria, Jordi Del Castillo, Haoran Xi, Tiffany Bao, Ruoyu Wang, Yan
Shoshitaishvili, Adam Doupe, Hammond Pearce, Brendan Dolan-Gavitt, et al. Arvo: Atlas of
reproducible vulnerabilities for open source software. arXiv preprint arXiv:2408.02153, 2024.
Michal Zalewski. American fuzzy lop. https://lcamtuf.coredump.cx/afl/. Accessed:
2025-09-15.
Barton P Miller, Lars Fredriksen, and Bryan So. An empirical study of the reliability of unix utilities.
Communications of the ACM, 33(12):32-44, 1990.
MSRC. A proactive approach to more secure code. https://www.microsoft.com/en-u
s/msrc/blog/2019/07/a-proactive-approach-to-more-secure-code, July
2019. Microsoft MSRC blog. Accessed: 2025-11-27."""

refs = _split_references(TEXT)

print(f"Found {len(refs)} references:\n")
for i, r in enumerate(refs, 1):
    print(f"  [{i}] {r[:100]}{'...' if len(r) > 100 else ''}")

assert len(refs) >= 15, f"Expected >= 15 references, got {len(refs)}"
assert any("OSS-Fuzz" in r for r in refs), "Missing OSS-Fuzz reference"
assert any("SWE-bench" in r for r in refs), "Missing SWE-bench reference"
assert any("2504.05408" in r or "2504.054 08" in r for r in refs), "URL fragment '08.' should be merged into Guo et al. reference, not split"

print(f"\nAll assertions passed! ({len(refs)} references)")
