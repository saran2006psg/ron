# AI Use Disclosure

In compliance with the IncuBrix Engineering Assessment guidelines (Point 1: "Disclose everything"), this document details the AI tools, models, and coding assistants utilized during development.

---

## 1. AI Tools & Coding Assistants

| Tool / Assistant | Provider / Model | Purpose / Application |
|---|---|---|
| **ChatGPT / Claude / Antigravity Agent** | Anthropic / Google / OpenAI | Architecture brainstorming, FastAPI endpoint scaffolding, regex pattern drafting, and test case generation. |
| **Microsoft Edge Neural Speech** | Microsoft Speech Platform (`edge-tts`) | High-fidelity neural TTS narration generation across English (`en-IN`, `en-US`), Hindi (`hi-IN`), and Tamil (`ta-IN`). |
| **Pixabay / Pexels Search API** | Pixabay / Canva | Automated semantic visual search for CC0/commercial-licensed B-roll footage. |

---

## 2. Engineering Responsibility & Verification

- **Code Review**: Every line of code, configuration, and test case generated with AI assistance was manually reviewed, verified, and adjusted for performance and compliance.
- **Licence Integrity**: No proprietary, non-commercial (e.g., CC BY-NC), or unverified AI generated media is shipped in the default path.
- **Offline Test Rig**: All 43 automated pytest unit and integration tests run 100% offline using local fixtures and mock adapters, proving the architecture functions independently of external AI services.
- **Live Explanation**: The candidate understands every architectural choice, data flow, FFmpeg filter graph, and error recovery mechanism, and is prepared to walk through and modify any part of the codebase during the live session.


