// OSMachine - Frontend Logic
console.group('🖥️ OSMachine');
const pageLoadStart = performance.now();
const initStart = performance.now();

let currentRestartIP = '';
let currentRestartID = '';
let currentLogsIP = '';
let currentLogsID = '';
let currentBatchGroup = '';
let machineStatusCache = {};

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing OSMachine...');
    
    // Set up search functionality
    const searchBox = document.getElementById('searchBox');
    if (searchBox) {
        searchBox.addEventListener('input', handleSearch);
    }
    
    // Set today's date for logs
    const logsDateInput = document.getElementById('logsDate');
    if (logsDateInput) {
        logsDateInput.valueAsDate = new Date();
    }
    
    // Update health summary from initial page load
    updateHealthSummary();
    
    const initEnd = performance.now();
    console.log(`✅ OSMachine initialization complete in ${(initEnd - initStart).toFixed(2)}ms`);
    
    const pageLoadEnd = performance.now();
    console.log(`📊 Total page load time: ${(pageLoadEnd - pageLoadStart).toFixed(2)}ms`);
    console.groupEnd();
});

// Search functionality
function handleSearch() {
    const searchTerm = document.getElementById('searchBox').value.toLowerCase();
    const machineCards = document.querySelectorAll('.machine-card');
    
    let visibleCount = 0;
    
    machineCards.forEach(card => {
        const ip = card.getAttribute('data-ip').toLowerCase();
        const configId = card.getAttribute('data-config-id').toLowerCase();
        const group = card.getAttribute('data-group').toLowerCase();
        
        if (ip.includes(searchTerm) || configId.includes(searchTerm) || group.includes(searchTerm)) {
            card.style.display = '';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    console.log(`🔍 Search: "${searchTerm}" - ${visibleCount} machines found`);
}

// Toggle category collapse
function toggleCategory(categoryId) {
    const content = document.getElementById(`grid-${categoryId}`);
    const icon = document.getElementById(`icon-${categoryId}`);
    
    if (content && icon) {
        content.classList.toggle('collapsed');
        icon.classList.toggle('collapsed');
    }
}

// Toggle group collapse
function toggleGroup(groupName) {
    const grid = document.getElementById(`grid-${groupName}`);
    const icon = document.getElementById(`icon-${groupName}`);
    
    if (grid && icon) {
        grid.classList.toggle('collapsed');
        icon.classList.toggle('collapsed');
    }
}

// Update health summary
function updateHealthSummary() {
    const machineCards = document.querySelectorAll('.machine-card');
    let total = machineCards.length;
    let online = 0;
    let offline = 0;
    let error = 0;
    let checking = 0;
    
    machineCards.forEach(card => {
        const ip = card.getAttribute('data-ip');
        const statusIndicator = document.getElementById(`status-${ip.replace(/\./g, '-')}`);
        
        if (statusIndicator) {
            if (statusIndicator.classList.contains('online')) online++;
            else if (statusIndicator.classList.contains('offline')) offline++;
            else if (statusIndicator.classList.contains('error')) error++;
            else if (statusIndicator.classList.contains('checking')) checking++;
        }
    });
    
    document.getElementById('totalMachines').textContent = total;
    document.getElementById('onlineMachines').textContent = online;
    document.getElementById('offlineMachines').textContent = offline;
    document.getElementById('errorMachines').textContent = error;
    document.getElementById('checkingMachines').textContent = checking;
}

// Update group stats
function updateGroupStats(groupName) {
    const grid = document.getElementById(`grid-${groupName}`);
    if (!grid) return;
    
    const cards = grid.querySelectorAll('.machine-card');
    let online = 0;
    let offline = 0;
    let error = 0;
    
    cards.forEach(card => {
        const ip = card.getAttribute('data-ip');
        const statusIndicator = document.getElementById(`status-${ip.replace(/\./g, '-')}`);
        
        if (statusIndicator) {
            if (statusIndicator.classList.contains('online')) online++;
            else if (statusIndicator.classList.contains('offline')) offline++;
            else if (statusIndicator.classList.contains('error')) error++;
        }
    });
    
    const onlineSpan = document.getElementById(`online-${groupName}`);
    const offlineSpan = document.getElementById(`offline-${groupName}`);
    const errorSpan = document.getElementById(`error-${groupName}`);
    
    if (onlineSpan) onlineSpan.textContent = online;
    if (offlineSpan) offlineSpan.textContent = offline;
    if (errorSpan) errorSpan.textContent = error;
}

// Check machine status
async function checkMachineStatus(ip) {
    console.log(`📡 Checking status for ${ip}...`);
    const startTime = performance.now();
    
    const statusIndicator = document.getElementById(`status-${ip.replace(/\./g, '-')}`);
    if (statusIndicator) {
        statusIndicator.className = 'machine-status-indicator checking';
        statusIndicator.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
    
    try {
        const response = await fetch('/osmachine/check-machine-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ machine_ip: ip })
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        if (data.status === 'success' && statusIndicator) {
            if (data.is_online) {
                statusIndicator.className = 'machine-status-indicator online';
                statusIndicator.innerHTML = '<i class="fas fa-check-circle"></i>';
                machineStatusCache[ip] = 'online';
                console.log(`✅ ${ip} is online (${(endTime - startTime).toFixed(2)}ms)`);
            } else {
                statusIndicator.className = 'machine-status-indicator offline';
                statusIndicator.innerHTML = '<i class="fas fa-times-circle"></i>';
                machineStatusCache[ip] = 'offline';
                console.log(`⚠️ ${ip} is offline: ${data.status_message} (${(endTime - startTime).toFixed(2)}ms)`);
            }
        } else {
            statusIndicator.className = 'machine-status-indicator error';
            statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            machineStatusCache[ip] = 'error';
            console.error(`❌ Error checking ${ip}: ${data.message}`);
        }
        
        // Update group stats and health summary
        const card = document.querySelector(`.machine-card[data-ip="${ip}"]`);
        if (card) {
            const groupName = card.getAttribute('data-group');
            updateGroupStats(groupName);
        }
        updateHealthSummary();
        
    } catch (error) {
        console.error(`❌ Error checking status for ${ip}:`, error);
        if (statusIndicator) {
            statusIndicator.className = 'machine-status-indicator error';
            statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        }
        updateHealthSummary();
    }
}

// Check group status
async function checkGroupStatus(groupName) {
    console.log(`📊 Checking status for group: ${groupName}...`);
    const startTime = performance.now();
    
    showProgressModal('Checking Group Status', `Checking machines in ${groupName}...`);
    
    try {
        const response = await fetch('/osmachine/batch-check-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                group_name: groupName,
                max_concurrent: 20
            })
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        if (data.status === 'success') {
            // Update UI with results
            Object.values(data.results).forEach(result => {
                const ip = result.ip;
                const statusIndicator = document.getElementById(`status-${ip.replace(/\./g, '-')}`);
                
                if (statusIndicator) {
                    if (result.status === 'online') {
                        statusIndicator.className = 'machine-status-indicator online';
                        statusIndicator.innerHTML = '<i class="fas fa-check-circle"></i>';
                    } else if (result.status === 'offline') {
                        statusIndicator.className = 'machine-status-indicator offline';
                        statusIndicator.innerHTML = '<i class="fas fa-times-circle"></i>';
                    } else {
                        statusIndicator.className = 'machine-status-indicator error';
                        statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                    }
                    machineStatusCache[ip] = result.status;
                }
            });
            
            updateGroupStats(groupName);
            updateHealthSummary();
            
            console.log(`✅ Group ${groupName} status check complete in ${(endTime - startTime).toFixed(2)}ms`);
            console.log(`📊 Results: ${data.health_summary.online} online, ${data.health_summary.offline} offline, ${data.health_summary.error} error`);
            
            hideProgressModal();
            showAlert(`Group status check complete!\n${data.health_summary.online} online, ${data.health_summary.offline} offline, ${data.health_summary.error} error`, 'success');
        } else {
            hideProgressModal();
            showAlert(`Error checking group status: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error checking group status:`, error);
        hideProgressModal();
        showAlert(`Error checking group status: ${error.message}`, 'error');
    }
}

// Check all machines
async function checkAllMachines() {
    console.log(`🚀 Checking status for ALL machines...`);
    const startTime = performance.now();
    
    showProgressModal('Checking All Machines', 'Checking status for all machines...');
    
    try {
        const response = await fetch('/osmachine/check-all-machines', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        if (data.status === 'success') {
            // Update UI with results
            Object.values(data.results).forEach(result => {
                const ip = result.ip;
                const statusIndicator = document.getElementById(`status-${ip.replace(/\./g, '-')}`);
                
                if (statusIndicator) {
                    if (result.status === 'online') {
                        statusIndicator.className = 'machine-status-indicator online';
                        statusIndicator.innerHTML = '<i class="fas fa-check-circle"></i>';
                    } else if (result.status === 'offline') {
                        statusIndicator.className = 'machine-status-indicator offline';
                        statusIndicator.innerHTML = '<i class="fas fa-times-circle"></i>';
                    } else {
                        statusIndicator.className = 'machine-status-indicator error';
                        statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
                    }
                    machineStatusCache[ip] = result.status;
                }
            });
            
            // Update all group stats
            Object.keys(data.group_stats).forEach(groupName => {
                updateGroupStats(groupName);
            });
            
            updateHealthSummary();
            
            console.log(`✅ All machines status check complete in ${(endTime - startTime).toFixed(2)}ms`);
            console.log(`📊 Total: ${data.total_machines}, Online: ${data.online_count}, Offline: ${data.offline_count}, Error: ${data.error_count}`);
            
            hideProgressModal();
            showAlert(`Status check complete!\n${data.online_count} online, ${data.offline_count} offline, ${data.error_count} error`, 'success');
        } else {
            hideProgressModal();
            showAlert(`Error checking all machines: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error checking all machines:`, error);
        hideProgressModal();
        showAlert(`Error checking all machines: ${error.message}`, 'error');
    }
}

// Show restart modal
function showRestartModal(ip, configId) {
    currentRestartIP = ip;
    currentRestartID = configId;
    
    document.getElementById('restartMachineIP').textContent = ip;
    document.getElementById('restartMachineID').textContent = configId;
    document.getElementById('restartModal').style.display = 'block';
    
    console.log(`🔄 Opening restart modal for ${ip}`);
}

// Close restart modal
function closeRestartModal() {
    document.getElementById('restartModal').style.display = 'none';
    currentRestartIP = '';
    currentRestartID = '';
}

// Execute restart
async function executeRestart() {
    const operationMode = document.querySelector('input[name="operationMode"]:checked').value;
    
    console.log(`🔄 Restarting ${currentRestartIP} with mode: ${operationMode}...`);
    const startTime = performance.now();
    
    closeRestartModal();
    showProgressModal('Restarting Machine', `Sending restart command to ${currentRestartIP}...`);
    
    try {
        const response = await fetch('/osmachine/restart-machine', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                machine_ip: currentRestartIP,
                operation_mode: operationMode
            })
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        hideProgressModal();
        
        if (data.status === 'success') {
            console.log(`✅ Restart command sent successfully in ${(endTime - startTime).toFixed(2)}ms`);
            showAlert(`${data.message}`, 'success');
        } else {
            console.error(`❌ Restart failed: ${data.message}`);
            showAlert(`Restart failed: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error restarting machine:`, error);
        hideProgressModal();
        showAlert(`Error restarting machine: ${error.message}`, 'error');
    }
}

// Show batch restart modal
function showBatchRestartModal(groupName) {
    currentBatchGroup = groupName;
    
    const grid = document.getElementById(`grid-${groupName}`);
    const machineCount = grid ? grid.querySelectorAll('.machine-card').length : 0;
    
    document.getElementById('batchGroupName').textContent = groupName;
    document.getElementById('batchTotalMachines').textContent = machineCount;
    document.getElementById('batchRestartModal').style.display = 'block';
    
    console.log(`🔄 Opening batch restart modal for group: ${groupName} (${machineCount} machines)`);
}

// Close batch restart modal
function closeBatchRestartModal() {
    document.getElementById('batchRestartModal').style.display = 'none';
    currentBatchGroup = '';
}

// Execute batch restart
async function executeBatchRestart() {
    const operationMode = document.querySelector('input[name="batchOperationMode"]:checked').value;
    
    console.log(`🔄 Batch restarting group ${currentBatchGroup} with mode: ${operationMode}...`);
    const startTime = performance.now();
    
    closeBatchRestartModal();
    showProgressModal('Batch Restarting Group', `Restarting machines in ${currentBatchGroup}...`);
    
    try {
        const response = await fetch('/osmachine/batch-restart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                group_name: currentBatchGroup,
                operation_mode: operationMode,
                max_concurrent: 3
            })
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        hideProgressModal();
        
        if (data.status === 'success') {
            console.log(`✅ Batch restart complete in ${(endTime - startTime).toFixed(2)}ms`);
            console.log(`📊 Results: ${data.summary.successful} successful, ${data.summary.failed} failed`);
            showAlert(`Batch restart complete!\n${data.summary.successful} successful, ${data.summary.failed} failed`, 'success');
        } else {
            console.error(`❌ Batch restart failed: ${data.message}`);
            showAlert(`Batch restart failed: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error batch restarting:`, error);
        hideProgressModal();
        showAlert(`Error batch restarting: ${error.message}`, 'error');
    }
}

// Show logs modal
function showLogsModal(ip, configId) {
    currentLogsIP = ip;
    currentLogsID = configId;
    
    document.getElementById('logsMachineIP').textContent = ip;
    document.getElementById('logsMachineID').textContent = configId;
    document.getElementById('logsModal').style.display = 'block';
    
    console.log(`📋 Opening logs modal for ${ip}`);
    
    // Fetch logs immediately
    fetchLogs();
}

// Close logs modal
function closeLogsModal() {
    document.getElementById('logsModal').style.display = 'none';
    currentLogsIP = '';
    currentLogsID = '';
}

// Fetch logs
async function fetchLogs() {
    const date = document.getElementById('logsDate').value;
    const lines = document.getElementById('logsLines').value;
    
    console.log(`📥 Fetching logs from ${currentLogsIP} (date: ${date}, lines: ${lines})...`);
    const startTime = performance.now();
    
    const logsContent = document.getElementById('logsContent');
    logsContent.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Thinking...</div>';
    
    try {
        const response = await fetch('/osmachine/get-machine-logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                machine_ip: currentLogsIP,
                date: date,
                lines: parseInt(lines)
            })
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        if (data.status === 'success') {
            logsContent.textContent = data.content || 'No logs available.';
            console.log(`✅ Logs fetched successfully (${data.lines_fetched} lines) in ${(endTime - startTime).toFixed(2)}ms`);
        } else {
            logsContent.innerHTML = `<div style="color: #f44336; text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 15px;"></i><br>
                ${data.message}
            </div>`;
            console.error(`❌ Error fetching logs: ${data.message}`);
        }
        
    } catch (error) {
        console.error(`❌ Error fetching logs:`, error);
        logsContent.innerHTML = `<div style="color: #f44336; text-align: center; padding: 40px;">
            <i class="fas fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 15px;"></i><br>
            Error fetching logs: ${error.message}
        </div>`;
    }
}

// Refresh machines
async function refreshMachines() {
    console.log(`🔄 Refreshing machine list...`);
    const startTime = performance.now();
    
    showProgressModal('Refreshing Machine List', 'Fetching latest machine data...');
    
    try {
        const response = await fetch('/osmachine/refresh-machines', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        const endTime = performance.now();
        
        hideProgressModal();
        
        if (data.status === 'success') {
            console.log(`✅ Machine list refreshed in ${(endTime - startTime).toFixed(2)}ms`);
            showAlert(data.message, 'success');
            // Reload the page to show updated machine list
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            console.error(`❌ Refresh failed: ${data.message}`);
            showAlert(`Refresh failed: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error refreshing machines:`, error);
        hideProgressModal();
        showAlert(`Error refreshing machines: ${error.message}`, 'error');
    }
}

// Show progress modal
function showProgressModal(title, message) {
    document.getElementById('progressTitle').textContent = title;
    document.getElementById('progressMessage').textContent = message;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressStats').textContent = '';
    document.getElementById('progressModal').style.display = 'block';
}

// Hide progress modal
function hideProgressModal() {
    document.getElementById('progressModal').style.display = 'none';
}

// Show alert
function showAlert(message, type) {
    alert(message);
}

// Close modals when clicking outside
window.onclick = function(event) {
    const restartModal = document.getElementById('restartModal');
    const batchRestartModal = document.getElementById('batchRestartModal');
    const logsModal = document.getElementById('logsModal');
    const progressModal = document.getElementById('progressModal');
    
    if (event.target === restartModal) {
        closeRestartModal();
    } else if (event.target === batchRestartModal) {
        closeBatchRestartModal();
    } else if (event.target === logsModal) {
        closeLogsModal();
    }
    // Don't close progress modal on outside click
}
