// static/script.js
let currentWeekStart = new Date();
currentWeekStart.setDate(currentWeekStart.getDate() - (currentWeekStart.getDay() + 6) % 7);
let earliestLoadedWeek = new Date(currentWeekStart);
let latestLoadedWeek = new Date(currentWeekStart);

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function showSpinner() {
    document.getElementById('spinner').style.display = 'block';
}

function hideSpinner() {
    document.getElementById('spinner').style.display = 'none';
}

function getCurrentFamilyMemberId() {
    return document.getElementById('family-member-select').value;
}

function createWeekTable(weekData, isCurrentWeek = false) {
    const table = document.createElement('table');
    if (isCurrentWeek) {
        table.id = 'current-week';
    }
    const headerRow = table.insertRow();
    ['Date', 'AM', 'PM', 'Overnight', 'Plans', 'Family Plans'].forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });

    const isMobile = window.innerWidth <= 768;

    weekData.forEach(day => {
        const row = table.insertRow();
        const date = new Date(day.date);
        const isCurrentDay = date.toDateString() === new Date().toDateString();
        
        if (isCurrentDay) {
            row.classList.add('current-day');
        }

        const dateCell = row.insertCell();
        dateCell.classList.add('date-cell');
        dateCell.textContent = `${date.toLocaleDateString('en-US', { weekday: 'short' })} ${date.getDate()}/${date.getMonth() + 1}`;

        ['am', 'pm', 'overnight', 'plans', 'family_plans'].forEach(field => {
            const cell = row.insertCell();
            cell.classList.add(`${field}-cell`);
            cell.dataset.date = day.date;
            cell.dataset.field = field;
            cell.dataset.value = day[field] || '';

            if (isMobile && (field === 'plans' || field === 'family_plans')) {
                const icon = document.createElement('i');
                icon.className = 'fas fa-edit edit-icon';
                if (day[field] && day[field].trim() !== '') {
                    icon.classList.add('has-content');
                }
                icon.addEventListener('click', () => showPopup(day.date, field));
                cell.appendChild(icon);
            } else {
                let input;
                if (field === 'plans' || field === 'family_plans') {
                    input = document.createElement('textarea');
                    input.rows = 1;
                    input.addEventListener('input', autoResize);
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                    input.addEventListener('input', updateLocationStyle);
                }
                input.value = day[field] || '';
                input.dataset.field = field;
                input.dataset.date = day.date;
                input.addEventListener('change', (event) => saveEntry(event.target));
                cell.appendChild(input);

                if (input.tagName.toLowerCase() === 'textarea') {
                    setTimeout(() => autoResize.call(input), 0);
                } else {
                    updateLocationStyle.call(input);
                }
            }
        });
    });

    return table;
}

function showPopup(date, field) {
    const popup = document.getElementById('popup');
    const textarea = document.getElementById('popup-textarea');
    const saveButton = document.getElementById('popup-save');
    const cancelButton = document.getElementById('popup-cancel');

    const cell = document.querySelector(`td.${field}-cell[data-date="${date}"]`);
    const currentValue = cell ? cell.dataset.value || '' : '';

    textarea.value = currentValue;
    popup.style.display = 'block';

    saveButton.onclick = () => {
        const newValue = textarea.value;
        saveEntry({
            dataset: { date, field },
            value: newValue
        });
        popup.style.display = 'none';
    };

    cancelButton.onclick = () => {
        popup.style.display = 'none';
    };
}

function updateIconColor(date, field, value) {
    const cell = document.querySelector(`td.${field}-cell[data-date="${date}"]`);
    if (cell) {
        const icon = cell.querySelector('.edit-icon');
        if (icon) {
            if (value && value.trim() !== '') {
                icon.classList.add('has-content');
            } else {
                icon.classList.remove('has-content');
            }
        }
    }
}

function autoResize() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
}

function updateLocationStyle() {
    this.classList.remove('location-sk', 'location-ls');
    const value = this.value.trim().toUpperCase();
    if (value === 'SK') {
        this.classList.add('location-sk');
    } else if (value === 'LS') {
        this.classList.add('location-ls');
    }
}

function saveEntry(inputElement) {
    showSpinner();
    const data = {
        date: inputElement.dataset.date,
        [inputElement.dataset.field]: inputElement.value,
        family_member_id: getCurrentFamilyMemberId()
    };

    fetch('/save_entry', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Entry saved:', data);
        hideSpinner();
        updateCellData(inputElement.dataset.date, inputElement.dataset.field, inputElement.value);
        updateIconColor(inputElement.dataset.date, inputElement.dataset.field, inputElement.value);
    })
    .catch((error) => {
        console.error('Error:', error);
        hideSpinner();
    });
}

function updateCellData(date, field, value) {
    const cell = document.querySelector(`td.${field}-cell[data-date="${date}"]`);
    if (cell) {
        cell.dataset.value = value;
    }
}

function loadWeek(startDate, prepend = false, isCurrentWeek = false) {
    showSpinner();
    return fetch('/get_week', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            start_date: formatDate(startDate),
            family_member_id: getCurrentFamilyMemberId()
        }),
    })
    .then(response => response.json())
    .then(data => {
        const weekTable = createWeekTable(data, isCurrentWeek);
        if (prepend) {
            document.getElementById('planner').prepend(weekTable);
            window.scrollBy(0, weekTable.offsetHeight);
        } else {
            document.getElementById('planner').appendChild(weekTable);
        }
        hideSpinner();
        return weekTable;
    })
    .catch((error) => {
        console.error('Error:', error);
        hideSpinner();
        return null;
    });
}

function loadMoreWeeks() {
    const contentDiv = document.getElementById('content');
    const scrollPosition = contentDiv.scrollTop;
    const totalHeight = contentDiv.scrollHeight;
    const viewportHeight = contentDiv.clientHeight;

    if (scrollPosition < 200) {
        const newEarliestWeek = new Date(earliestLoadedWeek);
        newEarliestWeek.setDate(newEarliestWeek.getDate() - 7);
        loadWeek(newEarliestWeek, true);
        earliestLoadedWeek = newEarliestWeek;
    }

    if (scrollPosition + viewportHeight >= totalHeight - 200) {
        const newLatestWeek = new Date(latestLoadedWeek);
        newLatestWeek.setDate(newLatestWeek.getDate() + 7);
        loadWeek(newLatestWeek);
        latestLoadedWeek = newLatestWeek;
    }
}

function goToToday() {
    const currentWeekTable = document.getElementById('current-week');
    if (currentWeekTable) {
        currentWeekTable.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
        initialLoad();
    }
}



async function initialLoad() {
    const weeks = [];
    for (let i = -2; i <= 2; i++) {
        const weekStart = new Date(currentWeekStart);
        weekStart.setDate(weekStart.getDate() + (i * 7));
        const isCurrentWeek = i === 0;
        const weekTable = await loadWeek(weekStart, false, isCurrentWeek);
        weeks.push(weekTable);
        
        if (i < 0) earliestLoadedWeek = new Date(weekStart);
        if (i > 0) latestLoadedWeek = new Date(weekStart);
    }

    const currentWeekTable = document.getElementById('current-week');
    if (currentWeekTable) {
        currentWeekTable.scrollIntoView({ behavior: 'auto', block: 'start' });
    }
}

initialLoad();

document.addEventListener('DOMContentLoaded', function() {
    
  

    document.getElementById('content').addEventListener('scroll', loadMoreWeeks);
    document.getElementById('go-to-today').addEventListener('click', goToToday);
    
    document.getElementById('family-member-select').addEventListener('change', function() {
        document.getElementById('planner').innerHTML = '';
        initialLoad();
    });
});

window.onclick = function(event) {
    if (event.target == document.getElementById('statsModal')) {
        document.getElementById('statsModal').style.display = 'none';
    }
}

window.addEventListener('resize', () => {
    const isMobile = window.innerWidth <= 768;
    const planner = document.getElementById('planner');
    if (planner) {
        planner.innerHTML = '';
        initialLoad();
    }
});