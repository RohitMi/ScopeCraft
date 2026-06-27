# ScopeCraft — Project Documentation
### Agentic Requirements Engineering Prototype
**Version:** 1.0 | **Date:** June 2026 | **Author:** Rohit Mittel

---

## Table of Contents

1. [Project Genesis — The Original Idea](#1-project-genesis)
2. [Idea Evolution — From Simple to Enhanced](#2-idea-evolution)
3. [Final Prototype Scope](#3-final-prototype-scope)
4. [System Architecture](#4-system-architecture)
5. [Tech Stack Decisions](#5-tech-stack-decisions)
6. [Project Description — Course Submission](#6-project-description)
7. [Environment Setup Guide](#7-environment-setup-guide)
8. [Project Folder Structure](#8-project-folder-structure)
9. [Development Roadmap](#9-development-roadmap)

---

## 1. Project Genesis

### The Original Idea

The initial concept was simple: build a system where a user can enter their software requirements (with or without examples), and the application would:

- Chat with the user to ask clarifying questions
- Generate a BRD (Business Requirements Document)
- Generate a development plan in whatever technology the user chooses

The core insight was to act as an **"idea dump"** — a place where a raw concept could be transformed into a developable solution following standard SDLC cycles.

### Why This Needed Enhancement

The base idea had real-world weaknesses:

| Weakness | Problem |
|---|---|
| BRD + doc generation | ChatGPT, Copilot, Notion AI already do this |
| Chat and generate | No differentiation from existing tools |
| One-shot generation | Real requirements change — no memory |
| No validation | Generated BRD has zero quality gate |
| Technology-agnostic HLD | Too vague to be useful to any real team |

---

## 2. Idea Evolution

### Enhanced Concept: SpectraAI

The enhanced vision added five differentiators to separate this from generic AI tools:

1. **Memory** — tracks requirement changes over time
2. **Conflict Detection** — flags contradictions in requirements
3. **Role-aware views** — different outputs for BA, Dev, QA, PM
4. **Effort Estimation** — story points + timeline auto-calculation
5. **Compliance Check** — GDPR, ISO, SOC2 flags built-in

**Target users:** All of the above — developers, BAs, non-technical founders, product managers

**Target industry:** Enterprise Software / SaaS Products

**Team mode:** Multiple roles contribute to the same project

### Why This Was Still Too Complex for a Prototype

| Feature | Complexity Added |
|---|---|
| All 5 differentiators | Scope explosion — undeliverable for course |
| Team mode + role-aware + memory | Needs auth, DB, session management |
| Compliance check (GDPR/ISO/SOC2) | Needs curated RAG knowledge base |
| Effort estimation without historical data | AI guesses = low trust output |

**Decision:** Simplify to MVP depth — demonstrate all concepts but scope each feature for prototype delivery.

---

## 3. Final Prototype Scope

### Name: ScopeCraft

### What It Does

ScopeCraft is a conversational multi-agent system that automates the transition from raw product ideas to structured development artifacts. It acts like a team of smart AI assistants that turns a simple app idea into a detailed plan for developers.

**The system:**
1. Chats with the user to ask specific, targeted questions about their app
2. Automatically checks answers for confusing mistakes or conflicting instructions
3. Writes clear, professional documents for both business owners and developers

### Outputs (Prototype Scope)

| Document | Audience | Content |
|---|---|---|
| BRD | Business Analysts | Problem statement, actors, functional requirements, constraints, scope |
| User Stories | Developers | Epics, stories in standard format, acceptance criteria, priority |

### Differentiators Kept (MVP Depth)

| Feature | Prototype Implementation |
|---|---|
| Conflict Detection | Scans all Q&A answers for contradictions, flags with explanation |
| Role-aware Views | BA tab (BRD) and Dev tab (User Stories) — role selector in UI |

### What Is Deferred

- Memory / versioning (future version)
- Effort estimation (future version)
- Compliance check (future version)
- HLD generation (future version)
- Real team collaboration (future version)

---

## 4. System Architecture

### Agent Pipeline

```
User Idea Input (free text)
        ↓
[Interview Agent]
  - Asks max 10 targeted questions
  - One question at a time (chat style)
  - Tracks internal completeness score (0-100%)
  - Triggers generation at 80%+ or 10 questions
        ↓
[Conflict Agent]
  - Scans all Q&A pairs for contradictions
  - Flags conflicts with plain-language explanation
  - Inserts warnings into generation context
        ↓
[Generator Agent]
  - Produces BRD (structured markdown)
  - Produces User Stories (structured markdown)
  - Both generated in single LLM call with role-split prompts
        ↓
[Role Filter — Streamlit UI]
  - Tab 1: BA View → BRD
  - Tab 2: Dev View → User Stories
  - On-screen markdown render
  - Copy button per section
```

### Module Responsibilities

| Module | File | Responsibility |
|---|---|---|
| Streamlit UI | `app.py` | Entry point, chat interface, tab rendering, role selector |
| Interview Agent | `agents/interview_agent.py` | Question generation, completeness scoring, chat management |
| Conflict Agent | `agents/conflict_agent.py` | Contradiction detection, flag generation |
| Generator Agent | `agents/generator_agent.py` | BRD + User Stories generation |
| State Manager | `utils/state_manager.py` | Session state, Q&A history, conversation tracking |

---

## 5. Tech Stack Decisions

| Component | Tool Chosen | Reason |
|---|---|---|
| Frontend | Streamlit | Fast to prototype, tab-based UI, zero infra, demo-ready |
| LLM | Groq API (Llama 3.3 70B) | Free tier, no credit card, 500+ tokens/sec, no rate limit for prototype |
| Agent Orchestration | LangChain | Free, pip install, industry standard, course-compatible |
| Session State | Streamlit session_state + Python dict | Zero DB needed for prototype |
| Environment Config | python-dotenv (.env file) | Secure API key management, git-excluded |
| Version Control | Git + GitHub | Full commit history, progress tracking from day one |

### Why Groq over OpenAI / Gemini

- OpenAI requires credit card even for free tier
- Gemini Flash is free but slower and less reliable for structured output
- Groq is genuinely free, fast, and uses Llama 3.3 70B — sufficient for all prototype needs

---

## 6. Project Description — Course Submission

> **ScopeCraft: Agentic Requirements Engineering Prototype for SaaS Products**
>
> ScopeCraft is a conversational multi-agent AI system that transforms raw product ideas into structured software development artifacts. A user describes their concept in natural language; an Interview Agent conducts a focused, bounded dialogue — asking up to 10 targeted clarifying questions to extract actors, goals, constraints, and scope. A Conflict Detection Agent then scans the gathered requirements for contradictions and flags them with explanations before document generation begins. Finally, a Generator Agent produces two role-filtered outputs: a structured Business Requirements Document for Business Analysts, and a prioritized User Story backlog for Development teams — both rendered as on-screen markdown. Built with Python, Streamlit, LangChain, and Groq's free LLM API, ScopeCraft demonstrates how agentic AI can replace the most error-prone and time-consuming phase of the SDLC — requirements gathering — making it directly applicable to SaaS startups, enterprise product teams, and digital transformation initiatives.

---

## 7. Environment Setup Guide

### Prerequisites Summary

| Tool | Version Confirmed | Status |
|---|---|---|
| Ubuntu Linux | — | ✅ Pre-installed |
| Python | 3.12.3 | ✅ Confirmed |
| pip | 24.0 | ✅ Confirmed |
| Git | 2.43.0 | ✅ Confirmed |
| VS Code | Latest | ✅ Pre-installed |
| GitHub Account | rohitmittel@gmail.com | ✅ Confirmed |
| Groq Account + API Key | console.groq.com | ✅ Confirmed |

---

### Step-by-Step Setup Log

#### STEP 1 — Verify Python Installation
```bash
python3 --version
```
**Result:** `Python 3.12.3` ✅

---

#### STEP 2 — Verify pip Installation
```bash
pip3 --version
```
**Result:** `pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)` ✅

---

#### STEP 3 — Verify Git Installation
```bash
sudo apt install git -y
git --version
```
**Result:** `git version 2.43.0` ✅
> Note: 2.43.0 is production-sufficient. No upgrade required.

---

#### STEP 4 — Configure Git Identity
```bash
git config --global user.name "ROHIT MITTEL"
git config --global user.email "rohitmittel@gmail.com"
git config --list
```
**Result:** Name and email confirmed in output ✅

---

#### STEP 5 — Create GitHub Repository
**Done manually on github.com:**
- Repository name: `ScopeCraft`
- Description: `Agentic Requirements Engineering Prototype`
- Visibility: Public
- README initialized: Yes

**Repository URL:** `https://github.com/RohitMi/ScopeCraft.git` ✅

---

#### STEP 6 — Clone Repository Locally
```bash
cd ~
git clone https://github.com/RohitMi/ScopeCraft.git
cd ScopeCraft
ls
```
**Result:** `README.md` visible in folder ✅

---

#### STEP 7 — Create Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```
**Result:** Terminal prompt changed to `(venv) ...` ✅

> **Important:** Always run `source venv/bin/activate` before working on the project in any new terminal session.

---

#### STEP 8 — Create .gitignore
```bash
cat > .gitignore << 'EOF'
venv/
.env
__pycache__/
*.pyc
.DS_Store
EOF
```
**Verify:**
```bash
cat .gitignore
```
**Result:** 5 lines printed ✅

> **Why this matters:** The `.env` file contains your Groq API key. This line ensures it is NEVER pushed to GitHub.

---

#### STEP 9 — Create Groq Account and API Key
**Done manually at console.groq.com:**
- Sign up using GitHub login (no credit card required)
- Navigate: API Keys → Create API Key
- Key name: `scopecraft`
- Key format: `gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Result:** API key secured ✅

---

#### STEP 10 — Create .env File
```bash
cat > .env << 'EOF'
GROQ_API_KEY=your_actual_key_here
EOF
```
**Verify (do not print contents):**
```bash
ls -la .env
```
**Result:** File created with correct permissions ✅

---

#### STEP 11 — Install Python Packages
```bash
pip install streamlit langchain langchain-groq python-dotenv
```
**Result:** All packages installed successfully ✅

**Packages installed:**
| Package | Purpose |
|---|---|
| streamlit | Web UI framework |
| langchain | Agent orchestration |
| langchain-groq | Groq LLM connector for LangChain |
| python-dotenv | Load API keys from .env file |

---

#### STEP 12 — Create Project Folder Structure
```bash
mkdir -p agents utils
touch app.py \
      agents/__init__.py \
      agents/interview_agent.py \
      agents/conflict_agent.py \
      agents/generator_agent.py \
      utils/__init__.py \
      utils/state_manager.py \
      requirements.txt
```
**Verify:**
```bash
find . -not -path './venv/*' -not -path './.git/*'
```
**Result:** All files and folders created ✅

---

#### STEP 13 — Freeze Requirements
```bash
pip freeze > requirements.txt
```
**Result:** requirements.txt populated with all dependencies ✅

> This file allows anyone to recreate the exact same environment using `pip install -r requirements.txt`

---

#### STEP 14 — First Git Push

**Issue encountered:** GitHub no longer accepts password authentication for git operations.

**Fix — Create Personal Access Token (PAT):**
1. GitHub → Profile → Settings → Developer Settings
2. Personal access tokens → Tokens (classic)
3. Generate new token (classic)
4. Scope: `repo` (full access)
5. Expiry: 90 days
6. Copy token: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Push with PAT:**
```bash
git add .
git commit -m "feat: initial project scaffold — ScopeCraft setup"
git push origin main
```
When prompted:
- Username: `RohitMi`
- Password: paste PAT token

**Result:** First commit pushed to GitHub successfully ✅

---

## 8. Project Folder Structure

```
ScopeCraft/
├── .env                          ← Groq API key (git-excluded)
├── .gitignore                    ← Excludes venv/, .env, __pycache__
├── README.md                     ← GitHub repo description
├── requirements.txt              ← All pip dependencies (frozen)
├── app.py                        ← Streamlit entry point + UI
├── agents/
│   ├── __init__.py
│   ├── interview_agent.py        ← Chat + completeness scoring
│   ├── conflict_agent.py         ← Contradiction detection + flagging
│   └── generator_agent.py        ← BRD + User Stories generation
└── utils/
    ├── __init__.py
    └── state_manager.py          ← Session state + Q&A history
```

---

## 9. Development Roadmap

### Build Order (Next Phase)

| Step | File | What Gets Built |
|---|---|---|
| 1 | `utils/state_manager.py` | Session state schema, Q&A storage, conversation history |
| 2 | `agents/interview_agent.py` | LLM-driven question generation, completeness scorer |
| 3 | `agents/conflict_agent.py` | Contradiction scanner, flag generator |
| 4 | `agents/generator_agent.py` | BRD generator, User Stories generator |
| 5 | `app.py` | Streamlit UI — chat interface, role tabs, output render |

### Git Commit Strategy

Each completed module = one commit with descriptive message:

```
feat: state_manager — session state schema and Q&A storage
feat: interview_agent — LLM question engine and completeness scorer
feat: conflict_agent — contradiction detection and flagging
feat: generator_agent — BRD and user stories generation
feat: app — streamlit UI with chat interface and role tabs
```

### Running the App (Once Built)

```bash
# Activate environment
source venv/bin/activate

# Run Streamlit
streamlit run app.py
```

App opens at: `http://localhost:8501`

---

*Document generated from project planning session — June 2026*
*GitHub: https://github.com/RohitMi/ScopeCraft*
