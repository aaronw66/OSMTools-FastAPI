// OSMachine - Frontend Logic
console.log('🔧 osmachine.js file loaded!');
console.group('🖥️ OSMachine');
const pageLoadStart = performance.now();
const initStart = performance.now();

let currentRestartIP = '';
let currentRestartID = '';
let currentLogsIP = '';
let currentLogsID = '';
let currentBatchGroup = '';
let machineStatusCache = {};
let allMachinesData = null;
let currentSelectedStudio = '';
let autoRefreshInterval = null;
let isAutoRefreshEnabled = true;

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
    
    // Load studio list
    loadStudioList();
    
    // Start auto-refresh immediately
    startAutoRefresh();
    
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

// Toggle category collapse for studio view
function toggleCategoryCollapse(studioId) {
    const content = document.getElementById(`category-${studioId}`);
    const header = content?.parentElement?.querySelector('.category-header');
    const icon = header?.querySelector('.collapse-icon');
    
    if (content) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            if (icon) icon.style.transform = 'rotate(0deg)';
        } else {
            content.style.display = 'none';
            if (icon) icon.style.transform = 'rotate(-90deg)';
        }
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
            },
            body: JSON.stringify({})
        });
        
        // Check if response is OK
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`❌ Server returned ${response.status}: ${errorText}`);
            throw new Error(`Server returned ${response.status}: ${errorText.substring(0, 100)}`);
        }
        
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

// Refresh machines - reload the studio list
async function refreshMachines() {
    console.log(`🔄 Refreshing studio list...`);
    const startTime = performance.now();
    
    try {
        // Force reload the studio list from server
        await loadStudioList();
        
        const endTime = performance.now();
        console.log(`✅ Studio list refreshed in ${(endTime - startTime).toFixed(2)}ms`);
        showAlert('Studio list refreshed successfully', 'success');
        
    } catch (error) {
        console.error(`❌ Error refreshing studio list:`, error);
        showAlert(`Error refreshing studio list: ${error.message}`, 'error');
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

// Load studio/group list
async function loadStudioList() {
    try {
        console.log('📡 Fetching studio list from /osmachine/refresh-machines...');
        const response = await fetch('/osmachine/refresh-machines', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📦 Received data:', data);
        
        if (data.status === 'success') {
            allMachinesData = data.machines;
            console.log('📊 Machine data loaded:', Object.keys(allMachinesData).length, 'studios');
            
            const studioSelect = document.getElementById('studioSelect');
            
            // Clear existing options except the first one
            while (studioSelect.options.length > 1) {
                studioSelect.remove(1);
            }
            
            // Populate dropdown with studio names
            Object.keys(allMachinesData).forEach(studio => {
                const option = document.createElement('option');
                option.value = studio;
                option.textContent = `${studio} (${allMachinesData[studio].length} machines)`;
                studioSelect.appendChild(option);
                console.log(`✅ Added studio: ${studio} with ${allMachinesData[studio].length} machines`);
            });
            
            console.log(`✅ Loaded ${Object.keys(allMachinesData).length} studios total`);
        } else {
            console.error('❌ Server returned error:', data.message);
            showAlert(`Failed to load studios: ${data.message}`, 'error');
        }
    } catch (error) {
        console.error('❌ Error loading studios:', error);
        showAlert(`Failed to load studio list: ${error.message}`, 'error');
    }
}

// Handle studio selection
function handleStudioChange() {
    const studioSelect = document.getElementById('studioSelect');
    const selectedStudio = studioSelect.value;
    
    if (!selectedStudio) {
        // Clear machine list
        document.getElementById('checkStatusBtn').style.display = 'none';
        document.querySelector('.machines-container').innerHTML = '';
        updateHealthSummary();
        return;
    }
    
    currentSelectedStudio = selectedStudio;
    
    // Show check status button
    document.getElementById('checkStatusBtn').style.display = 'inline-block';
    
    // Display machines for selected studio
    displayStudioMachines(selectedStudio);
    
    console.log(`📍 Studio selected: ${selectedStudio}`);
}

// Global search across all studios to find and highlight machines
function handleGlobalSearch() {
    const searchTerm = document.getElementById('globalSearchBox').value.trim().toLowerCase();
    const machineCards = document.querySelectorAll('.machine-card');
    
    // Remove all previous highlights first
    document.querySelectorAll('.machine-card.highlighted').forEach(card => {
        card.classList.remove('highlighted');
    });
    
    if (!searchTerm) {
        console.log('🔍 Search cleared');
        return;
    }
    
    console.log(`🔍 Global search for: "${searchTerm}"`);
    
    let foundCount = 0;
    let foundMachines = [];
    
    // Check all machines for matches (but don't hide any)
    machineCards.forEach(card => {
        const ip = card.getAttribute('data-ip')?.toLowerCase() || '';
        const configId = card.getAttribute('data-config-id')?.toLowerCase() || '';
        const machineIp = card.querySelector('.machine-ip')?.textContent.toLowerCase() || '';
        const machineId = card.querySelector('.machine-id')?.textContent.toLowerCase() || '';
        
        if (ip.includes(searchTerm) || configId.includes(searchTerm) || machineIp.includes(searchTerm) || machineId.includes(searchTerm)) {
            foundCount++;
            foundMachines.push(card);
        }
    });
    
    if (foundCount === 0) {
        console.log(`❌ No machines found matching: "${searchTerm}"`);
        showAlert('No machines found matching your search', 'error');
    } else {
        console.log(`✅ Found ${foundCount} machine(s) matching: "${searchTerm}"`);
        showAlert(`Found ${foundCount} machine(s) - highlighting with pulse effect`, 'success');
        
        // Auto-expand groups and highlight found machines
        foundMachines.forEach((card, index) => {
            // Find the category content containing this machine
            const categoryContent = card.closest('.category-content');
            if (categoryContent) {
                // Expand the category if it's collapsed
                if (categoryContent.style.display === 'none') {
                    categoryContent.style.display = 'block';
                    const header = categoryContent.parentElement?.querySelector('.category-header');
                    const icon = header?.querySelector('.collapse-icon');
                    if (icon) {
                        icon.style.transform = 'rotate(0deg)';
                    }
                }
            }
            
            // Add delay for multiple machines to create wave effect
            setTimeout(() => {
                // Highlight the found machine with pulse effect
                card.classList.add('highlighted');
                
                // Scroll to the first found machine
                if (index === 0) {
                    card.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                }
                
                // Remove highlight after 6 seconds
                setTimeout(() => {
                    card.classList.remove('highlighted');
                }, 6000);
            }, index * 200); // 200ms delay between each machine
        });
    }
}

// Render a single machine card
function renderMachineCard(machine) {
    const ipId = machine.ip.replace(/\./g, '-');
    return `
        <div class="machine-card" data-ip="${machine.ip}" data-group="${machine.display_group || ''}" data-config-id="${machine.config_id}">
            <div class="machine-status-indicator" id="status-${ipId}">
                <i class="fas fa-circle"></i>
            </div>
            <div class="machine-info">
                <div class="machine-ip">${machine.ip}</div>
                <div class="machine-id">${machine.config_id}</div>
            </div>
            <div class="machine-actions">
                <button class="btn-machine-action btn-check" onclick="checkMachineStatus('${machine.ip}')" title="Check Status">
                    <i class="fas fa-heartbeat"></i>
                </button>
                <button class="btn-machine-action btn-restart" onclick="showRestartModal('${machine.ip}', '${machine.config_id}')" title="Restart Machine">
                    <i class="fas fa-redo"></i>
                </button>
                <button class="btn-machine-action btn-logs" onclick="showLogsModal('${machine.ip}', '${machine.config_id}')" title="View Logs">
                    <i class="fas fa-file-alt"></i>
                </button>
            </div>
        </div>
    `;
}

// Display machines for selected studio
function displayStudioMachines(studio) {
    const machines = allMachinesData[studio];
    const container = document.querySelector('.machines-container');
    
    if (!machines || machines.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #8b949e; padding: 40px;">No machines found for this studio.</p>';
        return;
    }
    
    // Create single category view
    const categoryHTML = `
        <div class="machine-category">
            <div class="category-header" onclick="toggleCategoryCollapse('${studio}')">
                <div class="category-title">
                    <i class="fas fa-server"></i>
                    <span>${studio}</span>
                    <span class="machine-count">${machines.length} machines</span>
                </div>
                <div class="category-stats">
                    <span class="stat-badge stat-online" id="stat-online-${studio}">0 online</span>
                    <span class="stat-badge stat-offline" id="stat-offline-${studio}">0 offline</span>
                    <span class="stat-badge stat-error" id="stat-error-${studio}">0 error</span>
                </div>
                <i class="fas fa-chevron-down collapse-icon"></i>
            </div>
            <div class="category-content" id="category-${studio}">
                <div class="machine-group">
                    <div class="machines-grid">
                        ${machines.map(machine => renderMachineCard(machine)).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = categoryHTML;
    updateHealthSummary();
    
    console.log(`📋 Displayed ${machines.length} machines for ${studio}`);
}

// Check status for selected studio only
async function checkSelectedStudio() {
    if (!currentSelectedStudio) {
        showAlert('Please select a studio first', 'error');
        return;
    }
    
    const machines = allMachinesData[currentSelectedStudio];
    const ips = machines.map(m => m.ip);
    
    console.log(`🚀 Checking status for ${ips.length} machines in ${currentSelectedStudio}...`);
    
    showProgressModal(`Checking ${currentSelectedStudio}`, `Checking status for ${ips.length} machines...`);
    
    try {
        const response = await fetch('/osmachine/batch-check-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                machines: machines
            })
        });
        
        const data = await response.json();
        
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
            
            updateHealthSummary();
            hideProgressModal();
            showAlert(`Status check complete for ${currentSelectedStudio}!`, 'success');
        } else {
            hideProgressModal();
            showAlert(`Error checking status: ${data.message}`, 'error');
        }
        
    } catch (error) {
        console.error(`❌ Error checking status:`, error);
        hideProgressModal();
        showAlert(`Error checking status: ${error.message}`, 'error');
    }
}

// ========== AUTO-REFRESH FUNCTIONALITY ==========

// Start auto-refresh
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(() => {
        if (isAutoRefreshEnabled && currentSelectedStudio) {
            console.log('🔄 Auto-refresh triggered...');
            refreshStatusBackground();
        }
    }, 15000); // 15 seconds
    
    console.log('✅ Auto-refresh started: 15 second intervals');
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('⏸️ Auto-refresh stopped');
    }
}

// Background refresh without blocking UI
async function refreshStatusBackground() {
    if (!currentSelectedStudio || !allMachinesData) {
        console.log('⏸️ Skipping background refresh: no studio selected or no data loaded');
        return;
    }
    
    const machines = allMachinesData[currentSelectedStudio];
    if (!machines || machines.length === 0) {
        console.log('⏸️ Skipping background refresh: no machines for selected studio');
        return;
    }
    
    try {
        console.log(`🔄 Starting background refresh for ${machines.length} machines...`);
        
        // Show subtle refresh indicator (rotate refresh button icon if visible)
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            const icon = refreshBtn.querySelector('i');
            if (icon) {
                icon.style.transform = 'rotate(360deg)';
                icon.style.transition = 'transform 1s ease';
                setTimeout(() => {
                    icon.style.transform = 'rotate(0deg)';
                }, 1000);
            }
        }
        
        const response = await fetch('/osmachine/batch-check-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                machines: machines
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            console.log(`🔄 Processing ${Object.keys(data.results || {}).length} machine results...`);
            
            // Update all status indicators silently (no progress modal)
            let updatedCount = 0;
            Object.entries(data.results || {}).forEach(([ip, result]) => {
                if (result && result.status) {
                    updateStatusIndicatorSilent(ip, result.status);
                    updatedCount++;
                }
            });
            
            console.log(`✅ Updated ${updatedCount} machine statuses`);
            
            // Update health summary
            updateHealthSummary();
            
            // Show subtle notification
            showAlert(`🔄 Status refreshed (${updatedCount} machines)`, 'info');
        } else {
            console.warn('Background refresh returned error:', data.message);
        }
    } catch (error) {
        console.error('Background refresh error:', error);
        // Don't show error toast for background refresh to avoid spam
    }
}

// Update status indicator silently (without animations/sounds)
function updateStatusIndicatorSilent(ip, status) {
    const statusIndicator = document.getElementById(`status-${ip.replace(/\./g, '-')}`);
    
    if (statusIndicator) {
        if (status === 'online') {
            statusIndicator.className = 'machine-status-indicator online';
            statusIndicator.innerHTML = '<i class="fas fa-check-circle"></i>';
            machineStatusCache[ip] = 'online';
        } else if (status === 'offline') {
            statusIndicator.className = 'machine-status-indicator offline';
            statusIndicator.innerHTML = '<i class="fas fa-times-circle"></i>';
            machineStatusCache[ip] = 'offline';
        } else {
            statusIndicator.className = 'machine-status-indicator error';
            statusIndicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            machineStatusCache[ip] = 'error';
        }
    }
}
