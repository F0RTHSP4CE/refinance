/**
 * Date Toggle Functionality
 * Allows toggling between human-readable dates and original ISO format
 * Clicking any date toggles all dates on the page
 */

document.addEventListener('DOMContentLoaded', function () {
    // Find all elements with human-readable dates
    const dateElements = document.querySelectorAll('span.human-date[title]');

    // Global state for all dates
    let isShowingOriginal = false;

    // Store original data for each element
    const dateData = [];

    dateElements.forEach(function (element, index) {
        const originalDate = element.getAttribute('title');
        if (originalDate && (originalDate.includes('T') || originalDate.match(/\d{4}-\d{2}-\d{2}/))) {
            const humanReadableText = element.textContent;

            // Store data for this element
            dateData[index] = {
                element: element,
                humanReadableText: humanReadableText,
                originalDate: originalDate
            };

            // Add click event listener
            element.addEventListener('click', function () {
                toggleAllDates();
            });
        }
    });

    function toggleAllDates() {
        isShowingOriginal = !isShowingOriginal;

        dateData.forEach(function (data) {
            if (data) {
                if (isShowingOriginal) {
                    data.element.textContent = formatOriginalDate(data.originalDate);
                } else {
                    data.element.textContent = data.humanReadableText;
                }
            }
        });
    }

    function formatOriginalDate(dateString) {
        try {
            // Try to parse and format the date nicely
            const date = new Date(dateString);
            if (!isNaN(date.getTime())) {
                // Format as local date and time
                return date.toLocaleString();
            }
        } catch (e) {
            // If parsing fails, return the original string
        }
        return dateString;
    }
});
