// Image Recon JSON Generator JavaScript

let generatedJsonContent = '';
let availableServers = [];
let editServers = [];
let currentEditServer = null;
let currentJsonData = null;
let showingRawJson = false;

// Performance tracking
const pageLoadStart = performance.now();

document.addEventListener('DOMContentLoaded', function() {
    const initStart = performance.now();
    console.group('📝 Image Recon JSON');
    console.log('🚀 Initializing...');
    initializeImageReconJson();
    const initEnd = performance.now();
    console.log(`✅ Initialization complete in ${(initEnd - initStart).toFixed(2)}ms`);
    console.groupEnd();
});

// Track when everything is fully loaded
window.addEventListener('load', function() {
    const pageLoadEnd = performance.now();
    const totalLoadTime = pageLoadEnd - pageLoadStart;
    console.log(`⏱️ Total page load time: ${(totalLoadTime / 1000).toFixed(2)}s`);
});

async function initializeImageReconJson() {
    await loadMachineTypes();
    await loadGameTypes();
    setupEventListeners();
}

function setupEventListeners() {
    // Environment change handler
    const environmentSelect = document.getElementById('environment');
    if (environmentSelect) {
        environmentSelect.addEventListener('change', handleEnvironmentOrLocationChange);
    }
    
    // Location change handler
    const locationSelect = document.getElementById('location');
    if (locationSelect) {
        locationSelect.addEventListener('change', handleEnvironmentOrLocationChange);
    }
    
    // JSON Generator Form
    const jsonForm = document.getElementById('jsonGeneratorForm');
    if (jsonForm) {
        jsonForm.addEventListener('submit', handleJsonGeneration);
    }
    
    // Machine Type Management
    const addMachineForm = document.getElementById('addMachineTypeForm');
    if (addMachineForm) {
        addMachineForm.addEventListener('submit', handleAddMachineType);
    }
    
    const removeMachineForm = document.getElementById('removeMachineTypeForm');
    if (removeMachineForm) {
        removeMachineForm.addEventListener('submit', handleRemoveMachineType);
    }
    
    // JSON Actions
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', handleDownloadJson);
    }
    
    const sendToServersBtn = document.getElementById('sendToServersBtn');
    if (sendToServersBtn) {
        sendToServersBtn.addEventListener('click', handleSendToServers);
    }
    
    const sendJsonBtn = document.getElementById('sendJsonBtn');
    if (sendJsonBtn) {
        sendJsonBtn.addEventListener('click', handleSendJson);
    }
}

async function handleEnvironmentOrLocationChange(event) {
    const environmentSelect = document.getElementById('environment');
    const locationSelect = document.getElementById('location');
    const channelIdInput = document.getElementById('channelID');
    
    const environment = environmentSelect.value;
    const location = locationSelect.value;
    
    if (!environment || !location) {
        channelIdInput.value = '';
        channelIdInput.placeholder = 'Select environment and location first';
        return;
    }
    
    try {
        const response = await CommonUtils.apiRequest(`/image-recon-json/get-channel-id/${environment}/${location}`);
        
        if (response.channel_id) {
            channelIdInput.value = response.channel_id;
            channelIdInput.placeholder = `Channel ID for ${environment.toUpperCase()} - ${location}`;
            
            console.log(`Selected: ${environment.toUpperCase()} - ${location} - Channel ID: ${response.channel_id}`);
        }
        
    } catch (error) {
        console.error('Failed to get channel ID:', error);
        channelIdInput.value = '';
        channelIdInput.placeholder = 'Error loading channel ID';
    }
}

async function loadMachineTypes() {
    try {
        const machineTypes = await CommonUtils.apiRequest('/image-recon-json/get-machine-types');
        
        const machineTypeSelect = document.getElementById('machineType');
        const removeMachineSelect = document.getElementById('removeMachineType');
        
        // Clear existing options
        machineTypeSelect.innerHTML = '<option value="">Select Machine Type</option>';
        removeMachineSelect.innerHTML = '<option value="">Select to Remove</option>';
        
        // Add machine types to selects
        Object.keys(machineTypes).forEach(machineType => {
            const option1 = new Option(machineType, machineType);
            const option2 = new Option(machineType, machineType);
            machineTypeSelect.appendChild(option1);
            removeMachineSelect.appendChild(option2);
        });
        
        // Add event listener to show/hide poolType field
        machineTypeSelect.addEventListener('change', function() {
            const poolTypeGroup = document.getElementById('poolTypeGroup');
            if (this.value === 'BZZF') {
                poolTypeGroup.style.display = 'block';
            } else {
                poolTypeGroup.style.display = 'none';
                // Reset to 0 when hidden
                document.getElementById('poolType').value = '0';
            }
        });
        
    } catch (error) {
        console.error('Failed to load machine types:', error);
        CommonUtils.showAlert('Failed to load machine types', 'error');
    }
}

async function handleJsonGeneration(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const stopLoading = CommonUtils.showLoading(submitBtn);
    
    try {
        if (!CommonUtils.validateForm(form)) {
            CommonUtils.showAlert('Please fill in all required fields', 'error');
            return;
        }
        
        const formData = new FormData(form);
        const result = await CommonUtils.uploadFile('/image-recon-json/generate-json', formData);
        
        if (result.status === 'success') {
            generatedJsonContent = result.json_content;
            displayGeneratedJson(result.json_content);
            CommonUtils.showAlert('JSON generated successfully!', 'success');
        } else {
            throw new Error(result.message || 'Failed to generate JSON');
        }
        
    } catch (error) {
        console.error('JSON generation failed:', error);
        CommonUtils.showAlert(`Failed to generate JSON: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function displayGeneratedJson(jsonContent) {
    const jsonOutput = document.getElementById('jsonOutput');
    const jsonOutputCard = document.getElementById('jsonOutputCard');
    
    if (jsonOutput && jsonOutputCard) {
        // Use syntax highlighting for better readability
        const formattedJson = CommonUtils.formatJSONWithSyntaxHighlighting(jsonContent);
        
        // Add copy button
        jsonOutput.innerHTML = `
            <button class="json-copy-btn" onclick="copyJsonToClipboard()">📋 Copy</button>
            <pre style="margin: 0; padding: 0;">${formattedJson}</pre>
        `;
        
        jsonOutputCard.style.display = 'block';
        
        // Store the original JSON content for copying
        window.currentJsonContent = CommonUtils.formatJSON(jsonContent);
        
        // Scroll to the output
        jsonOutputCard.scrollIntoView({ behavior: 'smooth' });
    }
}

function copyJsonToClipboard() {
    if (window.currentJsonContent) {
        navigator.clipboard.writeText(window.currentJsonContent).then(() => {
            CommonUtils.showAlert('JSON copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = window.currentJsonContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            CommonUtils.showAlert('JSON copied to clipboard!', 'success');
        });
    }
}

async function handleAddMachineType(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const stopLoading = CommonUtils.showLoading(submitBtn);
    
    try {
        if (!CommonUtils.validateForm(form)) {
            CommonUtils.showAlert('Please fill in all required fields', 'error');
            return;
        }
        
        const formData = new FormData(form);
        const result = await CommonUtils.uploadFile('/image-recon-json/add-machine-type', formData);
        
        if (result.status === 'success') {
            CommonUtils.showAlert(result.message, 'success');
            form.reset();
            await loadMachineTypes(); // Reload machine types
            await loadGameTypes(); // Reload game types reference
        } else {
            throw new Error(result.message || 'Failed to add machine type');
        }
        
    } catch (error) {
        console.error('Add machine type failed:', error);
        CommonUtils.showAlert(`Failed to add machine type: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

async function handleRemoveMachineType(event) {
    event.preventDefault();
    
    const form = event.target;
    const machineType = form.machineType.value;
    
    if (!machineType) {
        CommonUtils.showAlert('Please select a machine type to remove', 'error');
        return;
    }
    
    if (!confirm(`Are you sure you want to remove machine type "${machineType}"?`)) {
        return;
    }
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const stopLoading = CommonUtils.showLoading(submitBtn);
    
    try {
        const formData = new FormData(form);
        const result = await CommonUtils.uploadFile('/image-recon-json/remove-machine-type', formData);
        
        if (result.status === 'success') {
            CommonUtils.showAlert(result.message, 'success');
            form.reset();
            await loadMachineTypes(); // Reload machine types
            await loadGameTypes(); // Reload game types reference
        } else {
            throw new Error(result.message || 'Failed to remove machine type');
        }
        
    } catch (error) {
        console.error('Remove machine type failed:', error);
        CommonUtils.showAlert(`Failed to remove machine type: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function handleDownloadJson() {
    if (!generatedJsonContent) {
        CommonUtils.showAlert('No JSON content to download', 'error');
        return;
    }
    
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    const filename = `list-new-${timestamp}.json`;
    
    CommonUtils.downloadJSON(generatedJsonContent, filename);
    CommonUtils.showAlert('JSON file downloaded successfully!', 'success');
}

async function handleSendToServers() {
    if (!generatedJsonContent) {
        CommonUtils.showAlert('No JSON content to send', 'error');
        return;
    }
    
    try {
        // Load available servers
        const response = await CommonUtils.apiRequest('/image-recon-json/get-servers-for-send');
        
        if (response.status === 'success') {
            availableServers = response.servers;
            displayServerSelection();
            CommonUtils.openModal('serverModal');
        } else {
            throw new Error(response.message || 'Failed to load servers');
        }
        
    } catch (error) {
        console.error('Failed to load servers:', error);
        CommonUtils.showAlert(`Failed to load servers: ${error.message}`, 'error');
    }
}

function displayServerSelection() {
    const serverList = document.getElementById('serverList');
    if (!serverList) return;
    
    serverList.innerHTML = '';
    
    if (availableServers.length === 0) {
        serverList.innerHTML = '<p>No servers available</p>';
        return;
    }
    
    availableServers.forEach((server, index) => {
        const serverItem = document.createElement('div');
        serverItem.className = 'server-item';
        serverItem.innerHTML = `
            <input type="checkbox" class="server-checkbox" id="server-${index}" value="${index}">
            <div class="server-info">
                <div class="server-hostname">${server.hostname}</div>
                <div class="server-details">
                    IP: ${server.ip}
                    <span class="server-label">${server.label}</span>
                </div>
            </div>
        `;
        
        // Add click handler for the entire item
        serverItem.addEventListener('click', function(e) {
            if (e.target.type !== 'checkbox') {
                const checkbox = serverItem.querySelector('.server-checkbox');
                checkbox.checked = !checkbox.checked;
            }
            
            const checkbox = serverItem.querySelector('.server-checkbox');
            if (checkbox.checked) {
                serverItem.classList.add('selected');
            } else {
                serverItem.classList.remove('selected');
            }
        });
        
        serverList.appendChild(serverItem);
    });
}

async function handleSendJson() {
    const selectedCheckboxes = document.querySelectorAll('.server-checkbox:checked');
    
    if (selectedCheckboxes.length === 0) {
        CommonUtils.showAlert('Please select at least one server', 'error');
        return;
    }
    
    const remotePath = document.getElementById('remotePath').value;
    if (!remotePath) {
        CommonUtils.showAlert('Please specify remote path', 'error');
        return;
    }
    
    const selectedServers = Array.from(selectedCheckboxes).map(checkbox => {
        const index = parseInt(checkbox.value);
        return availableServers[index];
    });
    
    const sendBtn = document.getElementById('sendJsonBtn');
    const stopLoading = CommonUtils.showLoading(sendBtn);
    
    try {
        const requestData = {
            json_content: generatedJsonContent,
            servers: selectedServers,
            remote_path: remotePath
        };
        
        const result = await CommonUtils.apiRequest('/image-recon-json/send-json-to-servers', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        if (result.status === 'success') {
            CommonUtils.closeModal('serverModal');
            displaySendResults(result.results);
            CommonUtils.openModal('resultsModal');
        } else {
            throw new Error(result.message || 'Failed to send JSON');
        }
        
    } catch (error) {
        console.error('Send JSON failed:', error);
        CommonUtils.showAlert(`Failed to send JSON: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function displaySendResults(results) {
    const sendResults = document.getElementById('sendResults');
    if (!sendResults) return;
    
    sendResults.innerHTML = '';
    
    results.forEach(result => {
        const resultItem = document.createElement('div');
        resultItem.className = `result-item result-${result.status}`;
        resultItem.innerHTML = `
            <div class="result-server">
                <span class="status-indicator status-${result.status}"></span>
                ${result.server} (${result.ip})
            </div>
            <div class="result-message">${result.message}</div>
        `;
        sendResults.appendChild(resultItem);
    });
}

function closeResultsModal() {
    CommonUtils.closeModal('resultsModal');
}

// Load and display game types reference with machine types
async function loadGameTypes() {
    try {
        const [gameTypesResponse, machineTypesResponse] = await Promise.all([
            fetch('/type/game_types.json'),
            fetch('/type/machine_types.json')
        ]);
        
        const gameTypes = await gameTypesResponse.json();
        const machineTypes = await machineTypesResponse.json();
        
        const gameTypesList = document.getElementById('gameTypesList');
        
        // Get list of active machine types
        const activeMachines = Object.keys(machineTypes).filter(key => machineTypes[key]);
        
        // Create a list of active machines with their game type IDs
        const machineGameTypes = activeMachines
            .map(name => ({
                name: name,
                id: gameTypes[name] !== undefined ? gameTypes[name] : '?'
            }))
            .sort((a, b) => {
                // Sort by ID, put unknowns at the end
                if (a.id === '?') return 1;
                if (b.id === '?') return -1;
                return a.id - b.id;
            });
        
        const gameTypesHTML = machineGameTypes.map(({ name, id }) => `
            <div class="game-type-item">
                <span class="game-type-name">${name}</span>
                <span class="game-type-id ${id === '?' ? 'unknown-id' : ''}">${id}</span>
            </div>
        `).join('');
        
        gameTypesList.innerHTML = gameTypesHTML || '<p style="color: #8b949e; text-align: center;">No machine types configured</p>';
    } catch (error) {
        console.error('Error loading game types:', error);
        document.getElementById('gameTypesList').innerHTML = 
            '<p style="color: #ff7b72; text-align: center;">Failed to load game types</p>';
    }
}

// ============================================================================
// EDIT JSON MODAL FUNCTIONS
// ============================================================================

async function showEditJsonModal() {
    try {
        // Load available servers
        const response = await CommonUtils.apiRequest('/image-recon-json/get-servers-for-send');
        
        if (response.status === 'success') {
            editServers = response.servers;
            
            // Render server list on the left
            renderServerList();
            
            // Clear editor and status
            document.getElementById('jsonEditor').value = '';
            document.getElementById('editJsonStatus').innerHTML = '';
            document.getElementById('machineListContainer').style.display = 'none';
            document.getElementById('rawJsonContainer').style.display = 'none';
            
            // Show modal
            document.getElementById('editJsonModal').style.display = 'block';
        } else {
            throw new Error(response.message || 'Failed to load servers');
        }
    } catch (error) {
        console.error('Failed to load servers:', error);
        CommonUtils.showAlert(`Failed to load servers: ${error.message}`, 'error');
    }
}

function renderServerList() {
    const container = document.getElementById('serverListContainer');
    
    if (!editServers || editServers.length === 0) {
        container.innerHTML = '<p style="color: #8b949e; text-align: center; padding: 20px;">No servers found</p>';
        return;
    }
    
    let html = '';
    editServers.forEach(server => {
        html += `
            <div class="server-list-item" onclick="selectServerForEdit('${server.ip}')" 
                 style="padding: 12px; margin-bottom: 8px; border: 1px solid #21262d; border-radius: 6px; cursor: pointer; transition: all 0.2s;"
                 onmouseover="this.style.background='#161b22'; this.style.borderColor='#8b949e';" 
                 onmouseout="this.style.background='transparent'; this.style.borderColor='#21262d';"
                 data-server-ip="${server.ip}">
                <div style="font-weight: 600; color: #c9d1d9; font-size: 14px; margin-bottom: 4px;">${server.label}</div>
                <div style="color: #8b949e; font-size: 12px;">${server.hostname}</div>
                <div style="color: #6e7681; font-size: 11px; font-family: monospace; margin-top: 4px;">${server.ip}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function selectServerForEdit(serverIp) {
    // Highlight selected server
    document.querySelectorAll('.server-list-item').forEach(item => {
        if (item.getAttribute('data-server-ip') === serverIp) {
            item.style.background = '#161b22';
            item.style.borderColor = '#8b949e';
        } else {
            item.style.background = 'transparent';
            item.style.borderColor = '#21262d';
        }
    });
    
    // Load JSON from this server
    currentEditServer = serverIp;
    loadJsonFromServerByIp(serverIp);
}

async function loadJsonFromServerByIp(serverIp) {
    const remotePath = document.getElementById('editRemotePath').value;
    const statusDiv = document.getElementById('editJsonStatus');
    const editor = document.getElementById('jsonEditor');
    const machineListContainer = document.getElementById('machineListContainer');
    const rawJsonContainer = document.getElementById('rawJsonContainer');
    
    if (!serverIp) {
        editor.value = '';
        statusDiv.innerHTML = '';
        machineListContainer.style.display = 'none';
        rawJsonContainer.style.display = 'none';
        return;
    }
    
    statusDiv.innerHTML = '<p style="color: #58a6ff;">🔄 Loading JSON from server...</p>';
    editor.value = '';
    machineListContainer.style.display = 'none';
    rawJsonContainer.style.display = 'none';
    
    try {
        const response = await CommonUtils.apiRequest('/image-recon-json/fetch-json-from-server', {
            method: 'POST',
            body: JSON.stringify({
                server_ip: serverIp,
                remote_path: remotePath
            })
        });
        
        if (response.status === 'success') {
            // Parse and store the JSON data
            currentJsonData = JSON.parse(response.content);
            const prettyJson = JSON.stringify(currentJsonData, null, 2);
            editor.value = prettyJson;
            currentEditServer = serverIp;
            
            // Show machine list view by default
            showingRawJson = false;
            renderMachineList();
            machineListContainer.style.display = 'flex';
            
            const machineCount = countMachines(currentJsonData);
            statusDiv.innerHTML = `<p style="color: #3fb950;">✅ Loaded ${machineCount} machines from ${serverIp}</p>`;
        } else {
            throw new Error(response.message || 'Failed to fetch JSON');
        }
    } catch (error) {
        console.error('Failed to load JSON:', error);
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Error: ${error.message}</p>`;
        editor.value = '';
    }
}

function countMachines(jsonData) {
    let count = 0;
    if (jsonData && jsonData.pool) {
        jsonData.pool.forEach(pool => {
            if (pool.gamelist) {
                count += pool.gamelist.length;
            }
        });
    }
    return count;
}

function renderMachineList() {
    const container = document.getElementById('machineListTable');
    
    if (!currentJsonData || !currentJsonData.pool) {
        container.innerHTML = '<p style="padding: 20px; color: #8b949e; text-align: center;">No machines found</p>';
        return;
    }
    
    let html = '<table style="width: 100%; border-collapse: collapse;">';
    html += '<thead style="position: sticky; top: 0; background: #161b22; z-index: 10;">';
    html += '<tr style="border-bottom: 2px solid #3a3f52;">';
    html += '<th style="padding: 12px; text-align: center; color: #58a6ff; font-weight: 600; width: 50px;">';
    html += '<input type="checkbox" id="selectAllMachines" onchange="toggleSelectAll(this)" style="width: 18px; height: 18px; cursor: pointer;">';
    html += '</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Machine ID</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Pool ID</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Type</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Stream ID</th>';
    html += '</tr>';
    html += '</thead>';
    html += '<tbody>';
    
    currentJsonData.pool.forEach((pool, poolIndex) => {
        if (pool.gamelist && pool.gamelist.length > 0) {
            pool.gamelist.forEach((machine, machineIndex) => {
                const rowId = `machine-${poolIndex}-${machineIndex}`;
                html += `<tr id="${rowId}" style="border-bottom: 1px solid #21262d;" onmouseover="this.style.background='#21262d'" onmouseout="if(!this.querySelector('input[type=checkbox]').checked) this.style.background='transparent'">`;
                html += `<td style="padding: 12px; text-align: center;">`;
                html += `<input type="checkbox" class="machine-checkbox" data-pool="${poolIndex}" data-machine="${machineIndex}" onchange="updateDeleteButtonState()" style="width: 18px; height: 18px; cursor: pointer;">`;
                html += `</td>`;
                html += `<td style="padding: 12px; color: #c9d1d9; font-family: monospace; font-size: 13px;">${machine.id || 'N/A'}</td>`;
                html += `<td style="padding: 12px; color: #8b949e;">${pool.id || 'N/A'}</td>`;
                html += `<td style="padding: 12px; color: #8b949e;">${pool.type || 'N/A'}</td>`;
                html += `<td style="padding: 12px; color: #8b949e; font-family: monospace; font-size: 12px;">${machine.sId || 'N/A'}</td>`;
                html += '</tr>';
            });
        }
    });
    
    html += '</tbody>';
    html += '</table>';
    
    container.innerHTML = html;
    updateDeleteButtonState();
}

function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.machine-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
        // Highlight selected rows
        const row = cb.closest('tr');
        if (cb.checked) {
            row.style.background = '#da363320';
        } else {
            row.style.background = 'transparent';
        }
    });
    updateDeleteButtonState();
}

function updateDeleteButtonState() {
    const checkboxes = document.querySelectorAll('.machine-checkbox:checked');
    const deleteBtn = document.getElementById('batchDeleteBtn');
    const selectAllCheckbox = document.getElementById('selectAllMachines');
    
    if (deleteBtn) {
        if (checkboxes.length > 0) {
            deleteBtn.disabled = false;
            deleteBtn.style.opacity = '1';
            deleteBtn.style.cursor = 'pointer';
            deleteBtn.innerHTML = `<i class="fas fa-trash-alt"></i> Delete Selected (${checkboxes.length})`;
        } else {
            deleteBtn.disabled = true;
            deleteBtn.style.opacity = '0.5';
            deleteBtn.style.cursor = 'not-allowed';
            deleteBtn.innerHTML = `<i class="fas fa-trash-alt"></i> Delete Selected`;
        }
    }
    
    // Update "select all" checkbox state
    if (selectAllCheckbox) {
        const totalCheckboxes = document.querySelectorAll('.machine-checkbox').length;
        selectAllCheckbox.checked = checkboxes.length === totalCheckboxes && totalCheckboxes > 0;
    }
    
    // Highlight checked rows
    document.querySelectorAll('.machine-checkbox').forEach(cb => {
        const row = cb.closest('tr');
        if (cb.checked) {
            row.style.background = '#da363320';
        } else {
            row.style.background = 'transparent';
        }
    });
}

function batchDeleteMachines() {
    const checkboxes = document.querySelectorAll('.machine-checkbox:checked');
    
    if (checkboxes.length === 0) {
        CommonUtils.showAlert('No machines selected', 'error');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete ${checkboxes.length} machine(s)?`)) {
        return;
    }
    
    console.log(`🗑️ Batch deleting ${checkboxes.length} machines...`);
    
    // Collect all machines to delete (pool index, machine index)
    const toDelete = [];
    checkboxes.forEach(cb => {
        toDelete.push({
            poolIndex: parseInt(cb.dataset.pool),
            machineIndex: parseInt(cb.dataset.machine)
        });
    });
    
    // Sort by pool index (descending) and machine index (descending) to avoid index shifting
    toDelete.sort((a, b) => {
        if (b.poolIndex !== a.poolIndex) return b.poolIndex - a.poolIndex;
        return b.machineIndex - a.machineIndex;
    });
    
    // Track pools that need updating
    const poolsToCheck = new Set();
    
    // Delete each machine
    toDelete.forEach(({poolIndex, machineIndex}) => {
        const pool = currentJsonData.pool[poolIndex];
        if (!pool || !pool.gamelist || !pool.gamelist[machineIndex]) return;
        
        const deletedMachine = pool.gamelist[machineIndex];
        const deletedSId = deletedMachine.sId;
        
        console.log(`  🗑️ Deleting: ${deletedMachine.id} (sId: ${deletedSId})`);
        
        // Remove the machine
        pool.gamelist.splice(machineIndex, 1);
        
        // Mark this pool for checking
        poolsToCheck.add(poolIndex);
    });
    
    // Check and update pools (in reverse order to avoid index issues)
    const poolIndices = Array.from(poolsToCheck).sort((a, b) => b - a);
    poolIndices.forEach(poolIndex => {
        const pool = currentJsonData.pool[poolIndex];
        if (!pool) return;
        
        // If pool is empty, remove it
        if (!pool.gamelist || pool.gamelist.length === 0) {
            console.log(`  ⚠️ Pool ${poolIndex} is now empty, removing...`);
            currentJsonData.pool.splice(poolIndex, 1);
        } else {
            // Check if we need to update the pool entry to point to new top machine
            const firstMachine = pool.gamelist[0];
            if (firstMachine && firstMachine.sId && pool.src) {
                // If the current src doesn't include the first machine's sId, update it
                if (!pool.src.includes(firstMachine.sId)) {
                    console.log(`  🔄 Updating pool ${poolIndex} to use new top machine: ${firstMachine.id} (sId: ${firstMachine.sId})`);
                    
                    // Extract the old sId from src and replace with new one
                    const srcMatch = pool.src.match(/\/OSM[^_]+/);
                    if (srcMatch) {
                        const oldSId = srcMatch[0].substring(1); // Remove leading /
                        pool.src = pool.src.replace(oldSId, firstMachine.sId);
                        
                        if (pool.channel && pool.channel.toLowerCase().includes(oldSId.toLowerCase())) {
                            pool.channel = pool.channel.replace(new RegExp(oldSId, 'gi'), firstMachine.sId);
                        }
                        
                        console.log(`  📝 Updated pool src: ${pool.src}`);
                    }
                }
            }
        }
    });
    
    // Update the raw JSON editor
    document.getElementById('jsonEditor').value = JSON.stringify(currentJsonData, null, 2);
    
    // Re-render the machine list
    renderMachineList();
    
    // Update status
    const machineCount = countMachines(currentJsonData);
    document.getElementById('editJsonStatus').innerHTML = 
        `<p style="color: #3fb950;">✅ Successfully deleted ${toDelete.length} machine(s). ${machineCount} machines remaining. Click "Save to Server" to apply changes.</p>`;
    
    console.log(`✅ Batch delete completed: ${toDelete.length} machines removed`);
}

function toggleJsonView() {
    const machineListContainer = document.getElementById('machineListContainer');
    const rawJsonContainer = document.getElementById('rawJsonContainer');
    
    if (showingRawJson) {
        // Switch to machine list view
        // First, try to parse any changes made in raw JSON
        try {
            const rawJson = document.getElementById('jsonEditor').value;
            currentJsonData = JSON.parse(rawJson);
            renderMachineList();
        } catch (e) {
            alert('Invalid JSON! Please fix the syntax errors before switching views.');
            return;
        }
        machineListContainer.style.display = 'flex';
        rawJsonContainer.style.display = 'none';
        showingRawJson = false;
    } else {
        // Switch to raw JSON view
        // Update the editor with current data
        document.getElementById('jsonEditor').value = JSON.stringify(currentJsonData, null, 2);
        machineListContainer.style.display = 'none';
        rawJsonContainer.style.display = 'flex';
        showingRawJson = true;
    }
}

async function saveJsonToServer() {
    const serverIp = currentEditServer;
    const remotePath = document.getElementById('editRemotePath').value;
    const statusDiv = document.getElementById('editJsonStatus');
    
    if (!serverIp) {
        CommonUtils.showAlert('Please select a server first', 'error');
        return;
    }
    
    // Get the current JSON content (either from currentJsonData or raw editor)
    let jsonContent;
    if (showingRawJson) {
        jsonContent = document.getElementById('jsonEditor').value;
    } else {
        jsonContent = JSON.stringify(currentJsonData, null, 2);
    }
    
    if (!jsonContent.trim()) {
        CommonUtils.showAlert('JSON content cannot be empty', 'error');
        return;
    }
    
    // Validate JSON syntax
    statusDiv.innerHTML = '<p style="color: #f0883e;">🔍 Validating JSON...</p>';
    
    let parsedJson;
    try {
        parsedJson = JSON.parse(jsonContent);
    } catch (e) {
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Invalid JSON syntax: ${e.message}</p>`;
        CommonUtils.showAlert(`Invalid JSON syntax: ${e.message}`, 'error');
        return;
    }
    
    // Validate JSON structure
    if (!parsedJson.pool || !Array.isArray(parsedJson.pool)) {
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Invalid JSON structure: missing 'pool' array</p>`;
        CommonUtils.showAlert('Invalid JSON structure: missing "pool" array', 'error');
        return;
    }
    
    // Check for required fields in each pool entry
    let structureValid = true;
    let errorMsg = '';
    parsedJson.pool.forEach((pool, index) => {
        if (!pool.gamelist || !Array.isArray(pool.gamelist)) {
            structureValid = false;
            errorMsg = `Pool entry ${index} is missing 'gamelist' array`;
        }
    });
    
    if (!structureValid) {
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Invalid JSON structure: ${errorMsg}</p>`;
        CommonUtils.showAlert(`Invalid JSON structure: ${errorMsg}`, 'error');
        return;
    }
    
    console.log('✅ JSON validation passed');
    statusDiv.innerHTML = '<p style="color: #58a6ff;">🔄 Saving JSON to server...</p>';
    
    try {
        const response = await CommonUtils.apiRequest('/image-recon-json/send-json-to-servers', {
            method: 'POST',
            body: JSON.stringify({
                json_content: jsonContent,
                servers: [{ ip: serverIp }],
                remote_path: remotePath
            })
        });
        
        if (response.status === 'success') {
            const result = response.results[0];
            if (result.status === 'success') {
                const machineCount = countMachines(currentJsonData);
                statusDiv.innerHTML = `<p style="color: #3fb950;">✅ Successfully saved ${machineCount} machines to ${serverIp}</p>`;
                CommonUtils.showAlert('JSON saved successfully!', 'success');
                
                // Ask user if they want to restart the service
                const restartConfirm = confirm(`✅ JSON saved successfully!\n\n🔄 Do you want to restart the OSM service on ${serverIp} now?\n\nThis will apply the new configuration.`);
                
                if (restartConfirm) {
                    await restartServiceAfterSave(serverIp);
                }
            } else {
                throw new Error(result.message || 'Failed to save');
            }
        } else {
            throw new Error(response.message || 'Failed to save JSON');
        }
    } catch (error) {
        console.error('Failed to save JSON:', error);
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Error: ${error.message}</p>`;
        CommonUtils.showAlert(`Failed to save: ${error.message}`, 'error');
    }
}

async function restartServiceAfterSave(serverIp) {
    const statusDiv = document.getElementById('editJsonStatus');
    
    console.log(`🔄 Restarting OSM service on ${serverIp}...`);
    statusDiv.innerHTML = '<p style="color: #f0883e;">🔄 Restarting OSM service...</p>';
    
    try {
        const response = await CommonUtils.apiRequest('/image-recon-service/restart-service', {
            method: 'POST',
            body: JSON.stringify({
                server_ip: serverIp,
                service_name: 'osm',
                initiated_by: 'Edit JSON Modal'
            })
        });
        
        if (response.status === 'success') {
            console.log(`✅ Service restart successful on ${serverIp}`);
            statusDiv.innerHTML = `<p style="color: #3fb950;">✅ Service restarted successfully on ${serverIp}!</p>`;
            CommonUtils.showAlert('Service restarted successfully!', 'success');
        } else {
            throw new Error(response.message || 'Failed to restart service');
        }
    } catch (error) {
        console.error(`❌ Service restart failed on ${serverIp}:`, error);
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Service restart failed: ${error.message}</p>`;
        CommonUtils.showAlert(`Service restart failed: ${error.message}`, 'error');
    }
}

async function searchMachineInServers() {
    const searchTerm = document.getElementById('machineSearchBox').value.trim();
    
    if (!searchTerm) {
        CommonUtils.showAlert('Please enter a machine ID to search', 'error');
        return;
    }
    
    if (editServers.length === 0) {
        CommonUtils.showAlert('No servers loaded. Please open the Edit JSON modal first.', 'error');
        return;
    }
    
    console.log(`🔍 Searching for machine ID: "${searchTerm}" across ${editServers.length} servers...`);
    
    const statusDiv = document.getElementById('editJsonStatus');
    statusDiv.innerHTML = `<p style="color: #58a6ff;">🔄 Searching for "${searchTerm}" across ${editServers.length} servers...</p>`;
    
    const remotePath = document.getElementById('editRemotePath').value;
    let foundInServer = null;
    let foundMachines = [];
    
    try {
        // Search through each server
        for (const server of editServers) {
            try {
                const response = await CommonUtils.apiRequest('/image-recon-json/fetch-json-from-server', {
                    method: 'POST',
                    body: JSON.stringify({
                        server_ip: server.ip,
                        remote_path: remotePath
                    })
                });
                
                if (response.status === 'success') {
                    const jsonData = JSON.parse(response.content);
                    
                    // Search through all machines in this server
                    if (jsonData.pool && Array.isArray(jsonData.pool)) {
                        for (const pool of jsonData.pool) {
                            if (pool.gamelist && Array.isArray(pool.gamelist)) {
                                for (const machine of pool.gamelist) {
                                    const machineId = machine.id || '';
                                    const sId = machine.sId || '';
                                    // Check if machine ID or sId contains the search term (case-insensitive, partial match)
                                    if (machineId.toLowerCase().includes(searchTerm.toLowerCase()) || 
                                        machineId.includes(searchTerm) ||
                                        sId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                                        sId.includes(searchTerm)) {
                                        foundMachines.push({
                                            id: machineId,
                                            sId: sId,
                                            pool: pool.channel || pool.id || 'N/A',
                                            gametype: pool.gametype || pool.type || 'N/A'
                                        });
                                    }
                                }
                            }
                        }
                    }
                    
                    // If we found machines in this server, stop searching
                    if (foundMachines.length > 0) {
                        foundInServer = server;
                        break;
                    }
                }
            } catch (err) {
                console.warn(`⚠️ Failed to search server ${server.ip}:`, err);
                // Continue to next server
            }
        }
        
        if (foundInServer && foundMachines.length > 0) {
            console.log(`✅ Found ${foundMachines.length} machine(s) in server ${foundInServer.ip}`);
            
            // Show results in status
            const machineList = foundMachines.map(m => m.id).join(', ');
            statusDiv.innerHTML = `<p style="color: #3fb950;">✅ Found ${foundMachines.length} machine(s) in <strong>${foundInServer.label || foundInServer.ip}</strong>: ${machineList}</p>`;
            
            // Automatically select and load that server
            selectServerForEdit(foundInServer.ip);
            
            CommonUtils.showAlert(`Found ${foundMachines.length} machine(s) in ${foundInServer.label || foundInServer.ip}!`, 'success');
        } else {
            console.log(`❌ No machines found matching: "${searchTerm}"`);
            statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ No machines found matching "${searchTerm}" across ${editServers.length} servers</p>`;
            CommonUtils.showAlert(`No machines found matching "${searchTerm}"`, 'error');
        }
    } catch (error) {
        console.error('❌ Search error:', error);
        statusDiv.innerHTML = `<p style="color: #ff7b72;">❌ Search failed: ${error.message}</p>`;
        CommonUtils.showAlert(`Search failed: ${error.message}`, 'error');
    }
}

function closeEditJsonModal() {
    const modal = document.getElementById('editJsonModal');
    if (modal) {
        modal.style.display = 'none';
    }
    currentEditServer = null;
    currentJsonData = null;
    showingRawJson = false;
    
    // Clear search box
    const searchBox = document.getElementById('machineSearchBox');
    if (searchBox) searchBox.value = '';
}

// Close modal when clicking outside of it
window.addEventListener('click', function(event) {
    const modal = document.getElementById('editJsonModal');
    if (event.target === modal) {
        closeEditJsonModal();
    }
});

// Export functions for global access
window.ImageReconJson = {
    loadMachineTypes,
    handleJsonGeneration,
    handleDownloadJson,
    closeResultsModal
};

// Make edit functions globally accessible
window.showEditJsonModal = showEditJsonModal;
window.selectServerForEdit = selectServerForEdit;
window.saveJsonToServer = saveJsonToServer;
window.closeEditJsonModal = closeEditJsonModal;
window.toggleJsonView = toggleJsonView;
window.toggleSelectAll = toggleSelectAll;
window.updateDeleteButtonState = updateDeleteButtonState;
window.batchDeleteMachines = batchDeleteMachines;
window.searchMachineInServers = searchMachineInServers;
