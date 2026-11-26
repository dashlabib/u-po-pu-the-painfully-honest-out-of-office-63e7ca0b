#!/usr/bin/env python3
"""Publish the one-sentence entry for the make.fun bounty
"The Painfully Honest Out-of-Office".

The sentence is a brutally honest but still polite out-of-office
auto-reply: the sender admits leaving with 400 unread emails and
no plan at all, then thanks the reader for their patience while
they dig their way back. This program checks it against the bounty
gate (one sentence, 1-200 characters, single line, printable text
only) and writes it to entry.txt in the output directory. Standard
library only: no network access, no clock reads, no randomness, so
two runs always produce identical output.

The output directory is ``$MAKEFUN_OUTPUT_DIR`` when set, else
``/output``. Pass ``--output-dir <dir>`` to choose it on the command
line, ``--verify-only`` to check the sentence without writing
anything, or ``--self-test`` to prove determinism across two runs.
"""

import argparse
import os
import sys
import tempfile
import unicodedata
from pathlib import Path

MAX_CHARS = 200

SENTENCE = (
    "I'm out of the office until Monday, and to be honest I left "
    "with 400 unread emails and no plan at all \u2014 thank you for "
    "your patience while I dig my way back to you."
)


def validate(text: str) -> None:
    """Enforce the bounty gate; raise SystemExit with a reason."""
    if not text or text.isspace():
        raise SystemExit("entry is empty or only white space")
    if len(text) > MAX_CHARS:
        raise SystemExit(
            f"entry is {len(text)} characters, over the {MAX_CHARS} limit"
        )
    if "\n" in text or "\r" in text:
        raise SystemExit("entry must be a single line")
    if "  " in text:
        raise SystemExit("entry must not contain double spaces")
    if text != text.strip():
        raise SystemExit("entry must not start or end with whitespace")
    bad = [
        ch
        for ch in text
        if ch in ("\u2028", "\u2029", "\u00a0")
        or unicodedata.category(ch).startswith("C")
        or not ch.isprintable()
    ]
    if bad:
        raise SystemExit(
            "entry contains control or non-printable characters: "
            + ", ".join(f"U+{ord(ch):04X}" for ch in sorted(set(bad)))
        )
    if not any(ch.isalnum() for ch in text):
        raise SystemExit("entry must contain letters or digits")
    ends = sum(text.count(mark) for mark in ".!?")
    if ends != 1 or text[-1] not in ".!?":
        raise SystemExit("entry must be exactly one sentence")


def publish(out_dir: Path) -> Path:
    validate(SENTENCE)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "entry.txt"
    # Write atomically: a crash mid-write must never leave a
    # half-written entry.txt behind for the judge to read.
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=out_dir, delete=False, prefix=".entry-"
    ) as tmp:
        tmp.write(SENTENCE + "\n")
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, out_path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    published = out_path.read_text(encoding="utf-8")
    if published != SENTENCE + "\n":
        raise SystemExit("published entry does not match the sentence")
    return out_path


def self_test() -> int:
    """Run the program twice into two fresh dirs; outputs must match."""
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        one = publish(Path(first))
        two = publish(Path(second))
        first_bytes = one.read_bytes()
        second_bytes = two.read_bytes()
        if first_bytes != second_bytes:
            print("self-test FAILED: outputs differ", file=sys.stderr)
            return 1
        print(
            f"self-test passed: {len(first_bytes)} bytes, "
            f"{len(SENTENCE)} characters, identical across two runs"
        )
        return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish the Painfully Honest Out-of-Office entry."
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"),
        help="directory to write entry.txt into (default: $MAKEFUN_OUTPUT_DIR or /output)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="validate the sentence without writing anything",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="prove determinism by running the publish step twice",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.verify_only:
        validate(SENTENCE)
        print(f"entry valid: {len(SENTENCE)} characters, one sentence")
        return 0
    out_path = publish(Path(args.output_dir))
    print(f"wrote {out_path} ({len(SENTENCE)} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
