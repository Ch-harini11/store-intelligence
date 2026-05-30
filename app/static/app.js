// Constant configuration
const STORE_ID = "store_001";
let funnelChart = null;

// Initialize charts on page load
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    refreshDashboard();
    
    // Auto-poll every 3 seconds for real-time intelligence feel
    setInterval(refreshDashboard, 3000);
});

function initCharts() {
    const ctx = document.getElementById("funnelChart").getContext("2d");
    
    funnelChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['1. Entered Store', '2. Visited Shelves', '3. Billed Counter'],
            datasets: [{
                label: 'Shopper Count',
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(6, 214, 160, 0.65)',
                    'rgba(58, 134, 200, 0.65)',
                    'rgba(157, 78, 221, 0.65)'
                ],
                borderColor: [
                    '#06d6a0',
                    '#3a86c8',
                    '#9d4edd'
                ],
                borderWidth: 1.5,
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y', // Make it horizontal
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#ffffff', font: { weight: 'bold' } }
                }
            }
        }
    });
}

async function refreshDashboard() {
    try {
        await Promise.all([
            fetchMetrics(),
            fetchFunnel(),
            fetchOccupancy(),
            fetchAnomalies()
        ]);
        document.getElementById("status-text").textContent = "Live Feed Connected";
        document.getElementById("system-status").style.background = "rgba(6, 214, 160, 0.1)";
        document.getElementById("system-status").style.borderColor = "rgba(6, 214, 160, 0.25)";
    } catch (error) {
        console.error("Dashboard refresh failed:", error);
        document.getElementById("status-text").textContent = "Server Offline";
        document.getElementById("system-status").style.background = "rgba(239, 71, 111, 0.1)";
        document.getElementById("system-status").style.borderColor = "rgba(239, 71, 111, 0.25)";
    }
}

async function fetchMetrics() {
    const res = await fetch(`/stores/${STORE_ID}/metrics`);
    if (!res.ok) throw new Error("Metrics fetch error");
    const data = await res.json();
    
    document.getElementById("val-footfall").textContent = data.footfall.toLocaleString();
    document.getElementById("val-unique").textContent = data.unique_visitors.toLocaleString();
    
    // Format Dwell Time
    const dwellSeconds = Math.round(data.avg_dwell_time_ms / 1000);
    const m = Math.floor(dwellSeconds / 60);
    const s = dwellSeconds % 60;
    document.getElementById("val-dwell").textContent = `${m}m ${s}s`;
    
    // Format Peak Hour
    const hour = data.peak_hour;
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const dispHour = hour % 12 === 0 ? 12 : hour % 12;
    document.getElementById("val-peak").textContent = `${dispHour}:00 ${ampm}`;
}

async function fetchFunnel() {
    const res = await fetch(`/stores/${STORE_ID}/funnel`);
    if (!res.ok) throw new Error("Funnel fetch error");
    const data = await res.json();
    
    // Update funnel conversion text rate
    document.getElementById("funnel-conversion-rate").textContent = `Conversion Rate: ${data.conversion_rate.toFixed(1)}%`;
    
    // Update funnel chart
    if (funnelChart) {
        funnelChart.data.datasets[0].data = [
            data.visitors_entered,
            data.visitors_visited_shelf,
            data.visitors_billed
        ];
        funnelChart.update();
    }
}

async function fetchOccupancy() {
    const res = await fetch(`/stores/${STORE_ID}/occupancy`);
    if (!res.ok) throw new Error("Occupancy fetch error");
    const data = await res.json();
    
    // Update floor occupancies
    document.getElementById("active-shopper-count").textContent = `${data.active_total} Active Shoppers`;
    
    document.getElementById("count-entrance").textContent = data.zones["Entrance"];
    document.getElementById("count-shelfa").textContent = data.zones["Shelf A"];
    document.getElementById("count-shelfb").textContent = data.zones["Shelf B"];
    document.getElementById("count-billing").textContent = data.zones["Billing Counter"];
    document.getElementById("count-exit").textContent = data.zones["Exit"];

    // Dynamic style update based on count presence
    const zoneElements = {
        "Entrance": "entrance",
        "Shelf A": "shelf-a",
        "Shelf B": "shelf-b",
        "Billing Counter": "billing",
        "Exit": "exit"
    };

    for (const [zoneName, className] of Object.entries(zoneElements)) {
        const count = data.zones[zoneName];
        const el = document.querySelector(`.floor-cell.${className}`);
        if (el) {
            if (count > 0) {
                el.style.background = "rgba(255, 255, 255, 0.08)";
            } else {
                el.style.background = "rgba(255, 255, 255, 0.04)";
            }
        }
    }
}

async function fetchAnomalies() {
    const res = await fetch(`/stores/${STORE_ID}/anomalies`);
    if (!res.ok) throw new Error("Anomalies fetch error");
    const data = await res.json();
    
    const listContainer = document.getElementById("anomalies-list");
    const countBadge = document.getElementById("anomaly-badge");
    
    countBadge.textContent = `${data.length} Active`;
    if (data.length > 0) {
        countBadge.style.background = "rgba(239, 71, 111, 0.15)";
        countBadge.style.color = "var(--accent-critical)";
    } else {
        countBadge.style.background = "rgba(255, 255, 255, 0.05)";
        countBadge.style.color = "var(--text-secondary)";
    }

    if (data.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-log">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                No active anomalies detected
            </div>
        `;
        return;
    }

    listContainer.innerHTML = data.map(anomaly => {
        const dateStr = new Date(anomaly.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        return `
            <div class="log-item severity-${anomaly.severity.toLowerCase()}">
                <div class="log-item-meta">
                    <span class="log-badge badge-${anomaly.severity.toLowerCase()}">${anomaly.type}</span>
                    <span class="log-time">${dateStr}</span>
                </div>
                <div class="log-msg">${anomaly.description}</div>
            </div>
        `;
    }).join('');
}

async function triggerMockData() {
    const btn = document.getElementById("btn-mock");
    btn.disabled = true;
    btn.textContent = "Seeding...";
    
    try {
        const res = await fetch(`/simulation/mock?store_id=${STORE_ID}`, { method: 'POST' });
        const result = await res.json();
        alert(result.message);
        refreshDashboard();
    } catch (e) {
        alert("Failed to seed mock data.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Seed Mock Data";
    }
}

async function clearData() {
    if (!confirm("Are you sure you want to clear all database store events?")) return;
    
    const btn = document.getElementById("btn-clear");
    btn.disabled = true;
    btn.textContent = "Resetting...";
    
    try {
        const res = await fetch(`/simulation/reset`, { method: 'POST' });
        const result = await res.json();
        alert(result.message);
        refreshDashboard();
    } catch (e) {
        alert("Failed to reset database.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Reset DB";
    }
}
