document.addEventListener('DOMContentLoaded', function () {
    const selectResultItem = (item) => {
        const name = item.getAttribute('x-name');
        const id = item.getAttribute('x-id');
        const container = item.closest('div[id$="_search_results"]');
        if (!container) return;

        const prefix = container.id.replace('_search_results', '');
        const nameInput = document.getElementById(prefix + '_name');
        const idInput = document.getElementById(prefix + '_id');
        if (!nameInput || !idInput) return;

        nameInput.value = name || '';
        idInput.value = id || '';
        container.innerHTML = '';
        idInput.focus();
    };

    // Initialize all entity-selector widgets on the page
    const widgets = document.querySelectorAll('.entity-selector');
    widgets.forEach(widget => {
        const prefix = widget.id.replace('_widget', '');
        const idInput = document.getElementById(prefix + '_id');
        const nameInput = document.getElementById(prefix + '_name');
        const resultsContainer = document.getElementById(prefix + '_search_results');
        const fetchUrl = widget.getAttribute('data-fetch-url');

        // On page load, if there's an initial id value, fetch the corresponding entity name
        if (idInput.value.trim() !== '') {
            fetch(`${fetchUrl}/${idInput.value}`)
                .then(response => response.json())
                .then(data => {
                    if (data.id) {
                        nameInput.value = data.name;
                    } else {
                        console.warn('Entity not found for pre-populated id:', idInput.value);
                    }
                })
                .catch(error => {
                    console.error('Error fetching entity name:', error);
                });
        }

        // Listen for changes on the ID input to update the name via AJAX
        idInput.addEventListener('change', function () {
            const entityId = idInput.value;
            if (entityId) {
                fetch(`${fetchUrl}/${entityId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.id) {
                            nameInput.value = data.name;
                        } else {
                            alert('Entity not found');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching entity name:', error);
                        alert('Error fetching entity name');
                    });
            }
        });

            nameInput.addEventListener('keydown', function (event) {
                const items = resultsContainer ? Array.from(resultsContainer.querySelectorAll('.search-result-item')) : [];
                if (!items.length) return;

                const activeIndex = items.findIndex(item => item === document.activeElement);

                if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    const nextIndex = activeIndex < 0 ? 0 : Math.min(activeIndex + 1, items.length - 1);
                    items[nextIndex].focus();
                    return;
                }

                if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    if (activeIndex <= 0) {
                        nameInput.focus();
                    } else {
                        items[activeIndex - 1].focus();
                    }
                    return;
                }

                if (event.key === 'Enter') {
                    event.preventDefault();
                    const currentItem = activeIndex >= 0 ? items[activeIndex] : items[0];
                    if (currentItem) {
                        selectResultItem(currentItem);
                    }
                }
            });
    });

    // Global click listener for search result items
    document.addEventListener('click', function (event) {
        const resultItem = event.target.closest('.search-result-item');
        if (resultItem) {
                event.preventDefault();
            selectResultItem(resultItem);
            }
        });

        document.addEventListener('keydown', function (event) {
        const resultItem = event.target.closest('.search-result-item');
        if (!resultItem) return;

            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
            selectResultItem(resultItem);
                return;
            }

            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
            const container = resultItem.closest('div[id$="_search_results"]');
                if (!container) return;
                const items = Array.from(container.querySelectorAll('.search-result-item'));
            const currentIndex = items.findIndex(item => item === resultItem);
                if (currentIndex < 0) return;

                if (event.key === 'ArrowDown') {
                    const nextIndex = Math.min(currentIndex + 1, items.length - 1);
                    items[nextIndex].focus();
                } else {
                    if (currentIndex === 0) {
                        const prefix = container.id.replace('_search_results', '');
                        const nameInput = document.getElementById(prefix + '_name');
                        if (nameInput) nameInput.focus();
                    } else {
                        items[currentIndex - 1].focus();
                    }
                }
        }
    });
});
