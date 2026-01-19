document.addEventListener('DOMContentLoaded', () => {
    const totalDetectedEl = document.getElementById('total-detected');
    const totalViolationsEl = document.getElementById('total-violations');
    const statusIndicatorEl = document.getElementById('status-indicator');
    const statusTextEl = statusIndicatorEl.querySelector('.status-text');
    const eventLogEl = document.getElementById('event-log');
    const clockEl = document.getElementById('clock');

    let lastViolationCount = 0;

    // Clock
    setInterval(() => {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString();
    }, 1000);

    // Poll API for status updates
    function updateMsg() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                totalDetectedEl.textContent = data.total_people;

                // Animate violation count if it changes
                if (data.violations !== parseInt(totalViolationsEl.textContent)) {
                    totalViolationsEl.textContent = data.violations;
                    // Add log entry
                    if (data.violations > lastViolationCount) {
                        addLog(`⚠️ Violation Detected! Count: ${data.violations}`);
                    }
                    lastViolationCount = data.violations;
                }

                // Update Status Indicator
                if (data.violations > 0) {
                    statusIndicatorEl.classList.add('danger');
                    statusIndicatorEl.classList.remove('success');
                    statusTextEl.textContent = "ATTENTION REQUIRED";
                } else {
                    statusIndicatorEl.classList.remove('danger');
                    statusIndicatorEl.classList.add('success');
                    statusTextEl.textContent = "SAFE";
                }
            })
            .catch(error => console.error('Error fetching stats:', error));
    }

    function addLog(msg) {
        const li = document.createElement('li');
        const time = new Date().toLocaleTimeString();
        li.textContent = `[${time}] ${msg}`;
        eventLogEl.prepend(li); // Add to top

        // Limit log size
        if (eventLogEl.children.length > 20) {
            eventLogEl.removeChild(eventLogEl.lastChild);
        }
    }

    // Poll every 500ms
    setInterval(updateMsg, 500);
});
