<div align="center">

# ⚡ OmniPrice

### Autonomous Price Intelligence & Real-Time Retail Arbitrage Engine

[![Cluster Verified Live](https://img.shields.io/badge/Cluster-Verified_Live-10b981?style=for-the-badge&logo=statuspage&logoColor=white)](#)
[![Built by OnePersonAI](https://img.shields.io/badge/Powered%20By-OnePersonAI-FF5E14?style=for-the-badge)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](#)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Baileys_v6-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)](#)

**Real-time multi-store price intelligence, AI-powered product parsing,  
price forecasting, automated tracking, and WhatsApp alerts.**

<br>

**[Explore Capabilities](#-core-capabilities) • [Architecture](#-system-architecture) • [Flow](#-execution-flow) • [Quickstart](#-quickstart) • [API](#-api-endpoints)**

</div>

---

# 🧠 What is OmniPrice?

**OmniPrice** is an autonomous price intelligence platform designed to discover, compare, monitor, and analyze product prices across multiple Indian e-commerce marketplaces.

Instead of manually checking several stores, OmniPrice creates a unified **market intelligence layer** that can:

- Resolve product URLs
- Extract product information
- Compare prices across marketplaces
- Detect price differences
- Analyze historical price movement
- Predict potential price drops
- Monitor products continuously
- Notify users through WhatsApp
- Provide AI-assisted buy-or-wait insights

The system combines **FastAPI, Python, AI reasoning models, marketplace adapters, SQLite, Docker, Node.js, and WhatsApp automation** into a single autonomous pipeline.

---

# ⚡ Core Capabilities

| Capability | Description |
|---|---|
| 🛒 Multi-Store Intelligence | Compare prices across major Indian marketplaces |
| ⚡ Fast Marketplace Retrieval | Fast-path marketplace API/RPC integrations |
| 🤖 AI Product Parser | Extract product intelligence from difficult pages |
| 📈 Price Forecasting | Analyze historical movement and potential price drops |
| 🎯 Price Tracking | Continuously monitor user-defined thresholds |
| 📲 WhatsApp Radar | Send automated price alerts |
| 🧠 AI Copilot | Assist users with product and pricing decisions |
| 🛡️ Security Layer | SSRF protection, isolation and hardened containers |
| 🐳 Docker Deployment | Production-oriented containerized architecture |
| 💾 SQLite WAL | Reliable background tracking and dispatch state |

---

# 🗺️ OmniPrice Mind Map

```mermaid
mindmap
  root((⚡ OmniPrice))
    Price Intelligence
      Amazon
      Flipkart
      Myntra
      AJIO
      Tata CLiQ
      JioMart
      Nykaa

    AI Engine
      Product Parsing
      URL Resolution
      ReAct Reasoning
      LLM Models
        Groq
        Qwen
        OpenRouter

    Analytics
      Price Comparison
      Historical Floors
      Price Trajectory
      Drop Probability
      Sale Detection

    Automation
      Price Tracking
      Background Daemon
      Threshold Monitoring
      WhatsApp Alerts

    Backend
      FastAPI
      Python
      SQLite
      WAL Mode
      Async Workers

    Infrastructure
      Docker
      Nginx
      Network Isolation
      Non Root Containers

    Security
      SSRF Protection
      Rate Limiting
      Request Filtering
      Security Headers
      Container Isolation

    User Experience
      Web Interface
      AI Copilot
      Real Time Results
      Buy or Wait Intelligence
```

---

# 🏗️ System Architecture

```mermaid
flowchart TD

    U["👤 User"]

    U -->|"Product URL"| EDGE

    subgraph SECURITY["🛡️ Security Perimeter"]
        EDGE["🌐 Nginx Edge / WAF"]
        RL["🚦 Rate Limiting"]
        FILTER["🔍 Request Filtering"]
    end

    EDGE --> RL
    RL --> FILTER

    FILTER --> CORE

    subgraph CORE_SYSTEM["⚡ OmniPrice Core"]
        CORE["🚀 FastAPI Core"]

        RESOLVER["🔗 URL Resolver"]
        PARSER["📦 Product Parser"]
        ENGINE["🧠 AI Reasoning Engine"]
        COMPARE["⚖️ Price Comparison Engine"]
        FORECAST["📈 Price Forecast Engine"]
        TRACKER["🎯 Tracking Engine"]
        DB[("💾 SQLite WAL")]

        CORE --> RESOLVER
        RESOLVER --> PARSER
        PARSER --> ENGINE
        ENGINE --> COMPARE
        COMPARE --> FORECAST
        FORECAST --> TRACKER
        TRACKER <--> DB
    end

    RESOLVER --> STORES

    subgraph STORES["🛒 Marketplace Layer"]
        AMAZON["Amazon India"]
        FLIPKART["Flipkart"]
        MYNTRA["Myntra"]
        AJIO["AJIO"]
        TATACLIQ["Tata CLiQ"]
        JIOMART["JioMart"]
        NYKAA["Nykaa"]
    end

    STORES --> COMPARE

    TRACKER --> WA

    subgraph WHATSAPP["📲 Notification Layer"]
        WA["Node.js WhatsApp Gateway"]
        BAILEYS["Baileys"]
    end

    WA --> BAILEYS
    BAILEYS --> USERWA["📱 WhatsApp User"]

    ENGINE --> LLM["☁️ LLM Providers"]
    LLM --> GROQ["Groq / Qwen"]
    LLM --> OPENROUTER["OpenRouter"]
```

---

# 🔄 Execution Flow

```mermaid
flowchart LR

    A["👤 User<br/>Product URL"]

    --> B["🌐 Request"]

    --> C["🛡️ Security Layer"]

    --> D["🔗 URL Resolver"]

    --> E["📦 Product Extraction"]

    --> F["🛒 Marketplace Queries"]

    --> G["⚖️ Price Aggregation"]

    --> H["📈 Price Analysis"]

    --> I["🧠 AI Reasoning"]

    --> J["🎯 Buy / Wait Intelligence"]

    --> K["📊 Result"]

    --> L["📲 WhatsApp Alert"]

    K --> M["👤 User"]
    L --> M
```

---

# 🔬 Price Intelligence Pipeline

```mermaid
flowchart TD

    INPUT["🔗 Product URL"]

    INPUT --> NORMALIZE["Normalize URL"]

    NORMALIZE --> IDENTIFY["Identify Marketplace"]

    IDENTIFY --> EXTRACT["Extract Product Identity"]

    EXTRACT --> SEARCH["Search / Resolve Product"]

    SEARCH --> COLLECT["Collect Marketplace Prices"]

    COLLECT --> VALIDATE["Validate Price Data"]

    VALIDATE --> COMPARE["Compare Market Prices"]

    COMPARE --> HISTORY["Historical Price Analysis"]

    HISTORY --> TRAJECTORY["7-Day Price Trajectory"]

    TRAJECTORY --> PROBABILITY["Drop Probability"]

    PROBABILITY --> AI["AI Reasoning"]

    AI --> DECISION["Buy / Wait Insight"]

    DECISION --> OUTPUT["⚡ OmniPrice Result"]
```

---

# 🛡️ Security Architecture

OmniPrice follows a **defense-in-depth architecture** where public traffic, application logic, and messaging infrastructure are isolated.

```mermaid
flowchart TD

    INTERNET["🌐 Public Internet"]

    INTERNET --> WAF["🛡️ Nginx Security Layer"]

    WAF --> CORE["⚡ OmniPrice Core"]

    CORE --> PRIVATE["🔒 Internal Network"]

    PRIVATE --> WA["📲 WhatsApp Gateway"]

    WA --> SESSION["🔐 Auth Session"]

    style WAF stroke-width:3px
    style CORE stroke-width:3px
    style WA stroke-width:3px
```

### Security Controls

#### 🛡️ Request Filtering

Suspicious requests can be filtered before reaching the application layer.

Examples include:

```text
/.env
/admin
/wp-login.php
SQL injection patterns
unexpected request signatures
```

#### 🔐 SSRF Protection

Target URLs are validated before outbound requests are made.

Protected destinations include:

```text
127.0.0.0/8
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
169.254.169.254
localhost
loopback interfaces
```

#### 👤 Least Privilege

The application container is designed to run without unnecessary root privileges.

```text
Application
     │
     ▼
Non-root User
     │
     ▼
Restricted Capabilities
```

#### 🔒 Network Isolation

The WhatsApp gateway is separated from direct public exposure.

```text
Internet
   │
   ▼
Nginx
   │
   ▼
OmniPrice Core
   │
   ▼
Internal Docker Network
   │
   ▼
WhatsApp Gateway
```

---

# 🧠 AI Architecture

```mermaid
flowchart TD

    PAGE["📄 Product Page"]

    PAGE --> PARSER["📦 Parser"]

    PARSER --> CLEAN["🧹 Data Normalization"]

    CLEAN --> CONTEXT["🧠 Product Context"]

    CONTEXT --> REACT["🔄 ReAct Reasoning"]

    REACT --> LLM["🤖 LLM"]

    LLM --> GROQ["Groq / Qwen"]

    LLM --> OPEN["OpenRouter"]

    GROQ --> RESULT["⚡ Structured Intelligence"]

    OPEN --> RESULT

    RESULT --> COPILOT["💬 AI Copilot"]
```

---

# 📲 24/7 WhatsApp Radar

OmniPrice can continuously monitor tracked products and dispatch notifications when configured conditions are reached.

```mermaid
flowchart LR

    PRODUCT["🛒 Tracked Product"]

    PRODUCT --> DB[("💾 SQLite WAL")]

    DB --> WORKER["⚙️ Background Worker"]

    WORKER --> CHECK["🔎 Check Current Price"]

    CHECK --> CONDITION{"🎯 Target Reached?"}

    CONDITION -->|"No"| WAIT["⏳ Continue Monitoring"]

    WAIT --> WORKER

    CONDITION -->|"Yes"| ALERT["🚨 Generate Alert"]

    ALERT --> NODE["Node.js Gateway"]

    NODE --> BAILEYS["Baileys"]

    BAILEYS --> PHONE["📱 WhatsApp"]
```

---

# 📊 Price Intelligence Model

OmniPrice combines several signals instead of relying only on the current price.

```text
Current Price
      │
      ├── Historical Floor
      │
      ├── Price Movement
      │
      ├── Marketplace Difference
      │
      ├── Sale / Event Signals
      │
      ├── Recent Drops
      │
      └── Target Threshold
              │
              ▼
       🧠 Price Intelligence
              │
              ▼
       Buy / Wait Insight
```

Potential event signals include:

```text
Big Billion Days
Great Indian Festival
End of Reason Sale
Flash Sales
Marketplace Promotions
```

---

# 🚀 Quickstart

## 1. Clone Repository

```bash
git clone https://github.com/AkshatRaj00/omniprice.git
cd omniprice
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Add the required API keys:

```env
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
WHATSAPP_GATEWAY=http://127.0.0.1:5001/send-message
```

---

# 🐳 Docker Deployment

```bash
docker compose up -d --build
```

Check running services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

Stop the cluster:

```bash
docker compose down
```

---

# 💻 Local Development

## Python Core

Create a virtual environment:

```bash
python -m venv venv
```

### Windows

```powershell
.\venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
python -m uvicorn main:app --reload --port 8000
```

---

# 📲 WhatsApp Gateway

```bash
cd whatsapp_gateway
npm install
npm start
```

Pair the gateway using the generated WhatsApp QR code.

---

# 📡 API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/compare` | Compare product prices across marketplaces |
| `POST` | `/api/track` | Start price tracking |
| `POST` | `/api/agent/chat` | Interact with the AI Copilot |
| `GET` | `/robots.txt` | Crawler instructions |
| `GET` | `/sitemap.xml` | Dynamic sitemap |

---

# 🔌 API Flow

```mermaid
sequenceDiagram

    participant U as 👤 User
    participant API as ⚡ FastAPI
    participant P as 📦 Parser
    participant M as 🛒 Marketplaces
    participant AI as 🧠 AI Engine
    participant DB as 💾 SQLite
    participant WA as 📲 WhatsApp

    U->>API: POST /api/compare
    API->>P: Resolve & Parse Product
    P->>M: Request Price Data
    M-->>P: Marketplace Prices
    P->>AI: Product Context
    AI-->>API: Price Intelligence
    API-->>U: Comparison Result

    U->>API: POST /api/track
    API->>DB: Save Tracking Rule
    API-->>U: Tracking Enabled

    DB->>API: Trigger Condition
    API->>WA: Send Alert
    WA-->>U: WhatsApp Notification
```

---

# 🗂️ Project Structure

```text
omniprice/
│
├── main.py
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── nginx/
│   └── nginx.conf
│
├── core/
│   ├── parser/
│   ├── marketplace/
│   ├── forecasting/
│   ├── tracking/
│   └── security/
│
├── whatsapp_gateway/
│   ├── package.json
│   ├── index.js
│   └── auth/
│
├── static/
├── templates/
│
├── README.md
├── CONTRIBUTING.md
└── SECURITY.md
```

---

# 🧩 Technology Stack

```text
                    ⚡ OmniPrice
                         │
        ┌────────────────┼────────────────┐
        │                │                │
     Backend           AI Layer       Automation
        │                │                │
     FastAPI           Groq            Node.js
     Python            Qwen            Baileys
     SQLite            OpenRouter      WhatsApp
        │
     Docker
        │
     Nginx
```

### Backend

- Python
- FastAPI
- SQLite
- Async processing

### AI

- Groq
- Qwen
- OpenRouter
- ReAct-style reasoning

### Automation

- Node.js
- Baileys
- Background workers
- WhatsApp notifications

### Infrastructure

- Docker
- Docker Compose
- Nginx
- Isolated networks

---

# 🔥 Why OmniPrice?

Traditional shopping requires:

```text
Search Store A
      ↓
Search Store B
      ↓
Search Store C
      ↓
Compare Prices
      ↓
Check History
      ↓
Wait for Discount
      ↓
Check Again
```

OmniPrice turns the workflow into:

```text
              🔗 Product URL
                    │
                    ▼
             ⚡ OmniPrice
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     Compare     Analyze      Monitor
        │           │           │
        └───────────┼───────────┘
                    ▼
              🧠 Intelligence
                    │
              ┌─────┴─────┐
              ▼           ▼
           Buy Now      Wait
              │           │
              └─────┬─────┘
                    ▼
              📲 Alert User
```

---

# 🎯 Project Vision

```mermaid
mindmap
  root((OmniPrice))
    Discover
      Find Products
      Resolve URLs
      Aggregate Stores

    Understand
      Product Identity
      Price History
      Market Differences

    Predict
      Price Movement
      Discount Windows
      Potential Drops

    Automate
      Continuous Tracking
      Threshold Alerts
      WhatsApp Dispatch

    Assist
      AI Copilot
      Buy-or-Wait Analysis
      Real-Time Intelligence
```

---

# 🤝 Contributing

Contributions are welcome.

```bash
git checkout -b feature/your-feature
```

Make your changes and run:

```bash
pip install ruff
ruff check .
```

Commit:

```bash
git add .
git commit -m "feat: add your feature"
```

Push:

```bash
git push origin feature/your-feature
```

Then open a Pull Request.

---

# 🔐 Security

If you discover a security vulnerability, please avoid publicly exposing sensitive details.

Review:

```text
SECURITY.md
```

before submitting a security report.

---

# 📄 License

OmniPrice is distributed under the **Apache License 2.0**.

Maintained by **OnePersonAI**.

---

<div align="center">

# ⚡ OmniPrice

### Price Intelligence. Automation. AI.

**Built by OnePersonAI**

</div>
