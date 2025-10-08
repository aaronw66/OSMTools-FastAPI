// Common JavaScript functions for all pages

// Show console tip on first load
if (!sessionStorage.getItem('consoleHintShown')) {
    console.log('%c💡 Console Tip', 'color: #4a9eff; font-size: 14px; font-weight: bold;');
    console.log('%cTo keep logs visible when switching pages:', 'color: #8b949e; font-size: 12px;');
    console.log('%c1. Open Console Settings (⚙️)', 'color: #8b949e; font-size: 12px;');
    console.log('%c2. Check "Preserve log"', 'color: #8b949e; font-size: 12px;');
    console.log('%c3. Logs will persist across page navigation!', 'color: #7ee787; font-size: 12px;');
    sessionStorage.setItem('consoleHintShown', 'true');
}

// Utility Functions
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    // Insert at the top of main content
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.insertBefore(alertDiv, mainContent.firstChild);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

function showLoading(button) {
    const originalText = button.textContent;
    button.innerHTML = '<span class="loading"></span>Thinking...';
    button.disabled = true;
    
    return () => {
        button.textContent = originalText;
        button.disabled = false;
    };
}

function formatJSON(jsonString) {
    try {
        const parsed = JSON.parse(jsonString);
        let formatted = JSON.stringify(parsed, null, 4);
        
        // Fix brace alignment - ensure opening braces are at the leftmost position
        formatted = formatted.replace(/^(\s+)(\{)/gm, '$2');
        formatted = formatted.replace(/^(\s+)(\[)/gm, '$2');
        
        return formatted;
    } catch (e) {
        return jsonString;
    }
}

function formatJSONWithSyntaxHighlighting(jsonString) {
    try {
        const parsed = JSON.parse(jsonString);
        let formatted = JSON.stringify(parsed, null, 4);
        
        // Add syntax highlighting
        return formatted
            .replace(/("[\w\-_]+")(\s*:)/g, '<span class="json-key">$1</span>$2')
            .replace(/:\s*(".*?")/g, ': <span class="json-string">$1</span>')
            .replace(/:\s*(\d+)/g, ': <span class="json-number">$1</span>')
            .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
            .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
    } catch (e) {
        return jsonString;
    }
}

function downloadJSON(content, filename = 'data.json') {
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Modal Functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId = null) {
    if (modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    } else {
        // Close all modals
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
        });
    }
    document.body.style.overflow = 'auto';
}

// API Helper Functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        } else {
            return await response.text();
        }
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

async function uploadFile(url, formData) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('File upload failed:', error);
        throw error;
    }
}

// Form Validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.style.borderColor = '#dc3545';
            isValid = false;
        } else {
            field.style.borderColor = '#ddd';
        }
    });
    
    return isValid;
}

// Navigation Management
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === currentPath || 
            (currentPath.includes(item.getAttribute('href')) && item.getAttribute('href') !== '/')) {
            item.classList.add('active');
        }
    });
}

// Event Listeners for Common Elements
document.addEventListener('DOMContentLoaded', function() {
    // Set active navigation item
    setActiveNavItem();
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            closeModal();
        }
    });
    
    // Close modal when clicking X
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', function() {
            closeModal();
        });
    });
    
    // Escape key to close modals
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
    
    // Form validation on input
    document.querySelectorAll('input[required], select[required], textarea[required]').forEach(field => {
        field.addEventListener('blur', function() {
            if (!this.value.trim()) {
                this.style.borderColor = '#dc3545';
            } else {
                this.style.borderColor = '#ddd';
            }
        });
        
        field.addEventListener('input', function() {
            if (this.style.borderColor === 'rgb(220, 53, 69)' && this.value.trim()) {
                this.style.borderColor = '#ddd';
            }
        });
    });
});

// Progress Bar Helper
function updateProgress(percentage) {
    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
        progressFill.style.width = `${percentage}%`;
    }
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Copy to clipboard function
function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        return new Promise((resolve, reject) => {
            if (document.execCommand('copy')) {
                textArea.remove();
                resolve();
            } else {
                textArea.remove();
                reject();
            }
        });
    }
}

// Export functions for use in other scripts
window.CommonUtils = {
    showAlert,
    showLoading,
    formatJSON,
    formatJSONWithSyntaxHighlighting,
    downloadJSON,
    openModal,
    closeModal,
    apiRequest,
    uploadFile,
    validateForm,
    updateProgress,
    debounce,
    copyToClipboard
};
