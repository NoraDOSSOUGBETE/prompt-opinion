from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response


async def get_patient_medications(
    patientId: Annotated[
        str | None,
        Field(description="The id of the patient. Optional if patient context already exists"),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)
        if not patientId:
            raise ValueError("No patient context found")

    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        raise ValueError("The fhir context could not be retrieved")

    fhir_client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    bundle = await fhir_client.search(
        "MedicationRequest",
        {"patient": patientId, "status": "active"}
    )

    if not bundle or not bundle.get("entry"):
        return create_text_response("No active medications found for this patient.")

    medications = []
    for entry in bundle["entry"]:
        resource = entry.get("resource", {})
        med = resource.get("medicationCodeableConcept", {})
        name = med.get("text") or (med.get("coding") or [{}])[0].get("display", "Unknown")
        dosage = resource.get("dosageInstruction", [{}])[0].get("text", "No dosage info")
        if name:
            medications.append(f"- {name}: {dosage}")

    if not medications:
        return create_text_response("No active medications found for this patient.")

    result = "Active medications:\n" + "\n".join(medications)
    return create_text_response(result)