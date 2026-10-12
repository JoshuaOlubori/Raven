import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn utility', () => {
  it('joins class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('foo', true && 'bar')).toBe('foo bar');
    expect(cn('foo', false && 'bar')).toBe('foo');
  });

  it('merges tailwind classes', () => {
    expect(cn('p-2 p-4')).toBe('p-4');
  });
});
