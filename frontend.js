const serverUrl = "http://YOUR_SERVER_IP:5000/ble-data";

async function fetchData() {
    const response = await fetch(serverUrl);
    const data = await response.json();
    updatePosition(data.position);
}

function updatePosition([x, y]) {
    const map = document.getElementById('map');
    const device = document.createElement('div');
    device.className = 'device';
    device.style.left = `${x * 50}px`;  // Adjust scaling based on room size
    device.style.top = `${y * 50}px`;
    map.appendChild(device);
}

setInterval(fetchData, 10000);  // Fetch data every 10 seconds
