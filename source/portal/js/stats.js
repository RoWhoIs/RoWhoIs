const p = document.createElement('p');
document.body.appendChild(p);

setInterval(() => {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            p.textContent = JSON.stringify(data);
        })
        .catch(error => {
            console.error(error);
        });
}, 5000);
