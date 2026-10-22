"""Offline, privacy-preserving declared-label support check."""

import json
import sys
from pathlib import Path

INVALID = '{"status":"invalid_input"}\n'
MAX_LABELS = 10_000
MAX_MINIMUM = 1_000_000


class InputError(ValueError):
    """An input document violates the public file contract."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate key")
        result[key] = value
    return result


def _constant(_value):
    raise InputError("non-finite number")


def _check_unicode(value):
    if isinstance(value, str):
        try:
            value.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise InputError("invalid Unicode scalar") from exc
    elif isinstance(value, list):
        for item in value:
            _check_unicode(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_unicode(key)
            _check_unicode(item)


def _decode(text):
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
        _check_unicode(value)
        return value
    except (ValueError, RecursionError) as exc:
        raise InputError("invalid JSON") from exc


def _read_utf8(path):
    try:
        return Path(path).read_bytes().decode("utf-8", "strict")
    except (OSError, UnicodeError, ValueError) as exc:
        raise InputError("unreadable UTF-8 input") from exc


def _policy(text):
    value = _decode(text)
    if not isinstance(value, dict) or set(value) != {"labels", "minimum"}:
        raise InputError("invalid policy shape")
    labels = value["labels"]
    minimum = value["minimum"]
    if not isinstance(labels, list) or not 1 <= len(labels) <= MAX_LABELS:
        raise InputError("invalid labels")
    if any(not isinstance(label, str) or not label for label in labels):
        raise InputError("invalid label")
    if len(set(labels)) != len(labels):
        raise InputError("duplicate label")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 0 <= minimum <= MAX_MINIMUM:
        raise InputError("invalid minimum")
    return labels, minimum


def _rows(text, labels):
    allowed = set(labels) if labels is not None else None
    indices = {label: index for index, label in enumerate(labels or [])}
    seen = set()
    record_count = 0
    # JSON Lines delimiters are only CR and LF. Accept CRLF and one final terminator.
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        if not line:
            raise InputError("blank JSONL record")
        value = _decode(line)
        if not isinstance(value, dict) or set(value) != {"id", "label"}:
            raise InputError("invalid row shape")
        record_id, label = value["id"], value["label"]
        if not isinstance(record_id, str) or not record_id or record_id in seen:
            raise InputError("invalid or duplicate row id")
        if not isinstance(label, str) or (allowed is not None and label not in allowed):
            raise InputError("unknown row label")
        seen.add(record_id)
        record_count += 1
    return record_count


def evaluate(policy_text, rows_text):
    """Validate both documents independently, returning output fields or None."""
    labels = minimum = None
    try:
        labels, minimum = _policy(policy_text)
    except InputError:
        pass
    rows_result = None
    # Validate rows fully even when policy parsing failed. A private placeholder lets
    # the row parser observe syntax, duplicate keys, JSON depth, and row object shape.
    try:
        rows_result = _rows(rows_text, labels)
    except InputError:
        pass
    if labels is None or rows_result is None:
        return None
    record_count = rows_result
    # Repeat count validation here using the supplied threshold; internal row parsing
    # never exposes label counts in the CLI result.
    counts = [0] * len(labels)
    indices = {label: index for index, label in enumerate(labels)}
    for line in rows_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line:
            row = _decode(line)
            counts[indices[row["label"]]] += 1
    insufficient = [i + 1 for i, count in enumerate(counts) if count < minimum]
    return {"status": "insufficient_support" if insufficient else "valid",
            "record_count": record_count, "insufficient_label_indices": insufficient}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["-h"], ["--help"]):
        sys.stdout.write("usage: label-support-gate POLICY.json ROWS.jsonl\n\nCheck declared-label support using a policy and JSON Lines rows.\n")
        return 0
    if len(args) != 2 or any(arg.startswith("-") for arg in args):
        sys.stdout.write(INVALID)
        return 2
    # Read/validate both files independently even if opening or decoding one fails.
    try:
        policy_text = _read_utf8(args[0])
    except InputError:
        policy_text = None
    try:
        rows_text = _read_utf8(args[1])
    except InputError:
        rows_text = None
    if policy_text is None or rows_text is None:
        sys.stdout.write(INVALID)
        return 2
    result = evaluate(policy_text, rows_text)
    if result is None:
        sys.stdout.write(INVALID)
        return 2
    sys.stdout.write(json.dumps(result, ensure_ascii=True, separators=(",", ":")) + "\n")
    return 1 if result["status"] == "insufficient_support" else 0


if __name__ == "__main__":
    raise SystemExit(main())
