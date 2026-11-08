// Runner fixture only. Do not register as an externally curated source.
import { readFileSync } from 'node:fs';
const text = readFileSync(0, 'utf8');
const tokens = text.split(/[ \t\r\n\v\f]+/).filter(Boolean);
const values = tokens.map(Number);
if (tokens.length > 10000 || tokens.some(s => !/^[+-]?[0-9]+$/.test(s)) ||
    values.some(n => !Number.isSafeInteger(n) || Math.abs(n) > 1000)) {
  process.stderr.write('INVALID\n');
  process.exitCode = 2;
} else {
  process.stdout.write(`${values.reduce((a, b) => a + b, 0)}\n`);
}
