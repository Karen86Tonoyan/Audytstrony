import OllamaClient from '../lib/ollama.js';
import AppGenerator from '../lib/appGenerator.js';

const ollama = new OllamaClient();
const appGen = new AppGenerator(ollama);

const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const modeSelect = document.getElementById('mode');
const appBuilder = document.getElementById('app-builder');

modeSelect.addEventListener('change', () => {
  appBuilder.style.display = modeSelect.value === 'app' ? 'block' : 'none';
});

sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

document.getElementById('generate-app').addEventListener('click', generateApp);

async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, 'user');
  input.value = '';

  const responseDiv = addMessage('Myślę...', 'assistant');

  try {
    let response = '';
    for await (const chunk of ollama.chatStream(text)) {
      response += chunk;
      responseDiv.innerHTML = formatCode(response);
    }
  } catch (err) {
    responseDiv.textContent = 'Błąd: ' + err.message;
  }
}

async function generateApp() {
  const config = {
    name: document.getElementById('app-name').value || 'my-app',
    description: document.getElementById('app-desc').value,
    backendType: document.getElementById('backend').value,
    frontendType: document.getElementById('frontend').value
  };

  addMessage(`Generuję aplikację: ${config.name}`, 'user');
  const responseDiv = addMessage('Generuję pliki...', 'assistant');

  try {
    const result = await appGen.generateApp(config);
    let output = `**Aplikacja ${result.name} wygenerowana!**\n\nPliki:\n`;
    for (const path of Object.keys(result.files)) {
      output += `- ${path}\n`;
    }
    output += `\n${result.instructions.join('\n')}`;
    responseDiv.innerHTML = formatCode(output);

    // Zapisz do pobrania
    chrome.storage.local.set({ generatedApp: result });
  } catch (err) {
    responseDiv.textContent = 'Błąd: ' + err.message;
  }
}

function addMessage(text, role) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = formatCode(text);
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function formatCode(text) {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

// Obsługa akcji z context menu
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'context-action') {
    const prompts = {
      explain: `Wyjaśnij ten kod:\n\`\`\`\n${msg.text}\n\`\`\``,
      fix: `Napraw błędy w tym kodzie:\n\`\`\`\n${msg.text}\n\`\`\``,
      improve: `Ulepsz ten kod:\n\`\`\`\n${msg.text}\n\`\`\``
    };
    input.value = prompts[msg.action] || msg.text;
    sendMessage();
  }
});
