#!/usr/bin/env python3
"""
codeup_commit.py — 하루치 문제 풀이 파일들을 파일 1개당 커밋 1개로 자동 커밋.

사용법:
    python codeup_commit.py                # 저장소 전체의 변경된 파일을 각각 커밋
    python codeup_commit.py --day day02     # day02 폴더 안의 변경된 파일만 각각 커밋
    python codeup_commit.py --dry-run       # 실제로 커밋하지 않고 어떤 순서/메시지로 커밋될지만 미리보기
    python codeup_commit.py --push          # 커밋 후 git push까지 실행

파일명이 "6021_기초-입출력_단어1개나누어출력.py" 형식이면
커밋 메시지를 "6021: [기초-입출력] 단어1개나누어출력" 형태로 자동으로 만들어줍니다.
그 외 파일(README.md 등)은 "파일경로: 업데이트" 형식으로 커밋합니다.

주의: git이 PATH에 등록되어 있어야 하고, 이 스크립트는 git 저장소 루트
(01_python_basic_100 폴더, .git이 있는 곳)에서 실행해야 합니다.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

FILENAME_RE = re.compile(r"^(\d+)_(.+?)_(.+)\.py$")


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def get_changed_files(repo_root: Path, day: Optional[str]):
    result = run(["git", "status", "--porcelain"], cwd=repo_root)
    if result.returncode != 0:
        print("git status 실행 실패. 이 폴더가 git 저장소가 맞는지 확인해주세요.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    files = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        # porcelain format: XY <path>  (rename의 경우 "R  old -> new" 형태도 있음)
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        path_part = path_part.strip().strip('"')
        files.append(path_part)

    if day:
        day = day.rstrip("/\\")
        files = [f for f in files if f.startswith(day + "/") or f.startswith(day + "\\")]

    return files


def commit_message_for(relpath: str) -> str:
    filename = Path(relpath).name
    m = FILENAME_RE.match(filename)
    if m:
        number, category, title = m.groups()
        return f"{number}: [{category}] {title}"
    return f"{relpath}: 업데이트"


def sort_key(relpath: str):
    filename = Path(relpath).name
    m = FILENAME_RE.match(filename)
    if m:
        return (0, int(m.group(1)))
    return (1, relpath)


def main():
    parser = argparse.ArgumentParser(description="문제 풀이 파일을 파일별로 하나씩 커밋")
    parser.add_argument("--day", help="특정 day 폴더만 대상으로 (예: day02)")
    parser.add_argument("--dry-run", action="store_true", help="실제 커밋 없이 순서/메시지만 미리보기")
    parser.add_argument("--push", action="store_true", help="커밋 완료 후 git push 실행")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent

    if not (repo_root / ".git").exists():
        print(f"{repo_root} 에 .git이 없습니다. 먼저 git init(또는 VSCode의 Initialize Repository)을 해주세요.", file=sys.stderr)
        sys.exit(1)

    files = get_changed_files(repo_root, args.day)
    if not files:
        print("커밋할 변경 사항이 없습니다.")
        return

    files.sort(key=sort_key)

    print(f"총 {len(files)}개 파일을 개별 커밋합니다:\n")
    for f in files:
        print(f"  {f}  ->  \"{commit_message_for(f)}\"")

    if args.dry_run:
        print("\n(--dry-run 이라 실제 커밋은 하지 않았습니다)")
        return

    print()
    for f in files:
        msg = commit_message_for(f)
        add_res = run(["git", "add", "--", f], cwd=repo_root)
        if add_res.returncode != 0:
            print(f"[실패] git add {f}: {add_res.stderr.strip()}", file=sys.stderr)
            continue
        commit_res = run(["git", "commit", "-m", msg], cwd=repo_root)
        if commit_res.returncode != 0:
            print(f"[실패] git commit ({f}): {commit_res.stderr.strip()}", file=sys.stderr)
            continue
        print(f"[커밋] {msg}")

    if args.push:
        push_res = run(["git", "push"], cwd=repo_root)
        if push_res.returncode != 0:
            print(f"[실패] git push: {push_res.stderr.strip()}", file=sys.stderr)
        else:
            print("\npush 완료.")


if __name__ == "__main__":
    main()
