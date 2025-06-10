// Global variables
let timeEntries = [];
let extractedData = [];
let editingId = null;
const API_URL = 'http://localhost:5000/api';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadEntries();
    updateStats();
    
    // Set default dates for reports
    const today = new Date();
    const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    document.getElementById('report-start').value = lastWeek.toISOString().split('T')[0];
    document.getElementById('report-end').value = today.toISOString().split('T')[0];
    
    // Add event listeners
    document.getElementById('manual-entry-form').addEventListener('submit', handleManualEntry);
    document.getElementById('upload-area').addEventListener('click', () => document.getElementById('file-input').click());
    document.getElementById('file-input').addEventListener('change', handleFileUpload);
    document.getElementById('search-entries').addEventListener('input', filterEntries);
    
    // Drag and drop functionality
    const uploadArea = document.getElementById('upload-area');
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload({ target: { files: files } });
        }
    });
});

// Switch between tabs
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Add active class to clicked nav tab
    event.target.classList.add('active');
    
    // Refresh data if viewing entries
    if (tabName === 'entries') {
        loadEntries();
    } else if (tabName === 'reports') {
        updateStats();
    }
}

// Toggle order number field based on entry type
function toggleOrderNumber() {
    const entryType = document.getElementById('entry-type').value;
    const orderNumberGroup = document.getElementById('order-number-group');
    const orderNumberInput = document.getElementById('order-number');
    
    if (entryType === 'service') {
        orderNumberGroup.style.display = 'block';
        orderNumberInput.required = true;
    } else {
        orderNumberGroup.style.display = 'none';
        orderNumberInput.required = false;
        orderNumberInput.value = '';
    }
}

// Handle manual entry form submission
async function handleManualEntry(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const entry = {
        employeeName: formData.get('employeeName'),
        entryType: formData.get('entryType'),
        orderNumber: formData.get('orderNumber') || '',
        startDateTime: formData.get('startDateTime'),
        endDateTime: formData.get('endDateTime'),
        notes: formData.get('notes') || ''
    };
    
    try {
        const response = await fetch(`${API_URL}/entries`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(entry)
        });
        
        if (response.ok) {
            // Reset form
            e.target.reset();
            toggleOrderNumber();
            
            // Show success message
            showToast('Time entry saved successfully!', 'success');
            
            // Update stats
            updateStats();
        } else {
            throw new Error('Failed to save entry');
        }
    } catch (error) {
        showToast('Error saving entry: ' + error.message, 'error');
    }
}

// Calculate elapsed time
function calculateElapsedTime(start, end) {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diff = endDate - startDate;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    return `${hours.toString().padStart(2, '0')}h:${minutes.toString().padStart(2, '0')}m:${seconds.toString().padStart(2, '0')}s`;
}

// Handle file upload
async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        showToast('Please upload an image file', 'error');
        return;
    }
    
    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
        showToast('File size must be less than 10MB', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // Convert image to base64
        const base64 = await fileToBase64(file);
        
        // Send to OCR endpoint
        const response = await fetch(`${API_URL}/ocr`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ image: base64 })
        });
        
        if (response.ok) {
            const data = await response.json();
            extractedData = data.entries;
            showExtractedDataPreview();
            showToast('Image processed successfully!', 'success');
        } else {
            throw new Error('Failed to process image');
        }
    } catch (error) {
        showToast('Error processing image: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Convert file to base64
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

// Show extracted data preview
function showExtractedDataPreview() {
    const previewSection = document.getElementById('ocr-preview');
    const previewContent = document.getElementById('preview-content');
    
    previewContent.innerHTML = '';
    
    extractedData.forEach((entry, index) => {
        const startDate = new Date(entry.startDateTime);
        const endDate = new Date(entry.endDateTime);
        
        const previewHtml = `
            <div class="preview-item">
                <div>
                    <strong>${entry.employeeName}</strong> - ${entry.orderNumber}<br>
                    <small>${startDate.toLocaleString()} - ${endDate.toLocaleString()}</small>
                </div>
                <div>
                    <span class="status-badge status-service">${entry.elapsedTime}</span>
                </div>
            </div>
        `;
        
        previewContent.innerHTML += previewHtml;
    });
    
    previewSection.style.display = 'block';
}

// Save extracted data
async function saveExtractedData() {
    showLoading();
    
    try {
        for (const data of extractedData) {
            const entry = {
                employeeName: data.employeeName,
                entryType: 'service',
                orderNumber: data.orderNumber,
                startDateTime: data.startDateTime,
                endDateTime: data.endDateTime,
                notes: 'Imported from image'
            };
            
            await fetch(`${API_URL}/entries`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(entry)
            });
        }
        
        showToast(`${extractedData.length} entries saved successfully!`, 'success');
        
        // Clear preview
        document.getElementById('ocr-preview').style.display = 'none';
        extractedData = [];
        
        // Update stats
        updateStats();
    } catch (error) {
        showToast('Error saving entries: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Edit extracted data
function editExtractedData() {
    // In a real application, this would open a modal to edit the extracted data
    showToast('Edit functionality would be implemented here', 'info');
}

// Cancel extraction
function cancelExtraction() {
    document.getElementById('ocr-preview').style.display = 'none';
    extractedData = [];
    document.getElementById('file-input').value = '';
}

// Load entries into table
async function loadEntries() {
    try {
        const response = await fetch(`${API_URL}/entries`);
        
        if (response.ok) {
            timeEntries = await response.json();
            displayEntries();
        } else {
            throw new Error('Failed to load entries');
        }
    } catch (error) {
        showToast('Error loading entries: ' + error.message, 'error');
    }
}

// Display entries in table
function displayEntries() {
    const tbody = document.getElementById('entries-tbody');
    tbody.innerHTML = '';
    
    if (timeEntries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">No entries found</td></tr>';
        return;
    }
    
    // Sort entries by start date (newest first)
    const sortedEntries = [...timeEntries].sort((a, b) => 
        new Date(b.startDateTime) - new Date(a.startDateTime)
    );
    
    sortedEntries.forEach(entry => {
        const row = createEntryRow(entry);
        tbody.appendChild(row);
    });
}

// Create entry row
function createEntryRow(entry) {
    const row = document.createElement('tr');
    const startDate = new Date(entry.startDateTime);
    const endDate = new Date(entry.endDateTime);
    
    row.innerHTML = `
        <td>${entry.employeeName}</td>
        <td><span class="status-badge status-${entry.entryType}">${entry.entryType}</span></td>
        <td>${entry.orderNumber || '-'}</td>
        <td>${startDate.toLocaleString()}</td>
        <td>${endDate.toLocaleString()}</td>
        <td>${entry.elapsedTime}</td>
        <td>
            <div class="action-buttons">
                <button class="btn btn-sm btn-secondary" onclick="editEntry(${entry.id})">✏️</button>
                <button class="btn btn-sm btn-danger" onclick="deleteEntry(${entry.id})">🗑️</button>
            </div>
        </td>
    `;
    
    return row;
}

// Filter entries
function filterEntries(e) {
    const searchTerm = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#entries-tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

// Edit entry
function editEntry(id) {
    const entry = timeEntries.find(e => e.id === id);
    if (!entry) return;
    
    editingId = id;
    
    const modal = document.getElementById('edit-modal');
    const form = document.getElementById('edit-form');
    
    form.innerHTML = `
        <div class="form-row">
            <div class="form-group">
                <label for="edit-employee-name">Employee Name</label>
                <input type="text" id="edit-employee-name" value="${entry.employeeName}" required>
            </div>
            <div class="form-group">
                <label for="edit-entry-type">Entry Type</label>
                <select id="edit-entry-type" required onchange="toggleEditOrderNumber()">
                    <option value="service" ${entry.entryType === 'service' ? 'selected' : ''}>Service Order</option>
                    <option value="vacation" ${entry.entryType === 'vacation' ? 'selected' : ''}>Vacation</option>
                    <option value="personal" ${entry.entryType === 'personal' ? 'selected' : ''}>Personal</option>
                    <option value="shop" ${entry.entryType === 'shop' ? 'selected' : ''}>Shop</option>
                    <option value="nonbillable" ${entry.entryType === 'nonbillable' ? 'selected' : ''}>Non-Billable</option>
                    <option value="drive" ${entry.entryType === 'drive' ? 'selected' : ''}>Drive Time</option>
                </select>
            </div>
        </div>
        
        <div class="form-group" id="edit-order-number-group" style="${entry.entryType === 'service' ? '' : 'display: none;'}">
            <label for="edit-order-number">Order Number</label>
            <input type="text" id="edit-order-number" value="${entry.orderNumber || ''}">
        </div>
        
        <div class="form-row">
            <div class="form-group">
                <label for="edit-start-datetime">Start Date & Time</label>
                <input type="datetime-local" id="edit-start-datetime" value="${entry.startDateTime}" required>
            </div>
            <div class="form-group">
                <label for="edit-end-datetime">End Date & Time</label>
                <input type="datetime-local" id="edit-end-datetime" value="${entry.endDateTime}" required>
            </div>
        </div>
        
        <div class="form-group">
            <label for="edit-notes">Notes</label>
            <textarea id="edit-notes" rows="3">${entry.notes || ''}</textarea>
        </div>
        
        <div style="display: flex; gap: 1rem;">
            <button type="button" class="btn btn-primary" onclick="saveEdit()">Save Changes</button>
            <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
        </div>
    `;
    
    modal.classList.add('active');
}

// Toggle edit order number field
function toggleEditOrderNumber() {
    const entryType = document.getElementById('edit-entry-type').value;
    const orderNumberGroup = document.getElementById('edit-order-number-group');
    
    if (entryType === 'service') {
        orderNumberGroup.style.display = 'block';
    } else {
        orderNumberGroup.style.display = 'none';
    }
}

// Save edit
async function saveEdit() {
    const entry = {
        employeeName: document.getElementById('edit-employee-name').value,
        entryType: document.getElementById('edit-entry-type').value,
        orderNumber: document.getElementById('edit-entry-type').value === 'service' ? document.getElementById('edit-order-number').value : '',
        startDateTime: document.getElementById('edit-start-datetime').value,
        endDateTime: document.getElementById('edit-end-datetime').value,
        notes: document.getElementById('edit-notes').value
    };
    
    try {
        const response = await fetch(`${API_URL}/entries/${editingId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(entry)
        });
        
        if (response.ok) {
            loadEntries();
            closeEditModal();
            showToast('Entry updated successfully!', 'success');
            updateStats();
        } else {
            throw new Error('Failed to update entry');
        }
    } catch (error) {
        showToast('Error updating entry: ' + error.message, 'error');
    }
}

// Close edit modal
function closeEditModal() {
    document.getElementById('edit-modal').classList.remove('active');
    editingId = null;
}

// Delete entry
async function deleteEntry(id) {
    if (confirm('Are you sure you want to delete this entry?')) {
        try {
            const response = await fetch(`${API_URL}/entries/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                loadEntries();
                showToast('Entry deleted successfully!', 'success');
                updateStats();
            } else {
                throw new Error('Failed to delete entry');
            }
        } catch (error) {
            showToast('Error deleting entry: ' + error.message, 'error');
        }
    }
}

// Update statistics
async function updateStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        
        if (response.ok) {
            const stats = await response.json();
            
            // Update UI
            document.getElementById('total-hours').textContent = stats.totalHoursThisWeek;
            document.getElementById('total-entries').textContent = stats.totalEntries;
            document.getElementById('active-orders').textContent = stats.activeOrders;
        }
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Generate report
async function generateReport() {
    const reportType = document.getElementById('report-type').value;
    const startDate = document.getElementById('report-start').value;
    const endDate = document.getElementById('report-end').value;
    const employee = document.getElementById('report-employee').value;
    
    if (!startDate || !endDate) {
        showToast('Please select date range', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_URL}/report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reportType,
                startDate,
                endDate,
                employee
            })
        });
        
        if (response.ok) {
            // Download the PDF
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${reportType}_report_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showToast('Report generated successfully!', 'success');
        } else {
            throw new Error('Failed to generate report');
        }
    } catch (error) {
        showToast('Error generating report: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Show loading spinner
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

// Hide loading spinner
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
