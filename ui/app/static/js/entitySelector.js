document.addEventListener('DOMContentLoaded', function () {
    // Initialize all entity-selector widgets on the page
    const widgets = document.querySelectorAll('.entity-selector');
    widgets.forEach(widget => {
        const prefix = widget.id.replace('_widget', '');
        const idInput = document.getElementById(prefix + '_id');
        const nameInput = document.getElementById(prefix + '_name');
        const fetchUrl = widget.getAttribute('data-fetch-url');
        let selectedIndex = -1;

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
        
        // Add keyboard navigation for dropdown
        nameInput.addEventListener('keydown', function(event) {
            const resultsContainer = document.getElementById(prefix + '_search_results');
            const items = resultsContainer.querySelectorAll('.search-result-item');
            
            if (items.length === 0) return;
            
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                updateSelection(items, selectedIndex);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection(items, selectedIndex);
            } else if (event.key === 'Enter' && selectedIndex >= 0) {
                event.preventDefault();
                const selectedItem = items[selectedIndex];
                if (selectedItem) {
                    const name = selectedItem.getAttribute('x-name');
                    const id = selectedItem.getAttribute('x-id');
                    nameInput.value = name;
                    idInput.value = id;
                    resultsContainer.innerHTML = '';
                    selectedIndex = -1;
                }
            }
        });
        
        function updateSelection(items, index) {
            items.forEach((item, i) => {
                if (i === index) {
                    item.style.backgroundColor = '#e9ecef';
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.style.backgroundColor = '';
                }
            });
        }
    });

    // Global click listener for search result items and closing dropdowns
    document.addEventListener('click', function (event) {
        if (event.target.matches('.search-result-item')) {
            event.preventDefault();
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
        } else if (!event.target.closest('.entity-selector')) {
            // Close all dropdowns when clicking outside
            document.querySelectorAll('.search-results-dropdown').forEach(dropdown => {
                dropdown.innerHTML = '';
            });
        }
    });
    
    // Handle escape key to close dropdowns
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            document.querySelectorAll('.search-results-dropdown').forEach(dropdown => {
                dropdown.innerHTML = '';
            });
        }
    });
});
