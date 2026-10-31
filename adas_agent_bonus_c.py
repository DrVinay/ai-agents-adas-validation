import asyncio
import hashlib
import json
import threading
import uuid

from pathlib import Path
from typing import Literal


from pydantic import BaseModel, Field


from agents import (
    Agent,
    RunConfig,
    Runner,
    RunContextWrapper,
    RunState,
    ToolExecutionConfig,
    ToolGuardrailFunctionOutput,
    flush_traces,
    trace,
)

from agents.decorators import (
    tool,
    tool_input_guardrail,
)

from agents.tracing import custom_span


# ============================================================
# TERMINAL OUTPUT
# ============================================================

PRINT_LOCK = threading.Lock()


def print_block(
    title,
    arguments=None,
    observation=None
):

    with PRINT_LOCK:

        print(
            f"\n========== {title} =========="
        )

        if arguments is not None:

            print(
                "Arguments:",
                arguments
            )

        if observation is not None:

            print(
                "Observation:",
                observation
            )


# ============================================================
# SIMULATED HIL ENVIRONMENT
# ============================================================

REGRESSION_SUMMARY = {

    "run_id":
        "HIL_NIGHTLY_2026_10_26",

    "build":
        "4821",

    "total_tests":
        500,

    "passed_tests":
        463,

    "failed_tests":
        37,

    "duration_minutes":
        142,

    "status":
        "COMPLETED"
}


FAILURE_GROUPS = {

    "G1": {

        "subsystem":
            "ECU flashing",

        "failure_count":
            30,

        "symptom":
            "UDS programming session timeout after ECU reboot",

        "example_tests": [
            "HIL_FLASH_014",
            "HIL_FLASH_027",
            "HIL_FLASH_031"
        ]
    },


    "G2": {

        "subsystem":
            "Camera synchronization",

        "failure_count":
            5,

        "symptom":
            "Camera timestamp synchronization error",

        "example_tests": [
            "CAM_SYNC_007",
            "CAM_SYNC_011"
        ]
    },


    "G3": {

        "subsystem":
            "Perception",

        "failure_count":
            2,

        "symptom":
            "AEB scenario perception confidence mismatch",

        "example_tests": [
            "AEB_SCN_044",
            "AEB_SCN_052"
        ]
    }
}


FAILURE_LOGS = {

    "G1": {

        "evidence_id":
            "E_LOG_FLASH",

        "observation":
            "30 failures occur approximately 10 seconds "
            "after ECU reset. The flashing harness aborts "
            "after 10 seconds, while ECU boot-ready is "
            "observed at approximately 13.8 seconds."
    },


    "G2": {

        "evidence_id":
            "E_LOG_CAMERA",

        "observation":
            "Camera PTP offset reached 45 ms. "
            "Four of five tests passed when rerun."
    },


    "G3": {

        "evidence_id":
            "E_LOG_PERCEPTION",

        "observation":
            "Two isolated perception-confidence mismatches "
            "occurred close to the configured decision threshold."
    }
}


BUILD_CHANGES = {

    "4821": {

        "evidence_id":
            "E_BUILD_4821",

        "changes": [

            "New bootloader integrity/security check introduced.",

            "Measured ECU boot-ready time increased from "
            "approximately 7.1 s to 13.8 s.",

            "HIL flashing harness timeout remains configured "
            "at 10 s."
        ]
    }
}


KNOWN_ISSUES = [

    {

        "issue_id":
            "KI-204",

        "evidence_id":
            "E_KNOWN_204",

        "title":
            "Programming-session timeout after ECU reboot",

        "description":
            "A flashing timeout can occur when ECU boot-ready "
            "time exceeds the HIL harness timeout. "
            "Reported on build 4821.",

        "status":
            "OPEN"
    },


    {

        "issue_id":
            "KI-188",

        "evidence_id":
            "E_KNOWN_188",

        "title":
            "Intermittent camera PTP synchronization",

        "description":
            "Occasional timestamp offset during bench startup.",

        "status":
            "MONITORING"
    }
]


# ============================================================
# APPLICATION CONTEXT
# ============================================================

RUNTIME_CONTEXT = {

    "observed_evidence": {},

    "metrics": {},

    "hil_config": {

        "flashing_timeout_seconds":
            10,

        "config_version":
            1
    },

    "configuration_changed":
        False,

    "full_regression_completed":
        False
}


# ============================================================
# TRUSTED VERIFICATION REGISTRY
#
# IMPORTANT:
#
# The Manager Agent cannot directly modify this.
#
# Only trusted Python code processing the actual Verifier
# Agent result writes here.
#
# In production this would normally live in a durable
# database / workflow state store.
# ============================================================

VERIFIER_STATE = {

    "approved":
        False,

    "verification_id":
        None,

    "score":
        0.0,

    "candidate_fingerprint":
        None,

    "issues":
        []
}


# ============================================================
# CONTEXT HELPERS
# ============================================================

def store_evidence(
    wrapper,
    source_tool,
    result
):

    context = wrapper.context


    if isinstance(
        result,
        dict
    ):

        evidence_id = result.get(
            "evidence_id"
        )


        if evidence_id:

            context[
                "observed_evidence"
            ][evidence_id] = {

                "source_tool":
                    source_tool,

                "data":
                    result
            }


    elif isinstance(
        result,
        list
    ):

        for item in result:

            if not isinstance(
                item,
                dict
            ):

                continue


            evidence_id = item.get(
                "evidence_id"
            )


            if evidence_id:

                context[
                    "observed_evidence"
                ][evidence_id] = {

                    "source_tool":
                        source_tool,

                    "data":
                        item
                }


def store_metric(
    wrapper,
    metric_key,
    percentage
):

    wrapper.context[
        "metrics"
    ][metric_key] = percentage


# ============================================================
# INVESTIGATION TOOLS
# ============================================================

@tool
def record_plan(
    steps: list[str],
    success_criteria: list[str]
) -> dict:

    """
    Record a concise observable investigation plan.

    Args:
        steps:
            Planned engineering actions.

        success_criteria:
            Conditions required for success.
    """

    result = {

        "plan_recorded":
            True,

        "steps":
            steps,

        "success_criteria":
            success_criteria
    }


    print_block(
        "MANAGER TOOL: record_plan",
        {
            "steps":
                steps,

            "success_criteria":
                success_criteria
        },
        result
    )


    return result


@tool
def get_latest_regression_summary() -> dict:

    """
    Return the latest completed HIL regression summary.
    """

    result = REGRESSION_SUMMARY


    print_block(
        "MANAGER TOOL: get_latest_regression_summary",
        {},
        result
    )


    return result


@tool
def get_failure_groups() -> dict:

    """
    Return grouped failures from the latest HIL regression.
    """

    result = FAILURE_GROUPS


    print_block(
        "MANAGER TOOL: get_failure_groups",
        {},
        result
    )


    return result


@tool
def get_failure_log(
    wrapper: RunContextWrapper[dict],
    group_id: str
) -> dict:

    """
    Return detailed evidence for a failure group.

    Args:
        group_id:
            G1, G2 or G3.
    """

    if group_id not in FAILURE_LOGS:

        result = {

            "error":
                f"Unknown failure group {group_id}"
        }

    else:

        result = FAILURE_LOGS[
            group_id
        ]


    store_evidence(
        wrapper,
        "get_failure_log",
        result
    )


    print_block(
        "MANAGER TOOL: get_failure_log",
        {
            "group_id":
                group_id
        },
        result
    )


    return result


@tool
def get_build_changes(
    wrapper: RunContextWrapper[dict],
    build: str
) -> dict:

    """
    Return engineering changes associated with a build.

    Args:
        build:
            Software build identifier.
    """

    if build not in BUILD_CHANGES:

        result = {

            "error":
                f"No build information for {build}"
        }

    else:

        result = BUILD_CHANGES[
            build
        ]


    store_evidence(
        wrapper,
        "get_build_changes",
        result
    )


    print_block(
        "MANAGER TOOL: get_build_changes",
        {
            "build":
                build
        },
        result
    )


    return result


@tool
def search_known_issues(
    wrapper: RunContextWrapper[dict],
    keyword: str
) -> list[dict]:

    """
    Search known engineering issues.

    Args:
        keyword:
            Engineering symptom/search phrase.
    """

    words = [

        word

        for word in keyword.lower().split()

        if len(word) > 3
    ]


    matches = []


    for issue in KNOWN_ISSUES:

        searchable_text = (

            issue["title"]
            + " "
            + issue["description"]

        ).lower()


        if any(

            word in searchable_text

            for word in words

        ):

            matches.append(issue)


    store_evidence(
        wrapper,
        "search_known_issues",
        matches
    )


    print_block(
        "MANAGER TOOL: search_known_issues",
        {
            "keyword":
                keyword
        },
        matches
    )


    return matches


@tool
def calculate_percentage(
    wrapper: RunContextWrapper[dict],
    part: float,
    total: float,
    metric_key: Literal[
        "overall_failure_rate",
        "dominant_failure_share",
        "post_change_failure_rate"
    ],
    metric_name: str
) -> dict:

    """
    Calculate and record an engineering percentage.

    Args:
        part:
            Numerator.

        total:
            Denominator.

        metric_key:
            Stable machine-readable metric identifier.

        metric_name:
            Human-readable metric description.
    """

    if total == 0:

        result = {

            "error":
                "Total cannot be zero."
        }


    else:

        percentage = round(
            (part / total) * 100,
            2
        )


        result = {

            "part":
                part,

            "total":
                total,

            "percentage":
                percentage,

            "metric_key":
                metric_key,

            "metric":
                metric_name
        }


        store_metric(
            wrapper,
            metric_key,
            percentage
        )


    print_block(
        "MANAGER TOOL: calculate_percentage",
        {
            "part":
                part,

            "total":
                total,

            "metric_key":
                metric_key,

            "metric_name":
                metric_name
        },
        result
    )


    return result


# ============================================================
# TARGETED VALIDATION
# ============================================================

@tool
def run_targeted_validation(
    wrapper: RunContextWrapper[dict],
    group_id: str,
    timeout_seconds: float
) -> dict:

    """
    Run a targeted validation experiment of the flashing
    timeout mechanism.

    Args:
        group_id:
            Failure group.

        timeout_seconds:
            Experimental flashing timeout.
    """

    if group_id != "G1":

        result = {

            "error":
                "Targeted timeout validation is only "
                "configured for G1."
        }


    elif timeout_seconds <= 13.8:

        result = {

            "evidence_id":
                "E_RERUN_FLASH_TIMEOUT_FAIL",

            "group_id":
                group_id,

            "timeout_seconds":
                timeout_seconds,

            "tests_rerun":
                30,

            "passed":
                0,

            "failed":
                30,

            "result":
                "FAIL",

            "observation":
                "The experimental timeout remains below "
                "the observed ECU boot-ready time."
        }


    else:

        result = {

            "evidence_id":
                "E_RERUN_FLASH_EXTENDED_TIMEOUT",

            "group_id":
                group_id,

            "timeout_seconds":
                timeout_seconds,

            "tests_rerun":
                30,

            "passed":
                30,

            "failed":
                0,

            "result":
                "PASS",

            "observation":
                "All 30 flashing tests passed when "
                "the timeout exceeded ECU boot-ready time."
        }


    store_evidence(
        wrapper,
        "run_targeted_validation",
        result
    )


    print_block(
        "MANAGER TOOL: run_targeted_validation",
        {
            "group_id":
                group_id,

            "timeout_seconds":
                timeout_seconds
        },
        result
    )


    return result


# ============================================================
# READ HIL CONFIGURATION
# ============================================================

@tool
def get_hil_config(
    wrapper: RunContextWrapper[dict]
) -> dict:

    """
    Read the current HIL configuration.
    """

    config = wrapper.context[
        "hil_config"
    ]


    result = {

        "evidence_id":
            "E_CONFIG_CURRENT",

        "flashing_timeout_seconds":
            config[
                "flashing_timeout_seconds"
            ],

        "config_version":
            config[
                "config_version"
            ]
    }


    store_evidence(
        wrapper,
        "get_hil_config",
        result
    )


    print_block(
        "MANAGER TOOL: get_hil_config",
        {},
        result
    )


    return result


# ============================================================
# VERIFIER INPUT / OUTPUT MODELS
# ============================================================

class VerificationRequest(
    BaseModel
):

    root_cause: str

    confidence: float = Field(
        ge=0,
        le=1
    )

    failure_rate_percent: float

    dominant_failure_share_percent: float

    evidence_ids: list[str]

    evidence_summary: str

    recommended_action: str


class VerificationResult(
    BaseModel
):

    approved: bool

    score: float = Field(
        ge=0,
        le=1
    )

    issues: list[str]

    required_actions: list[str]

    feedback: str


# ============================================================
# INDEPENDENT VERIFIER AGENT
#
# It has no ability to modify HIL configuration.
#
# Its only responsibility is technical review.
# ============================================================

VERIFIER_INSTRUCTIONS = """
You are an independent ADAS HIL validation reviewer.

You are NOT the Manager Agent.

Your job is to independently assess whether the proposed
engineering conclusion is sufficiently supported before any
system modification is authorized.

Evaluate:

1. Are the requested percentages mathematically consistent?

Expected baseline values for this scenario are:

- 37 failed / 500 total = 7.4%
- 30 dominant flashing failures / 37 total failures = 81.08%

2. Is the dominant mechanism supported by evidence?

3. Does experimental evidence exist showing that a timeout
   above approximately 13.8 seconds resolves all 30 dominant
   flashing failures?

4. Does the candidate avoid claiming that the new bootloader
   security/integrity check caused the latency increase unless
   direct isolating evidence exists?

5. Are residual camera and perception failures treated as
   separate mechanisms?

6. Does the recommended action follow from the evidence?

APPROVAL POLICY

Approval requires:

- correct metrics
- E_LOG_FLASH evidence
- E_RERUN_FLASH_EXTENDED_TIMEOUT evidence
- experimentally successful targeted validation
- evidence-bounded causal wording
- a reasonable timeout remediation

A complete full regression is NOT required before approving
the proposed configuration remediation.

Do not invent evidence.

Return only VerificationResult.
"""


verifier_agent = Agent(

    name=
        "Independent ADAS Verification Agent",

    model=
        "gpt-5.6",

    instructions=
        VERIFIER_INSTRUCTIONS,

    output_type=
        VerificationResult
)


# ============================================================
# TRUSTED VERIFIER OUTPUT PROCESSOR
#
# This is application code, not Manager reasoning.
#
# It:
#
# 1. reads the real Verifier Agent output
# 2. registers the decision
# 3. generates an approval ID if approved
# 4. returns the judgment to the Manager
# ============================================================

async def extract_verifier_output(
    run_result
) -> str:

    verdict = run_result.final_output


    if not isinstance(
        verdict,
        VerificationResult
    ):

        VERIFIER_STATE[
            "approved"
        ] = False

        VERIFIER_STATE[
            "verification_id"
        ] = None


        return json.dumps({

            "approved":
                False,

            "score":
                0,

            "issues": [
                "Verifier did not return the expected "
                "structured result."
            ],

            "required_actions": [
                "Repeat independent verification."
            ],

            "feedback":
                "Invalid verifier output.",

            "verification_id":
                None
        })


    # --------------------------------------------------------
    # FINGERPRINT THE ACTUAL CANDIDATE SENT TO VERIFIER
    # --------------------------------------------------------

    invocation = (
        run_result.agent_tool_invocation
    )


    raw_arguments = (

        invocation.tool_arguments

        if invocation is not None

        else "{}"
    )


    fingerprint = hashlib.sha256(

        raw_arguments.encode(
            "utf-8"
        )

    ).hexdigest()[:16]


    verification_id = None


    if verdict.approved:

        verification_id = (

            "verify_"
            + uuid.uuid4().hex[:12]
        )


    VERIFIER_STATE.update({

        "approved":
            verdict.approved,

        "verification_id":
            verification_id,

        "score":
            verdict.score,

        "candidate_fingerprint":
            fingerprint,

        "issues":
            verdict.issues
    })


    with custom_span(

        "verifier_decision_registered",

        data={

            "approved":
                verdict.approved,

            "score":
                verdict.score,

            "candidate_fingerprint":
                fingerprint,

            "verification_id":
                verification_id
        }

    ):

        pass


    payload = {

        "approved":
            verdict.approved,

        "score":
            verdict.score,

        "issues":
            verdict.issues,

        "required_actions":
            verdict.required_actions,

        "feedback":
            verdict.feedback,

        "verification_id":
            verification_id,

        "candidate_fingerprint":
            fingerprint
    }


    print_block(
        "VERIFIER AGENT RESULT",
        None,
        payload
    )


    return json.dumps(
        payload
    )


# ============================================================
# VERIFIER EXPOSED AS AN AGENT TOOL
#
# Manager keeps control.
#
# This is not a handoff.
# ============================================================

verifier_tool = (
    verifier_agent.as_tool(

        tool_name=
            "request_independent_verification",

        tool_description=(
            "Send the proposed ADAS/HIL investigation "
            "conclusion to an independent Verifier Agent. "
            "This verification is mandatory before any "
            "configuration-changing action."
        ),

        parameters=
            VerificationRequest,

        include_input_schema=
            True,

        max_turns=
            4,

        custom_output_extractor=
            extract_verifier_output
    )
)


# ============================================================
# TIMEOUT CHANGE GUARDRAIL
#
# The Manager cannot simply say "verified".
#
# It must provide the real verification ID generated by
# trusted application code after the Verifier Agent approved.
# ============================================================

@tool_input_guardrail
def timeout_change_guardrail(
    data
):

    arguments = json.loads(
        data.context.tool_arguments
        or "{}"
    )


    context = (
        data.context.context
    )


    new_timeout = arguments.get(
        "new_timeout_seconds"
    )


    supplied_verification_id = (
        arguments.get(
            "verification_id"
        )
    )


    approval_state = (
        data.context.is_tool_approved(

            data.context.tool_name,

            data.context.tool_call_id
        )
    )


    phase = (

        "POST-APPROVAL RECHECK"

        if approval_state is True

        else "PRE-APPROVAL CHECK"
    )


    print_block(
        f"GUARDRAIL: CONFIG WRITE - {phase}",
        arguments,
        None
    )


    # --------------------------------------------------------
    # REQUIRE ACTUAL VERIFIER APPROVAL
    # --------------------------------------------------------

    if not VERIFIER_STATE[
        "approved"
    ]:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Configuration change blocked. "
                "The independent Verifier Agent has not "
                "approved the investigation."
            )
        )


    # --------------------------------------------------------
    # REQUIRE THE REAL VERIFICATION ID
    # --------------------------------------------------------

    if (
        supplied_verification_id
        != VERIFIER_STATE[
            "verification_id"
        ]
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Configuration change blocked. "
                "The supplied verification ID is invalid."
            )
        )


    # --------------------------------------------------------
    # REQUIRE CURRENT CONFIG READ
    # --------------------------------------------------------

    if (
        "E_CONFIG_CURRENT"
        not in context[
            "observed_evidence"
        ]
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Read the current HIL configuration first."
            )
        )


    # --------------------------------------------------------
    # REQUIRE SUCCESSFUL EXPERIMENT
    # --------------------------------------------------------

    rerun = context[
        "observed_evidence"
    ].get(
        "E_RERUN_FLASH_EXTENDED_TIMEOUT"
    )


    if rerun is None:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Successful targeted validation evidence "
                "is required."
            )
        )


    validated_timeout = (
        rerun[
            "data"
        ][
            "timeout_seconds"
        ]
    )


    # --------------------------------------------------------
    # ONLY APPLY THE TESTED VALUE
    # --------------------------------------------------------

    if (
        new_timeout
        != validated_timeout
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "The requested timeout does not match "
                "the experimentally validated value."
            )
        )


    # --------------------------------------------------------
    # ENGINEERING BOUNDS
    # --------------------------------------------------------

    if not (
        14
        <= new_timeout
        <= 30
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Timeout must remain between "
                "14 and 30 seconds."
            )
        )


    current_timeout = (

        context[
            "hil_config"
        ][
            "flashing_timeout_seconds"
        ]
    )


    if (
        new_timeout
        <= current_timeout
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "New timeout must exceed "
                "the current timeout."
            )
        )


    print(
        "Guardrail result: ALLOWED"
    )


    return (
        ToolGuardrailFunctionOutput.allow({

            "verification_id":
                supplied_verification_id,

            "validated_timeout":
                validated_timeout
        })
    )


# ============================================================
# SENSITIVE TOOL 1
# ============================================================

@tool(
    needs_approval=True,
    tool_input_guardrails=[
        timeout_change_guardrail
    ]
)
def apply_timeout_change(
    wrapper: RunContextWrapper[dict],
    new_timeout_seconds: float,
    verification_id: str,
    reason: str
) -> dict:

    """
    Apply a verified HIL flashing timeout change.

    This action requires:
    - Verifier Agent approval
    - application guardrail approval
    - human approval

    Args:
        new_timeout_seconds:
            New timeout.

        verification_id:
            Approval ID returned by the Verifier Agent tool.

        reason:
            Engineering justification.
    """

    config = wrapper.context[
        "hil_config"
    ]


    previous_timeout = (

        config[
            "flashing_timeout_seconds"
        ]
    )


    config[
        "flashing_timeout_seconds"
    ] = new_timeout_seconds


    config[
        "config_version"
    ] += 1


    wrapper.context[
        "configuration_changed"
    ] = True


    result = {

        "evidence_id":
            "E_CONFIG_TIMEOUT_APPLIED",

        "status":
            "CONFIGURATION_CHANGED",

        "previous_timeout_seconds":
            previous_timeout,

        "new_timeout_seconds":
            new_timeout_seconds,

        "config_version":
            config[
                "config_version"
            ],

        "verification_id":
            verification_id,

        "reason":
            reason
    }


    store_evidence(
        wrapper,
        "apply_timeout_change",
        result
    )


    print_block(
        "EXECUTED: apply_timeout_change",
        {
            "new_timeout_seconds":
                new_timeout_seconds,

            "verification_id":
                verification_id
        },
        result
    )


    return result


# ============================================================
# FULL REGRESSION GUARDRAIL
# ============================================================

@tool_input_guardrail
def full_regression_guardrail(
    data
):

    arguments = json.loads(
        data.context.tool_arguments
        or "{}"
    )


    context = (
        data.context.context
    )


    approval_state = (
        data.context.is_tool_approved(

            data.context.tool_name,

            data.context.tool_call_id
        )
    )


    phase = (

        "POST-APPROVAL RECHECK"

        if approval_state is True

        else "PRE-APPROVAL CHECK"
    )


    print_block(
        f"GUARDRAIL: FULL REGRESSION - {phase}",
        arguments,
        None
    )


    if not VERIFIER_STATE[
        "approved"
    ]:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Full regression blocked because "
                "independent verification is not approved."
            )
        )


    if not context[
        "configuration_changed"
    ]:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "No approved configuration change "
                "has been applied."
            )
        )


    if (
        "E_CONFIG_TIMEOUT_APPLIED"
        not in context[
            "observed_evidence"
        ]
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Configuration-change evidence is missing."
            )
        )


    timeout = (

        context[
            "hil_config"
        ][
            "flashing_timeout_seconds"
        ]
    )


    if timeout <= 13.8:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Applied timeout is not above "
                "ECU boot-ready time."
            )
        )


    if context[
        "full_regression_completed"
    ]:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "A post-change regression "
                "has already completed."
            )
        )


    print(
        "Guardrail result: ALLOWED"
    )


    return (
        ToolGuardrailFunctionOutput.allow({

            "active_timeout":
                timeout,

            "verification_score":
                VERIFIER_STATE[
                    "score"
                ]
        })
    )


# ============================================================
# SENSITIVE TOOL 2
# ============================================================

@tool(
    needs_approval=True,
    tool_input_guardrails=[
        full_regression_guardrail
    ]
)
def trigger_full_regression(
    wrapper: RunContextWrapper[dict],
    reason: str
) -> dict:

    """
    Run a complete post-change HIL regression.

    This consumes engineering resources and requires
    human approval.

    Args:
        reason:
            Engineering reason for the full regression.
    """

    timeout = (

        wrapper.context[
            "hil_config"
        ][
            "flashing_timeout_seconds"
        ]
    )


    if timeout > 13.8:

        flashing_failures = 0

    else:

        flashing_failures = 30


    camera_failures = 5

    perception_failures = 2


    failed_tests = (

        flashing_failures
        + camera_failures
        + perception_failures
    )


    passed_tests = (
        500
        - failed_tests
    )


    wrapper.context[
        "full_regression_completed"
    ] = True


    result = {

        "evidence_id":
            "E_FULL_REGRESSION_POST_CHANGE",

        "run_id":
            "HIL_VALIDATION_AFTER_MULTI_AGENT_CHANGE",

        "build":
            "4821",

        "configuration": {

            "flashing_timeout_seconds":
                timeout,

            "config_version":
                wrapper.context[
                    "hil_config"
                ][
                    "config_version"
                ]
        },

        "total_tests":
            500,

        "passed_tests":
            passed_tests,

        "failed_tests":
            failed_tests,

        "failure_groups": {

            "ECU_flashing":
                flashing_failures,

            "Camera_synchronization":
                camera_failures,

            "Perception":
                perception_failures
        },

        "status":
            "COMPLETED",

        "reason":
            reason
    }


    store_evidence(
        wrapper,
        "trigger_full_regression",
        result
    )


    print_block(
        "EXECUTED: trigger_full_regression",
        {
            "reason":
                reason
        },
        result
    )


    return result


# ============================================================
# FINAL MANAGER OUTPUT
# ============================================================

class MultiAgentMissionResult(
    BaseModel
):

    mission_status: Literal[
        "COMPLETED",
        "STOPPED_BY_HUMAN",
        "VERIFICATION_REJECTED"
    ]

    verified_root_cause: str

    confidence: float = Field(
        ge=0,
        le=1
    )

    verifier_score: float = Field(
        ge=0,
        le=1
    )

    verification_id: (
        str | None
    )

    pre_change_failure_rate_percent: float

    post_change_failure_rate_percent: (
        float | None
    )

    post_change_failed_tests: (
        int | None
    )

    configuration_before_seconds: float

    configuration_after_seconds: (
        float | None
    )

    evidence_ids: list[str]

    summary: str


# ============================================================
# MANAGER AGENT
# ============================================================

MANAGER_INSTRUCTIONS = """
You are the Manager Agent for an ADAS HIL validation and
remediation workflow.

You own the overall mission.

You have engineering investigation tools, an independent
Verifier Agent exposed as a tool, and two sensitive actions.

PHASE 1 — INVESTIGATE

1. Begin with record_plan.

2. Retrieve regression summary and failure groups.

3. Calculate:
   - overall_failure_rate
   - dominant_failure_share

4. Inspect dominant and residual failure logs.

5. Inspect build changes and known issues.

6. Do not overstate causality.

The evidence supports the mechanism:

- harness timeout ≈ 10 seconds
- ECU boot-ready ≈ 13.8 seconds
- harness aborts before readiness

Do NOT claim that the bootloader security/integrity check
caused the latency increase unless evidence directly proves it.

PHASE 2 — EXPERIMENT

7. Run targeted validation with a reasonable timeout just above
   13.8 seconds.

8. Record whether all 30 dominant flashing tests pass.

PHASE 3 — INDEPENDENT VERIFICATION

9. Before ANY configuration-changing action, you MUST call:

   request_independent_verification

10. Send the Verifier Agent:

   - proposed root cause
   - confidence
   - calculated metrics
   - evidence IDs
   - concise evidence summary
   - recommended action

11. You may not claim verification yourself.

12. If the Verifier rejects the candidate:
    - address its required actions where possible
    - re-run verification
    - do not perform a sensitive action while rejected

13. Only an approved Verifier response containing a real
    verification_id may be used for configuration change.

PHASE 4 — GOVERNED ACTION

14. Read current HIL configuration.

15. If verification is approved and remediation is justified,
    call apply_timeout_change using the exact verification_id
    returned by the Verifier Agent.

16. That tool is additionally protected by:
    - application guardrail
    - human approval

17. Never bypass a guardrail.

18. If the human rejects a sensitive action:
    - respect the decision
    - do not repeat the same request
    - finish with STOPPED_BY_HUMAN

19. If the change executes successfully, request a complete
    regression using trigger_full_regression.

20. That regression requires a separate human approval.

PHASE 5 — OUTCOME

21. After full regression, calculate post_change_failure_rate.

22. Compare baseline and post-change results.

23. Return MultiAgentMissionResult.

Do not reveal private chain-of-thought.

Expose only observable plans, evidence, specialist verdicts,
guardrail decisions, approvals, actions and conclusions.
"""


GOAL = """
Investigate the latest HIL regression.

Determine and experimentally validate the dominant failure
mechanism.

Obtain independent technical verification from the Verifier
Agent before any remediation.

If independently verified:

1. inspect the current configuration
2. propose the experimentally validated timeout change
3. respect application guardrails
4. obtain explicit human approval
5. apply the change only if approved
6. obtain separate approval for a full regression
7. measure the post-change result
8. compare performance with baseline

Finish with a structured evidence-backed report.
"""


manager_agent = Agent[dict](

    name=
        "ADAS HIL Manager Agent",

    model=
        "gpt-5.6",

    instructions=
        MANAGER_INSTRUCTIONS,

    tools=[

        record_plan,

        get_latest_regression_summary,

        get_failure_groups,

        get_failure_log,

        get_build_changes,

        search_known_issues,

        calculate_percentage,

        run_targeted_validation,

        get_hil_config,

        verifier_tool,

        apply_timeout_change,

        trigger_full_regression
    ],

    output_type=
        MultiAgentMissionResult
)


# ============================================================
# RUN CONFIG
#
# Keeps both PRE and POST approval guardrail checks,
# just like our successful Bonus B.
#
# Compact tracing removes extra task/turn nesting while
# retaining agent, generation, function and guardrail spans.
# ============================================================

RUN_CONFIG = RunConfig(

    tool_execution=
        ToolExecutionConfig(

            max_function_tool_concurrency=
                1,

            pre_approval_tool_input_guardrails=
                True
        ),

    tracing={
        "include_task_and_turn_spans":
            False
    }
)


# ============================================================
# RUNSTATE
# ============================================================

STATE_PATH = Path(
    ".cache/bonus_c_hitl_state.json"
)


# ============================================================
# HUMAN REVIEW
# ============================================================

def prompt_human_approval(
    tool_name,
    arguments
):

    print(
        "\n"
        "============================================\n"
        " SDK HUMAN APPROVAL REQUIRED\n"
        "============================================"
    )


    print(
        "\nSensitive tool:",
        tool_name
    )


    print(
        "\nProposed arguments:"
    )


    try:

        parsed = json.loads(
            arguments
            or "{}"
        )


        print(
            json.dumps(
                parsed,
                indent=2
            )
        )


    except Exception:

        print(
            arguments
        )


    while True:

        decision = input(

            "\nType APPROVE or REJECT: "

        ).strip().upper()


        if decision == "APPROVE":

            return True


        if decision == "REJECT":

            return False


        print(
            "Please type APPROVE or REJECT."
        )


# ============================================================
# MAIN WORKFLOW
# ============================================================

async def main():

    global_trace_id = None


    print(
        "\n"
        "============================================\n"
        " BONUS C - MULTI-AGENT ADAS HIL SYSTEM\n"
        " MANAGER + VERIFIER + HITL + TRACING\n"
        "============================================"
    )


    run_group_id = (

        "adas_bonus_c_"
        + uuid.uuid4().hex[:10]
    )


    try:

        # ====================================================
        # HIGH-LEVEL WORKFLOW TRACE
        #
        # Manager run, nested Verifier Agent, guardrails,
        # approvals and resumed executions stay under one
        # logical workflow trace.
        # ====================================================

        with trace(

            "ADAS HIL Bonus C Multi-Agent Workflow",

            group_id=
                run_group_id,

            metadata={

                "project":
                    "AI Agent 5 Levels",

                "stage":
                    "5_bonus_c",

                "domain":
                    "ADAS_HIL",

                "architecture":
                    "manager_verifier_hitl"
            }

        ) as workflow_trace:

            global_trace_id = (
                workflow_trace.trace_id
            )


            print(
                "\nTrace ID:",
                global_trace_id
            )


            # ================================================
            # INITIAL MANAGER RUN
            # ================================================

            result = await Runner.run(

                manager_agent,

                GOAL,

                context=
                    RUNTIME_CONTEXT,

                max_turns=
                    25,

                run_config=
                    RUN_CONFIG
            )


            # ================================================
            # HITL PAUSE / RESUME LOOP
            # ================================================

            while result.interruptions:

                print(
                    "\n========== SDK RUN PAUSED =========="
                )


                print(
                    "Pending approvals:",
                    len(
                        result.interruptions
                    )
                )


                state = (
                    result.to_state()
                )


                STATE_PATH.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )


                STATE_PATH.write_text(

                    state.to_string(),

                    encoding="utf-8"
                )


                print(
                    "\nRunState saved to:",
                    STATE_PATH
                )


                # --------------------------------------------
                # Rehydrate the saved state
                # --------------------------------------------

                stored_state = json.loads(

                    STATE_PATH.read_text(
                        encoding="utf-8"
                    )
                )


                state = await RunState.from_json(

                    manager_agent,

                    stored_state
                )


                pending_interruptions = (
                    state.get_interruptions()
                )


                for interruption in pending_interruptions:

                    tool_name = (

                        getattr(
                            interruption,
                            "name",
                            None
                        )

                        or

                        getattr(
                            interruption,
                            "tool_name",
                            None
                        )

                        or

                        "unknown_tool"
                    )


                    arguments = getattr(

                        interruption,

                        "arguments",

                        None
                    )


                    approved = await asyncio.to_thread(

                        prompt_human_approval,

                        tool_name,

                        arguments
                    )


                    # ----------------------------------------
                    # Add human decision to trace
                    # ----------------------------------------

                    with custom_span(

                        "human_approval_decision",

                        data={

                            "tool":
                                tool_name,

                            "decision":
                                (
                                    "APPROVE"
                                    if approved
                                    else "REJECT"
                                )
                        }

                    ):

                        pass


                    if approved:

                        print(
                            "\nHuman decision: APPROVED"
                        )


                        state.approve(

                            interruption,

                            always_approve=
                                False
                        )


                    else:

                        print(
                            "\nHuman decision: REJECTED"
                        )


                        state.reject(

                            interruption,

                            always_reject=
                                False,

                            rejection_message=(

                                "The human reviewer rejected "
                                "this sensitive action. "
                                "Respect this decision. "
                                "Do not request the same action "
                                "again. Finish with "
                                "mission_status STOPPED_BY_HUMAN."
                            )
                        )


                print(
                    "\n========== SDK RUN RESUMING =========="
                )


                result = await Runner.run(

                    manager_agent,

                    state,

                    run_config=
                        RUN_CONFIG
                )


            # ================================================
            # FINAL OUTPUT
            # ================================================

            final = (
                result.final_output
            )


            print(
                "\n"
                "============================================\n"
                " BONUS C MULTI-AGENT MISSION COMPLETE\n"
                "============================================"
            )


            print(
                "\nMission status:",
                final.mission_status
            )


            print(
                "\nVerified root cause:",
                final.verified_root_cause
            )


            print(
                "\nConfidence:",
                final.confidence
            )


            print(
                "\nVerifier score:",
                final.verifier_score
            )


            print(
                "\nVerification ID:",
                final.verification_id
            )


            print(
                "\nPre-change failure rate:",
                final.pre_change_failure_rate_percent,
                "%"
            )


            print(
                "\nPost-change failure rate:",
                final.post_change_failure_rate_percent
            )


            print(
                "\nPost-change failed tests:",
                final.post_change_failed_tests
            )


            print(
                "\nConfiguration:"
            )


            print(
                " Before:",
                final.configuration_before_seconds,
                "s"
            )


            print(
                " After:",
                final.configuration_after_seconds,
                "s"
            )


            print(
                "\nEvidence:"
            )


            for evidence_id in final.evidence_ids:

                print(
                    " -",
                    evidence_id
                )


            print(
                "\nSummary:",
                final.summary
            )


            usage = (
                result.context_wrapper.usage
            )


            print(
                "\n========== SDK OBSERVABILITY =========="
            )


            print(
                "\nModel requests:",
                usage.requests
            )


            print(
                "Input tokens:",
                usage.input_tokens
            )


            print(
                "Output tokens:",
                usage.output_tokens
            )


            print(
                "Total tokens:",
                usage.total_tokens
            )


            print(
                "\nFinal active agent:",
                result.last_agent.name
            )


            print(
                "\nVerifier approved:",
                VERIFIER_STATE[
                    "approved"
                ]
            )


            print(
                "Verifier score:",
                VERIFIER_STATE[
                    "score"
                ]
            )


            print(
                "Verifier candidate fingerprint:",
                VERIFIER_STATE[
                    "candidate_fingerprint"
                ]
            )


            print(
                "\nTrace ID:",
                global_trace_id
            )


            print(
                "\nRunState snapshot:",
                STATE_PATH
            )


            print(
                "\n================== END =================="
            )


    finally:

        # ----------------------------------------------------
        # Force buffered trace data to be exported promptly.
        # Call AFTER the outer trace context has closed.
        # ----------------------------------------------------

        flush_traces()


        if global_trace_id:

            print(
                "\nTrace export flushed:",
                global_trace_id
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )