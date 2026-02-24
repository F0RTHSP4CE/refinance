export const isLinkActive = (pathname: string, to: string) => {
  if (to === '/') return pathname === '/';
  return pathname === to || pathname.startsWith(`${to}/`);
};

export const getActiveLinkTextProps = (isActive: boolean) => ({
  c: isActive ? 'green.5' : undefined,
  fw: isActive ? 600 : 400,
});
