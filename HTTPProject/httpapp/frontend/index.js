
'use strict';
const button = document.getElementById('submit-btn');

button.addEventListener('click', async (e) => {
    console.log(e);
    e.preventDefault();

    try {
        let name = document.getElementById('name').value;
        let email = document.getElementById('email').value;
        let age = document.getElementById('age').value;
        let avatar = document.getElementById('avatar').files[0];
        let resume = document.getElementById('resume').files[0];

        const req_body = new FormData();
        req_body.append('name', name);
        req_body.append('email', email);
        req_body.append('age', age);
        req_body.append('avatar', avatar);
        req_body.append('resume', resume);
        
        const response = await fetch('http://localhost:8000/api/register/', {
            method: 'POST',
            body: req_body
        });

        const data = await response.json();
        console.log('Success:', data);
        let resp = response.status;
            if (resp === 201) {
                alert('Profile created successfully!');
            }
                else { 
                    alert('Failed to create profile. Please try again.');
                }

    } catch (error) {
        console.error('Error:', error);
    }
    e.preventDefault();
});

const fetchProfile = document.getElementById('fetch-btn');
fetchProfile.addEventListener('click', async (e) => {
    e.preventDefault();
    try {
        const url = 'http://localhost:8000/api/profile/9/';

        // Try a HEAD request to inspect headers (fast, no body)
        let head;
        try {
            head = await fetch(url, { method: 'HEAD' });
        } catch (err) {
            // If server doesn't accept HEAD, fall back to opening directly
            window.open(url, '_blank');
            return;
        }

        if (!head.ok) throw new Error(`HTTP ${head.status}`);

        // Let browser decide: open the file URL in a new tab/window so
        // the browser handles inline display vs Save As based on headers
        window.open(url, '_blank');
    } catch (error) {
        console.error('Error:', error);
    }
});
