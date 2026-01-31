// Ollama Agent - Content Script
// Dodaje funkcjonalność do stron

(function() {
  // Floating button
  const btn = document.createElement('div');
  btn.id = 'ollama-agent-btn';
  btn.innerHTML = '🤖';
  btn.style.cssText = `
    position: fixed; bottom: 20px; right: 20px; width: 50px; height: 50px;
    background: #e94560; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: 24px; cursor: pointer; z-index: 999999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: transform 0.2s;
  `;
  btn.onmouseenter = () => btn.style.transform = 'scale(1.1)';
  btn.onmouseleave = () => btn.style.transform = 'scale(1)';
  btn.onclick = () => chrome.runtime.sendMessage({ type: 'open-popup' });

  document.body.appendChild(btn);

  // Nasłuchuj na zaznaczenie tekstu
  document.addEventListener('mouseup', (e) => {
    const selection = window.getSelection().toString().trim();
    if (selection.length > 10) {
      showQuickMenu(e.pageX, e.pageY, selection);
    }
  });

  let quickMenu = null;

  function showQuickMenu(x, y, text) {
    if (quickMenu) quickMenu.remove();

    quickMenu = document.createElement('div');
    quickMenu.style.cssText = `
      position: absolute; left: ${x}px; top: ${y}px; background: #16213e;
      border: 1px solid #0f3460; border-radius: 8px; padding: 8px; z-index: 999999;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: flex; gap: 4px;
    `;

    const actions = [
      { icon: '💡', title: 'Wyjaśnij', action: 'explain' },
      { icon: '🔧', title: 'Napraw', action: 'fix' },
      { icon: '✨', title: 'Ulepsz', action: 'improve' }
    ];

    actions.forEach(({ icon, title, action }) => {
      const btn = document.createElement('button');
      btn.textContent = icon;
      btn.title = title;
      btn.style.cssText = `
        padding: 8px 12px; border: none; border-radius: 4px;
        background: #1a1a2e; color: white; cursor: pointer; font-size: 16px;
      `;
      btn.onclick = () => {
        chrome.runtime.sendMessage({ type: 'context-action', action, text });
        quickMenu.remove();
        quickMenu = null;
      };
      quickMenu.appendChild(btn);
    });

    document.body.appendChild(quickMenu);

    // Auto-hide
    setTimeout(() => {
      if (quickMenu) {
        quickMenu.remove();
        quickMenu = null;
      }
    }, 5000);
  }

  document.addEventListener('click', (e) => {
    if (quickMenu && !quickMenu.contains(e.target)) {
      quickMenu.remove();
      quickMenu = null;
    }
  });
})();
