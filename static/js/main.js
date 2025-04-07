// Main JavaScript for PDF Question Answering Web UI

// Store the PDF text globally to use when asking questions
let pdfText = '';

// DOM elements
const uploadBtn = document.getElementById('uploadBtn');
const askBtn = document.getElementById('askBtn');
const newQuestionBtn = document.getElementById('newQuestionBtn');
const newPdfBtn = document.getElementById('newPdfBtn');
const pdfFileInput = document.getElementById('pdfFile');
const questionInput = document.getElementById('questionInput');
const uploadStatus = document.getElementById('uploadStatus');
const uploadProgress = document.getElementById('uploadProgress');
const progressBar = document.querySelector('.progress-bar');
const uploadSection = document.getElementById('upload-section');
const questionSection = document.getElementById('question-section');
const answerSection = document.getElementById('answer-section');
const answerContent = document.getElementById('answerContent');
const loadingAnswer = document.getElementById('loadingAnswer');
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Upload PDF button
    uploadBtn.addEventListener('click', uploadPdf);
    
    // Ask question button
    askBtn.addEventListener('click', askQuestion);
    
    // New question button
    newQuestionBtn.addEventListener('click', function() {
        // Hide answer section and show question section
        answerSection.classList.add('d-none');
        questionInput.value = '';
        questionSection.classList.remove('d-none');
    });
    
    // New PDF button
    newPdfBtn.addEventListener('click', function() {
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
});

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
        
        // After a short delay, move to question section
        setTimeout(() => {
            uploadSection.classList.add('d-none');
            questionSection.classList.remove('d-none');
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
        
        // Display answer
        answerContent.textContent = data.answer;
        
        // Show answer section and hide question section
        questionSection.classList.add('d-none');
        answerSection.classList.remove('d-none');
        
        // Re-enable ask button
        askBtn.disabled = false;
    })
    .catch(error => {
        console.error('Error:', error);
        showError(error.message);
        
        // Hide loading and re-enable ask button
        loadingAnswer.classList.add('d-none');
        askBtn.disabled = false;
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
    
    // Reset question input
    questionInput.value = '';
    
    // Reset sections visibility
    uploadSection.classList.remove('d-none');
    questionSection.classList.add('d-none');
    answerSection.classList.add('d-none');
    loadingAnswer.classList.add('d-none');
    
    // Hide any errors
    hideError();
}
