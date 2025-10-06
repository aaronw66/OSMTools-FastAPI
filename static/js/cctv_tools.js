// CCTV Tools JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeCCTVTools();
});

function initializeCCTVTools() {
    setupEventListeners();
    loadSystemStatus();
}

function setupEventListeners() {
    // Status refresh
    document.getElementById('refreshStatusBtn').addEventListener('click', loadSystemStatus);
    
    // Configuration tools
    document.getElementById('setupCamerasBtn').addEventListener('click', setupCameras);
    document.getElementById('configMonitoringBtn').addEventListener('click', configureMonitoring);
    
    // CSV upload
    document.getElementById('csvUploadForm').addEventListener('submit', handleCSVUpload);
}

async function loadSystemStatus() {
    const refreshBtn = document.getElementById('refreshStatusBtn');
    const stopLoading = CommonUtils.showLoading(refreshBtn);
    
    try {
        const response = await CommonUtils.apiRequest('/cctv-tools/status');
        
        if (response.status === 'success') {
            displaySystemStatus(response.data);
            CommonUtils.showAlert('Status updated successfully!', 'success');
        } else {
            throw new Error(response.message || 'Failed to load status');
        }
        
    } catch (error) {
        console.error('Failed to load status:', error);
        CommonUtils.showAlert(`Failed to load status: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function displaySystemStatus(data) {
    document.getElementById('systemStatusValue').textContent = data.system_status;
    document.getElementById('systemStatusValue').className = `status-value ${data.system_status}`;
    
    document.getElementById('activeCameras').textContent = `${data.active_cameras}/${data.total_cameras}`;
    document.getElementById('storageUsage').textContent = data.storage_usage;
    document.getElementById('alertCount').textContent = data.alerts;
    
    // Add status classes based on values
    const alertElement = document.getElementById('alertCount');
    if (data.alerts > 0) {
        alertElement.className = 'status-value warning';
    } else {
        alertElement.className = 'status-value operational';
    }
}

async function setupCameras() {
    const setupBtn = document.getElementById('setupCamerasBtn');
    const stopLoading = CommonUtils.showLoading(setupBtn);
    
    try {
        const cameraCount = parseInt(document.getElementById('cameraCount').value);
        const resolution = document.getElementById('resolution').value;
        
        const requestData = {
            config_type: "camera_setup",
            parameters: {
                camera_count: cameraCount,
                resolution: resolution,
                fps: 30
            }
        };
        
        const response = await CommonUtils.apiRequest('/cctv-tools/configure', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        if (response.status === 'success') {
            displayCameraSetupResults(response.data);
            CommonUtils.showAlert(response.message, 'success');
        } else {
            throw new Error(response.message || 'Camera setup failed');
        }
        
    } catch (error) {
        console.error('Camera setup failed:', error);
        CommonUtils.showAlert(`Camera setup failed: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function displayCameraSetupResults(data) {
    const resultsCard = document.getElementById('resultsCard');
    const resultsContent = document.getElementById('resultsContent');
    
    resultsContent.innerHTML = `
        <h3>Camera Setup Complete</h3>
        <p>Successfully configured ${data.total_count} cameras</p>
        <div class="camera-grid">
            ${data.cameras.map(camera => `
                <div class="camera-item">
                    <div class="camera-name">${camera.name}</div>
                    <div class="camera-details">
                        ID: ${camera.id}<br>
                        Resolution: ${camera.resolution}<br>
                        FPS: ${camera.fps}<br>
                        Stream: ${camera.stream_url}
                    </div>
                    <span class="camera-status ${camera.status}">${camera.status}</span>
                </div>
            `).join('')}
        </div>
    `;
    
    resultsCard.style.display = 'block';
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

async function configureMonitoring() {
    const configBtn = document.getElementById('configMonitoringBtn');
    const stopLoading = CommonUtils.showLoading(configBtn);
    
    try {
        const monitoringType = document.getElementById('monitoringType').value;
        const checkInterval = parseInt(document.getElementById('checkInterval').value);
        
        const requestData = {
            config_type: "monitoring_config",
            parameters: {
                type: monitoringType,
                interval: checkInterval,
                alerts: true
            }
        };
        
        const response = await CommonUtils.apiRequest('/cctv-tools/configure', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });
        
        if (response.status === 'success') {
            displayMonitoringConfig(response.data);
            CommonUtils.showAlert(response.message, 'success');
        } else {
            throw new Error(response.message || 'Monitoring configuration failed');
        }
        
    } catch (error) {
        console.error('Monitoring configuration failed:', error);
        CommonUtils.showAlert(`Monitoring configuration failed: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function displayMonitoringConfig(data) {
    const resultsCard = document.getElementById('resultsCard');
    const resultsContent = document.getElementById('resultsContent');
    
    resultsContent.innerHTML = `
        <h3>Monitoring Configuration Updated</h3>
        <div class="monitoring-config">
            <div class="config-summary">
                <div class="config-item">
                    <div class="config-label">Type</div>
                    <div class="config-value">${data.monitoring_type}</div>
                </div>
                <div class="config-item">
                    <div class="config-label">Interval</div>
                    <div class="config-value">${data.check_interval}s</div>
                </div>
                <div class="config-item">
                    <div class="config-label">Alerts</div>
                    <div class="config-value">${data.alerts_enabled ? 'Enabled' : 'Disabled'}</div>
                </div>
                <div class="config-item">
                    <div class="config-label">Status</div>
                    <div class="config-value">${data.status}</div>
                </div>
            </div>
        </div>
    `;
    
    resultsCard.style.display = 'block';
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

async function handleCSVUpload(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const stopLoading = CommonUtils.showLoading(submitBtn);
    
    try {
        if (!CommonUtils.validateForm(form)) {
            CommonUtils.showAlert('Please select a CSV file', 'error');
            return;
        }
        
        const formData = new FormData(form);
        const response = await CommonUtils.uploadFile('/cctv-tools/upload-csv', formData);
        
        if (response.status === 'success') {
            displayCSVResults(response.data);
            CommonUtils.showAlert(response.message, 'success');
            form.reset();
        } else {
            throw new Error(response.message || 'CSV upload failed');
        }
        
    } catch (error) {
        console.error('CSV upload failed:', error);
        CommonUtils.showAlert(`CSV upload failed: ${error.message}`, 'error');
    } finally {
        stopLoading();
    }
}

function displayCSVResults(data) {
    const resultsCard = document.getElementById('resultsCard');
    const resultsContent = document.getElementById('resultsContent');
    
    resultsContent.innerHTML = `
        <h3>CSV Processing Complete</h3>
        <p>Processed ${data.count} items from CSV file</p>
        <div class="csv-results">
            ${data.items.map(item => `
                <div class="csv-item">
                    <div class="csv-item-header">${item.name || item.id}</div>
                    <div class="csv-item-details">
                        ID: ${item.id}<br>
                        IP: ${item.ip}<br>
                        Status: ${item.status}<br>
                        Processed: ${new Date(item.timestamp).toLocaleString()}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    resultsCard.style.display = 'block';
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

// Export functions for global access
window.CCTVTools = {
    loadSystemStatus,
    setupCameras,
    configureMonitoring,
    handleCSVUpload
};
