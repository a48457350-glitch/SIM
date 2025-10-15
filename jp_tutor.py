#!/usr/bin/env python3
"""
Japanese Tutor CLI — Lesson 1 (Greetings, Self-Intro, Vowels)
- Interactive flow with adaptive hints
- Validates kana (hiragana/katakana) and optional romaji
- Configurable speed and explanation verbosity
- Self-check mode for quick non-interactive verification
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from typing import Callable, Optional, Tuple


# ---------------------------- Utilities ---------------------------- #

def normalize_nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def katakana_to_hiragana(text: str) -> str:
    # Katakana block: 0x30A1-0x30FA; convert by -0x60 to hiragana
    converted_chars = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F3:  # ァ to ン
            converted_chars.append(chr(code - 0x60))
        elif ch == "ヵ":  # small ka
            converted_chars.append("ゕ")
        elif ch == "ヶ":  # small ke
            converted_chars.append("ゖ")
        else:
            converted_chars.append(ch)
    return "".join(converted_chars)


def to_hiragana_lower(text: str) -> str:
    text = normalize_nfkc(text)
    text = katakana_to_hiragana(text)
    return text.lower()


def collapse_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def strip_all_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)


# ---------------------------- Checkers ---------------------------- #

GreetingCheckResult = Tuple[bool, str]
SelfIntroCheckResult = Tuple[bool, str, Optional[str]]
VowelsCheckResult = Tuple[bool, str]


def check_greeting(answer: str, allow_romaji: bool) -> GreetingCheckResult:
    """Check for こんにちは.
    - Accepts hiragana (preferred), katakana equivalent, and optional romaji 'konnichiwa'
    - Provides targeted hint if 'こんにちわ' mistake is made
    """
    hira = to_hiragana_lower(answer)
    hira_nospace = strip_all_spaces(hira)

    correct = "こんにちは"
    if hira_nospace == correct:
        return True, "좋아요! こんにちは"

    # Common mistake: using わ instead of は
    if "こんにちわ" == hira_nospace:
        return False, "거의 맞았어요! 'wa'는 は로 씁니다: こんにちは"

    if allow_romaji:
        rom = normalize_nfkc(answer).lower()
        rom = re.sub(r"[^a-z]", "", rom)
        if rom == "konnichiwa":
            return True, "좋아요! こんにちは"

    return False, "힌트: 낮 인사(こんにちは). 'wa' 표기는 は를 사용해요."


def check_self_intro(answer: str, allow_romaji: bool) -> SelfIntroCheckResult:
    """Check pattern: わたしは NAME です。
    - Accepts 私/わたし/ぼく/わたくし + は ... です[。]
    - Accepts optional romaji: (watashi|boku|watakushi) wa ... desu
    Returns: (ok, message, extracted_name or None)
    """
    raw = normalize_nfkc(answer)
    kana = katakana_to_hiragana(raw)

    # Japanese path (hiragana/kanji)
    jp_pat = re.compile(r"^(?:わたし|私|ぼく|わたくし)\s*は\s*(.+?)\s*です[。\.]?\s*$")
    m = jp_pat.match(collapse_spaces(kana))
    if m:
        name = m.group(1)
        if name:
            return True, "좋아요! 자연스러워요.", name

    # Romaji path
    if allow_romaji:
        rom = collapse_spaces(raw.lower())
        m2 = re.match(r"^(?:watashi|boku|watakushi)\s+wa\s+(.+?)\s+desu\.?$", rom)
        if m2:
            name = m2.group(1)
            return True, "좋아요! 자연스러워요.", name

    return False, "패턴: わたしは [이름] です。 (romaji: watashi wa [name] desu)", None


def check_vowels(answer: str, allow_romaji: bool) -> VowelsCheckResult:
    """Check sequence for vowels: あ い う え お
    - Accept both space-separated and contiguous inputs
    - Accept katakana equivalents and optional romaji 'a i u e o' or 'aiueo'
    """
    raw = normalize_nfkc(answer)
    hira = katakana_to_hiragana(raw)

    # Tokenize by spaces; if single token and length==5, split chars
    tokens = [t for t in re.split(r"\s+", hira.strip()) if t]
    if len(tokens) == 1:
        tokens = list(tokens[0])

    target = ["あ", "い", "う", "え", "お"]
    if tokens == target:
        return True, "완벽해요! あ い う え お"

    if allow_romaji:
        rom = re.sub(r"[^a-z]", "", raw.lower())
        if rom == "aiueo":
            return True, "완벽해요! あ い う え お"

    # Partial hint if close length
    if len(tokens) == 5:
        wrong = []
        for idx, (got, exp) in enumerate(zip(tokens, target), start=1):
            if got != exp:
                wrong.append(f"{idx}번째는 {exp}")
        if wrong:
            return False, "힌트: " + ", ".join(wrong)

    return False, "정답: あ い う え お (romaji: a i u e o)"


# ---------------------------- Interactive Flow ---------------------------- #

class Session:
    def __init__(self, speed: str = "normal", explain: str = "normal") -> None:
        self.delay = {"fast": 0.0, "normal": 0.25, "slow": 0.6}.get(speed, 0.25)
        self.explain = explain
        self.score = 0
        self.total = 0

    def say(self, text: str) -> None:
        print(text)
        if self.delay > 0:
            time.sleep(self.delay)

    def ask(self, prompt: str, checker: Callable[[str], Tuple[bool, str]], reveal: Optional[str] = None) -> None:
        tries = 0
        self.total += 1
        while True:
            try:
                self.say(prompt)
                user = input("> ").strip()
            except KeyboardInterrupt:
                self.say("중단했습니다. 다시 이어가도 좋아요.")
                return

            ok, msg = checker(user)
            if ok:
                self.say(msg)
                self.score += 1
                break
            tries += 1
            if tries == 1:
                self.say(msg)
                self.say("한 번 더 시도해볼까요?")
            elif tries == 2:
                self.say(msg)
                if reveal:
                    self.say(f"참고: {reveal}")
                self.say("마지막으로 한 번 더!")
            else:
                self.say("다음엔 더 잘할 수 있어요. 넘어갈게요.")
                if reveal:
                    self.say(f"정답 예: {reveal}")
                break


def run_lesson_one(speed: str, explain: str, allow_romaji: bool, name_hint: Optional[str]) -> int:
    s = Session(speed=speed, explain=explain)

    s.say("세션 1 — 인사, 자기소개, 히라가나 모음")
    if explain == "normal":
        s.say("발음: a / i / u / e / o")
        s.say("핵심 인사: こんにちは | ありがとう | すみません | はい/いいえ")
        s.say("자기소개: わたしは [이름] です。 (watashi wa [name] desu)")

    # Q1: Greeting
    def q1_checker(user: str) -> Tuple[bool, str]:
        ok, msg = check_greeting(user, allow_romaji=allow_romaji)
        return ok, msg

    reveal_q1 = "こんにちは (romaji: konnichiwa)"
    s.ask("1) 일본어로 '안녕하세요'를 쓰세요.", q1_checker, reveal=reveal_q1)

    # Q2: Self-intro
    display_name = name_hint or "(당신의 이름)"
    prompt_q2 = f"2) '저는 {display_name}입니다'를 일본어로 쓰세요."

    def q2_checker(user: str) -> Tuple[bool, str]:
        ok, msg, _name = check_self_intro(user, allow_romaji=allow_romaji)
        return ok, msg

    reveal_q2 = "わたしは [이름] です。 (romaji: watashi wa [name] desu.)"
    s.ask(prompt_q2, q2_checker, reveal=reveal_q2)

    # Q3: Vowels
    def q3_checker(user: str) -> Tuple[bool, str]:
        ok, msg = check_vowels(user, allow_romaji=allow_romaji)
        return ok, msg

    reveal_q3 = "あ い う え お (romaji: a i u e o)"
    s.ask("3) a i u e o에 해당하는 히라가나 5개를 공백으로 적으세요.", q3_checker, reveal=reveal_q3)

    # Summary
    s.say("")
    s.say(f"점수: {s.score} / {s.total}")
    if s.score == s.total:
        s.say("아주 좋아요! 다음에는 ㄱ) 숫자 1-10, ㄴ) 간단한 질문 응답으로 가봐요.")
    else:
        s.say("충분히 잘했어요. 틀린 문제는 다음에 다시 복습해요.")

    return 0


# ---------------------------- Self-Check ---------------------------- #

def self_check() -> int:
    failures = []

    def ensure(cond: bool, label: str) -> None:
        if not cond:
            failures.append(label)

    # Greeting
    ok, _ = check_greeting("こんにちは", allow_romaji=False)
    ensure(ok, "greeting_hira_correct")
    ok, _ = check_greeting("こんにちわ", allow_romaji=False)
    ensure(not ok, "greeting_common_mistake_rejected")
    ok, _ = check_greeting("konnichiwa", allow_romaji=True)
    ensure(ok, "greeting_romaji_correct")

    # Self intro
    ok, _, _ = check_self_intro("わたしは ボブ です。", allow_romaji=False)
    ensure(ok, "selfintro_jp")
    ok, _, _ = check_self_intro("watashi wa bob desu.", allow_romaji=True)
    ensure(ok, "selfintro_romaji")
    ok, _, _ = check_self_intro("わたし ボブ です", allow_romaji=False)
    ensure(not ok, "selfintro_missing_wa")

    # Vowels
    ok, _ = check_vowels("あ い う え お", allow_romaji=False)
    ensure(ok, "vowels_hira")
    ok, _ = check_vowels("aiueo", allow_romaji=True)
    ensure(ok, "vowels_romaji")
    ok, _ = check_vowels("あ う い え お", allow_romaji=False)
    ensure(not ok, "vowels_wrong_order")

    if failures:
        print("SELF-CHECK FAILURES:")
        for f in failures:
            print("-", f)
        return 1

    print("Self-check passed.")
    return 0


# ---------------------------- CLI ---------------------------- #

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Japanese Tutor CLI — Lesson 1")
    parser.add_argument("--speed", choices=["fast", "normal", "slow"], default="normal", help="출력 속도 (기본: normal)")
    parser.add_argument("--explain", choices=["minimal", "normal"], default="normal", help="설명 양 (기본: normal)")
    parser.add_argument("--allow-romaji", action="store_true", help="정답으로 로마자 입력 허용")
    parser.add_argument("--name", default="", help="자기소개 예시용 이름 표시")
    parser.add_argument("--self-check", action="store_true", help="내장 테스트 실행 후 종료")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.self_check:
        return self_check()

    try:
        return run_lesson_one(speed=args.speed, explain=args.explain, allow_romaji=args.allow_romaji, name_hint=args.name)
    except KeyboardInterrupt:
        print("\n종료합니다. 수고하셨어요!")
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
