const button = document.getElementById('fetch');
const output = document.getElementById('data');

if (button) {
    button.addEventListener('click', fetchData);
}

async function fetchData() {
    try {
        // Ensure this matches the backend URL/port where Django is running
        const response = await fetch('http://127.0.0.1:8000/api/event-stream', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept-Language':'en',
                'accept':'text/event-stream',
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc1MjAwNTMwLCJpYXQiOjE3NzUxNDA1MzAsImp0aSI6IjQ2NWJhNWYwZGQyYTRhYjZhMWQzYmVjMDc5ZTBkMDRkIiwidXNlcl9pZCI6IjEifQ.O5tt40idbQq5CjyOQOD3Pv5NlIICEkxWbSJpPJbzWEk'
            }
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', [...response.headers.entries()]);

        // If server returns a streaming body (SSE-like), read chunks via reader
        if (response.body && response.ok) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;
            let buffer = '';
            // append area
            if (output) output.textContent = '';
            while (!done) {
                const { value, done: readDone } = await reader.read();
                done = readDone;
                if (value) {
                    const chunk = decoder.decode(value, { stream: !done });
                    buffer += chunk;
                    // SSE events end with double newline; process complete events
                    const parts = buffer.split(/\r?\n\r?\n/);
                    // Keep last partial in buffer
                    buffer = parts.pop() || '';
                    for (const part of parts) {
                        // Extract lines starting with 'data:' and join
                        const lines = part.split(/\r?\n/);
                        const dataLines = lines
                            .filter(l => l.startsWith('data:'))
                            .map(l => l.slice(5).trim());
                        const dataText = dataLines.join('\n');
                        if (output) {
                            // append nicely
                            output.textContent += dataText + '\n';
                        }
                        console.log('event data:', dataText);
                    }
                }
            }
            // If any leftover buffer, append it
            if (buffer && output) output.textContent += buffer;
        } else {
            // Non-streaming fallback
            let data;
            try {
                data = await response.json();
            } catch (e) {
                const text = await response.text();
                console.warn('Response was not JSON:', text);
                data = text;
            }
            if (output) {
                output.textContent = JSON.stringify(data, null, 2);
            }
            console.log(data);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}