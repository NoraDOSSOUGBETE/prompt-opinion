# 🏥 MedReconcile MCP — AI-Powered Medication Reconciliation

> **Agents Assemble Hackathon 2026** — Built on [Prompt Opinion](https://promptopinion.ai)

[![MCP](https://img.shields.io/badge/Protocol-MCP-blue)](https://modelcontextprotocol.io)
[![FHIR](https://img.shields.io/badge/Standard-FHIR%20R4-green)](https://hl7.org/fhir/R4/)
[![SHARP](https://img.shields.io/badge/Extension-SHARP-orange)](https://app.promptopinion.ai/schemas/a2a/v1/fhir-context)
[![Python](https://img.shields.io/badge/Python-3.12-yellow)](https://python.org)

---

## 🎯 The Problem

Medication reconciliation is a **legally required process** in France (HAS 2018, Law 2025) that consists of reconstructing the complete and accurate list of a patient's medications at each care transition (admission, transfer, discharge).

**The numbers are alarming:**
- 56% of hospitalized patients have at least one medication error at admission
- 75% of errors are **omissions** (forgotten medications)
- 38% of these errors would have required medical intervention
- Manual reconciliation takes **20 to 45 minutes** per patient

**MedReconcile MCP reduces this to under 3 minutes** by automating data collection and AI-powered cross-referencing.

---

## 💡 The Solution

MedReconcile MCP is a **Model Context Protocol (MCP) server** that exposes 3 specialized healthcare tools. When invoked by any agent on the Prompt Opinion platform, it:

1. **Automatically retrieves** the patient's active medications, conditions, and allergies from a FHIR R4 server
2. **Cross-references** these 3 data sources using a local LLM (llama3.2 via Ollama)
3. **Generates a structured reconciliation report** with critical alerts, inconsistencies, and recommendations
4. **Reminds** the clinical team that validation by a qualified clinician is required

### Why AI is essential here

A classical rule-based system can display a medication list. But **detecting that Apixaban + Aspirin in a patient with Atrial Fibrillation and CKD Stage 3 represents a critical bleeding risk** requires contextual reasoning — only possible with a Large Language Model.

---

## 🛠️ Architecture

```
Clinical Agent (Prompt Opinion Launchpad)
              │
              │ SHARP Context (Patient ID + FHIR token)
              ▼
    ┌─────────────────────┐
    │   MedReconcile MCP  │  ← FastMCP + Python + FastAPI
    │                     │
    │  ┌───────────────┐  │
    │  │ GetMedications│  │──→ FHIR R4 MedicationRequest
    │  ├───────────────┤  │
    │  │ GetConditions │  │──→ FHIR R4 Condition
    │  ├───────────────┤  │
    │  │ GetAllergies  │  │──→ FHIR R4 AllergyIntolerance
    │  ├───────────────┤  │
    │  │  Reconcile    │  │──→ Ollama llama3.2 (local LLM)
    │  └───────────────┘  │
    └─────────────────────┘
              │
              ▼
    Structured Reconciliation Report
    (validated by clinician before use)
```

---

## 🔧 MCP Tools

| Tool | Description | FHIR Resource |
|------|-------------|---------------|
| `FindPatientId` | Find a patient ID by name | `Patient` |
| `GetPatientAge` | Get patient age | `Patient` |
| `GetPatientAllergies` | Get known allergies | `AllergyIntolerance` |
| `GetPatientMedications` | Get active medications | `MedicationRequest` |
| `GetPatientConditions` | Get active conditions | `Condition` |
| `ReconcileMedications` | **Full AI reconciliation** | All of the above |

---

## 📋 Sample Output

```
MEDICATION RECONCILIATION REPORT
Generated automatically by MedReconcile MCP
==================================================

Active medications:
- Apixaban 5mg BID: Twice daily
- Aspirin 81mg daily: Once daily
- Lisinopril: Once daily
- Atorvastatin: Once daily
- Metoprolol: Once daily

Active conditions:
- Atrial Fibrillation
- Hypertension
- Coronary Artery Disease
- Chronic Kidney Disease stage 3

Known allergies: No Known Drug Allergies

==================================================
AI ANALYSIS (llama3.2):

CRITICAL ALERTS:
⚠️ Apixaban + Aspirin 81mg: Concurrent use significantly 
increases bleeding risk. Verify necessity with prescriber.

INCONSISTENCIES:
- Dosage missing for Atorvastatin and Metoprolol

RECOMMENDATIONS:
1. Confirm aspirin indication given anticoagulation therapy
2. Verify and document missing dosages
3. Monitor renal function (CKD Stage 3) for dose adjustments

==================================================
This report must be validated by a qualified clinician 
before any prescription change.
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://astral.sh/uv) package manager
- [Ollama](https://ollama.ai) with `llama3.2` model
- [ngrok](https://ngrok.com) or [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) for tunnel
- A [Prompt Opinion](https://promptopinion.ai) account

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/po-community-mcp
cd po-community-mcp/python

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### Run locally

```bash
# Terminal 1 — Start Ollama
ollama serve

# Terminal 2 — Start MCP server
uvicorn main:app --reload

# Terminal 3 — Expose with ngrok
ngrok http 8000
```

### Connect to Prompt Opinion

1. Go to **Configuration > MCP Servers > + Add MCP Server**
2. Fill in:
   - **Friendly Name**: `MedReconcile MCP`
   - **Endpoint**: `https://YOUR_NGROK_URL/mcp`
   - **Transport Type**: `StreamableHTTP`
3. Enable **Prompt Opinion FHIR Context Extension**
4. Grant FHIR permissions: `Patient`, `MedicationRequest`, `Condition`, `AllergyIntolerance`
5. Save

### Test the tool

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "ReconcileMedications",
      "arguments": {
        "patientId": "131283452",
        "fhir_base_url": "https://hapi.fhir.org/baseR4"
      }
    }
  }'
```

---

## 📁 Project Structure

```
python/
├── main.py                          # FastAPI entrypoint
├── mcp_instance.py                  # MCP server + tool registration
├── fhir_client.py                   # FHIR HTTP client
├── fhir_context.py                  # SHARP context model
├── fhir_utilities.py                # SHARP header extraction
├── mcp_constants.py                 # SHARP header constants
├── mcp_utilities.py                 # Response helpers
├── requirements.txt                 # Dependencies
└── tools/
    ├── patient_id_tool.py           # FindPatientId
    ├── patient_age_tool.py          # GetPatientAge
    ├── patient_allergies_tool.py    # GetPatientAllergies
    ├── patient_medications_tool.py  # GetPatientMedications ✨
    ├── patient_conditions_tool.py   # GetPatientConditions ✨
    └── medication_reconciliation_tool.py  # ReconcileMedications ✨
```

*✨ = added for this hackathon*

---

## 🔐 FHIR Permissions (SHARP)

This MCP server declares the following FHIR scopes via the Prompt Opinion SHARP extension:

```json
{
  "ai.promptopinion/fhir-context": {
    "scopes": [
      { "name": "patient/Patient.rs", "required": true },
      { "name": "patient/MedicationRequest.rs" },
      { "name": "patient/Condition.rs" },
      { "name": "patient/AllergyIntolerance.rs" }
    ]
  }
}
```

---

## 📊 Impact

| Metric | Before | After |
|--------|--------|-------|
| Reconciliation time | 20–45 min | < 3 min |
| Data sources checked | Manual | Automatic (3 FHIR sources) |
| Critical alert detection | Human memory | AI-powered |
| Clinician validation | Required | Still required ✅ |

---

## ⚕️ Clinical Safety

This tool is designed as a **clinical decision support system**:
- It never makes autonomous prescription decisions
- Every report includes a mandatory validation reminder
- The clinician always has final authority
- Compatible with French regulatory framework (HAS 2018, Law June 2025)

---


## 📄 License

MIT License — See [LICENSE](LICENSE) for details.
