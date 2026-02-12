(function () {
  const toggleButton = document.querySelector('.mobile-menu-toggle');
  const menu = document.getElementById('mobile-menu');
  const closeButton = document.querySelector('.mobile-menu-close');

  if (!toggleButton || !menu || !closeButton) return;

  let lastActiveElement = null;

  function openMenu() {
    lastActiveElement = document.activeElement;
    menu.hidden = false;
    toggleButton.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
    closeButton.focus();
  }

  function closeMenu() {
    menu.hidden = true;
    toggleButton.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
    if (lastActiveElement && typeof lastActiveElement.focus === 'function') {
      lastActiveElement.focus();
    } else {
      toggleButton.focus();
    }
  }

  toggleButton.addEventListener('click', function (event) {
    event.preventDefault();
    if (menu.hidden) openMenu();
    else closeMenu();
  });

  closeButton.addEventListener('click', function (event) {
    event.preventDefault();
    closeMenu();
  });

  menu.addEventListener('click', function (event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    if (target.closest('.mobile-menu-title')) {
      closeMenu();
      return;
    }

    if (target.closest('a')) {
      closeMenu();
      return;
    }

    if (target === menu) {
      closeMenu();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !menu.hidden) {
      event.preventDefault();
      closeMenu();
    }
  });
})();
