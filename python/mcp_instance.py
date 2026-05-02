from mcp.server.fastmcp import FastMCP
from tools.patient_age_tool import get_patient_age
from tools.patient_allergies_tool import get_patient_allergies
from tools.patient_id_tool import find_patient_id
from tools.patient_medications_tool import get_patient_medications
from tools.patient_conditions_tool import get_patient_conditions
from tools.medication_reconciliation_tool import reconcile_medications

mcp = FastMCP("MedReconcile MCP", stateless_http=True, host="0.0.0.0")

_original_get_capabilities = mcp._mcp_server.get_capabilities

def _patched_get_capabilities(notification_options, experimental_capabilities):
    caps = _original_get_capabilities(notification_options, experimental_capabilities)
    caps.model_extra["extensions"] = {
        "ai.promptopinion/fhir-context": {
            "scopes": [
                {"name": "patient/Patient.rs", "required": True},
                {"name": "patient/MedicationRequest.rs"},
                {"name": "patient/Condition.rs"},
                {"name": "patient/AllergyIntolerance.rs"},
            ]
        }
    }
    return caps

mcp._mcp_server.get_capabilities = _patched_get_capabilities

# Outils existants
mcp.tool(name="FindPatientId", description="Finds a patient id given a first name and last name")(find_patient_id)
mcp.tool(name="GetPatientAge", description="Gets the age of a patient.")(get_patient_age)
mcp.tool(name="GetPatientAllergies", description="Gets the known allergies of a patient.")(get_patient_allergies)

# Nouveaux outils
mcp.tool(name="GetPatientMedications", description="Gets the active medications of a patient.")(get_patient_medications)
mcp.tool(name="GetPatientConditions", description="Gets the active medical conditions of a patient.")(get_patient_conditions)
mcp.tool(
    name="ReconcileMedications",
    description="Performs AI-powered medication reconciliation by cross-referencing medications, conditions and allergies to detect inconsistencies and critical alerts."
)(reconcile_medications)