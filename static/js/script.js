document.addEventListener('DOMContentLoaded', function() {
    // References to elements
    const testForm = document.getElementById('test-form');
    const resetFormBtn = document.getElementById('reset-form-btn');
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    const historyTableBody = document.getElementById('history-table-body');
    const noHistoryRow = document.getElementById('no-history-row');
    const httpMethodSelect = document.getElementById('http_method');
    const bodyContainer = document.getElementById('body-container');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    const testProgress = document.getElementById('test-progress');
    
    // Load test history when page loads
    loadTestHistory();
    
    // Show/hide body field based on HTTP method
    httpMethodSelect.addEventListener('change', function() {
        const method = this.value;
        if (method === 'GET' || method === 'HEAD') {
            bodyContainer.style.display = 'none';
        } else {
            bodyContainer.style.display = 'block';
        }
    });
    
    // Submit form - Run Test
    testForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Basic validation
        const targetUrl = document.getElementById('target_url').value;
        const numRequests = parseInt(document.getElementById('num_requests').value);
        const concurrency = parseInt(document.getElementById('concurrency').value);
        
        if (!targetUrl) {
            showAlert('Please enter a target URL', 'danger');
            return;
        }
        
        if (numRequests < 1) {
            showAlert('Number of requests must be at least 1', 'danger');
            return;
        }
        
        if (concurrency < 1) {
            showAlert('Concurrency must be at least 1', 'danger');
            return;
        }
        
        if (concurrency > numRequests) {
            showAlert('Concurrency cannot be greater than the number of requests', 'danger');
            return;
        }
        
        // Show loading modal with progress bar
        loadingModal.show();
        simulateProgress(numRequests);
        
        // Submit form data
        const formData = new FormData(testForm);
        
        fetch('/run_test', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loadingModal.hide();
            
            if (data.error) {
                showAlert(`Error: ${data.error}`, 'danger');
            } else {
                showAlert('Test completed successfully!', 'success');
                loadTestHistory();
                
                // Redirect to report page
                window.location.href = `/view_report/${data.test_id}`;
            }
        })
        .catch(error => {
            loadingModal.hide();
            showAlert(`Error: ${error.message}`, 'danger');
        });
    });
    
    // Reset form button
    resetFormBtn.addEventListener('click', function() {
        testForm.reset();
        // Ensure body container display is updated
        if (httpMethodSelect.value === 'GET' || httpMethodSelect.value === 'HEAD') {
            bodyContainer.style.display = 'none';
        } else {
            bodyContainer.style.display = 'block';
        }
    });
    
    // Clear history button
    clearHistoryBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to clear all test history?')) {
            fetch('/clear_history', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Test history cleared!', 'success');
                    loadTestHistory();
                }
            })
            .catch(error => {
                showAlert(`Error: ${error.message}`, 'danger');
            });
        }
    });
    
    // Load test history from server
    function loadTestHistory() {
        fetch('/all_reports')
        .then(response => response.json())
        .then(data => {
            // Clear existing rows
            while (historyTableBody.firstChild) {
                historyTableBody.removeChild(historyTableBody.firstChild);
            }
            
            if (data.length === 0) {
                // If no history, show the "no history" row
                historyTableBody.appendChild(noHistoryRow);
            } else {
                // Add each test to the history table
                data.forEach(test => {
                    const row = document.createElement('tr');
                    
                    // Format date if timestamp exists
                    const timestamp = test.timestamp || 'N/A';
                    
                    // Format success rate
                    const successRate = test.summary ? 
                        `${test.summary.success_rate_percent.toFixed(2)}%` : 'N/A';
                    
                    // Format avg response time
                    const avgResponseTime = test.summary ? 
                        `${test.summary.avg_response_time_ms.toFixed(2)} ms` : 'N/A';
                    
                    row.innerHTML = `
                        <td>${timestamp}</td>
                        <td>${test.test_config.target_url}</td>
                        <td>${test.test_config.http_method}</td>
                        <td>${test.test_config.num_requests}</td>
                        <td>${successRate}</td>
                        <td>${avgResponseTime}</td>
                        <td>
                            <a href="/view_report/${test.test_id}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-chart-bar"></i> View
                            </a>
                        </td>
                    `;
                    
                    historyTableBody.appendChild(row);
                });
            }
        })
        .catch(error => {
            console.error('Error loading test history:', error);
        });
    }
    
    // Show alert message
    function showAlert(message, type) {
        // Create alert element
        const alertEl = document.createElement('div');
        alertEl.className = `alert alert-${type} alert-dismissible fade show`;
        alertEl.role = 'alert';
        alertEl.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Find a place to insert the alert
        const container = document.querySelector('.container');
        container.insertBefore(alertEl, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertEl);
            bsAlert.close();
        }, 5000);
    }
    
    // Simulate progress for the loading modal
    function simulateProgress(totalRequests) {
        testProgress.style.width = '0%';
        testProgress.setAttribute('aria-valuenow', 0);
        
        let progress = 0;
        const interval = setInterval(() => {
            // Increase progress at decreasing rate (slower towards the end)
            const increment = Math.max(1, Math.floor((100 - progress) / 10));
            progress = Math.min(95, progress + increment);  // Never reach 100% with simulation
            
            testProgress.style.width = `${progress}%`;
            testProgress.setAttribute('aria-valuenow', progress);
            
            if (progress >= 95) {
                clearInterval(interval);
            }
        }, 200);
        
        // Store interval ID in a data attribute to clear it if needed
        testProgress.dataset.intervalId = interval;
    }
    
    // Initial check for HTTP method to show/hide body field
    if (httpMethodSelect.value === 'GET' || httpMethodSelect.value === 'HEAD') {
        bodyContainer.style.display = 'none';
    }
});
