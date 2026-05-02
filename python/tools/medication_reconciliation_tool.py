import os
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field
import httpx

from fhir_client import FhirClient
from fhir_context import FhirContext
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response
from tools.patient_medications_tool import get_patient_medications
from tools.patient_conditions_tool import get_patient_conditions
from tools.patient_allergies_tool import get_patient_allergies


OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


async def reconcile_medications(
    patientId: Annotated[
        str | None,
        Field(description="The id of the patient. Optional if patient context already exists"),
    ] = None,
    fhir_base_url: Annotated[
        str | None,
        Field(description="Optional FHIR server base URL override e.g. https://hapi.fhir.org/baseR4"),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)
        if not patientId:
            raise ValueError("No patient context found")

    # Récupère le contexte FHIR depuis les headers SHARP
    fhir_context = get_fhir_context(ctx)

    # Si une URL alternative est fournie, on l'utilise
    # Sinon on utilise celle de la plateforme
    if fhir_base_url:
        fhir_context = FhirContext(url=fhir_base_url, token=None)
    elif not fhir_context:
        raise ValueError("The fhir context could not be retrieved")

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)

    # 1. Récupère les 3 sources FHIR directement
    # Médicaments
    bundle = await fhir_client.search("MedicationRequest", {"patient": patientId, "status": "active"})
    if bundle and bundle.get("entry"):
        meds_list = []
        for entry in bundle["entry"]:
            resource = entry.get("resource", {})
            med = resource.get("medicationCodeableConcept", {})
            name = med.get("text") or (med.get("coding") or [{}])[0].get("display", "Unknown")
            dosage = resource.get("dosageInstruction", [{}])[0].get("text", "No dosage info")
            if name:
                meds_list.append(f"- {name}: {dosage}")
        medications = "Active medications:\n" + "\n".join(meds_list) if meds_list else "No active medications found."
    else:
        medications = "No active medications found."

    # Conditions
    bundle = await fhir_client.search("Condition", {"patient": patientId, "clinical-status": "active"})
    if bundle and bundle.get("entry"):
        cond_list = []
        for entry in bundle["entry"]:
            resource = entry.get("resource", {})
            code = resource.get("code", {})
            name = code.get("text") or (code.get("coding") or [{}])[0].get("display", "Unknown")
            if name:
                cond_list.append(f"- {name}")
        conditions = "Active conditions:\n" + "\n".join(cond_list) if cond_list else "No active conditions found."
    else:
        conditions = "No active conditions found."

    # Allergies
    bundle = await fhir_client.search("AllergyIntolerance", {"patient": patientId, "clinical-status": "active"})
    if bundle and bundle.get("entry"):
        allergy_list = []
        for entry in bundle["entry"]:
            resource = entry.get("resource", {})
            name = resource.get("code", {}).get("text", "Unknown")
            severity = resource.get("reaction", [{}])[0].get("severity", "unknown")
            allergy_list.append(f"- {name} (severity: {severity})")
        allergies = "Known allergies:\n" + "\n".join(allergy_list) if allergy_list else "No known allergies."
    else:
        allergies = "No known allergies."

    # 2. Construit le prompt pour le LLM
    prompt = f"""You are a clinical pharmacist assistant performing medication reconciliation.

PATIENT DATA:
{medications}

{conditions}

{allergies}

TASK:
Analyze the above patient data and produce a structured medication reconciliation report.

Your report must include:
1. CONSISTENT MEDICATIONS: Medications that appear appropriate given the conditions
2. INCONSISTENCIES: Medications that seem mismatched with conditions (e.g. wrong drug class)
3. CRITICAL ALERTS: Any medication prescribed despite a known allergy or dangerous interaction
4. RECOMMENDATIONS: Specific actions for the clinical team to verify or correct

Be concise, clinical, and actionable. Flag any allergy-medication conflicts as CRITICAL.
If no issues are found, say so clearly.
"""

    # 3. Appelle Ollama pour le raisonnement (local, gratuit, pas de quota)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            report = data["response"]
    except Exception as e:
        report = f"AI analysis unavailable: {str(e)}\nRaw data collected successfully from FHIR."

    final_report = f"""MEDICATION RECONCILIATION REPORT
Generated automatically by MedReconcile MCP
{'='*50}

{medications}

{conditions}

{allergies}

{'='*50}
AI ANALYSIS (llama3.2):
{report}

{'='*50}
This report must be validated by a qualified clinician before any prescription change.
"""

    return create_text_response(final_report)