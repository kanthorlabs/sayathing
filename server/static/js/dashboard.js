/**
 * Dashboard JavaScript
 * Handles tab navigation, task loading, pagination, and modal interactions
 */

class TaskDashboard {
    constructor() {
        this.currentState = '';
        this.currentCursor = null;
        this.pageSize = 25;
        this.taskStates = [];
        this.taskCounts = {};
        this.voices = [];
        this.enqueueItemCounter = 0;
        this.currentAudioUrl = null; // Track current audio URL for cleanup
        
        this.initializeElements();
        this.attachEventListeners();
        this.initialize();
    }
    
    initializeElements() {
        // Main elements
        this.tabsContainer = document.querySelector('.tabs');
        this.tasksTable = document.getElementById('tasks-table');
        this.tasksTableBody = document.getElementById('tasks-tbody');
        this.loadingEl = document.getElementById('loading');
        this.errorEl = document.getElementById('error');
        this.errorMessageEl = document.getElementById('error-message');
        this.emptyStateEl = document.getElementById('empty-state');
        this.tasksContainer = document.getElementById('tasks-container');
        
        // Controls
        this.pageSizeSelect = document.getElementById('page-size');
        this.refreshBtn = document.getElementById('refresh-btn');
        this.enqueueBtn = document.getElementById('enqueue-btn');
        this.createSpeechBtn = document.getElementById('create-speech-btn');
        
        // Pagination
        this.prevBtn = document.getElementById('prev-btn');
        this.nextBtn = document.getElementById('next-btn');
        this.paginationInfo = document.getElementById('pagination-info');
        
        // Task Detail Modal
        this.modal = document.getElementById('task-modal');
        this.modalContent = document.getElementById('modal-content');
        this.closeModalBtn = document.getElementById('close-modal');
        this.modalCloseBtn = document.getElementById('modal-close-btn');
        
        // Enqueue Modal
        this.enqueueModal = document.getElementById('enqueue-modal');
        this.enqueueForm = document.getElementById('enqueue-form');
        this.itemsContainer = document.getElementById('items-list');
        this.addItemBtn = document.getElementById('add-item-btn');
        this.enqueueCancelBtn = document.getElementById('enqueue-cancel-btn');
        this.enqueueSubmitBtn = document.getElementById('enqueue-submit-btn');
        this.closeEnqueueModalBtn = document.getElementById('close-enqueue-modal');
        
        // Create Speech Modal
        this.createSpeechModal = document.getElementById('create-speech-modal');
        this.createSpeechForm = document.getElementById('create-speech-form');
        this.speechTextArea = document.getElementById('speech-text');
        this.speechVoiceSelect = document.getElementById('speech-voice');
        this.speechLoadingEl = document.getElementById('speech-loading');
        this.speechResultEl = document.getElementById('speech-result');
        this.speechAudio = document.getElementById('speech-audio');
        this.speechDownloadBtn = document.getElementById('speech-download-btn');
        this.speechRequestDetails = document.getElementById('speech-request-details');
        this.speechErrorEl = document.getElementById('speech-error');
        this.speechErrorMessage = document.getElementById('speech-error-message');
        this.speechCancelBtn = document.getElementById('speech-cancel-btn');
        this.speechSubmitBtn = document.getElementById('speech-submit-btn');
        this.speechResetBtn = document.getElementById('speech-reset-btn');
        this.closeSpeechModalBtn = document.getElementById('close-create-speech-modal');
    }
    
    attachEventListeners() {
        // Page size change
        this.pageSizeSelect.addEventListener('change', () => {
            this.pageSize = parseInt(this.pageSizeSelect.value);
            this.currentCursor = null; // Reset pagination
            this.loadTasks();
        });
        
        // Refresh button
        this.refreshBtn.addEventListener('click', () => {
            this.currentCursor = null; // Reset pagination
            this.loadTasks();
            this.loadTaskCounts(); // Also refresh counts
        });
        
        // Enqueue button
        this.enqueueBtn.addEventListener('click', () => this.showEnqueueModal());
        
        // Create Speech button
        this.createSpeechBtn.addEventListener('click', () => this.showCreateSpeechModal());
        
        // Pagination
        this.prevBtn.addEventListener('click', () => this.goToPreviousPage());
        this.nextBtn.addEventListener('click', () => this.goToNextPage());
        
        // Task detail modal close handlers
        this.closeModalBtn.addEventListener('click', () => this.closeModal());
        this.modalCloseBtn.addEventListener('click', () => this.closeModal());
        
        // Enqueue modal handlers
        this.closeEnqueueModalBtn.addEventListener('click', () => this.closeEnqueueModal());
        this.enqueueCancelBtn.addEventListener('click', () => this.closeEnqueueModal());
        this.addItemBtn.addEventListener('click', () => this.addEnqueueItem());
        this.enqueueForm.addEventListener('submit', (e) => this.handleEnqueueSubmit(e));
        
        // Create Speech modal handlers
        this.closeSpeechModalBtn.addEventListener('click', () => this.closeCreateSpeechModal());
        this.speechCancelBtn.addEventListener('click', () => this.closeCreateSpeechModal());
        this.speechResetBtn.addEventListener('click', () => this.resetCreateSpeechModal());
        this.speechDownloadBtn.addEventListener('click', () => this.downloadGeneratedAudio());
        this.createSpeechForm.addEventListener('submit', (e) => this.handleCreateSpeechSubmit(e));
        
        // Close modals when clicking outside
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
        
        this.enqueueModal.addEventListener('click', (e) => {
            if (e.target === this.enqueueModal) {
                this.closeEnqueueModal();
            }
        });
        
        this.createSpeechModal.addEventListener('click', (e) => {
            if (e.target === this.createSpeechModal) {
                this.closeCreateSpeechModal();
            }
        });
        
        // ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.modal.open) {
                    this.closeModal();
                } else if (this.enqueueModal.open) {
                    this.closeEnqueueModal();
                } else if (this.createSpeechModal.open) {
                    this.closeCreateSpeechModal();
                }
            }
        });
    }
    
    async initialize() {
        try {
            // Load task states first to create tabs
            await this.loadTaskStates();
            this.createTabs();
            
            // Load voices for enqueue modal
            await this.loadVoices();
            
            // Load initial tasks and counts
            await Promise.all([
                this.loadTasks(),
                this.loadTaskCounts()
            ]);
            
        } catch (error) {
            this.showError('Failed to initialize dashboard: ' + error.message);
        }
    }
    
    async loadTaskStates() {
        try {
            const response = await fetch('/api/task-states');
            if (!response.ok) throw new Error('Failed to load task states');
            
            const data = await response.json();
            this.taskStates = data.states;
        } catch (error) {
            console.error('Error loading task states:', error);
            throw error;
        }
    }
    
    async loadVoices() {
        try {
            const response = await fetch('/api/voices');
            if (!response.ok) throw new Error('Failed to load voices');
            
            this.voices = await response.json();
        } catch (error) {
            console.error('Error loading voices:', error);
            throw error;
        }
    }
    
    createTabs() {
        // Clear existing tabs except the "All" tab
        const existingTabs = this.tabsContainer.querySelectorAll('.tab-button:not(#tab-all)');
        existingTabs.forEach(tab => tab.remove());
        
        // Create tabs for each state
        this.taskStates.forEach(state => {
            const tab = document.createElement('button');
            tab.className = 'tab-button';
            tab.id = `tab-${state.name}`;
            tab.setAttribute('role', 'tab');
            tab.setAttribute('data-state', state.name);
            tab.innerHTML = `
                ${this.formatStateName(state.name)} 
                <span class="badge" id="count-${state.name}">0</span>
            `;
            
            tab.addEventListener('click', () => this.switchTab(state.name, tab));
            this.tabsContainer.appendChild(tab);
        });
        
        // Add click handler for "All" tab
        const allTab = document.getElementById('tab-all');
        allTab.addEventListener('click', () => this.switchTab('', allTab));
    }
    
    formatStateName(stateName) {
        return stateName.charAt(0).toUpperCase() + stateName.slice(1).toLowerCase();
    }
    
    switchTab(state, tabElement) {
        // Update active tab
        document.querySelectorAll('.tab-button').forEach(tab => {
            tab.classList.remove('active');
            tab.setAttribute('aria-selected', 'false');
        });
        
        tabElement.classList.add('active');
        tabElement.setAttribute('aria-selected', 'true');
        
        // Update current state and reset pagination
        this.currentState = state;
        this.currentCursor = null;
        
        // Load tasks for the new state
        this.loadTasks();
    }
    
    async loadTasks() {
        try {
            this.showLoading();
            this.hideError();
            
            const params = new URLSearchParams({
                limit: this.pageSize.toString()
            });
            
            if (this.currentState) {
                params.append('state', this.currentState);
            }
            
            if (this.currentCursor) {
                params.append('cursor', this.currentCursor.toString());
            }
            
            const response = await fetch(`/api/tasks?${params}`);
            if (!response.ok) throw new Error('Failed to load tasks');
            
            const data = await response.json();
            this.renderTasks(data.tasks);
            this.updatePaginationControls(data.has_more, data.next_cursor);
            
        } catch (error) {
            console.error('Error loading tasks:', error);
            this.showError('Failed to load tasks: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async loadTaskCounts() {
        try {
            // Load counts for all states
            const promises = ['', ...this.taskStates.map(s => s.name)].map(async (state) => {
                const params = new URLSearchParams({ limit: '1' });
                if (state) params.append('state', state);
                
                const response = await fetch(`/api/tasks?${params}`);
                if (!response.ok) return { state, count: 0 };
                
                const data = await response.json();
                // This is a rough count - for exact counts we'd need a separate endpoint
                return { state: state || 'all', count: data.tasks.length > 0 ? '?' : 0 };
            });
            
            const results = await Promise.all(promises);
            
            results.forEach(({ state, count }) => {
                const countEl = document.getElementById(`count-${state}`);
                if (countEl) {
                    countEl.textContent = count;
                }
            });
            
        } catch (error) {
            console.error('Error loading task counts:', error);
        }
    }
    
    renderTasks(tasks) {
        this.tasksTableBody.innerHTML = '';
        
        if (tasks.length === 0) {
            this.tasksTable.style.display = 'none';
            this.emptyStateEl.style.display = 'block';
            return;
        }
        
        this.tasksTable.style.display = 'table';
        this.emptyStateEl.style.display = 'none';
        
        tasks.forEach(task => {
            const row = this.createTaskRow(task);
            this.tasksTableBody.appendChild(row);
        });
    }
    
    createTaskRow(task) {
        const row = document.createElement('tr');
        
        // Format dates
        const createdDate = new Date(task.created_at).toLocaleString();
        const updatedDate = new Date(task.updated_at).toLocaleString();
        
        // Get state info
        const stateInfo = this.taskStates.find(s => s.value === task.state);
        const stateName = stateInfo ? stateInfo.name : 'unknown';
        
        row.innerHTML = `
            <td>
                <span class="task-id" title="${task.id}">${task.id.slice(0, 8)}...</span>
            </td>
            <td>
                <span class="task-state ${stateName}">${this.formatStateName(stateName)}</span>
            </td>
            <td class="task-timestamp">${createdDate}</td>
            <td class="task-timestamp">${updatedDate}</td>
            <td>${task.item_count}</td>
            <td>${task.attempt_count}</td>
            <td>
                <button class="action-button secondary" onclick="dashboard.viewTask('${task.id}')">
                    👁️ View
                </button>
            </td>
        `;
        
        return row;
    }
    
    updatePaginationControls(hasMore, nextCursor) {
        // For now, simple pagination - could be enhanced with page numbers
        this.nextBtn.disabled = !hasMore;
        this.prevBtn.disabled = this.currentCursor === null;
        
        // Update pagination info
        const pageInfo = this.currentCursor ? 'Next Page' : 'Page 1';
        this.paginationInfo.textContent = pageInfo;
        
        // Store next cursor for navigation
        this.nextCursor = nextCursor;
    }
    
    goToNextPage() {
        if (this.nextCursor) {
            this.currentCursor = this.nextCursor;
            this.loadTasks();
        }
    }
    
    goToPreviousPage() {
        // Simple implementation - go back to first page
        // Could be enhanced to maintain page history
        this.currentCursor = null;
        this.loadTasks();
    }
    
    async viewTask(taskId) {
        try {
            this.showLoading();
            
            const response = await fetch(`/api/tasks/${taskId}`);
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Task not found');
                }
                throw new Error('Failed to load task details');
            }
            
            const task = await response.json();
            this.showTaskModal(task);
            
        } catch (error) {
            console.error('Error loading task details:', error);
            this.showError('Failed to load task details: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    showTaskModal(task) {
        const stateInfo = this.taskStates.find(s => s.value === task.state);
        const stateName = stateInfo ? stateInfo.name : 'unknown';
        
        // Format dates
        const createdDate = new Date(task.created_at).toLocaleString();
        const updatedDate = new Date(task.updated_at).toLocaleString();
        const attemptedDate = task.attempted_at ? new Date(task.attempted_at).toLocaleString() : 'Never';
        const finalizedDate = task.finalized_at ? new Date(task.finalized_at).toLocaleString() : 'Not finalized';
        
        let modalHTML = `
            <div class="task-detail">
                <h4>Task Information</h4>
                <div class="task-detail-grid">
                    <div class="task-detail-item">
                        <strong>ID</strong>
                        <code>${task.id}</code>
                    </div>
                    <div class="task-detail-item">
                        <strong>State</strong>
                        <span class="task-state ${stateName}">${this.formatStateName(stateName)}</span>
                    </div>
                    <div class="task-detail-item">
                        <strong>Created</strong>
                        ${createdDate}
                    </div>
                    <div class="task-detail-item">
                        <strong>Updated</strong>
                        ${updatedDate}
                    </div>
                    <div class="task-detail-item">
                        <strong>Attempts</strong>
                        ${task.attempt_count}
                    </div>
                    <div class="task-detail-item">
                        <strong>Last Attempt</strong>
                        ${attemptedDate}
                    </div>
                </div>
        `;
        
        // Show errors if any
        if (task.attempted_error && task.attempted_error.length > 0) {
            const errors = JSON.parse(task.attempted_error);
            modalHTML += `
                <div class="error-list">
                    <strong>Errors:</strong>
                    <ul>
                        ${errors.map(error => `<li>${this.escapeHtml(error)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        modalHTML += `</div>`;
        
        // Show task items
        if (task.items && task.items.length > 0) {
            modalHTML += `
                <div class="task-detail">
                    <h4>Task Items (${task.items.length})</h4>
                    <div class="task-items">
            `;
            
            task.items.forEach((item, index) => {
                modalHTML += `
                    <div class="task-item">
                        <h5>Item ${index + 1}</h5>
                        <div class="task-item-text">${this.escapeHtml(JSON.stringify(item.request, null, 2))}</div>
                `;
                
                if (item.response_url && item.response_url.trim()) {
                    const audioId = `audio-${task.id}-${index}`;
                    const downloadId = `download-${task.id}-${index}`;
                    modalHTML += `
                        <div class="audio-player">
                            <strong>Audio:</strong>
                            <div class="audio-container">
                                <audio id="${audioId}" controls preload="none" style="width: 100%;">
                                    <source src="${this.escapeHtml(item.response_url)}" type="audio/wav">
                                    <source src="${this.escapeHtml(item.response_url)}" type="audio/mpeg">
                                    Your browser does not support the audio element.
                                </audio>
                                <button id="${downloadId}" type="button" class="secondary outline" style="margin-top: 0.5rem; font-size: 0.875rem;" onclick="dashboard.downloadTaskAudio('${this.escapeHtml(item.response_url)}', '${task.id}_${index}')">
                                    📥 Download MP3
                                </button>
                            </div>
                        </div>
                    `;
                } else {
                    modalHTML += '<div class="no-audio">No audio available</div>';
                }
                
                modalHTML += '</div>';
            });
            
            modalHTML += '</div></div>';
        } else {
            modalHTML += `
                <div class="task-detail">
                    <h4>Task Items</h4>
                    <p class="no-audio">No items found for this task.</p>
                </div>
            `;
        }
        
        this.modalContent.innerHTML = modalHTML;
        this.modal.showModal();
    }
    
    closeModal() {
        this.modal.close();
    }
    
    showEnqueueModal() {
        // Reset form
        this.enqueueItemCounter = 0;
        this.itemsContainer.innerHTML = '';
        
        // Add initial item
        this.addEnqueueItem();
        
        // Show modal
        this.enqueueModal.showModal();
    }
    
    closeEnqueueModal() {
        this.enqueueModal.close();
    }
    
    addEnqueueItem() {
        this.enqueueItemCounter++;
        const itemId = `item-${this.enqueueItemCounter}`;
        
        const itemDiv = document.createElement('div');
        itemDiv.className = 'enqueue-item';
        itemDiv.setAttribute('data-item-id', itemId);
        
        // Create voice options
        const voiceOptions = this.voices.map(voice => 
            `<option value="${voice.id}">${voice.name} (${voice.language}, ${voice.gender})</option>`
        ).join('');
        
        itemDiv.innerHTML = `
            <div class="enqueue-item-header">
                <h5>Item ${this.enqueueItemCounter}</h5>
                ${this.enqueueItemCounter > 1 ? `<button type="button" class="remove-item-btn" onclick="dashboard.removeEnqueueItem('${itemId}')">🗑️ Remove</button>` : ''}
            </div>
            
            <div class="form-group">
                <label for="${itemId}-text">Text to synthesize *</label>
                <textarea id="${itemId}-text" name="text" placeholder="Enter the text you want to convert to speech..." required></textarea>
            </div>
            
            <div class="form-group">
                <label for="${itemId}-voice">Voice *</label>
                <select id="${itemId}-voice" name="voice_id" class="voice-select" required>
                    <option value="">Select a voice...</option>
                    ${voiceOptions}
                </select>
            </div>
            
            <div class="form-group">
                <label for="${itemId}-metadata">Metadata (JSON, optional)</label>
                <textarea id="${itemId}-metadata" name="metadata" class="metadata-input" placeholder='{"session_id": "example", "user_id": "123"}'></textarea>
            </div>
        `;
        
        this.itemsContainer.appendChild(itemDiv);
    }
    
    removeEnqueueItem(itemId) {
        const itemDiv = document.querySelector(`[data-item-id="${itemId}"]`);
        if (itemDiv) {
            itemDiv.remove();
            this.updateItemNumbers();
        }
    }
    
    updateItemNumbers() {
        const items = this.itemsContainer.querySelectorAll('.enqueue-item');
        items.forEach((item, index) => {
            const header = item.querySelector('h5');
            if (header) {
                header.textContent = `Item ${index + 1}`;
            }
        });
    }
    
    async handleEnqueueSubmit(e) {
        e.preventDefault();
        
        try {
            // Disable submit button and show loading
            this.enqueueSubmitBtn.disabled = true;
            this.enqueueSubmitBtn.innerHTML = '<div class="spinner"></div> Enqueueing...';
            
            // Collect form data
            const items = [];
            const itemDivs = this.itemsContainer.querySelectorAll('.enqueue-item');
            
            // Validate and collect items
            let hasErrors = false;
            for (const itemDiv of itemDivs) {
                const textArea = itemDiv.querySelector('textarea[name="text"]');
                const voiceSelect = itemDiv.querySelector('select[name="voice_id"]');
                const metadataArea = itemDiv.querySelector('textarea[name="metadata"]');
                
                // Clear previous errors
                this.clearFieldError(textArea);
                this.clearFieldError(voiceSelect);
                this.clearFieldError(metadataArea);
                
                // Validate required fields
                if (!textArea.value.trim()) {
                    this.showFieldError(textArea, 'Text is required');
                    hasErrors = true;
                    continue;
                }
                
                if (!voiceSelect.value) {
                    this.showFieldError(voiceSelect, 'Voice selection is required');
                    hasErrors = true;
                    continue;
                }
                
                // Parse metadata
                let metadata = {};
                if (metadataArea.value.trim()) {
                    try {
                        metadata = JSON.parse(metadataArea.value);
                    } catch (error) {
                        this.showFieldError(metadataArea, 'Invalid JSON format');
                        hasErrors = true;
                        continue;
                    }
                }
                
                items.push({
                    text: textArea.value.trim(),
                    voice_id: voiceSelect.value,
                    metadata: metadata
                });
            }
            
            if (hasErrors) {
                throw new Error('Please fix the validation errors above');
            }
            
            if (items.length === 0) {
                throw new Error('At least one item is required');
            }
            
            // Submit to API
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ items })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to enqueue task');
            }
            
            const result = await response.json();
            
            // Show success message
            const message = `Successfully created task with ${items.length} items`;
            this.showError(`✅ ${message}. Task ID: ${result.task_ids[0]}`);
            this.errorEl.style.backgroundColor = '#e8f5e8';
            this.errorEl.style.borderColor = '#388e3c';
            this.errorEl.style.color = '#388e3c';
            
            // Close modal and refresh tasks
            this.closeEnqueueModal();
            this.currentCursor = null;
            await this.loadTasks();
            await this.loadTaskCounts();
            
        } catch (error) {
            console.error('Error enqueueing task:', error);
            this.showError('Failed to enqueue task: ' + error.message);
        } finally {
            // Re-enable submit button
            this.enqueueSubmitBtn.disabled = false;
            this.enqueueSubmitBtn.innerHTML = '📤 Enqueue Task';
        }
    }
    
    showFieldError(field, message) {
        const formGroup = field.closest('.form-group');
        formGroup.classList.add('error');
        
        // Remove existing error message
        const existingError = formGroup.querySelector('.error-text');
        if (existingError) {
            existingError.remove();
        }
        
        // Add error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-text';
        errorDiv.textContent = message;
        formGroup.appendChild(errorDiv);
    }
    
    clearFieldError(field) {
        const formGroup = field.closest('.form-group');
        formGroup.classList.remove('error');
        
        const errorText = formGroup.querySelector('.error-text');
        if (errorText) {
            errorText.remove();
        }
    }
    
    showLoading() {
        this.loadingEl.style.display = 'block';
        this.tasksContainer.style.display = 'none';
    }
    
    hideLoading() {
        this.loadingEl.style.display = 'none';
        this.tasksContainer.style.display = 'block';
    }
    
    showError(message) {
        this.errorMessageEl.textContent = message;
        this.errorEl.style.display = 'block';
    }
    
    hideError() {
        this.errorEl.style.display = 'none';
    }
    
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    // Create Speech Modal Methods
    showCreateSpeechModal() {
        this.resetCreateSpeechModal();
        this.populateVoicesInSpeechModal();
        this.createSpeechModal.showModal();
    }
    
    closeCreateSpeechModal() {
        // Stop audio if playing
        if (this.speechAudio && !this.speechAudio.paused) {
            this.speechAudio.pause();
            this.speechAudio.currentTime = 0;
        }
        
        this.createSpeechModal.close();
    }
    
    resetCreateSpeechModal() {
        // Reset form
        this.createSpeechForm.reset();
        
        // Stop and clear audio
        if (this.speechAudio && !this.speechAudio.paused) {
            this.speechAudio.pause();
            this.speechAudio.currentTime = 0;
        }
        this.speechAudio.src = '';
        
        // Revoke previous audio URL to prevent memory leaks
        if (this.currentAudioUrl) {
            URL.revokeObjectURL(this.currentAudioUrl);
            this.currentAudioUrl = null;
        }
        
        // Hide all states
        this.speechLoadingEl.style.display = 'none';
        this.speechResultEl.style.display = 'none';
        this.speechErrorEl.style.display = 'none';
        
        // Reset buttons
        this.speechSubmitBtn.style.display = '';
        this.speechResetBtn.style.display = 'none';
        this.speechSubmitBtn.disabled = false;
        
        // Clear request details
        this.speechRequestDetails.textContent = '';
    }
    
    populateVoicesInSpeechModal() {
        // Clear existing options except the first one
        const defaultOption = this.speechVoiceSelect.querySelector('option[value=""]');
        this.speechVoiceSelect.innerHTML = '';
        this.speechVoiceSelect.appendChild(defaultOption);
        
        // Add voice options
        this.voices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = `${voice.name} (${voice.gender}, ${voice.language})`;
            this.speechVoiceSelect.appendChild(option);
        });
    }
    
    async handleCreateSpeechSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(this.createSpeechForm);
        const text = formData.get('text');
        const voice_id = formData.get('voice_id');
        
        if (!text || !voice_id) {
            this.showSpeechError('Please fill in all required fields.');
            return;
        }
        
        // Hide error and show loading
        this.speechErrorEl.style.display = 'none';
        this.speechResultEl.style.display = 'none';
        this.speechLoadingEl.style.display = 'block';
        this.speechSubmitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: text,
                    voice_id: voice_id,
                    metadata: {}
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Server error: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Hide loading and show result
            this.speechLoadingEl.style.display = 'none';
            this.showSpeechResult(result);
            
        } catch (error) {
            console.error('Error creating speech:', error);
            this.speechLoadingEl.style.display = 'none';
            this.showSpeechError(`Failed to generate speech: ${error.message}`);
            this.speechSubmitBtn.disabled = false;
        }
    }
    
    showSpeechResult(result) {
        // Revoke previous audio URL if exists
        if (this.currentAudioUrl) {
            URL.revokeObjectURL(this.currentAudioUrl);
        }
        
        // Create audio blob from base64
        const audioData = result.audio;
        const audioBlob = this.base64ToBlob(audioData, 'audio/wav');
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Track the new URL for cleanup
        this.currentAudioUrl = audioUrl;
        
        // Set audio source
        this.speechAudio.src = audioUrl;
        
        // Show request details
        this.speechRequestDetails.textContent = JSON.stringify(result.request, null, 2);
        
        // Show result container
        this.speechResultEl.style.display = 'block';
        
        // Update buttons
        this.speechSubmitBtn.style.display = 'none';
        this.speechResetBtn.style.display = '';
    }
    
    showSpeechError(message) {
        this.speechErrorMessage.textContent = message;
        this.speechErrorEl.style.display = 'block';
    }
    
    downloadGeneratedAudio() {
        if (this.currentAudioUrl) {
            // Generate filename with current date in YYYYMMDD format
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            const filename = `sayathing_${year}${month}${day}.wav`;
            
            const link = document.createElement('a');
            link.href = this.currentAudioUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    downloadTaskAudio(audioUrl, filename) {
        const link = document.createElement('a');
        link.href = audioUrl;
        link.download = `${filename}.mp3`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    base64ToBlob(base64, mimeType) {
        const bytes = atob(base64);
        const array = new Uint8Array(bytes.length);
        for (let i = 0; i < bytes.length; i++) {
            array[i] = bytes.charCodeAt(i);
        }
        return new Blob([array], { type: mimeType });
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new TaskDashboard();
});
