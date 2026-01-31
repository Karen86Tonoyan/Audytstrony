/**
 * Ollama API Client dla rozszerzenia przeglądarki
 * ================================================
 */

class OllamaClient {
  constructor(host = 'http://localhost:11434') {
    this.host = host;
    this.model = 'llama3.2';
    this.visionModel = 'llava';
    this.conversationHistory = [];
    this.systemPrompt = this.getDefaultSystemPrompt();
  }

  getDefaultSystemPrompt() {
    return `Jesteś Ollama Agent - zaawansowanym asystentem AI do programowania.

Twoje możliwości:
1. TWORZENIE APLIKACJI - generujesz kompletne projekty (backend + frontend)
2. KODOWANIE - piszesz kod w dowolnym języku (Python, JavaScript, TypeScript, React, Node.js, etc.)
3. DEBUGOWANIE - znajdujesz i naprawiasz błędy
4. WYJAŚNIANIE - tłumaczysz kod i koncepcje
5. REFAKTORYZACJA - ulepszasz istniejący kod
6. AUDYTY - sprawdzasz bezpieczeństwo i jakość kodu

Gdy użytkownik prosi o stworzenie aplikacji:
- Zawsze twórz KOMPLETNY, DZIAŁAJĄCY kod
- Używaj najlepszych praktyk
- Dodawaj komentarze po polsku
- Strukturyzuj projekt logicznie

Formaty odpowiedzi:
- Kod w blokach \`\`\`język
- Nazwy plików przed kodem: **plik.js**
- Wyjaśnienia są zwięzłe i konkretne

Odpowiadaj po polsku.`;
  }

  // ==================== API Statusu ====================

  async isAvailable() {
    try {
      const response = await fetch(`${this.host}/api/tags`);
      return response.ok;
    } catch (error) {
      console.error('Ollama niedostępna:', error);
      return false;
    }
  }

  async listModels() {
    try {
      const response = await fetch(`${this.host}/api/tags`);
      const data = await response.json();
      return data.models || [];
    } catch (error) {
      console.error('Błąd pobierania modeli:', error);
      return [];
    }
  }

  // ==================== Generowanie ====================

  async generate(prompt, options = {}) {
    const payload = {
      model: options.model || this.model,
      prompt: prompt,
      stream: false,
      options: {
        temperature: options.temperature || 0.7,
        top_p: options.top_p || 0.9,
        num_predict: options.maxTokens || 4096,
      }
    };

    if (options.system) {
      payload.system = options.system;
    }

    try {
      const response = await fetch(`${this.host}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      return data.response || '';
    } catch (error) {
      console.error('Błąd generowania:', error);
      throw error;
    }
  }

  async *generateStream(prompt, options = {}) {
    const payload = {
      model: options.model || this.model,
      prompt: prompt,
      stream: true,
      options: {
        temperature: options.temperature || 0.7,
        num_predict: options.maxTokens || 4096,
      }
    };

    if (options.system) {
      payload.system = options.system;
    }

    try {
      const response = await fetch(`${this.host}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.response) {
              yield data.response;
            }
          } catch (e) {
            // Ignoruj błędy parsowania
          }
        }
      }
    } catch (error) {
      console.error('Błąd streamingu:', error);
      throw error;
    }
  }

  // ==================== Chat ====================

  async chat(message, options = {}) {
    // Dodaj wiadomość do historii
    this.conversationHistory.push({
      role: 'user',
      content: message
    });

    const messages = [];

    // System prompt
    if (this.systemPrompt) {
      messages.push({
        role: 'system',
        content: options.systemPrompt || this.systemPrompt
      });
    }

    // Historia (ostatnie N wiadomości)
    const historyLimit = options.historyLimit || 20;
    const recentHistory = this.conversationHistory.slice(-historyLimit);
    messages.push(...recentHistory);

    const payload = {
      model: options.model || this.model,
      messages: messages,
      stream: false,
      options: {
        temperature: options.temperature || 0.7,
        num_predict: options.maxTokens || 4096,
      }
    };

    try {
      const response = await fetch(`${this.host}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      const assistantMessage = data.message?.content || '';

      // Zapisz odpowiedź w historii
      this.conversationHistory.push({
        role: 'assistant',
        content: assistantMessage
      });

      return assistantMessage;
    } catch (error) {
      console.error('Błąd chatu:', error);
      throw error;
    }
  }

  async *chatStream(message, options = {}) {
    this.conversationHistory.push({
      role: 'user',
      content: message
    });

    const messages = [];

    if (this.systemPrompt) {
      messages.push({
        role: 'system',
        content: options.systemPrompt || this.systemPrompt
      });
    }

    const historyLimit = options.historyLimit || 20;
    messages.push(...this.conversationHistory.slice(-historyLimit));

    const payload = {
      model: options.model || this.model,
      messages: messages,
      stream: true,
      options: {
        temperature: options.temperature || 0.7,
        num_predict: options.maxTokens || 4096,
      }
    };

    try {
      const response = await fetch(`${this.host}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.message?.content) {
              fullResponse += data.message.content;
              yield data.message.content;
            }
          } catch (e) {
            // Ignoruj błędy parsowania
          }
        }
      }

      // Zapisz pełną odpowiedź
      this.conversationHistory.push({
        role: 'assistant',
        content: fullResponse
      });
    } catch (error) {
      console.error('Błąd streamingu:', error);
      throw error;
    }
  }

  // ==================== Vision ====================

  async analyzeImage(imageBase64, prompt = 'Opisz co widzisz na tym obrazie.') {
    const payload = {
      model: this.visionModel,
      messages: [
        {
          role: 'user',
          content: prompt,
          images: [imageBase64]
        }
      ],
      stream: false
    };

    try {
      const response = await fetch(`${this.host}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      return data.message?.content || '';
    } catch (error) {
      console.error('Błąd analizy obrazu:', error);
      throw error;
    }
  }

  // ==================== Pomocnicze ====================

  clearHistory() {
    this.conversationHistory = [];
  }

  setModel(model) {
    this.model = model;
  }

  setSystemPrompt(prompt) {
    this.systemPrompt = prompt;
  }

  getHistory() {
    return [...this.conversationHistory];
  }

  // ==================== Specjalne Prompty ====================

  async explainCode(code, language = '') {
    const prompt = `Wyjaśnij poniższy kod${language ? ` (${language})` : ''}:

\`\`\`${language}
${code}
\`\`\`

Opisz:
1. Co robi ten kod
2. Jak działa krok po kroku
3. Ważne elementy i wzorce`;

    return await this.generate(prompt, { system: this.systemPrompt });
  }

  async fixCode(code, error, language = '') {
    const prompt = `Napraw błąd w kodzie${language ? ` (${language})` : ''}:

**Kod:**
\`\`\`${language}
${code}
\`\`\`

**Błąd:**
${error}

Zwróć poprawiony kod z wyjaśnieniem co było nie tak.`;

    return await this.generate(prompt, { system: this.systemPrompt });
  }

  async refactorCode(code, language = '') {
    const prompt = `Zrefaktoryzuj poniższy kod${language ? ` (${language})` : ''} zgodnie z najlepszymi praktykami:

\`\`\`${language}
${code}
\`\`\`

Ulepsz:
1. Czytelność
2. Wydajność
3. Strukturę
4. Nazewnictwo`;

    return await this.generate(prompt, { system: this.systemPrompt });
  }

  async generateTests(code, language = '', framework = '') {
    const prompt = `Wygeneruj testy dla poniższego kodu${language ? ` (${language})` : ''}${framework ? ` używając ${framework}` : ''}:

\`\`\`${language}
${code}
\`\`\`

Stwórz kompletne testy jednostkowe pokrywające wszystkie przypadki.`;

    return await this.generate(prompt, { system: this.systemPrompt });
  }
}

// Export dla modułów ES
export default OllamaClient;

// Export dla globalnego dostępu
if (typeof window !== 'undefined') {
  window.OllamaClient = OllamaClient;
}
