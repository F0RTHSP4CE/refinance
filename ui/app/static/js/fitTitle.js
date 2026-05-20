/**
 * Scales .home-title to fill the width of its parent without overflowing.
 * Runs on load and on every resize.
 */
(function () {
    const el = document.currentScript.previousElementSibling;
    if (!el || !el.classList.contains('home-title')) return;

    el.style.whiteSpace = 'nowrap';
    el.style.letterSpacing = '0';

    function fit() {
        const parent = el.parentElement;
        let lo = 8, hi = 300;
        while (hi - lo > 0.25) {
            const mid = (lo + hi) / 2;
            el.style.fontSize = mid + 'px';
            if (el.scrollWidth <= parent.clientWidth) lo = mid;
            else hi = mid;
        }
        el.style.fontSize = lo + 'px';
    }

    fit();

    let raf;
    window.addEventListener('resize', function () {
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(fit);
    });
})();
