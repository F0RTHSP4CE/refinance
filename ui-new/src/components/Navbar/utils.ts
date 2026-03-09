export const isLinkActive = (pathname: string, to: string) => {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
};

export const getActiveLinkTextProps = (isActive: boolean) => ({
  c: isActive ? 'var(--app-accent)' : 'var(--app-text-secondary)',
  fw: 500,
});
