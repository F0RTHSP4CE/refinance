import { describe, expect, it } from 'vitest';
import { getActiveLinkTextProps, isLinkActive } from './utils';

describe('Navbar active-link behavior', () => {
  it('matches home only on exact root path', () => {
    expect(isLinkActive('/', '/')).toBe(true);
    expect(isLinkActive('/transactions', '/')).toBe(false);
  });

  it('matches section links on exact or nested paths', () => {
    expect(isLinkActive('/users', '/users')).toBe(true);
    expect(isLinkActive('/users/123', '/users')).toBe(true);
  });

  it('does not treat similarly prefixed paths as active', () => {
    expect(isLinkActive('/transactions-old', '/transactions')).toBe(false);
  });
});

describe('Navbar active text props', () => {
  it('uses burger-style active appearance', () => {
    expect(getActiveLinkTextProps(true)).toEqual({ c: 'var(--app-accent)', fw: 500 });
    expect(getActiveLinkTextProps(false)).toEqual({ c: 'var(--app-text-secondary)', fw: 500 });
  });
});
