# IntelWeave

### Multi-Source OSINT Intelligence & Investigation Platform

Live Application: [intel-weave.vercel.app](https://intel-weave.vercel.app)

IntelWeave is a modular OSINT investigation platform that transforms a single identifier—such as a username, email, phone number, domain, IP address, MAC address, or cryptocurrency wallet—into a structured investigation containing correlated intelligence, relationships, evidence, timelines, and reports.

Instead of manually searching dozens of services and copying results between browser tabs, IntelWeave provides a unified investigation workspace where multiple OSINT sources can be executed, normalized, correlated, and visualized in one place.

> **IntelWeave is designed for legitimate investigative, defensive, fraud-analysis, and cybersecurity use using publicly accessible information.**

---

## Features

### Multi-Identifier OSINT

IntelWeave supports investigations starting from multiple types of identifiers:

* **Username**
* **Email address**
* **Phone number**
* **Domain**
* **IP address**
* **MAC/BSSID**
* **Bitcoin wallet**
* **Ethereum wallet**
* **Solana wallet**

Multiple identifiers can be combined within an investigation to uncover relationships between different pieces of information.

---

### Username OSINT

Username investigations search across a large collection of public platforms using a declarative connector architecture.

Supported platform categories include:

* Developer platforms
* Social media
* Professional networks
* Creative platforms
* Forums
* Gaming platforms
* Content platforms

Results include platform-specific information and direct profile URLs where available.

Failed or unavailable platforms are isolated so that one unavailable service does not prevent the rest of the investigation from completing.

---

### Email OSINT

Email investigations provide public and technical intelligence surrounding an address.

Current capabilities include:

* Email normalization and validation
* Domain extraction
* MX/mail-server analysis
* Mail-provider inference
* Disposable-email detection
* Public Gravatar profile lookup
* Public profile information and links when available
* Domain intelligence through existing domain connectors

IntelWeave does **not** attempt mailbox login, password verification, or private-account access.

---

### Phone OSINT

Phone investigations use number intelligence and available enrichment sources to determine information such as:

* Country
* Regional information
* Number validity
* Number formatting
* Carrier
* Line type
* Timezone
* VoIP/virtual-line indicators where supported
* Additional carrier/reputation intelligence where configured

Carrier and enrichment results are treated as inferred intelligence rather than guaranteed ownership information.

---

### Domain OSINT

Domain investigations can combine multiple sources including:

* WHOIS
* RDAP
* DNS
* Reverse DNS
* SSL/TLS certificate information
* Certificate transparency
* Historical/public web intelligence

The resulting domain information can be connected into the investigation graph.

---

### IP OSINT

IP investigations provide network and geographic intelligence including:

* IPv4/IPv6 validation
* Country
* Region
* City
* Timezone
* ASN
* ISP/organization
* IP geolocation estimate
* Reverse DNS / PTR hostname

IP geolocation is treated as an approximation and is **not** presented as the exact physical location of a person.

---

### MAC / Wi-Fi OSINT

MAC/BSSID investigations can provide publicly available hardware and wireless-network intelligence, including:

* Hardware vendor/manufacturer
* BSSID/Wi-Fi information
* SSID where available
* Wi-Fi location information
* Geographic coordinates where the external source provides them

Availability depends on the public data associated with the queried BSSID.

---

### Cryptocurrency OSINT

IntelWeave supports public blockchain investigations for multiple cryptocurrency networks.

Depending on the chain and available source data, investigations can provide:

* Wallet/address information
* Transaction history
* Incoming/outgoing transactions
* Transaction values
* Transaction timestamps
* Related addresses
* Blockchain-specific metadata

Supported blockchain connectors currently include:

* Bitcoin
* Ethereum
* Solana

Blockchain data is particularly useful for relationship and transaction-graph analysis because the underlying ledger is publicly observable.

---

## Investigation Graph

IntelWeave converts discovered relationships into an interactive graph.

The graph can connect entities such as:

```text
Username
   │
   ├── found_on → GitHub
   │
   ├── found_on → Reddit
   │
   └── found_on → YouTube
          │
          └── linked evidence

Email
   │
   ├── uses_domain → example.com
   │
   └── has_gravatar → Public Profile

IP
   │
   └── reverse_dns → hostname.example.com

Wallet
   │
   ├── transaction → Wallet B
   └── transaction → Wallet C
```

The graph is designed to make relationships and corroborating evidence easier to understand than a collection of disconnected lookup results.

---

## Evidence & Confidence

Connector responses are not passed directly to the interface.

IntelWeave uses a normalization pipeline:

```text
Identifier
    ↓
Connector Selection
    ↓
OSINT Source Execution
    ↓
Raw Connector Result
    ↓
Normalization
    ↓
Normalized Facts
    ↓
Correlation
    ↓
Confidence / Evidence
    ↓
Investigation Graph
    ↓
Profile / Timeline / Report
```

This provides a common representation for information originating from completely different sources.

Confidence scores help distinguish stronger technical observations from weaker inferred information.

---

## Investigation Timeline

IntelWeave can collect dated events discovered during an investigation and present them chronologically.

This makes it easier to understand:

* When information was observed
* When domains or certificates were active
* When relevant public events occurred
* How discovered evidence relates temporally

IntelWeave does not invent dates when a source does not provide them.

---

## PDF Investigation Reports

Completed investigations can be exported into structured PDF reports.

Reports can contain:

* Investigation summary
* Identifiers
* Discovered facts
* Confidence information
* Evidence
* Sources
* Relationships
* Graph information
* Timeline events

The goal is to turn an interactive investigation into a portable artifact suitable for review or case documentation.

---

## Modular Connector Architecture

One of IntelWeave's core design principles is that adding a new OSINT source should not require rewriting the application.

Connectors follow a common interface and are registered with the connector framework.

Conceptually:

```text
                 ┌── WHOIS
                 ├── RDAP
                 ├── DNS
Identifier ──────┼── Username Platforms
                 ├── Email OSINT
                 ├── Phone
                 ├── IP Intelligence
                 ├── MAC / Wi-Fi
                 └── Blockchain
                         │
                         ▼
                  Normalization
                         │
                         ▼
                    Correlation
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
            Graph     Timeline    Report
```

Each connector can fail independently. A timeout, unavailable API, or rate limit from one source should not invalidate the entire investigation.

---

## Architecture

IntelWeave follows a **modular monolith** architecture.

### Frontend

* React
* TypeScript
* Tailwind CSS
* Interactive graph visualization
* Deployed on Vercel: [intel-weave.vercel.app](https://intel-weave.vercel.app)

### Backend

* Python
* FastAPI
* Async connector execution
* Pydantic models
* Modular connector/normalizer architecture

### Databases

**PostgreSQL**

System of record for:

* Investigations
* Connector results
* Normalized facts
* Reports
* Application state

**Neo4j**

Graph/query layer for:

* Entities
* Relationships
* Investigation graphs

PostgreSQL remains the authoritative data store while Neo4j provides graph-oriented querying and visualization.

### Reporting

* ReportLab

### Deployment

IntelWeave is container-friendly and can be deployed with the backend, PostgreSQL, and Neo4j as separate services. Live frontend is hosted at [intel-weave.vercel.app](https://intel-weave.vercel.app).

---

## Authentication

IntelWeave includes authentication for investigator access.

The authentication flow includes:

* Sign up
* Login
* Email verification / OTP
* Password authentication
* Authenticated investigation access

Sensitive configuration such as API keys and credentials is provided through environment variables (`backend/.env`) rather than being hard-coded into the application.

---

## Getting Started

### Prerequisites

Install:

* Git
* Docker
* Docker Compose

For development without Docker, you will also need:

* Python 3.x
* Node.js
* npm

---

### Clone the repository

```bash
git clone https://github.com/JanavRana/OSINT.git
cd OSINT
```

---

### Environment configuration

Create the required environment files from the project's environment configuration.

Do **not** commit secrets.

Typical configuration includes:

```env
DATABASE_URL=...
NEO4J_URI=...
NEO4J_USERNAME=...
NEO4J_PASSWORD=...

JWT_SECRET_KEY=...

# Optional external OSINT provider credentials
ABSTRACT_IP_API_KEY=...
ABSTRACT_PHONE_API_KEY=...
WIGLE_API_NAME=...
WIGLE_API_TOKEN=...
TRUECALLER_RAPIDAPI_KEY=...
```

Only configure credentials for providers you intend to use.

---

### Run with Docker

```bash
docker compose up --build
```

The application services will start according to the project's Docker Compose configuration.

---

### Backend development

```bash
cd backend
pip install -r requirements.txt
```

Run the FastAPI application using the project's configured startup command.

---

### Frontend development

```bash
cd frontend
npm install
npm run dev
```

The frontend communicates with the FastAPI backend through the configured API provider.

---

## Testing

Backend tests can be executed with:

```bash
cd backend
python -m pytest tests/ -v
```

Frontend type checking:

```bash
cd frontend
npx tsc --noEmit
```

For production builds:

```bash
npm run build
```

External OSINT services should be mocked where appropriate in automated tests so that the test suite does not depend on third-party availability.

---

## Project Structure

A simplified view of the project:

```text
OSINT/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── connectors/
│   │   ├── normalizers/
│   │   ├── services/
│   │   ├── correlation/
│   │   ├── graph/
│   │   └── ...
│   │
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── docs/
│   ├── MASTER_DESIGN.md
│   └── planning/
│
├── docker-compose.yml
└── README.md
```

---

## Future Expansion

The architecture is designed to support future capabilities such as:

* AI Investigation Copilot
* Risk Dashboard
* Investigation Replay
* Reverse Image Search
* Continuous Monitoring
* Local-language matching
* Natural-language investigation queries
* Investigation workspaces
* Monitoring alerts

These are future extensions rather than requirements for the current implementation.
