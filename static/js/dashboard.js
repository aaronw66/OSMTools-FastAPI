// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth animations
    const toolCards = document.querySelectorAll('.tool-card');
    
    // Animate cards on load
    toolCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Add click analytics (optional)
    toolCards.forEach(card => {
        card.addEventListener('click', function(e) {
            if (e.target.classList.contains('tool-button')) {
                const toolName = this.querySelector('h3').textContent;
                console.log(`Navigating to: ${toolName}`);
                
                // Add loading state
                const button = e.target;
                const originalText = button.textContent;
                button.textContent = 'Thinking...';
                button.style.opacity = '0.7';
                
                // Reset after navigation (in case of same-page navigation)
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.opacity = '1';
                }, 1000);
            }
        });
    });
    
    // Add keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key >= '1' && e.key <= '5') {
            const index = parseInt(e.key) - 1;
            const card = toolCards[index];
            if (card) {
                const button = card.querySelector('.tool-button');
                if (button) {
                    button.click();
                }
            }
        }
    });
    
    // Load system stats
    loadSystemStats();
    
    // Refresh stats every 5 seconds
    setInterval(loadSystemStats, 5000);
});

async function loadSystemStats() {
    try {
        const response = await fetch('/api/system-stats');
        const data = await response.json();
        
        // Update CPU
        document.getElementById('cpuUsage').textContent = data.cpu.display;
        document.getElementById('cpuUsage').style.color = data.cpu.percent > 80 ? '#ff7b72' : '#58a6ff';
        
        // Update RAM
        document.getElementById('ramUsage').textContent = data.ram.display;
        document.getElementById('ramUsage').style.color = data.ram.percent > 80 ? '#ff7b72' : '#58a6ff';
        
        // Update Disk
        document.getElementById('diskUsage').textContent = data.disk.display;
        document.getElementById('diskUsage').style.color = data.disk.percent > 80 ? '#ff7b72' : '#58a6ff';
        
    } catch (error) {
        console.warn('Failed to load system stats:', error);
        document.getElementById('cpuUsage').textContent = 'N/A';
        document.getElementById('ramUsage').textContent = 'N/A';
        document.getElementById('diskUsage').textContent = 'N/A';
    }
}
