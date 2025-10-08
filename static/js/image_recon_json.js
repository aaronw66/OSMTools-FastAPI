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
            ${formattedJson}
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
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Machine ID</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Pool ID</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Type</th>';
    html += '<th style="padding: 12px; text-align: left; color: #58a6ff; font-weight: 600;">Stream ID</th>';
    html += '<th style="padding: 12px; text-align: center; color: #58a6ff; font-weight: 600; width: 100px;">Action</th>';
    html += '</tr>';
    html += '</thead>';
    html += '<tbody>';
    
    currentJsonData.pool.forEach((pool, poolIndex) => {
        if (pool.gamelist && pool.gamelist.length > 0) {
            pool.gamelist.forEach((machine, machineIndex) => {
                html += '<tr style="border-bottom: 1px solid #21262d;" onmouseover="this.style.background=\'#21262d\'" onmouseout="this.style.background=\'transparent\'">';
                html += `<td style="padding: 12px; color: #c9d1d9; font-family: monospace; font-size: 13px;">${machine.id || 'N/A'}</td>`;
                html += `<td style="padding: 12px; color: #8b949e;">${pool.id || 'N/A'}</td>`;
                html += `<td style="padding: 12px; color: #8b949e;">${pool.type || 'N/A'}</td>`;
                html += `<td style="padding: 12px; color: #8b949e; font-family: monospace; font-size: 12px;">${machine.sId || 'N/A'}</td>`;
                html += `<td style="padding: 12px; text-align: center;">`;
                html += `<button onclick="deleteMachine(${poolIndex}, ${machineIndex})" class="btn-delete-machine" style="background: linear-gradient(135deg, #da3633 0%, #b02a28 100%); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; transition: all 0.2s;" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(218, 54, 51, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none'">`;
                html += `<i class="fas fa-trash"></i> Delete`;
                html += `</button>`;
                html += `</td>`;
                html += '</tr>';
            });
        }
    });
    
    html += '</tbody>';
    html += '</table>';
    
    container.innerHTML = html;
}

function deleteMachine(poolIndex, machineIndex) {
    if (!confirm('Are you sure you want to delete this machine?')) {
        return;
    }
    
    // Remove the machine from the data
    currentJsonData.pool[poolIndex].gamelist.splice(machineIndex, 1);
    
    // If pool is now empty, remove the pool
    if (currentJsonData.pool[poolIndex].gamelist.length === 0) {
        currentJsonData.pool.splice(poolIndex, 1);
    }
    
    // Update the raw JSON editor
    document.getElementById('jsonEditor').value = JSON.stringify(currentJsonData, null, 2);
    
    // Re-render the machine list
    renderMachineList();
    
    // Update status
    const machineCount = countMachines(currentJsonData);
    document.getElementById('editJsonStatus').innerHTML = 
        `<p style="color: #f0883e;">⚠️ Machine deleted. ${machineCount} machines remaining. Click "Save to Server" to apply changes.</p>`;
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
    
    // Validate JSON
    try {
        JSON.parse(jsonContent);
    } catch (e) {
        CommonUtils.showAlert(`Invalid JSON: ${e.message}`, 'error');
        return;
    }
    
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
            if (result.success) {
                const machineCount = countMachines(currentJsonData);
                statusDiv.innerHTML = `<p style="color: #3fb950;">✅ Successfully saved ${machineCount} machines to ${serverIp}</p>`;
                CommonUtils.showAlert('JSON saved successfully!', 'success');
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

function closeEditJsonModal() {
    const modal = document.getElementById('editJsonModal');
    if (modal) {
        modal.style.display = 'none';
    }
    currentEditServer = null;
    currentJsonData = null;
    showingRawJson = false;
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
window.deleteMachine = deleteMachine;
window.toggleJsonView = toggleJsonView;
