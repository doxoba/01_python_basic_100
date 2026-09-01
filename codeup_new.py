#!/usr/bin/env python3
"""
codeup_new.py — Codeup 문제 페이지에서 정보를 긁어와 규칙에 맞는 풀이 파일을 자동 생성.

사용법:
    python codeup_new.py <day폴더> <문제번호...>

    문제번호는 공백으로 여러 개 나열하거나 6001-6008 처럼 범위로 줄 수 있습니다.

예시:
    python codeup_new.py day02 6021              # day02/6021_..._....py 1개 생성
    python codeup_new.py day02 6021 6022 6023     # 3개 생성
    python codeup_new.py day02 6021-6024          # 6021~6024 범위 생성
    python codeup_new.py day02 6021-6024 --open   # 생성 후 VSCode로 열기(code 명령 필요)

이미 존재하는 파일은 덮어쓰지 않고 건너뜁니다.

필요 패키지: requests, beautifulsoup4
    pip install requests beautifulsoup4
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.codeup.kr/problem.php?id={}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TEMPLATE = """# ---------------------------------------------------------
# {header}
# ---------------------------------------------------------
# 문제: {problem}
# ---------------------------------------------------------
# (여기에 내 풀이)

# 메모:
"""


def parse_ids(args_list):
    ids = []
    for token in args_list:
        if "-" in token:
            start, end = token.split("-", 1)
            ids.extend(range(int(start), int(end) + 1))
        else:
            ids.append(int(token))
    return ids


def fetch_problem(problem_id: int):
    url = BASE_URL.format(problem_id)
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    h2 = soup.find("h2")
    if not h2:
        raise RuntimeError(f"{problem_id}: 문제 제목(h2)을 찾지 못했습니다. 사이트 구조가 바뀌었을 수 있습니다.")
    header_text = h2.get_text(strip=True)  # 예: "6001 : [기초-출력] 출력하기01(설명)(py)"

    m = re.match(r"\d+\s*:\s*\[(.+?)\]\s*(.+)", header_text)
    if not m:
        raise RuntimeError(f"{problem_id}: 제목 형식을 해석하지 못했습니다: {header_text}")
    category, raw_title = m.group(1), m.group(2)

    title_wo_suffix = re.sub(r"\(설명\)|\(py\)", "", raw_title).strip()
    title_compact = re.sub(r"\s+", "", title_wo_suffix)
    # 파일명에 쓸 수 없는 문자 제거 (Windows 기준 \ / : * ? " < > | 등)
    title_compact = re.sub(r'[\\/:*?"<>|]', "", title_compact)

    def section_text(elem_id):
        el = soup.find(id=elem_id)
        if not el:
            return None
        for br in el.find_all("br"):
            br.replace_with("\n")
        text = el.get_text().strip()
        return text or None

    problem_text = section_text("pro1") or "(문제 설명을 가져오지 못했습니다. 직접 붙여넣어 주세요)"
    input_text = section_text("pro2")   # 입력 설명
    output_text = section_text("pro3")  # 출력 설명

    return {
        "id": problem_id,
        "category": category,
        "title_compact": title_compact,
        "header": header_text,
        "problem_text": problem_text,
        "input_text": input_text,
        "output_text": output_text,
    }


def format_problem_block(problem_text: str, input_text: Optional[str], output_text: Optional[str]) -> str:
    # 문제 설명 + 입력 + 출력을 하나의 "문제" 블록으로 합친다 (입력/출력도 문제의 일부로 취급).
    parts = [problem_text.strip()]
    if input_text:
        parts.append("[입력]\n" + input_text.strip())
    if output_text:
        parts.append("[출력]\n" + output_text.strip())
    full_text = "\n\n".join(parts)

    lines = [ln.rstrip() for ln in full_text.splitlines() if ln.strip() != ""]
    if not lines:
        return "(문제 설명 없음)"
    out = [lines[0]]
    for ln in lines[1:]:
        out.append("#       " + ln)
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Codeup 문제 풀이 파일 자동 생성")
    parser.add_argument("day", help="day 폴더명 (예: day02)")
    parser.add_argument("ids", nargs="+", help="문제 번호 또는 범위 (예: 6021 6022-6025)")
    parser.add_argument("--open", action="store_true", help="생성 후 VSCode(code)로 파일 열기")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    day_dir = repo_root / args.day
    day_dir.mkdir(parents=True, exist_ok=True)

    problem_ids = parse_ids(args.ids)
    created = []

    for pid in problem_ids:
        try:
            info = fetch_problem(pid)
        except Exception as e:
            print(f"[실패] {pid}: {e}", file=sys.stderr)
            continue

        filename = f"{info['id']}_{info['category']}_{info['title_compact']}.py"
        filepath = day_dir / filename

        if filepath.exists():
            print(f"[건너뜀] 이미 존재: {filepath.name}")
            created.append(filepath)
            continue

        content = TEMPLATE.format(
            header=info["header"],
            problem=format_problem_block(
                info["problem_text"], info["input_text"], info["output_text"]
            ),
        )
        filepath.write_text(content, encoding="utf-8")
        created.append(filepath)
        print(f"[생성] {filepath.relative_to(repo_root)}")

    if args.open and created:
        try:
            subprocess.run(["code"] + [str(p) for p in created])
        except FileNotFoundError:
            print("VSCode 'code' 명령을 찾을 수 없습니다. code CLI를 PATH에 등록해주세요.", file=sys.stderr)


if __name__ == "__main__":
    main()
