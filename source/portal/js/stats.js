const p = document.createElement('p');
document.body.appendChild(p);


function fetchData() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.status === false) {
                runblurb = "Offline";
                document.querySelector('.danger-button').disabled = true;
                document.querySelector('.go-button').disabled = false;
                document.querySelector('.danger-button').classList.add('disabled-danger-button');
                document.querySelector('.go-button').classList.remove('disabled-go-button');
            } else {
                runblurb = "Online";
                document.querySelector('.danger-button').disabled = false;
                document.querySelector('.go-button').disabled = true;
                document.querySelector('.danger-button').classList.remove('disabled-danger-button');
                document.querySelector('.go-button').classList.add('disabled-go-button');
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

document.addEventListener('DOMContentLoaded', function() {
    fetchData();
    setInterval(fetchData, 5000);
});