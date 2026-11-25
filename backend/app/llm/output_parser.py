r"""
Robust JSON extraction and parsing helpers for messy LLM output.

Replaces the old greedy `re.search(r'{[\s\S]*}', text)` approach, which broke
on nested braces, code fences, prose surrounding the JSON, and truncated
responses. The scanner below is deterministic:

  1. Markdown code fences (```json / ``` / any language tag) are stripped.
  2. A balanced scanner walks the text tracking string-literal state, escape
     sequences, and brace/bracket depth, yielding every balanced JSON
     object/array substring in order of appearance.
  3. Candidates are tried with `json.loads`; the first that parses wins.
  4. If every candidate fails, a small repair function attempts to close
     open string literals / brackets on a truncated candidate.
  5. Fallback: the raw cleaned text (previous greedy-extraction behaviour).
"""

import json
import re
from typing import Any, Iterator, List, Optional, Union


# ---------------------------------------------------------------------------
# Markdown fence stripping (handles ```json, ```JSON, plain ```, etc.)
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\s*([\s\S]*?)```", re.IGNORECASE)


def strip_markdown_fences(text: str) -> str:
    """
    Replace markdown code fences with their inner content so a ```json …```
    block becomes a plain JSON literal that the balanced scanner can find.
    """
    if not text:
        return ""
    return _FENCE_RE.sub(lambda m: m.group(1), text)


# ---------------------------------------------------------------------------
# Balanced scanner — tracks string literals, escapes, and bracket depth
# ---------------------------------------------------------------------------

_OPEN_TO_CLOSE = {"{": "}", "[": "]"}
_CLOSERS = set("}]")
_STRUCTURAL = set('{[,:}"')


def _scan_state(text: str) -> tuple:
    r"""
    Scan `text` and return (stack_of_open_brackets, in_string, escaped_dangling).
    `in_string`  — the text ends inside an unterminated string literal.
    `escaped_dangling` — the text ends inside an escape sequence (trailing `\`).
    """
    stack: List[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in _OPEN_TO_CLOSE:
                stack.append(ch)
            elif ch in _CLOSERS and stack:
                if ch == _OPEN_TO_CLOSE[stack[-1]]:
                    stack.pop()
                else:
                    # Mismatched closer — structure is wrong, stop trusting it.
                    break
    return stack, in_string, escaped


def extract_json_candidates(text: Union[str, None]) -> Iterator[str]:
    """
    Yield every balanced top-level JSON object/array substring found in `text`,
    in order of appearance. Handles:
      - nested braces/brackets (correct depth counting),
      - braces and quotes *inside* string literals (incl. escaped \\" and \\\\),
      - prose/labels before or after the JSON,
      - markdown ```json / plain ``` fenced blocks.

    Truncated output is NOT yielded here — pass the raw text to
    `repair_truncated_json` for that case.
    """
    if not text or not isinstance(text, str):
        return
    cleaned = strip_markdown_fences(text)
    n = len(cleaned)
    i = 0
    while i < n:
        if cleaned[i] not in ("{", "["):
            i += 1
            continue

        start = i
        depth = 0
        stack: List[str] = []
        in_string = False
        escaped = False
        j = i
        while j < n:
            c = cleaned[j]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c in _OPEN_TO_CLOSE:
                    stack.append(c)
                    depth += 1
                elif c in _CLOSERS and stack:
                    if c != _OPEN_TO_CLOSE[stack[-1]]:
                        break  # mismatched closer — not valid JSON here
                    stack.pop()
                    depth -= 1
                    if depth == 0:
                        yield cleaned[start:j + 1]
                        i = j  # outer loop advances past this candidate
                        break
            j += 1
        i += 1


def extract_json_block(text: Union[str, None]) -> Optional[str]:
    """
    Return the best single JSON substring from `text`, or None when nothing
    plausible was found. Order of preference:
      1. The first candidate that `json.loads` accepts.
      2. A repaired version of any candidate (for truncated output).
      3. A repaired version of the text starting at the first bracket.
      4. None.
    """
    first_candidate: Optional[str] = None
    for candidate in extract_json_candidates(text):
        if first_candidate is None:
            first_candidate = candidate
        try:
            json.loads(candidate)
            return candidate
        except (json.JSONDecodeError, ValueError):
            continue

    for candidate in (first_candidate,):
        if candidate is not None:
            repaired = repair_truncated_json(candidate)
            if repaired is not None:
                return repaired

    if text and isinstance(text, str):
        cleaned = strip_markdown_fences(text).strip()
        for ch in ("{", "["):
            idx = cleaned.find(ch)
            if idx != -1:
                repaired = repair_truncated_json(cleaned[idx:])
                if repaired is not None:
                    return repaired
                break
    return None


# ---------------------------------------------------------------------------
# Truncation repair — close open string literals and brackets
# ---------------------------------------------------------------------------

def _parseable(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _attempt_close(body: str) -> Optional[str]:
    """
    Close the fragment `body` assuming it is truncated: drop dangling escapes,
    close an unterminated string, strip dangling separators, then append the
    missing closers in stack order. Returns a JSON-parsable string or None.
    """
    s = body
    # 1. Drop a dangling escape at the cut point.
    _, in_string, escaped = _scan_state(s)
    if escaped:
        s = s[:-1]

    # 2. Close an unterminated string literal.
    _, in_string, _ = _scan_state(s)
    if in_string:
        s += '"'

    # 3. Strip dangling separators at the cut point (", {…: → {).
    s = s.rstrip()
    if s.endswith(":"):
        s = s[:-1].rstrip()
        if s.endswith(","):
            s = s[:-1].rstrip()
    elif s.endswith(","):
        s = s[:-1].rstrip()

    # 4. Append missing closers in stack order (re-scan after edits).
    stack, in_string, _ = _scan_state(s)
    if in_string:
        return None
    repaired = s + "".join(_OPEN_TO_CLOSE[op] for op in reversed(stack))
    return repaired if _parseable(repaired) else None


def _trim_last_token(text: str) -> Optional[str]:
    """
    Remove one trailing "unit" from `text` so repair can retry:
      - a separator / lone closer / dangling opener (one char),
      - a complete trailing quoted string,
      - a partially-typed bare literal (word / number after the last
        structural character, e.g. `tru` or `12.5`).
    """
    s = text.rstrip()
    if not s:
        return None
    last = s[-1]
    if last in '{[,:}]':
        return s[:-1]
    if last == '"':
        # Cut back to the opening quote of the trailing string literal.
        i = len(s) - 1
        while i >= 0:
            if s[i] == '"' and (i == 0 or s[i - 1] != "\\"):
                return s[:i].rstrip()
            i -= 1
        return s[:-1]
    if last == "\\":
        return s[:-1]
    # Bare literal: cut back to the previous structural character.
    i = len(s) - 1
    while i >= 0 and s[i] not in _STRUCTURAL:
        i -= 1
    return s[:i + 1]


def repair_truncated_json(fragment: Union[str, None]) -> Optional[str]:
    """
    Best-effort repair of a truncated JSON fragment so it parses:
      - drops dangling escapes and separators at the cut point,
      - closes open string literals with `\"`,
      - appends `}`/`]` closers in stack order,
      - trims the last complete token (quoted key/value, bare literal, …)
        and retries a few times when the naive close does not parse.

    Returns a JSON-parsable string, or None when the fragment has no
    plausible JSON structure.
    """
    if not fragment or not isinstance(fragment, str):
        return None

    stripped = fragment.strip()
    if not any(ch in stripped for ch in "{["):
        return None  # no container to repair — caller should keep raw text

    body = stripped
    for _ in range(10):
        closed = _attempt_close(body)
        if closed is not None:
            return closed
        body = _trim_last_token(body)
        if body is None:
            break
    return None


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------

def parse_llm_json(text: Union[str, None]) -> Any:
    """
    Parse a (possibly messy) LLM response into a Python object, or {} when
    nothing usable can be recovered.

    Order of operations:
      1. None/empty → {}.
      2. `json.loads` on the raw text, then on fence-stripped text.
      3. Balanced-scanner candidates → first that parses wins.
      4. Repair truncated candidates → try again.
      5. Fallback: {}.
    """
    if text is None:
        return {}
    if isinstance(text, (dict, list)):
        return text

    if not isinstance(text, str):
        text = str(text)
    if not text.strip():
        return {}

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    cleaned = strip_markdown_fences(text).strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    block = extract_json_block(cleaned)
    if block is not None:
        try:
            return json.loads(block)
        except (json.JSONDecodeError, ValueError):
            pass

    return {}


class BaseOutputParser:
    """Thin parser facade kept for API compatibility."""

    def extract_json(self, text: Union[str, None]) -> Any:
        """Extract + parse the first usable JSON value from `text`."""
        return parse_llm_json(text)

    def extract_json_block(self, text: Union[str, None]) -> Optional[str]:
        """Return the raw recovered JSON substring (or repaired truncation)."""
        return extract_json_block(text)
