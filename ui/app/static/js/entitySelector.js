document.addEventListener('DOMContentLoaded', function () {
    // Initialize all entity-selector widgets on the page
    const widgets = document.querySelectorAll('.entity-selector');
    widgets.forEach(widget => {
        const prefix = widget.id.replace('_widget', '');
        const idInput = document.getElementById(prefix + '_id');
        const nameInput = document.getElementById(prefix + '_name');
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
    });

    // Global click listener for search result items
    document.addEventListener('click', function (event) {
        if (event.target.matches('.search-result-item')) {
            const name = event.target.getAttribute('x-name');
            const id = event.target.getAttribute('x-id');
            const container = event.target.closest('div[id$="_search_results"]');
            if (container) {
                const prefix = container.id.replace('_search_results', '');
                document.getElementById(prefix + '_name').value = name;
                document.getElementById(prefix + '_id').value = id;
                document.getElementById(prefix + '_id').focus();
                container.innerHTML = '';
            }
        }
    });
});
