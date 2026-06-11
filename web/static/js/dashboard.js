// Глобальний стан фільтрів та кеш лічильників
let currentMode = '1min';
let currentType = 'all'; 
window.latestTotals = { all: 0, person: 0, transport: 0 };

// Запобіжник стану гонки (Race Condition) при завантаженні історії
window.isChartInitialized = false;

const ctx = document.getElementById('trafficChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], 
        datasets: [{
            label: 'Зафіксовано об\'єктів',
            data: [],
            borderColor: '#00ff00',
            backgroundColor: 'rgba(0, 255, 0, 0.1)',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: '#00ff00',
            fill: true,
            tension: 0.3
        }]
    },
    options: {
        responsive: true,
        animation: { duration: 300 },
        scales: {
            x: { ticks: { color: '#aaa', maxRotation: 45, maxTicksLimit: 15 }, grid: { display: false } },
            y: { ticks: { color: '#aaa', stepSize: 1 }, grid: { color: '#333' }, beginAtZero: true }
        },
        plugins: { legend: { display: false } }
    }
});

async function fetchChartData() {
    try {
        const response = await fetch(`/api/history?interval=${currentMode}&obj_type=${currentType}`);
        const data = await response.json();
        
        chart.data.labels = data.map(item => item.timestamp_group);
        chart.data.datasets[0].data = data.map(item => item.total_objects);
        chart.update();

        updateTotalBadge();
        window.isChartInitialized = true; // Дозволяємо WebSocket малювати нові точки
    } catch (error) {
        console.error("Помилка завантаження історії:", error);
    }
}

function setMode(mode, event) {
    currentMode = mode;
    const buttons = document.querySelectorAll('#time-filters .btn');
    buttons.forEach(btn => {
        btn.classList.remove('btn-outline-success', 'active');
        btn.classList.add('btn-outline-secondary');
    });
    
    const targetBtn = event ? event.currentTarget : document.querySelector(`[onclick*="setMode('${mode}'"]`);
    if (targetBtn) {
        targetBtn.classList.remove('btn-outline-secondary');
        targetBtn.classList.add('btn-outline-success', 'active');
    }
    
    window.isChartInitialized = false;
    fetchChartData();
}

function setType(type, event) {
    currentType = type;
    const buttons = document.querySelectorAll('#type-filters .btn');
    buttons.forEach(btn => {
        if(btn.classList.contains('active')) btn.classList.remove('active');
    });
    
    const targetBtn = event ? event.currentTarget : document.querySelector(`[onclick*="setType('${type}'"]`);
    if (targetBtn) targetBtn.classList.add('active');

    if (type === 'all') {
        chart.data.datasets[0].borderColor = '#00ff00';
        chart.data.datasets[0].backgroundColor = 'rgba(0, 255, 0, 0.1)';
        chart.data.datasets[0].pointBackgroundColor = '#00ff00';
    } else if (type === 'transport') {
        chart.data.datasets[0].borderColor = '#0dcaf0'; 
        chart.data.datasets[0].backgroundColor = 'rgba(13, 202, 240, 0.1)';
        chart.data.datasets[0].pointBackgroundColor = '#0dcaf0';
    } else if (type === 'person') {
        chart.data.datasets[0].borderColor = '#fd7e14'; 
        chart.data.datasets[0].backgroundColor = 'rgba(253, 126, 20, 0.1)';
        chart.data.datasets[0].pointBackgroundColor = '#fd7e14';
    }
    
    updateTotalBadge();
    window.isChartInitialized = false;
    fetchChartData();
}

function updateTotalBadge() {
    if (chart.data.datasets[0].data.length > 0) {
        const dataArray = chart.data.datasets[0].data;
        document.getElementById('total').innerText = dataArray[dataArray.length - 1];
    }
}

fetchChartData();

/* =====================================================================
 * WEBSOCKET (Backend-Driven UI)
 * Використовуються мітки (buckets) від сервера.
 * ===================================================================== */
const ws = new WebSocket(`ws://${window.location.host}/ws/stats`);

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (window.lastTotalObjects === undefined) {
        window.lastTotalObjects = data.total_objects;
        window.lastTotalPersons = data.total_persons;
        window.lastTotalTransport = data.total_transport;
    }

    window.latestTotals.all = data.total_objects;
    window.latestTotals.person = data.total_persons;
    window.latestTotals.transport = data.total_transport;
    
    updateTotalBadge();
    
    // Оновлення бейджа стану трафіку
    const stateEl = document.getElementById('state');
    stateEl.innerText = data.traffic_state;
    stateEl.className = `state-badge align-middle ${
        data.traffic_state === "FREE" ? "text-success border-success" :
        data.traffic_state === "NORMAL" ? "text-warning border-warning" : 
        "text-danger border-danger"
    }`;

    if (!window.isChartInitialized) return;

    // Готова мітка від сервера для поточного режиму
    const expectedLabel = data.buckets[currentMode];

    if (expectedLabel) {
        let delta = 0;
        
        if (currentType === 'all') delta = data.total_objects - window.lastTotalObjects;
        else if (currentType === 'person') delta = data.total_persons - window.lastTotalPersons;
        else if (currentType === 'transport') delta = data.total_transport - window.lastTotalTransport;
        
        const labels = chart.data.labels;
        const chartData = chart.data.datasets[0].data;
        
        if (labels.length > 0) {
            let shouldUpdateChart = false; // рендер тільки при змінах

            if (labels[labels.length - 1] === expectedLabel) {
                if (delta > 0) {
                    chartData[chartData.length - 1] += delta;
                    shouldUpdateChart = true;
                }
            } else {
                labels.push(expectedLabel);
                chartData.push(delta);
                
                if (labels.length > 20) {
                    labels.shift();
                    chartData.shift();
                }
                shouldUpdateChart = true;
            }

            if (shouldUpdateChart) {
                chart.update(); 
            }
        }
    }

    window.lastTotalObjects = data.total_objects;
    window.lastTotalPersons = data.total_persons;
    window.lastTotalTransport = data.total_transport;
};
