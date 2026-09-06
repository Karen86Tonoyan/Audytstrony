# Ollama Agent / Audytstrony

> **Experimental local Python agent with automation, audit, vision, voice and file-generation modules**

Audytstrony contains a Python package called `agent` plus a small `src/`
application. The modules cover local Ollama communication, screen and web
inspection, automation, scheduling, file generation, voice and a separate
`smart_lock` namespace. The components have distinct permissions and should be
enabled only after review.

## Project structure

```text
agent/core/          agent loop, Ollama client and scheduler
agent/modules/       automation, communication, vision, voice and web audit
agent/modules/smart_lock/
                     health, key, emergency and controller experiments
agent/config/        settings
config/roles.yaml    role configuration
tests/               smart-lock test module
```

## Requirements

- Python 3.10+;
- a local Ollama service and models for LLM-dependent flows;
- optional OS tools and devices for OCR, browser automation, audio, social
  integrations or smart-lock experiments.

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
```

The project declares the `ollama-agent` console command:

```bash
ollama-agent
```

`requirements.txt` lists a broader optional tool set. Install it only when the
corresponding feature is required.

## Configuration

Copy `.env.example` to a local `.env` and set only the integrations in use.
The example includes Ollama, OCR and voice settings, followed by optional
Telegram, social-media and Smart Lock placeholders. Keep tokens, passwords,
device identifiers and endpoints out of version control.

## Safety and status

Screen capture, keyboard/mouse automation, browser automation and smart-device
modules can affect personal data, accounts or physical equipment. Run them
only with permission, use test targets first and keep a human in control.
This is a beta-stage prototype, not a certified audit or access-control
system.

## Licence

`pyproject.toml` declares an MIT licence, but the repository has no root
`LICENSE` file. Confirm the intended licensing with the maintainer before
redistribution.
