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
    
    // Health check
    checkHealth();
});

async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('System Status:', data);
    } catch (error) {
        console.warn('Health check failed:', error);
    }
}
