export function fieldInput(value: unknown): string {
  if (value == null) return '';
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
}

export function editedValue(original: unknown, input: string): unknown {
  if (fieldInput(original) === input) return original;
  if (original == null || typeof original === 'string') return input;
  let parsed: unknown;
  try {
    parsed = JSON.parse(input);
  } catch {
    throw new Error('Enter a valid ' + (typeof original === 'object' ? 'JSON value' : typeof original) + '.');
  }
  if (parsed === null || typeof parsed !== typeof original || Array.isArray(parsed) !== Array.isArray(original)) {
    throw new Error('Keep the original field type when editing this value.');
  }
  return parsed;
}
