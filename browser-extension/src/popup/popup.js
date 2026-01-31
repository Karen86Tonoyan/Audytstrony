import OllamaClient from '../lib/ollama.js';
import AppGenerator from '../lib/appGenerator.js';

class PopupApp {
  constructor() {
    this.ollama = new OllamaClient();
    this.appGenerator = new AppGenerator(this.ollama);
    this.init();
  }

  async init() {
    this.bindElements();
    this.bindEvents();
    await this.checkConnection();
    this.loadHistory();
  }

  bindElements() {
    this.chat = document.getElementById('chat');
    this.input = document.getElementById('input');
    this.sendBtn = document.getElementById('send');
    this.status = document.getElementById('status');
    this.sidepanelBtn = document.getElementById('sidepanel-btn');
    this.settingsBtn = document.getElementById('settings-btn');
  }

  bindEvents() {
    this.sendBtn.addEventListener('click', () => this.sendMessage());

    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    document.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', () => this.quickAction(btn.dataset.action));
    });

    this.sidepanelBtn.addEventListener('click', () => {
      chrome.sidePanel.open({ windowId: chrome.windows.WINDOW_ID_CURRENT });
    });

    this.settingsBtn.addEventListener('click', () => {
      chrome.runtime.openOptionsPage();
    });
  }

  async checkConnection() {
    const available = await this.ollama.isAvailable();
    const dot = this.status.querySelector('.status-dot');
    const text = this.status.querySelector('.status-text');

    if (available) {
      dot.classList.add('connected');
      text.textContent = 'Połączono';
    } else {
      dot.classList.add('disconnected');
      text.textContent = 'Offline';
    }
  }

  async sendMessage() {
    const message = this.input.value.trim();
    if (!message) return;

    this.addMessage(message, 'user');
    this.input.value = '';
    this.input.focus();

    const responseDiv = this.addMessage('', 'assistant', true);

    try {
      let fullResponse = '';
      for await (const chunk of this.ollama.chatStream(message)) {
        fullResponse += chunk;
        responseDiv.innerHTML = this.formatMessage(fullResponse);
        this.chat.scrollTop = this.chat.scrollHeight;
      }
    } catch (error) {
      responseDiv.innerHTML = `<span class="error">Błąd: ${error.message}</span>`;
    }

    this.saveHistory();
  }

  addMessage(content, role, isStreaming = false) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = isStreaming ? '<span class="typing">●●●</span>' : this.formatMessage(content);
    this.chat.appendChild(div);
    this.chat.scrollTop = this.chat.scrollHeight;
    return div;
  }

  formatMessage(content) {
    // Markdown-like formatting
    return content
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  }

  async quickAction(action) {
    const prompts = {
      app: 'Chcę stworzyć nową aplikację. Zapytaj mnie o szczegóły: nazwa, technologie (backend/frontend), funkcjonalności.',
      explain: 'Wyjaśnij kod który wkleję w następnej wiadomości.',
      fix: 'Pomóż mi naprawić błąd w kodzie. Wkleję kod i opis błędu.'
    };

    if (prompts[action]) {
      this.input.value = prompts[action];
      this.sendMessage();
    }
  }

  saveHistory() {
    const history = this.ollama.getHistory().slice(-20);
    chrome.storage.local.set({ chatHistory: history });
  }

  async loadHistory() {
    const { chatHistory } = await chrome.storage.local.get('chatHistory');
    if (chatHistory) {
      this.ollama.conversationHistory = chatHistory;
      chatHistory.forEach(msg => {
        if (msg.role !== 'system') {
          this.addMessage(msg.content, msg.role);
        }
      });
    }
  }
}

new PopupApp();
