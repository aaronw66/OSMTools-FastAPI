// Image Recon JSON Generator JavaScript

let generatedJsonContent = '';
let availableServers = [];

document.addEventListener('DOMContentLoaded', function() {
    initializeImageReconJson();
});

async function initializeImageReconJson() {
    await loadMachineTypes();
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

// Export functions for global access
window.ImageReconJson = {
    loadMachineTypes,
    handleJsonGeneration,
    handleDownloadJson,
    closeResultsModal
};
