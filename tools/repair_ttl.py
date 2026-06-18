"""
TTL Repair Tool: 파싱 에러가 있는 Turtle 파일을 수정해주는 도구.

사용법:
    python tools/repair_ttl.py --input broken.ttl
    python tools/repair_ttl.py --input broken.ttl --output fixed.ttl
    python tools/repair_ttl.py --input broken.ttl --inplace
    python tools/repair_ttl.py --input broken.ttl --dry-run

옵션:
    --input     수정할 TTL 파일 경로 (필수)
    --output    결과 저장 경로 (기본값: <input>_repaired.ttl)
    --inplace   원본 파일을 직접 덮어씀
    --dry-run   수정 여부와 통계만 출력하고 파일은 저장하지 않음
    --verbose   제거된 블록의 내용을 상세히 출력
"""
import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from coha.owl_utils import (
    BASE_PREFIXES,
    _strip_code_fence,
    _fix_prefix_declarations,
    _filter_turtle_lines,
    _is_valid_turtle,
)


# ---------------------------------------------------------------------------
# 수리 파이프라인 (repair_turtle()의 상세 진단 버전)
# ---------------------------------------------------------------------------

def _count_triples(ttl: str) -> int:
    """rdflib으로 파싱 가능한 경우 트리플 수를 반환, 불가능하면 -1."""
    if not ttl.strip():
        return 0
    try:
        import rdflib
        g = rdflib.Graph()
        g.parse(data=ttl, format="turtle")
        return len(g)
    except Exception:
        return -1


def _repair_turtle_verbose(ttl: str, verbose: bool = False) -> tuple:
    """
    TTL을 단계별로 수리하고 (repaired_ttl, steps_log, dropped_blocks)를 반환.

    steps_log: 적용된 수리 단계 목록 (문자열 리스트)
    dropped_blocks: 파싱 실패로 제거된 블록 목록
    """
    steps = []
    dropped_blocks = []

    # Step 1: 마크다운 코드 펜스 제거
    stripped = _strip_code_fence(ttl)
    if stripped != ttl.strip():
        steps.append("마크다운 코드 펜스(```turtle / ```) 제거")
    ttl = stripped

    # Step 2: @prefix 문법 수정 (콜론 누락, 마침표 누락)
    fixed = _fix_prefix_declarations(ttl)
    if fixed != ttl:
        steps.append("@prefix 선언 문법 수정 (콜론/마침표 누락)")
    ttl = fixed

    # Step 3: 유효성 확인 — 이미 올바르면 바로 반환
    test = ttl if "@prefix" in ttl else BASE_PREFIXES + "\n" + ttl
    if _is_valid_turtle(test):
        return ttl, steps, dropped_blocks

    # Step 4: 산문(prose) 줄 제거
    filtered = _filter_turtle_lines(ttl)
    if filtered.strip() and filtered != ttl:
        steps.append("Turtle 문법이 아닌 산문(설명 텍스트) 줄 제거")
        ttl = filtered
        test = ttl if "@prefix" in ttl else BASE_PREFIXES + "\n" + ttl
        if _is_valid_turtle(test):
            return ttl, steps, dropped_blocks

    # Step 5: 블록 단위 수리 — 빈 줄 기준으로 쪼개서 파싱 가능한 블록만 유지
    import re
    blocks = re.split(r'\n{2,}', ttl.strip())
    valid_blocks = []

    for block in blocks:
        stripped_block = block.strip()
        if not stripped_block:
            continue
        # 주석과 @prefix는 항상 유지
        if stripped_block.startswith('#') or stripped_block.startswith('@prefix'):
            valid_blocks.append(block)
            continue
        block_test = BASE_PREFIXES + "\n" + stripped_block
        if _is_valid_turtle(block_test):
            valid_blocks.append(block)
        else:
            dropped_blocks.append(stripped_block)
            if verbose:
                pass  # 호출측에서 출력

    if dropped_blocks:
        steps.append(f"파싱 불가 블록 {len(dropped_blocks)}개 제거 (블록 단위 수리)")

    repaired = "\n\n".join(valid_blocks)
    return repaired, steps, dropped_blocks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="rdflib 파싱 에러가 있는 TTL 파일을 자동 수리합니다."
    )
    parser.add_argument("--input",   required=True, help="수정할 TTL 파일 경로")
    parser.add_argument("--output",  default="",    help="결과 저장 경로 (기본: <input>_repaired.ttl)")
    parser.add_argument("--inplace", action="store_true", help="원본 파일을 직접 덮어씀")
    parser.add_argument("--dry-run", action="store_true", help="통계만 출력하고 파일은 저장하지 않음")
    parser.add_argument("--verbose", action="store_true", help="제거된 블록 내용을 상세히 출력")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[오류] 파일을 찾을 수 없습니다: {args.input}")
        sys.exit(1)

    raw = open(args.input, encoding="utf-8").read()

    # 원본 파싱 상태 확인
    original_triples = _count_triples(raw)
    if original_triples >= 0:
        print(f"[확인] 원본 파일이 이미 유효한 Turtle입니다. ({original_triples}개 트리플)")
        print("       수리가 필요하지 않습니다.")
        sys.exit(0)

    # 원본 파싱 에러 메시지 출력
    try:
        import rdflib
        rdflib.Graph().parse(data=raw, format="turtle")
    except Exception as e:
        err_lines = str(e).strip().splitlines()
        short_err = next((l for l in err_lines if l.startswith("Bad syntax") or l.startswith("Expected")), str(e)[:120])
        print(f"[파싱 에러] {short_err}")

    print(f"\n원본: {args.input}")
    print(f"원본 크기: {len(raw.splitlines())}줄, {len(raw.encode())} bytes")
    print()

    # 수리 실행
    repaired, steps, dropped = _repair_turtle_verbose(raw, verbose=args.verbose)

    if not steps:
        print("[결과] 자동 수리로 고칠 수 없는 에러입니다. 파일을 직접 확인해 주세요.")
        sys.exit(2)

    # 수리 결과 검증
    repaired_test = repaired if "@prefix" in repaired else BASE_PREFIXES + "\n" + repaired
    repaired_triples = _count_triples(repaired_test)

    print("── 적용된 수리 단계 ──────────────────────────────────")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print()

    if dropped:
        print(f"── 제거된 블록 ({len(dropped)}개) ────────────────────────────")
        for i, block in enumerate(dropped, 1):
            preview = block[:120].replace("\n", " ").strip()
            if len(block) > 120:
                preview += " ..."
            print(f"  [{i}] {preview}")
        print()

    if repaired_triples >= 0:
        print(f"[결과] 수리 성공 ✓  →  {repaired_triples}개 트리플 보존")
    else:
        print("[결과] 수리 후에도 파싱 에러가 남아 있습니다. --verbose 옵션으로 상세 확인하세요.")
        sys.exit(2)

    if args.verbose and dropped:
        print()
        print("── 제거된 블록 전체 내용 ─────────────────────────────")
        for i, block in enumerate(dropped, 1):
            print(f"\n--- 블록 {i} ---")
            print(block)

    if args.dry_run:
        print("\n[dry-run] 파일을 저장하지 않았습니다.")
        return

    # 출력 경로 결정
    if args.inplace:
        out_path = args.input
    elif args.output:
        out_path = args.output
    else:
        base, ext = os.path.splitext(args.input)
        out_path = base + "_repaired" + (ext or ".ttl")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(repaired)

    print(f"\n저장 완료: {out_path}")
    print(f"저장 크기: {len(repaired.splitlines())}줄, {len(repaired.encode())} bytes")


if __name__ == "__main__":
    main()
