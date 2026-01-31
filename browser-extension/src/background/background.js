// Ollama Agent - Background Service Worker

const OLLAMA_HOST = 'http://localhost:11434';

// Inicjalizacja przy instalacji
chrome.runtime.onInstalled.addListener(() => {
  console.log('Ollama Agent zainstalowany');

  // Ustaw domyślne ustawienia
  chrome.storage.local.set({
    ollamaHost: OLLAMA_HOST,
    model: 'llama3.2',
    visionModel: 'llava'
  });

  // Utwórz menu kontekstowe
  chrome.contextMenus.create({
    id: 'ollama-explain',
    title: 'Wyjaśnij zaznaczony kod',
    contexts: ['selection']
  });

  chrome.contextMenus.create({
    id: 'ollama-fix',
    title: 'Napraw błąd w kodzie',
    contexts: ['selection']
  });

  chrome.contextMenus.create({
    id: 'ollama-improve',
    title: 'Ulepsz kod',
    contexts: ['selection']
  });
});

// Obsługa menu kontekstowego
chrome.contextMenus.onClicked.addListener((info, tab) => {
  const text = info.selectionText;

  if (info.menuItemId === 'ollama-explain') {
    handleContextAction('explain', text, tab);
  } else if (info.menuItemId === 'ollama-fix') {
    handleContextAction('fix', text, tab);
  } else if (info.menuItemId === 'ollama-improve') {
    handleContextAction('improve', text, tab);
  }
});

async function handleContextAction(action, text, tab) {
  // Otwórz side panel z wynikiem
  await chrome.sidePanel.open({ windowId: tab.windowId });

  // Wyślij wiadomość do side panelu
  chrome.runtime.sendMessage({
    type: 'context-action',
    action,
    text
  });
}

// Obsługa wiadomości
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'check-ollama') {
    checkOllama().then(sendResponse);
    return true;
  }

  if (message.type === 'generate') {
    generateWithOllama(message.prompt, message.options).then(sendResponse);
    return true;
  }

  if (message.type === 'chat') {
    chatWithOllama(message.messages, message.options).then(sendResponse);
    return true;
  }
});

async function checkOllama() {
  try {
    const response = await fetch(`${OLLAMA_HOST}/api/tags`);
    return { available: response.ok };
  } catch {
    return { available: false };
  }
}

async function generateWithOllama(prompt, options = {}) {
  try {
    const response = await fetch(`${OLLAMA_HOST}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: options.model || 'llama3.2',
        prompt,
        stream: false
      })
    });

    const data = await response.json();
    return { success: true, response: data.response };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function chatWithOllama(messages, options = {}) {
  try {
    const response = await fetch(`${OLLAMA_HOST}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: options.model || 'llama3.2',
        messages,
        stream: false
      })
    });

    const data = await response.json();
    return { success: true, response: data.message?.content };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Obsługa skrótów klawiszowych
chrome.commands.onCommand.addListener((command) => {
  if (command === 'toggle_sidepanel') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.sidePanel.open({ windowId: tabs[0].windowId });
    });
  }
});
