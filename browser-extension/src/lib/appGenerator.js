/**
 * Generator Aplikacji - tworzenie kompletnych projektów
 * =====================================================
 */

class AppGenerator {
  constructor(ollamaClient) {
    this.ollama = ollamaClient;
    this.templates = this.loadTemplates();
  }

  loadTemplates() {
    return {
      // ==================== BACKEND TEMPLATES ====================
      backend: {
        // --- Node.js Express ---
        'node-express': {
          name: 'Node.js + Express API',
          files: {
            'package.json': `{
  "name": "{{name}}",
  "version": "1.0.0",
  "description": "{{description}}",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1",
    "helmet": "^7.1.0",
    "morgan": "^1.10.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.2",
    "jest": "^29.7.0"
  }
}`,
            'src/index.js': `const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'API działa!', timestamp: new Date() });
});

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// {{routes}}

// Error handling
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Coś poszło nie tak!' });
});

app.listen(PORT, () => {
  console.log(\`Serwer działa na http://localhost:\${PORT}\`);
});`,
            '.env.example': `PORT=3000
NODE_ENV=development`,
            '.gitignore': `node_modules/
.env
*.log`
          }
        },

        // --- Python FastAPI ---
        'python-fastapi': {
          name: 'Python + FastAPI',
          files: {
            'requirements.txt': `fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
python-dotenv>=1.0.0
sqlalchemy>=2.0.0
alembic>=1.12.0`,
            'main.py': `from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="{{name}}",
    description="{{description}}",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

# Database (in-memory dla przykładu)
items_db: List[Item] = []

# Routes
@app.get("/")
async def root():
    return {"message": "API działa!", "docs": "/docs"}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/items", response_model=List[Item])
async def get_items():
    return items_db

@app.post("/api/items", response_model=Item)
async def create_item(item: Item):
    item.id = len(items_db) + 1
    items_db.append(item)
    return item

@app.get("/api/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

# {{routes}}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)`,
            '.env.example': `DATABASE_URL=sqlite:///./app.db
SECRET_KEY=your-secret-key`,
            '.gitignore': `__pycache__/
*.pyc
.env
*.db
venv/`
          }
        },

        // --- Python Flask ---
        'python-flask': {
          name: 'Python + Flask',
          files: {
            'requirements.txt': `flask>=3.0.0
flask-cors>=4.0.0
python-dotenv>=1.0.0
flask-sqlalchemy>=3.1.0`,
            'app.py': `from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

# Routes
@app.route('/')
def index():
    return jsonify({'message': 'API działa!', 'docs': '/api'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

# {{routes}}

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Nie znaleziono'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Błąd serwera'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)`,
            '.gitignore': `__pycache__/
*.pyc
.env
venv/
instance/`
          }
        }
      },

      // ==================== FRONTEND TEMPLATES ====================
      frontend: {
        // --- React + Vite ---
        'react-vite': {
          name: 'React + Vite',
          files: {
            'package.json': `{
  "name": "{{name}}",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}`,
            'vite.config.js': `import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})`,
            'index.html': `<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{name}}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>`,
            'src/main.jsx': `import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)`,
            'src/App.jsx': `import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="app">
      <header>
        <h1>{{name}}</h1>
        <p>{{description}}</p>
      </header>
      <main>
        {loading ? (
          <p>Ładowanie...</p>
        ) : (
          <div className="status">
            <p>Status API: {data?.status || 'Błąd'}</p>
          </div>
        )}
        {/* {{components}} */}
      </main>
    </div>
  )
}

export default App`,
            'src/index.css': `* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
}`,
            'src/App.css': `.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

header h1 {
  color: #2563eb;
  margin-bottom: 0.5rem;
}

main {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.status {
  padding: 1rem;
  background: #f0f9ff;
  border-radius: 4px;
}`
          }
        },

        // --- Vue 3 + Vite ---
        'vue-vite': {
          name: 'Vue 3 + Vite',
          files: {
            'package.json': `{
  "name": "{{name}}",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.3.0",
    "vue-router": "^4.2.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.0",
    "vite": "^5.0.0"
  }
}`,
            'vite.config.js': `import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})`,
            'index.html': `<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{name}}</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>`,
            'src/main.js': `import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')`,
            'src/App.vue': `<template>
  <div class="app">
    <header>
      <h1>{{name}}</h1>
      <p>{{description}}</p>
    </header>
    <main>
      <div v-if="loading">Ładowanie...</div>
      <div v-else class="status">
        <p>Status API: {{ data?.status || 'Błąd' }}</p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const data = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await fetch('/api/health')
    data.value = await res.json()
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

header h1 {
  color: #42b883;
}

main {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.status {
  padding: 1rem;
  background: #f0fff4;
  border-radius: 4px;
}
</style>`,
            'src/style.css': `* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
}`
          }
        },

        // --- Vanilla HTML/CSS/JS ---
        'vanilla': {
          name: 'HTML + CSS + JavaScript',
          files: {
            'index.html': `<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{name}}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="app">
    <header>
      <h1>{{name}}</h1>
      <p>{{description}}</p>
    </header>
    <main id="main">
      <p>Ładowanie...</p>
    </main>
  </div>
  <script src="app.js"></script>
</body>
</html>`,
            'styles.css': `* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

header h1 {
  color: #2563eb;
  margin-bottom: 0.5rem;
}

main {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}`,
            'app.js': `// {{name}} - Main Application
document.addEventListener('DOMContentLoaded', async () => {
  const main = document.getElementById('main');

  try {
    const response = await fetch('/api/health');
    const data = await response.json();

    main.innerHTML = \`
      <div class="status">
        <p>Status API: \${data.status}</p>
      </div>
    \`;
  } catch (error) {
    main.innerHTML = '<p class="error">Błąd połączenia z API</p>';
    console.error(error);
  }
});`
          }
        }
      },

      // ==================== FULL STACK TEMPLATES ====================
      fullstack: {
        'mern': {
          name: 'MERN Stack (MongoDB, Express, React, Node)',
          backend: 'node-express',
          frontend: 'react-vite',
          additionalFiles: {
            'docker-compose.yml': `version: '3.8'
services:
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db

  backend:
    build: ./backend
    ports:
      - "3001:3001"
    depends_on:
      - mongodb
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/{{name}}

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  mongo-data:`
          }
        },
        'pern': {
          name: 'PERN Stack (PostgreSQL, Express, React, Node)',
          backend: 'node-express',
          frontend: 'react-vite'
        }
      }
    };
  }

  // ==================== Generator Methods ====================

  async generateApp(config) {
    const {
      name,
      description,
      backendType,
      frontendType,
      features = [],
      customPrompt = ''
    } = config;

    const result = {
      name,
      description,
      files: {},
      instructions: []
    };

    // Generuj backend
    if (backendType && this.templates.backend[backendType]) {
      const backendFiles = await this.generateBackend({
        name,
        description,
        type: backendType,
        features,
        customPrompt
      });
      result.files = { ...result.files, ...this.prefixPaths(backendFiles, 'backend/') };
      result.instructions.push(`cd backend && npm install && npm run dev`);
    }

    // Generuj frontend
    if (frontendType && this.templates.frontend[frontendType]) {
      const frontendFiles = await this.generateFrontend({
        name,
        description,
        type: frontendType,
        features,
        customPrompt
      });
      result.files = { ...result.files, ...this.prefixPaths(frontendFiles, 'frontend/') };
      result.instructions.push(`cd frontend && npm install && npm run dev`);
    }

    // Generuj README
    result.files['README.md'] = this.generateReadme(config);

    return result;
  }

  async generateBackend(config) {
    const template = this.templates.backend[config.type];
    if (!template) throw new Error(`Nieznany typ backendu: ${config.type}`);

    const files = {};

    // Kopiuj pliki z szablonu z podstawieniem zmiennych
    for (const [path, content] of Object.entries(template.files)) {
      files[path] = this.replaceVariables(content, config);
    }

    // Jeśli są dodatkowe features, poproś AI o wygenerowanie kodu
    if (config.features.length > 0 || config.customPrompt) {
      const additionalCode = await this.generateAdditionalBackendCode(config);
      // Merge additional code into files
      Object.assign(files, additionalCode);
    }

    return files;
  }

  async generateFrontend(config) {
    const template = this.templates.frontend[config.type];
    if (!template) throw new Error(`Nieznany typ frontendu: ${config.type}`);

    const files = {};

    for (const [path, content] of Object.entries(template.files)) {
      files[path] = this.replaceVariables(content, config);
    }

    if (config.features.length > 0 || config.customPrompt) {
      const additionalCode = await this.generateAdditionalFrontendCode(config);
      Object.assign(files, additionalCode);
    }

    return files;
  }

  async generateAdditionalBackendCode(config) {
    const prompt = `Wygeneruj dodatkowy kod backend dla aplikacji "${config.name}" (${config.type}).

Wymagane funkcjonalności:
${config.features.map(f => `- ${f}`).join('\n')}

${config.customPrompt ? `Dodatkowe wymagania:\n${config.customPrompt}` : ''}

Zwróć kod w formacie:
**ścieżka/do/pliku.js**
\`\`\`javascript
kod
\`\`\`

Dla każdego pliku osobno.`;

    const response = await this.ollama.generate(prompt);
    return this.parseCodeBlocks(response);
  }

  async generateAdditionalFrontendCode(config) {
    const prompt = `Wygeneruj dodatkowe komponenty frontend dla aplikacji "${config.name}" (${config.type}).

Wymagane funkcjonalności:
${config.features.map(f => `- ${f}`).join('\n')}

${config.customPrompt ? `Dodatkowe wymagania:\n${config.customPrompt}` : ''}

Zwróć kod w formacie:
**ścieżka/do/pliku.jsx**
\`\`\`jsx
kod
\`\`\`

Dla każdego komponentu osobno.`;

    const response = await this.ollama.generate(prompt);
    return this.parseCodeBlocks(response);
  }

  // ==================== Helpers ====================

  replaceVariables(content, config) {
    return content
      .replace(/\{\{name\}\}/g, config.name || 'my-app')
      .replace(/\{\{description\}\}/g, config.description || 'Aplikacja wygenerowana przez Ollama Agent')
      .replace(/\{\{routes\}\}/g, '// Tutaj dodaj własne routes')
      .replace(/\{\{components\}\}/g, '{/* Tutaj dodaj własne komponenty */}');
  }

  prefixPaths(files, prefix) {
    const result = {};
    for (const [path, content] of Object.entries(files)) {
      result[prefix + path] = content;
    }
    return result;
  }

  parseCodeBlocks(response) {
    const files = {};
    const fileRegex = /\*\*([^\*]+)\*\*\s*```(\w*)\n([\s\S]*?)```/g;

    let match;
    while ((match = fileRegex.exec(response)) !== null) {
      const [, path, , code] = match;
      files[path.trim()] = code.trim();
    }

    return files;
  }

  generateReadme(config) {
    return `# ${config.name}

${config.description || 'Aplikacja wygenerowana przez Ollama Agent'}

## Technologie

- **Backend:** ${config.backendType || 'Brak'}
- **Frontend:** ${config.frontendType || 'Brak'}

## Uruchomienie

### Backend
\`\`\`bash
cd backend
npm install  # lub pip install -r requirements.txt
npm run dev  # lub python main.py
\`\`\`

### Frontend
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

## Struktura projektu

\`\`\`
${config.name}/
├── backend/          # Serwer API
├── frontend/         # Aplikacja kliencka
└── README.md
\`\`\`

---
*Wygenerowano przez Ollama Agent*
`;
  }

  // ==================== Quick Generators ====================

  async generateComponent(name, type, description) {
    const prompt = `Wygeneruj komponent ${type} o nazwie "${name}".
Opis: ${description}

Wymagania:
- Nowoczesny, czysty kod
- Obsługa błędów
- Komentarze po polsku
- Responsywny design (jeśli UI)

Zwróć kompletny, gotowy do użycia kod.`;

    return await this.ollama.generate(prompt);
  }

  async generateAPI(endpoints, language = 'node') {
    const prompt = `Wygeneruj API REST w ${language} z następującymi endpointami:

${endpoints.map(e => `- ${e.method} ${e.path}: ${e.description}`).join('\n')}

Wymagania:
- Walidacja danych
- Obsługa błędów
- Dokumentacja (komentarze)
- Bezpieczeństwo (sanityzacja)

Zwróć kompletny kod.`;

    return await this.ollama.generate(prompt);
  }

  async generateDatabase(schema, dbType = 'postgresql') {
    const prompt = `Wygeneruj schemat bazy danych ${dbType}:

${JSON.stringify(schema, null, 2)}

Zwróć:
1. SQL do utworzenia tabel
2. Migracje (jeśli dotyczy)
3. Modele ORM (SQLAlchemy/Prisma/Sequelize)`;

    return await this.ollama.generate(prompt);
  }

  getAvailableTemplates() {
    return {
      backend: Object.entries(this.templates.backend).map(([key, val]) => ({
        id: key,
        name: val.name
      })),
      frontend: Object.entries(this.templates.frontend).map(([key, val]) => ({
        id: key,
        name: val.name
      })),
      fullstack: Object.entries(this.templates.fullstack).map(([key, val]) => ({
        id: key,
        name: val.name
      }))
    };
  }
}

export default AppGenerator;

if (typeof window !== 'undefined') {
  window.AppGenerator = AppGenerator;
}
