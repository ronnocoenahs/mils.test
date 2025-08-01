// Custom JS for SlimFlix

document.addEventListener('DOMContentLoaded', function() {
    // Logic for collapsible seasons on TV show detail page
    const seasonToggles = document.querySelectorAll('.season-toggle');
    seasonToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const targetId = toggle.getAttribute('data-target');
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                // This is a simple implementation. For production, you might want a more robust accordion.
                if (targetElement.style.display === 'none') {
                    targetElement.style.display = 'block';
                } else {
                    targetElement.style.display = 'none';
                }
            }
        });
    });

    // --- Admin Page Settings ---
    const jackettForm = document.getElementById('jackett-settings-form');
    if (jackettForm) {
        jackettForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = {
                jackett_url: document.getElementById('jackett_url').value,
                jackett_api_key: document.getElementById('jackett_api_key').value,
            };
            saveSettings(formData, this);
        });
    }

    const qbitForm = document.getElementById('qbittorrent-settings-form');
    if (qbitForm) {
        qbitForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = {
                qbittorrent_url: document.getElementById('qbittorrent_url').value,
                qbittorrent_user: document.getElementById('qbittorrent_user').value,
                qbittorrent_pass: document.getElementById('qbittorrent_pass').value,
            };
            saveSettings(formData, this);
        });
    }

    function saveSettings(data, formElement) {
        const button = formElement.querySelector('button[type="submit"]');
        const originalButtonText = button.textContent;
        button.textContent = 'Saving...';
        button.disabled = true;

        const notificationArea = document.getElementById('settings-notifications');
        notificationArea.innerHTML = ''; // Clear previous messages

        fetch('/admin/save_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Add CSRF token header if you implement it
            },
            body: JSON.stringify(data),
        })
        .then(response => response.json())
        .then(result => {
            let alertClass = result.success ? 'alert-success' : 'alert-danger';
            let message = `<div class="alert ${alertClass}" role="alert">${result.message}</div>`;
            notificationArea.innerHTML = message;
        })
        .catch((error) => {
            console.error('Error:', error);
            let message = `<div class="alert alert-danger" role="alert">An unexpected error occurred. Check console for details.</div>`;
            notificationArea.innerHTML = message;
        })
        .finally(() => {
            button.textContent = originalButtonText;
            button.disabled = false;
            // Auto-dismiss the notification after 5 seconds
            setTimeout(() => {
                notificationArea.innerHTML = '';
            }, 5000);
        });
    }
});

