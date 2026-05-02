from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response


async def get_patient_conditions(
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
        "Condition",
        {"patient": patientId, "clinical-status": "active"}
    )

    if not bundle or not bundle.get("entry"):
        return create_text_response("No active conditions found for this patient.")

    conditions = []
    for entry in bundle["entry"]:
        resource = entry.get("resource", {})
        code = resource.get("code", {})
        name = code.get("text") or (code.get("coding") or [{}])[0].get("display", "Unknown")
        onset = resource.get("onsetDateTime", "Unknown date")
        if name:
            conditions.append(f"- {name} (since {onset})")

    if not conditions:
        return create_text_response("No active conditions found for this patient.")

    result = "Active conditions:\n" + "\n".join(conditions)
    return create_text_response(result)