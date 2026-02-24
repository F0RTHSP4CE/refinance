import { describe, expect, it } from 'vitest';
import { getActiveLinkTextProps, isLinkActive } from './utils';

describe('Navbar active-link behavior', () => {
  it('matches home only on exact root path', () => {
    expect(isLinkActive('/', '/')).toBe(true);
    expect(isLinkActive('/transactions', '/')).toBe(false);
  });

  it('matches section links on exact or nested paths', () => {
    expect(isLinkActive('/deposits', '/deposits')).toBe(true);
    expect(isLinkActive('/deposits/123', '/deposits')).toBe(true);
  });

  it('does not treat similarly prefixed paths as active', () => {
    expect(isLinkActive('/transactions-old', '/transactions')).toBe(false);
  });
});

describe('Navbar active text props', () => {
  it('uses burger-style active appearance', () => {
    expect(getActiveLinkTextProps(true)).toEqual({ c: 'green.5', fw: 600 });
    expect(getActiveLinkTextProps(false)).toEqual({ c: undefined, fw: 400 });
  });
});
