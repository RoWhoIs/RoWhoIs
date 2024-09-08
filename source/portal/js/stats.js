setInterval(() => {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            const p = document.createElement('p');
            p.textContent = JSON.stringify(data);
            document.body.appendChild(p);
        })
        .catch(error => {
            console.error(error);
        });
}, 5000);
