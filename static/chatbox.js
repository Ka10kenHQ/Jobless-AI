let ws = null;
let currentChatId = null;
let chatHistory = [];
let currentMessages = [];
const userId = 'user_' + Math.random().toString(36).substr(2, 9);

// Settings
let settings = {
    autoScroll: true,
    soundEnabled: true,
    defaultLocation: '',
    maxResults: 10
};

// Initialize app
function initializeApp() {
    console.log('Initializing Job Search AI');
    
    // Load settings from localStorage
    loadSettings();
    
    // Set user ID display
    document.getElementById('userIdDisplay').textContent = userId.substring(0, 12) + '...';
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Load chat history
    loadChatHistory();
    
    // Focus on input
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.focus();
    }
    
    // Start new chat
    startNewChat();
}

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    ws = new WebSocket(`${protocol}//${host}/ws/${userId}`);
    
    ws.onopen = function(event) {
        console.log('Connected to job search server');
        updateConnectionStatus('Connected', 'success');
    };
    
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'job_search_response') {
                handleJobSearchResponse(data.data);
            } else if (data.type === 'chat_history') {
                handleChatHistoryResponse(data.data);
            } else if (data.type === 'error') {
                displayError(data.message);
            } else {
                console.log('Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('Error parsing message:', error);
            displayError('Failed to parse server response');
        }
    };
    
    ws.onclose = function(event) {
        console.log('Disconnected from server');
        updateConnectionStatus('Disconnected', 'error');
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        updateConnectionStatus('Connection Error', 'error');
    };
}

// Connection status
function updateConnectionStatus(message, type) {
    const statusEl = document.getElementById('connectionStatus');
    const iconClass = type === 'success' ? 'fa-circle' : 
                     type === 'error' ? 'fa-times-circle' : 'fa-exclamation-circle';
    const colorClass = type === 'success' ? 'var(--success-color)' : 
                      type === 'error' ? 'var(--error-color)' : 'var(--warning-color)';
    
    statusEl.innerHTML = `<i class="fas ${iconClass}"></i> ${message}`;
    statusEl.style.color = colorClass;
}

// Chat management
function startNewChat() {
    currentChatId = 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    currentMessages = [];
    
    // Clear messages container
    const container = document.getElementById('messagesContainer');
    container.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">
                <i class="fas fa-briefcase"></i>
            </div>
            <h3>Welcome to Job Search AI</h3>
            <p>I'm here to help you find your dream job. Tell me what you're looking for!</p>
            <div class="suggestion-chips">
                <button class="chip" onclick="sendSuggestion('Remote Python developer')">
                    Remote Python developer
                </button>
                <button class="chip" onclick="sendSuggestion('Frontend engineer in NYC')">
                    Frontend engineer in NYC
                </button>
                <button class="chip" onclick="sendSuggestion('Data scientist with ML experience')">
                    Data scientist with ML
                </button>
                <button class="chip" onclick="sendSuggestion('Senior full-stack developer')">
                    Senior full-stack developer
                </button>
            </div>
        </div>
    `;
    
    // Update active chat in history
    updateChatHistoryDisplay();
    
    // Focus on input
    document.getElementById('messageInput').focus();
}

function sendSuggestion(text) {
    document.getElementById('messageInput').value = text;
    sendMessage();
}

// Message handling
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (message === '') return;
    
    // Hide welcome message if present
    const welcomeMsg = document.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    // Display user message
    displayMessage(message, 'user');
    
    // Add to current messages
    const userMessage = {
        id: 'msg_' + Date.now(),
        content: message,
        sender: 'user',
        timestamp: new Date().toISOString()
    };
    currentMessages.push(userMessage);
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to server
    if (ws && ws.readyState === WebSocket.OPEN) {
        try {
            ws.send(JSON.stringify({
                message: message,
                timestamp: new Date().toISOString(),
                user_id: userId,
                chat_id: currentChatId,
                message_id: userMessage.id
            }));
        } catch (error) {
            console.error('Error sending message:', error);
            hideTypingIndicator();
            displayError('Failed to send message');
        }
    } else {
        hideTypingIndicator();
        displayError('Not connected to server. Attempting to reconnect...');
        connectWebSocket();
    }
    
    // Clear input
    input.value = '';
    autoResize(input);
}

function handleJobSearchResponse(data) {
    hideTypingIndicator();
    
    // Create bot message
    const botMessage = {
        id: 'msg_' + Date.now(),
        content: data.response || 'Here are your job search results:',
        sender: 'bot',
        timestamp: new Date().toISOString(),
        jobs: data.matched_jobs || data.jobs || [],
        totalJobs: data.total_jobs_found
    };
    
    // Display response
    if (data.response) {
        displayMessage(data.response, 'bot');
    }
    
    // Display job matches
    if (botMessage.jobs && botMessage.jobs.length > 0) {
        displayJobMatches(botMessage.jobs);
    }
    
    // Display summary
    if (data.total_jobs_found !== undefined) {
        const summary = `📊 Found ${data.total_jobs_found} total jobs, showing ${botMessage.jobs.length} best matches.`;
        displayMessage(summary, 'bot');
    }
    
    // Add to current messages
    currentMessages.push(botMessage);
    
    // Save to chat history
    saveChatToHistory();
    
    // Play notification sound
    if (settings.soundEnabled) {
        playNotificationSound();
    }
}

// Message display
function displayMessage(content, sender, isHtml = false) {
    const container = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isHtml) {
        contentDiv.innerHTML = content;
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    container.appendChild(messageDiv);
    
    if (settings.autoScroll) {
        scrollToBottom();
    }
}

function displayJobMatches(jobs) {
    let jobsHtml = '<div class="jobs-section"><h4><i class="fas fa-briefcase"></i> Job Matches:</h4>';
    
    const jobsToShow = jobs.slice(0, settings.maxResults);
    
    jobsToShow.forEach((job, index) => {
        const matchScore = job.match_score ? Math.round(job.match_score * 100) : null;
        
        jobsHtml += `
            <div class="job-card">
                <h5>${escapeHtml(job.title)}</h5>
                <p><strong>Company:</strong> ${escapeHtml(job.company)}</p>
                <p><strong>Location:</strong> ${escapeHtml(job.location || 'Not specified')}</p>
                <p><strong>Source:</strong> ${escapeHtml(job.source)}</p>
                ${matchScore ? `<span class="match-score">${matchScore}% match</span>` : ''}
                ${job.url ? `<p><a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">View Details <i class="fas fa-external-link-alt"></i></a></p>` : ''}
                ${job.description ? `<p><strong>Description:</strong> ${truncateText(escapeHtml(job.description), 150)}</p>` : ''}
            </div>
        `;
    });
    
    jobsHtml += '</div>';
    
    if (jobs.length > settings.maxResults) {
        jobsHtml += `<p style="text-align: center; color: var(--text-muted); font-style: italic;">... and ${jobs.length - settings.maxResults} more jobs found</p>`;
    }
    
    displayMessage(jobsHtml, 'bot', true);
}

function showTypingIndicator() {
    const container = document.getElementById('messagesContainer');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message';
    typingDiv.id = 'typingIndicator';
    
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="typing-indicator">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    container.appendChild(typingDiv);
    
    if (settings.autoScroll) {
        scrollToBottom();
    }
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function displayError(message) {
    hideTypingIndicator();
    displayMessage(`❌ ${message}`, 'bot');
}

// Chat history management
function saveChatToHistory() {
    if (currentMessages.length === 0) return;
    
    const chatData = {
        id: currentChatId,
        title: generateChatTitle(),
        messages: currentMessages,
        timestamp: new Date().toISOString(),
        userId: userId
    };
    
    // Save to localStorage
    let savedChats = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    const existingIndex = savedChats.findIndex(chat => chat.id === currentChatId);
    
    if (existingIndex >= 0) {
        savedChats[existingIndex] = chatData;
    } else {
        savedChats.unshift(chatData);
    }
    
    // Keep only last 50 chats
    savedChats = savedChats.slice(0, 50);
    localStorage.setItem('chatHistory', JSON.stringify(savedChats));
    
    // Update display
    updateChatHistoryDisplay();
    
    // Send to server for MongoDB storage
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'save_chat',
            chat_data: chatData
        }));
    }
}

function loadChatHistory() {
    const savedChats = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    chatHistory = savedChats;
    updateChatHistoryDisplay();
    
    // Request from server
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'load_chat_history',
            user_id: userId
        }));
    }
}

function handleChatHistoryResponse(data) {
    if (data && data.chats) {
        chatHistory = data.chats;
        updateChatHistoryDisplay();
    }
}

function updateChatHistoryDisplay() {
    const historyList = document.getElementById('chatHistoryList');
    historyList.innerHTML = '';
    
    chatHistory.forEach(chat => {
        const historyItem = document.createElement('div');
        historyItem.className = `history-item ${chat.id === currentChatId ? 'active' : ''}`;
        historyItem.onclick = () => loadChat(chat.id);
        
        const timeAgo = getTimeAgo(new Date(chat.timestamp));
        const preview = chat.messages.length > 0 ? chat.messages[0].content : 'Empty chat';
        
        historyItem.innerHTML = `
            <div class="history-item-title">${escapeHtml(chat.title)}</div>
            <div class="history-item-preview">${escapeHtml(truncateText(preview, 50))}</div>
            <div class="history-item-time">${timeAgo}</div>
        `;
        
        historyList.appendChild(historyItem);
    });
}

function loadChat(chatId) {
    const chat = chatHistory.find(c => c.id === chatId);
    if (!chat) return;
    
    currentChatId = chatId;
    currentMessages = [...chat.messages];
    
    // Clear and rebuild messages
    const container = document.getElementById('messagesContainer');
    container.innerHTML = '';
    
    chat.messages.forEach(msg => {
        displayMessage(msg.content, msg.sender, msg.sender === 'bot' && msg.jobs);
        
        if (msg.jobs && msg.jobs.length > 0) {
            displayJobMatches(msg.jobs);
        }
    });
    
    updateChatHistoryDisplay();
    scrollToBottom();
}

function generateChatTitle() {
    if (currentMessages.length === 0) return 'New Chat';
    
    const firstMessage = currentMessages.find(m => m.sender === 'user');
    if (!firstMessage) return 'New Chat';
    
    return truncateText(firstMessage.content, 30);
}

function clearChatHistory() {
    if (confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
        chatHistory = [];
        localStorage.removeItem('chatHistory');
        updateChatHistoryDisplay();
        
        // Send clear request to server
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'clear_chat_history',
                user_id: userId
            }));
        }
    }
}

// Sidebar functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

// Settings
function toggleSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.add('show');
    
    // Load current settings
    document.getElementById('autoScroll').checked = settings.autoScroll;
    document.getElementById('soundEnabled').checked = settings.soundEnabled;
    document.getElementById('defaultLocation').value = settings.defaultLocation;
    document.getElementById('maxResults').value = settings.maxResults;
}

function closeSettings() {
    const modal = document.getElementById('settingsModal');
    modal.classList.remove('show');
    
    // Save settings
    settings.autoScroll = document.getElementById('autoScroll').checked;
    settings.soundEnabled = document.getElementById('soundEnabled').checked;
    settings.defaultLocation = document.getElementById('defaultLocation').value;
    settings.maxResults = parseInt(document.getElementById('maxResults').value);
    
    saveSettings();
}

function loadSettings() {
    const saved = localStorage.getItem('chatSettings');
    if (saved) {
        settings = { ...settings, ...JSON.parse(saved) };
    }
}

function saveSettings() {
    localStorage.setItem('chatSettings', JSON.stringify(settings));
}

// Utility functions
function handleKeyDown(event) {
    if (event.key === 'Enter') {
        if (event.shiftKey) {
            // Allow new line with Shift+Enter
            return;
        }
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

function playNotificationSound() {
    try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmAaAy+I1PLOdCEHKHTI9eOVQQkEXLPr9qxdGAtOpdftvHkUCTOI1++6dSgMZq/VtqBKEAg/iMv0sWYaBDeI1OWnciwKWKji8bJoAx+F0vHTdSQIUaze8LdXKQ1kq+X0t2QdBjiN1vbTekMKJHfJ9t2SQgoUY7Xp7ahYEQpJot+3bxIKNInR8LllKglZp+P3s2MdBzWI1OylpSgKXKfg8rVnMQ1sqN/ztmMd...');
        audio.volume = 0.1;
        audio.play().catch(() => {}); // Ignore errors
    } catch (e) {
        // Ignore audio errors
    }
}

function exportChat() {
    if (currentMessages.length === 0) {
        alert('No messages to export.');
        return;
    }
    
    const chatData = {
        title: generateChatTitle(),
        timestamp: new Date().toISOString(),
        messages: currentMessages
    };
    
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${currentChatId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
    } else {
        document.exitFullscreen().catch(() => {});
    }
}

// Event listeners
window.addEventListener('load', initializeApp);

window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
});

// Click outside modal to close
window.addEventListener('click', (event) => {
    const modal = document.getElementById('settingsModal');
    if (event.target === modal) {
        closeSettings();
    }
});

// Handle connection state changes
window.addEventListener('online', () => {
    updateConnectionStatus('Connected', 'success');
    connectWebSocket();
});

window.addEventListener('offline', () => {
    updateConnectionStatus('Offline', 'error');
}); 
