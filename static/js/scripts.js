document.addEventListener('DOMContentLoaded', function() {
    // Dynamically set the favicon
    const favicon = document.createElement('link');
    favicon.rel = 'icon';
    const canvas = document.createElement('canvas');
    canvas.width = 64; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#1DB954';
    ctx.fillRect(0, 0, 64, 64);
    ctx.font = 'bold 48px Teko, sans-serif';
    ctx.fillStyle = 'white';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('SF', 32, 34);
    favicon.href = canvas.toDataURL('image/png');
    document.head.appendChild(favicon);
});

// Alpine.js data function for Jackett search functionality
function jackettSearch() {
    return {
        query: '', results: [], loading: false, searched: false,
        search() {
            if (this.query.trim().length < 3) { this.results = []; this.searched = false; return; }
            this.loading = true; this.searched = true;
            const formData = new FormData();
            formData.append('query', this.query);
            formData.append('media_type', 'all'); // Search both
            fetch('/search_jackett', { method: 'POST', body: formData })
                .then(res => res.json()).then(data => this.results = data.error ? [] : data)
                .catch(err => console.error('Fetch Error:', err))
                .finally(() => this.loading = false);
        }
    };
}

// Alpine.js data function for the "Available" tab panels
function availableMedia(mediaType, limit) {
    return {
        results: [], loading: true,
        init() {
            fetch(`/jackett_available/${mediaType}?limit=${limit}`)
                .then(res => res.json()).then(data => this.results = data.error ? [] : data)
                .catch(err => console.error('Fetch Error:', err))
                .finally(() => this.loading = false);
        }
    };
}

// Alpine.js data function for the "Recent" tab panels
function recentMedia(mediaType) {
    return {
        results: [], loading: true,
        init() {
            fetch(`/jackett_recent/${mediaType}`)
                .then(res => res.json()).then(data => this.results = data.error ? [] : data)
                .catch(err => console.error('Fetch Error:', err))
                .finally(() => this.loading = false);
        }
    };
}

