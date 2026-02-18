/**
 * Guardian - Ochroniarz i Policjant Bota
 * ======================================
 * System bezpieczeństwa dla rozszerzenia przeglądarki
 */

class Guardian {
  constructor(ollamaClient) {
    this.ollama = ollamaClient;
    this.events = [];
    this.blockedPatterns = [];
    this.rateLimits = new Map();
    this.actionCounts = new Map();

    this.loadDefaultRules();
    this.setupRateLimits();

    console.log('Guardian zainicjalizowany - ochrona aktywna');
  }

  loadDefaultRules() {
    // Wzorce do blokowania
    this.blockedPatterns = [
      // Destrukcyjne komendy
      /rm\s+-rf\s+[\/~]/i,
      /format\s+[cC]:/i,
      /del\s+\/[sS]/i,
      /mkfs\./i,

      // Kradzież danych
      /\.ssh\/id_rsa/i,
      /\.aws\/credentials/i,
      /passwords?\.(txt|json)/i,
      /\/etc\/shadow/i,

      // Niebezpieczny kod
      /eval\s*\(/i,
      /exec\s*\(/i,
      /Function\s*\(/i,
      /__proto__/i,

      // Ataki XSS
      /<script[^>]*>/i,
      /javascript:/i,
      /on\w+\s*=/i,
    ];

    // Dozwolone domeny dla żądań
    this.allowedDomains = [
      'localhost',
      '127.0.0.1',
      'api.github.com',
      'registry.npmjs.org',
    ];
  }

  setupRateLimits() {
    this.rateLimits.set('command', { perMinute: 30, perHour: 200 });
    this.rateLimits.set('file', { perMinute: 60, perHour: 500 });
    this.rateLimits.set('network', { perMinute: 100, perHour: 1000 });
    this.rateLimits.set('ai', { perMinute: 20, perHour: 200 });
  }

  // ==================== Główne API ====================

  async checkAction(actionType, description, details = {}) {
    const eventId = this.generateId();
    const timestamp = new Date();

    // Sprawdź rate limit
    if (!this.checkRateLimit(actionType)) {
      this.logEvent(eventId, actionType, 'blocked', description, 'Rate limit exceeded');
      return { allowed: false, reason: 'Przekroczono limit akcji' };
    }

    // Sprawdź wzorce
    const content = description + ' ' + JSON.stringify(details);
    for (const pattern of this.blockedPatterns) {
      if (pattern.test(content)) {
        this.logEvent(eventId, actionType, 'blocked', description, `Matched pattern: ${pattern}`);
        await this.sendAlert('critical', 'Zablokowano niebezpieczną akcję', description);
        return { allowed: false, reason: 'Wykryto niebezpieczny wzorzec' };
      }
    }

    // Dla kodu - dodatkowa analiza AI
    if (actionType === 'code' && this.ollama) {
      const aiCheck = await this.aiEvaluateCode(description, details);
      if (!aiCheck.safe) {
        this.logEvent(eventId, actionType, 'blocked', description, aiCheck.reason);
        return { allowed: false, reason: aiCheck.reason };
      }
    }

    // Dozwolone
    this.logEvent(eventId, actionType, 'allowed', description);
    this.incrementCounter(actionType);
    return { allowed: true };
  }

  async aiEvaluateCode(description, details) {
    const prompt = `Jesteś systemem bezpieczeństwa Guardian. Oceń czy ten kod jest BEZPIECZNY.

KOD DO OCENY:
${details.code || description}

Sprawdź:
1. Czy nie zawiera destrukcyjnych operacji?
2. Czy nie kradnie danych/poświadczeń?
3. Czy nie ma luk bezpieczeństwa (XSS, injection)?
4. Czy nie wykonuje nieautoryzowanych operacji?

Odpowiedz JSON: {"safe": true/false, "reason": "powód", "threats": []}`;

    try {
      const response = await this.ollama.generate(prompt, { temperature: 0.1 });
      const match = response.match(/\{[\s\S]*\}/);
      if (match) {
        return JSON.parse(match[0]);
      }
    } catch (e) {
      console.error('Guardian AI evaluation error:', e);
    }

    // Domyślnie - bezpieczne (by nie blokować niepotrzebnie)
    return { safe: true, reason: 'AI evaluation failed - allowing' };
  }

  // ==================== Rate Limiting ====================

  checkRateLimit(actionType) {
    const limit = this.rateLimits.get(actionType);
    if (!limit) return true;

    const key = actionType;
    const now = Date.now();

    if (!this.actionCounts.has(key)) {
      this.actionCounts.set(key, []);
    }

    const counts = this.actionCounts.get(key);

    // Wyczyść stare
    const hourAgo = now - 3600000;
    const filtered = counts.filter(t => t > hourAgo);
    this.actionCounts.set(key, filtered);

    // Sprawdź limity
    const minuteAgo = now - 60000;
    const perMinute = filtered.filter(t => t > minuteAgo).length;
    const perHour = filtered.length;

    return perMinute < limit.perMinute && perHour < limit.perHour;
  }

  incrementCounter(actionType) {
    const key = actionType;
    if (!this.actionCounts.has(key)) {
      this.actionCounts.set(key, []);
    }
    this.actionCounts.get(key).push(Date.now());
  }

  // ==================== Logging ====================

  generateId() {
    return Math.random().toString(36).substr(2, 9);
  }

  logEvent(id, actionType, status, description, reason = '') {
    const event = {
      id,
      timestamp: new Date().toISOString(),
      actionType,
      status,
      description: description.substring(0, 200),
      reason,
    };

    this.events.push(event);

    // Limit historii
    if (this.events.length > 1000) {
      this.events = this.events.slice(-500);
    }

    // Zapisz do storage
    this.saveToStorage();

    console.log(`[Guardian] ${status.toUpperCase()}: ${actionType} - ${description.substring(0, 50)}`);
  }

  async saveToStorage() {
    try {
      await chrome.storage.local.set({
        guardianEvents: this.events.slice(-100),
        guardianLastUpdate: new Date().toISOString(),
      });
    } catch (e) {
      console.error('Guardian storage error:', e);
    }
  }

  async loadFromStorage() {
    try {
      const data = await chrome.storage.local.get(['guardianEvents']);
      if (data.guardianEvents) {
        this.events = data.guardianEvents;
      }
    } catch (e) {
      console.error('Guardian load error:', e);
    }
  }

  // ==================== Alerts ====================

  async sendAlert(level, title, description) {
    console.error(`[GUARDIAN ALERT - ${level.toUpperCase()}] ${title}: ${description}`);

    // Pokaż powiadomienie
    if (chrome.notifications) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: '/public/icons/icon48.png',
        title: `Guardian Alert: ${title}`,
        message: description,
        priority: 2,
      });
    }

    // Zapisz alert
    const alerts = (await chrome.storage.local.get(['guardianAlerts'])).guardianAlerts || [];
    alerts.push({
      timestamp: new Date().toISOString(),
      level,
      title,
      description,
    });
    await chrome.storage.local.set({ guardianAlerts: alerts.slice(-50) });
  }

  // ==================== Raporty ====================

  getReport() {
    const now = Date.now();
    const hourAgo = now - 3600000;
    const recent = this.events.filter(e => new Date(e.timestamp).getTime() > hourAgo);

    const report = {
      totalEvents: recent.length,
      blocked: recent.filter(e => e.status === 'blocked').length,
      allowed: recent.filter(e => e.status === 'allowed').length,
      byType: {},
    };

    for (const event of recent) {
      report.byType[event.actionType] = (report.byType[event.actionType] || 0) + 1;
    }

    return report;
  }

  getRecentEvents(limit = 20) {
    return this.events.slice(-limit);
  }

  // ==================== Sanityzacja ====================

  sanitizeInput(input) {
    if (typeof input !== 'string') return input;

    return input
      .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<[^>]+on\w+\s*=/gi, '<')
      .replace(/javascript:/gi, '')
      .replace(/eval\s*\(/gi, 'blocked(')
      .replace(/Function\s*\(/gi, 'blocked(');
  }

  sanitizeCode(code) {
    // Sprawdź czy kod nie zawiera niebezpiecznych wzorców
    const dangerous = [
      /process\.env/i,
      /require\s*\(\s*['"]child_process['"]\s*\)/i,
      /fs\.(unlink|rmdir|rm)Sync/i,
      /\.exec\s*\(/i,
    ];

    for (const pattern of dangerous) {
      if (pattern.test(code)) {
        console.warn('Guardian: Sanitized dangerous code pattern');
        code = code.replace(pattern, '/* BLOCKED */');
      }
    }

    return code;
  }

  // ==================== Walidacja URL ====================

  isUrlAllowed(url) {
    try {
      const parsed = new URL(url);

      // Localhost zawsze OK
      if (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
        return true;
      }

      // Sprawdź whitelist
      for (const domain of this.allowedDomains) {
        if (parsed.hostname.endsWith(domain)) {
          return true;
        }
      }

      // Sprawdź niebezpieczne protokoły
      if (['javascript:', 'data:', 'vbscript:'].includes(parsed.protocol)) {
        return false;
      }

      return true; // Domyślnie pozwól (nie jesteśmy zbyt restrykcyjni)
    } catch {
      return false;
    }
  }
}

export default Guardian;

if (typeof window !== 'undefined') {
  window.Guardian = Guardian;
}
