// Main JavaScript for PDF Question Answering Web UI

// Store the PDF text globally to use when asking questions
let pdfText = '';

// Store chat history
let chatHistory = [];

// DOM elements
const uploadBtn = document.getElementById('uploadBtn');
const askBtn = document.getElementById('askBtn');
const quitBtn = document.getElementById('quitBtn');
const newQuestionBtn = document.getElementById('newQuestionBtn');
const newPdfBtn = document.getElementById('newPdfBtn');
const pdfFileInput = document.getElementById('pdfFile');
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
    // Upload PDF button
    uploadBtn.addEventListener('click', uploadPdf);
    
    // Ask question button
    askBtn.addEventListener('click', askQuestion);
    
    // Quit button
    quitBtn.addEventListener('click', function() {
        // Reset all sections to initial state
        resetUI();
    });
    
    // PDF file input change
    pdfFileInput.addEventListener('change', function() {
        if (pdfFileInput.files.length > 0) {
            uploadStatus.textContent = `File selected: ${pdfFileInput.files[0].name}`;
            uploadStatus.className = 'mt-3 text-info';
        } else {
            uploadStatus.textContent = '';
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
function addMessageToChat(text, sender, timestamp = new Date()) {
    // Create message container
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;
    
    // Add message text
    messageDiv.textContent = text;
    
    // Add timestamp
    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    timeSpan.textContent = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    messageDiv.appendChild(timeSpan);
    
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
        
        // Re-enable upload button
        uploadBtn.disabled = false;
    });
}

// Function to ask a question
function askQuestion() {
    // Check if question is empty
    const question = questionInput.value.trim();
    if (!question) {
        showError('Please enter a question.');
        return;
    }
    
    // Check if we have PDF text
    if (!pdfText) {
        showError('No PDF content available. Please upload a PDF first.');
        return;
    }
    
    // Disable ask button and show loading
    askBtn.disabled = true;
    
    // Add user question to chat
    addMessageToChat(question, 'user');
    
    // Clear question input
    questionInput.value = '';
    
    // Show loading indicator in chat
    loadingAnswer.classList.remove('d-none');
    
    // Hide any previous errors
    hideError();
    
    // Send request to server
    fetch('/ask', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question: question,
            pdfText: pdfText
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Error getting answer');
            });
        }
        return response.json();
    })
    .then(data => {
        // Hide loading
        loadingAnswer.classList.add('d-none');
        
        // Add AI response to chat
        addMessageToChat(data.answer, 'ai');
        
        // Re-enable ask button
        askBtn.disabled = false;
        
        // Focus on question input
        questionInput.focus();
    })
    .catch(error => {
        console.error('Error:', error);
        showError(error.message);
        
        // Hide loading and re-enable ask button
        loadingAnswer.classList.add('d-none');
        askBtn.disabled = false;
        
        // Add error message to chat
        const systemErrorDiv = document.createElement('div');
        systemErrorDiv.className = 'system-message text-center p-2 mb-3';
        systemErrorDiv.innerHTML = `
            <span class="badge bg-danger">Error</span>
            <p class="small mt-1">${error.message}</p>
        `;
        chatMessages.appendChild(systemErrorDiv);
    });
}

// Function to show error message
function showError(message) {
    errorMessage.textContent = message;
    errorAlert.classList.remove('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideError();
    }, 5000);
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
