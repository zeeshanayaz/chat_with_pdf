// Main JavaScript for PDF Question Answering Web UI

// Store the PDF text globally to use when asking questions
let pdfText = '';

// Store chat history
let chatHistory = [];

// Add to the top with other global variables
let selectedPdfs = new Set();

// DOM elements
const uploadBtn = document.getElementById('uploadBtn');
const askBtn = document.getElementById('askBtn');
const quitBtn = document.getElementById('quitBtn');
const newQuestionBtn = document.getElementById('newQuestionBtn');
const newPdfBtn = document.getElementById('newPdfBtn');
const pdfFileInput = document.getElementById('pdfFile');
const clearFileBtn = document.getElementById('clearFileBtn');
const questionInput = document.getElementById('questionInput');
const uploadStatus = document.getElementById('uploadStatus');
const uploadProgress = document.getElementById('uploadProgress');
const progressBar = document.querySelector('.progress-bar');
const uploadSection = document.getElementById('upload-section');
const chatSection = document.getElementById('chat-section');
const chatMessages = document.getElementById('chatMessages');
const loadingAnswer = document.getElementById('loadingAnswer');
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Load PDFs when page loads
    loadPdfList();
    
    // Upload PDF button
    uploadBtn.addEventListener('click', uploadPdf);
    
    // Ask question button
    askBtn.addEventListener('click', askQuestion);
    
    // Quit button
    quitBtn.addEventListener('click', function() {
        // Reset all sections to initial state
        resetUI();
    });
    
    // Clear file button
    clearFileBtn.addEventListener('click', function() {
        pdfFileInput.value = '';
        clearFileBtn.style.display = 'none';
        uploadStatus.textContent = '';
        hideError();
    });
    
    // PDF file input change
    pdfFileInput.addEventListener('change', function() {
        if (pdfFileInput.files.length > 0) {
            uploadStatus.textContent = `File selected: ${pdfFileInput.files[0].name}`;
            uploadStatus.className = 'mt-3 text-info';
            clearFileBtn.style.display = 'block';
        } else {
            uploadStatus.textContent = '';
            clearFileBtn.style.display = 'none';
        }
    });
    
    // Question input for Enter key
    questionInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            askQuestion();
        }
    });
    
    // Auto-scroll to bottom of chat when new content is added
    chatMessages.addEventListener('DOMNodeInserted', function(event) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
});

// Function to add a message to the chat
function addMessageToChat(sender, text, timestamp = new Date()) {
    // Create message container
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;
    
    // Create message content container
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Add sender label
    const senderLabel = document.createElement('div');
    senderLabel.className = 'sender-label';
    senderLabel.textContent = sender === 'user' ? 'You' : 'Assistant';
    contentDiv.appendChild(senderLabel);
    
    // Add message text
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = text;
    contentDiv.appendChild(textDiv);
    
    // Add timestamp
    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    timeSpan.textContent = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    contentDiv.appendChild(timeSpan);
    
    // Add content to message container
    messageDiv.appendChild(contentDiv);
    
    // Add to chat container
    chatMessages.appendChild(messageDiv);
    
    // Auto scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Save to history
    chatHistory.push({
        text: text,
        sender: sender,
        timestamp: timestamp
    });
    
    return messageDiv;
}

// Function to upload PDF
function uploadPdf() {
    // Check if a file is selected
    if (pdfFileInput.files.length === 0) {
        showError('Please select a PDF file first.');
        return;
    }
    
    const file = pdfFileInput.files[0];
    
    // Check if file is a PDF
    if (file.type !== 'application/pdf') {
        showError('Please upload a PDF file.');
        return;
    }
    
    // Create form data
    const formData = new FormData();
    formData.append('pdfFile', file);
    
    // Show progress bar and reset it
    uploadProgress.classList.remove('d-none');
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', 0);
    
    // Update status
    uploadStatus.textContent = 'Uploading and processing PDF...';
    uploadStatus.className = 'mt-3 text-info';
    
    // Disable upload button
    uploadBtn.disabled = true;
    
    // Simulate progress (since we can't get actual progress easily)
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 5;
        if (progress > 90) clearInterval(progressInterval);
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }, 200);
    
    // Send request to server
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        clearInterval(progressInterval);
        
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Error uploading PDF');
            });
        }
        return response.json();
    })
    .then(data => {
        // Complete progress bar
        progressBar.style.width = '100%';
        progressBar.setAttribute('aria-valuenow', 100);
        
        // Save PDF text for later questions
        pdfText = data.text;
        
        // Update UI
        uploadStatus.textContent = 'PDF processed successfully!';
        uploadStatus.className = 'mt-3 text-success';
        
        // After a short delay, move to chat section
        setTimeout(() => {
            uploadSection.classList.add('d-none');
            chatSection.classList.remove('d-none');
            
            // Clear any existing chat history
            chatHistory = [];
            chatMessages.innerHTML = '';
            
            // Add welcome message
            const systemMessageDiv = document.createElement('div');
            systemMessageDiv.className = 'system-message text-center p-2 mb-3';
            systemMessageDiv.innerHTML = `
                <span class="badge bg-info">PDF Loaded Successfully</span>
                <p class="small mt-1">Ask any question about the content of your PDF document.</p>
            `;
            chatMessages.appendChild(systemMessageDiv);
            
            // Focus on question input
            questionInput.focus();
        }, 1000);
    })
    .catch(error => {
        console.error('Error:', error);
        showError(error.message);
        
        // Reset progress bar
        uploadProgress.classList.add('d-none');
        
        // Clear upload status
        uploadStatus.textContent = '';
        
        // Re-enable upload button
        uploadBtn.disabled = false;
    });
}

// Function to ask a question
async function askQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;

    // Add user question to chat
    addMessageToChat('user', question);
    questionInput.value = '';

    // Show loading state
    const loadingMessage = addMessageToChat('assistant', 'Thinking...');
    loadingMessage.classList.add('loading');

    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to get answer');
        }

        // Update loading message with actual answer
        loadingMessage.textContent = data.answer;
        loadingMessage.classList.remove('loading');

    } catch (error) {
        // Update loading message with error
        loadingMessage.textContent = error.message;
        loadingMessage.classList.remove('loading');
        loadingMessage.classList.add('error');
    }
}

// Function to show error message
function showError(message) {
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        hideError();
    }, 10000);
}

// Function to hide error message
function hideError() {
    errorAlert.classList.add('d-none');
}

// Function to reset the UI to initial state
function resetUI() {
    // Reset file input
    pdfFileInput.value = '';
    uploadStatus.textContent = '';
    
    // Reset progress bar
    uploadProgress.classList.add('d-none');
    
    // Reset buttons
    uploadBtn.disabled = false;
    askBtn.disabled = false;
    
    // Reset PDF text
    pdfText = '';
    
    // Reset chat history
    chatHistory = [];
    
    // Reset question input
    questionInput.value = '';
    
    // Reset sections visibility
    uploadSection.classList.remove('d-none');
    chatSection.classList.add('d-none');
    loadingAnswer.classList.add('d-none');
    
    // Hide any errors
    hideError();
}

// Function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Function to handle PDF selection
function handlePdfSelection() {
    const checkboxes = document.querySelectorAll('.pdf-checkbox');
    const multiSelectActions = document.getElementById('multiSelectActions');
    const selectAllCheckbox = document.getElementById('selectAllPdfs');
    
    // Update selected PDFs set
    selectedPdfs.clear();
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedPdfs.add(checkbox.value);
        }
    });
    
    // Show/hide multi-select actions
    multiSelectActions.style.display = selectedPdfs.size > 0 ? 'block' : 'none';
    
    // Update select all checkbox
    selectAllCheckbox.checked = checkboxes.length > 0 && 
        Array.from(checkboxes).every(checkbox => checkbox.checked);
}

// Function to handle select all checkbox
function handleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllPdfs');
    const checkboxes = document.querySelectorAll('.pdf-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
        if (selectAllCheckbox.checked) {
            selectedPdfs.add(checkbox.value);
        } else {
            selectedPdfs.delete(checkbox.value);
        }
    });
    
    document.getElementById('multiSelectActions').style.display = 
        selectAllCheckbox.checked ? 'block' : 'none';
}

// Function to cancel selection
function cancelSelection() {
    const checkboxes = document.querySelectorAll('.pdf-checkbox');
    const selectAllCheckbox = document.getElementById('selectAllPdfs');
    
    checkboxes.forEach(checkbox => checkbox.checked = false);
    selectAllCheckbox.checked = false;
    selectedPdfs.clear();
    document.getElementById('multiSelectActions').style.display = 'none';
}

// Function to chat with selected PDFs
function chatWithSelected() {
    if (selectedPdfs.size === 0) {
        showError('Please select at least one PDF');
        return;
    }
    
    // Hide upload section and show chat section
    document.getElementById('upload-section').classList.add('d-none');
    document.getElementById('chat-section').classList.remove('d-none');
    
    // Clear chat history
    chatHistory = [];
    
    // Clear chat messages and add system message
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = `
        <div class="system-message text-center p-2 mb-3">
            <span class="badge bg-info">PDFs Loaded Successfully</span>
            <p class="small mt-1">Loaded PDFs: ${Array.from(selectedPdfs).join(', ')}</p>
            <p class="small">Ask any question about the content of your selected PDF documents.</p>
        </div>
    `;
    
    // Enable question input and button
    questionInput.disabled = false;
    askBtn.disabled = false;
    questionInput.focus();
}

// Modify the loadPdfList function
async function loadPdfList() {
    try {
        const response = await fetch('/list-pdfs');
        const pdfs = await response.json();
        
        const pdfList = document.getElementById('pdfList');
        const noPdfsMessage = document.getElementById('noPdfsMessage');
        
        if (pdfs.length === 0) {
            pdfList.innerHTML = '';
            noPdfsMessage.classList.remove('d-none');
            return;
        }
        
        noPdfsMessage.classList.add('d-none');
        pdfList.innerHTML = pdfs.map(pdf => `
            <tr>
                <td>
                    <input type="checkbox" class="form-check-input pdf-checkbox" 
                           value="${pdf.file_name}" data-filename="${pdf.file_name}">
                </td>
                <td>${pdf.file_name}</td>
                <td>${pdf.total_chunks} chunks</td>
                <td>${formatDate(pdf.upload_time)}</td>
                <td>
                    <button class="btn btn-sm btn-primary load-pdf" data-filename="${pdf.file_name}">
                        <i class="fas fa-comments"></i> Chat
                    </button>
                    <button class="btn btn-sm btn-danger delete-pdf" data-filename="${pdf.file_name}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </td>
            </tr>
        `).join('');
        
        // Add event listeners to checkboxes
        document.querySelectorAll('.pdf-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', handlePdfSelection);
        });
        
        // Add event listener to select all checkbox
        document.getElementById('selectAllPdfs').addEventListener('change', handleSelectAll);
        
        // Add event listeners to action buttons
        document.getElementById('chatSelectedBtn').addEventListener('click', chatWithSelected);
        document.getElementById('cancelSelectionBtn').addEventListener('click', cancelSelection);
        
        // Add event listeners to existing buttons
        document.querySelectorAll('.load-pdf').forEach(button => {
            button.addEventListener('click', function() {
                const fileName = this.getAttribute('data-filename');
                loadPdfForChat(fileName);
            });
        });
        
        document.querySelectorAll('.delete-pdf').forEach(button => {
            button.addEventListener('click', function() {
                const fileName = this.getAttribute('data-filename');
                deletePdf(fileName);
            });
        });
        
    } catch (error) {
        console.error('Error loading PDF list:', error);
        showError('Failed to load PDF list. Please try again.');
    }
}

// Function to load PDF for chat
async function loadPdfForChat(fileName) {
    try {
        const response = await fetch('/load-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ file_name: fileName })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load PDF');
        }
        
        // Hide upload section and show chat section
        document.getElementById('upload-section').classList.add('d-none');
        document.getElementById('chat-section').classList.remove('d-none');
        
        // Clear chat history
        chatHistory = [];
        
        // Clear chat messages and add system message
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="system-message text-center p-2 mb-3">
                <span class="badge bg-info">PDF Loaded Successfully</span>
                <p class="small mt-1">Loaded PDF: ${fileName}</p>
                <p class="small">Ask any question about the content of your PDF document.</p>
            </div>
        `;
        
        // Enable question input and button
        questionInput.disabled = false;
        askBtn.disabled = false;
        questionInput.focus();
        
    } catch (error) {
        console.error('Error loading PDF:', error);
        showError(error.message || 'Failed to load PDF. Please try again.');
    }
}

// Function to delete PDF
async function deletePdf(fileName) {
    if (!confirm(`Are you sure you want to delete ${fileName}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ file_name: fileName })
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete PDF');
        }
        
        // Reload PDF list
        await loadPdfList();
        
    } catch (error) {
        console.error('Error deleting PDF:', error);
        showError('Failed to delete PDF. Please try again.');
    }
}
