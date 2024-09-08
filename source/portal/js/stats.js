const p = document.createElement('p');
document.body.appendChild(p);

function fetchData() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.status === false) {
                runblurb = "Offline";
            } else {
                runblurb = "Online";
            }
            p.innerHTML = `
            <strong>Status:</strong> ${runblurb}<br>
            <Strong>Users:</Strong> ${data.users}<br>
            <Strong>Servers:</Strong> ${data.servers}<br>
            <Strong>Shards:</Strong> ${data.shards}<br>
            <Strong>Uptime:</Strong> ${data.uptime}<br>
            <Strong>Cache Size:</Strong> ${data.cache_size}<br>
            `;
        })
        .catch(error => {
            console.error(error);
        });
}

fetchData();

setInterval(fetchData, 5000);
