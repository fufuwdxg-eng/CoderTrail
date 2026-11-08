"""Runner fixture, not a curated exercise or a quality-rated external source."""
import re
import sys

tokens = re.findall(r'[^ \t\r\n\v\f]+', sys.stdin.read())
if len(tokens) > 10000 or any(not re.fullmatch(r'[+-]?[0-9]+', s) for s in tokens):
    print('INVALID', file=sys.stderr)
    raise SystemExit(2)
try:
    # Normalize leading zeroes before conversion to avoid interpreter digit limits.
    normalized = [(s.startswith('-'), s.lstrip('+-').lstrip('0') or '0') for s in tokens]
    if any(len(digits) > 4 for _, digits in normalized):
        raise ValueError('out of range')
    values = [(-1 if negative else 1) * int(digits) for negative, digits in normalized]
    if any(abs(n) > 1000 for n in values):
        raise ValueError('out of range')
except ValueError:
    print('INVALID', file=sys.stderr)
    raise SystemExit(2)
print(sum(values))
