/* Putting this here for future use & reference when
the portal is ready to be integrated with the listener   

The listener refreshes the portal every 5 seconds
by creating a POST request to the server with a payload like this:
{"entity": "logs"}

It will then respond with a payload like this:
{"entity": "logs", 
"data": [
    {"level": "debug", "timestamp": "1716450000", "message": "Hello, world!"}
    ]
}

Note the unix timestamp is UTC
*/


const options = {
    hostname: 'localhost',
    port: 63415,
    path: '/',
    method: 'POST',
};

