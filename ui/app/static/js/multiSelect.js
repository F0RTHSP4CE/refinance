// Enhanced multi-select behavior - allows selection without holding Ctrl
document.addEventListener('DOMContentLoaded', function () {
    const multiSelects = document.querySelectorAll('select[multiple]');

    multiSelects.forEach(function (select) {
        // Add helpful text
        const helpText = document.createElement('div');
        helpText.className = 'multi-select-help';
        helpText.textContent = 'Click to select/deselect multiple options';
        select.parentNode.appendChild(helpText);

        select.addEventListener('mousedown', function (e) {
            e.preventDefault();

            const option = e.target;
            if (option.tagName !== 'OPTION') return;

            // Toggle the option's selected state
            option.selected = !option.selected;

            // Trigger change event
            select.dispatchEvent(new Event('change', { bubbles: true }));

            // Prevent the default browser behavior
            return false;
        });

        // Prevent scrolling when clicking on options
        select.addEventListener('scroll', function (e) {
            e.preventDefault();
        });
    });
});
