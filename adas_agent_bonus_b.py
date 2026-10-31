import asyncio
import threading
import json

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
)

from agents.decorators import (
    tool,
    tool_input_guardrail,
)


# ============================================================
# TERMINAL PRINT LOCK
#
# Bonus A showed that independent SDK tools can execute
# concurrently and their terminal printouts may interleave.
#
# We also limit function-tool concurrency later, but the lock
# keeps each display block atomic.
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
# LOCAL APPLICATION CONTEXT
#
# IMPORTANT:
#
# This is NOT sent to the LLM.
#
# It is trusted application-side state shared between:
#
# - tools
# - guardrails
# - resumed runs
#
# We deliberately use a plain dict because it serializes cleanly
# inside RunState for our pause/resume demonstration.
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
# READ-ONLY INVESTIGATION TOOLS
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
            Investigation steps.

        success_criteria:
            Conditions defining successful completion.
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
        "SDK TOOL: record_plan",
        {
            "steps": steps,
            "success_criteria": success_criteria
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
        "SDK TOOL: get_latest_regression_summary",
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
        "SDK TOOL: get_failure_groups",
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
    Return detailed log evidence for a failure group.

    Args:
        group_id:
            Failure group such as G1, G2 or G3.
    """

    if group_id not in FAILURE_LOGS:

        result = {

            "error":
                f"Unknown failure group: {group_id}"
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
        "SDK TOOL: get_failure_log",
        {
            "group_id": group_id
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
            Build identifier.
    """

    if build not in BUILD_CHANGES:

        result = {

            "error":
                f"No build information found for {build}"
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
        "SDK TOOL: get_build_changes",
        {
            "build": build
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
            Symptom or engineering search phrase.
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
        "SDK TOOL: search_known_issues",
        {
            "keyword": keyword
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
    Calculate and record a named engineering percentage.

    Args:
        part:
            Numerator.

        total:
            Denominator.

        metric_key:
            Stable machine-readable metric identifier.

        metric_name:
            Human-readable metric name.
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
        "SDK TOOL: calculate_percentage",
        {
            "part": part,
            "total": total,
            "metric_key": metric_key,
            "metric_name": metric_name
        },
        result
    )


    return result


# ============================================================
# TARGETED VALIDATION
#
# Still read/test behavior — it does NOT modify production HIL
# configuration.
# ============================================================

@tool
def run_targeted_validation(
    wrapper: RunContextWrapper[dict],
    group_id: str,
    timeout_seconds: float
) -> dict:

    """
    Run a targeted validation experiment of the flashing
    timeout hypothesis.

    Args:
        group_id:
            Failure group to test.

        timeout_seconds:
            Experimental timeout.
    """

    if group_id != "G1":

        result = {

            "error":
                "Targeted timeout validation is configured "
                "only for G1."
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
                "The experimental timeout remains shorter "
                "than ECU boot-ready time."
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
                "All 30 flashing tests passed when the "
                "experimental timeout exceeded ECU "
                "boot-ready time."
        }


    store_evidence(
        wrapper,
        "run_targeted_validation",
        result
    )


    print_block(
        "SDK TOOL: run_targeted_validation",
        {
            "group_id": group_id,
            "timeout_seconds": timeout_seconds
        },
        result
    )


    return result


# ============================================================
# READ CURRENT HIL CONFIGURATION
# ============================================================

@tool
def get_hil_config(
    wrapper: RunContextWrapper[dict]
) -> dict:

    """
    Read the current HIL flashing configuration.
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
        "SDK TOOL: get_hil_config",
        {},
        result
    )


    return result


# ============================================================
# BONUS B:
# TOOL INPUT GUARDRAIL FOR CONFIGURATION CHANGE
# ============================================================

@tool_input_guardrail
def timeout_change_guardrail(data):

    arguments = json.loads(
        data.context.tool_arguments
        or "{}"
    )


    app_context = (
        data.context.context
    )


    new_timeout = arguments.get(
        "new_timeout_seconds"
    )


    observed_evidence = app_context[
        "observed_evidence"
    ]


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
        f"GUARDRAIL: TIMEOUT CHANGE - {phase}",
        arguments,
        None
    )


    # --------------------------------------------------------
    # REQUIRE CURRENT CONFIGURATION TO HAVE BEEN READ
    # --------------------------------------------------------

    if (
        "E_CONFIG_CURRENT"
        not in observed_evidence
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the configuration change. "
                "Read the current HIL configuration first."
            )
        )


    # --------------------------------------------------------
    # REQUIRE SUCCESSFUL TARGETED VALIDATION
    # --------------------------------------------------------

    rerun = observed_evidence.get(
        "E_RERUN_FLASH_EXTENDED_TIMEOUT"
    )


    if rerun is None:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the configuration change. "
                "Successful targeted validation evidence "
                "is required first."
            )
        )


    validated_timeout = (
        rerun["data"][
            "timeout_seconds"
        ]
    )


    # --------------------------------------------------------
    # ONLY ALLOW THE EXPERIMENTALLY VALIDATED VALUE
    # --------------------------------------------------------

    if (
        new_timeout
        != validated_timeout
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the configuration change. "
                f"The proposed timeout {new_timeout} s does not "
                f"match the experimentally validated timeout "
                f"{validated_timeout} s."
            )
        )


    # --------------------------------------------------------
    # ENGINEERING POLICY BOUNDS
    # --------------------------------------------------------

    if not (
        14
        <= new_timeout
        <= 30
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the configuration change. "
                "Approved engineering bounds are 14 to 30 seconds."
            )
        )


    current_timeout = (
        app_context[
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

                "Guardrail blocked the configuration change. "
                "The new timeout must exceed the current timeout."
            )
        )


    print(
        "Guardrail result: ALLOWED"
    )


    return (
        ToolGuardrailFunctionOutput.allow(

            output_info={

                "validated_timeout":
                    validated_timeout,

                "current_timeout":
                    current_timeout
            }
        )
    )


# ============================================================
# BONUS B:
# SENSITIVE CONFIGURATION-WRITE TOOL
#
# needs_approval=True tells the Agents SDK:
#
# DO NOT execute immediately.
# Pause the run and return an interruption.
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
    reason: str
) -> dict:

    """
    Change the HIL flashing timeout.

    This is a sensitive configuration write and always
    requires explicit human approval.

    Args:
        new_timeout_seconds:
            New flashing timeout.

        reason:
            Evidence-based engineering justification.
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

        "reason":
            reason
    }


    store_evidence(
        wrapper,
        "apply_timeout_change",
        result
    )


    print_block(
        "SDK TOOL EXECUTED: apply_timeout_change",
        {
            "new_timeout_seconds":
                new_timeout_seconds,

            "reason":
                reason
        },
        result
    )


    return result


# ============================================================
# BONUS B:
# GUARDRAIL FOR FULL REGRESSION
# ============================================================

@tool_input_guardrail
def full_regression_guardrail(data):

    arguments = json.loads(
        data.context.tool_arguments
        or "{}"
    )


    app_context = (
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


    # --------------------------------------------------------
    # REQUIRE CONFIGURATION CHANGE
    # --------------------------------------------------------

    if not app_context[
        "configuration_changed"
    ]:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the full regression. "
                "No approved configuration change has been applied."
            )
        )


    if (
        "E_CONFIG_TIMEOUT_APPLIED"
        not in app_context[
            "observed_evidence"
        ]
    ):

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the full regression. "
                "No configuration-change evidence exists."
            )
        )


    timeout = (
        app_context[
            "hil_config"
        ][
            "flashing_timeout_seconds"
        ]
    )


    if timeout <= 13.8:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked the full regression. "
                "The applied timeout is not above ECU boot-ready time."
            )
        )


    if app_context[
        "full_regression_completed"
    ]:

        return (
            ToolGuardrailFunctionOutput.reject_content(

                "Guardrail blocked a duplicate full regression. "
                "A post-change regression has already completed."
            )
        )


    print(
        "Guardrail result: ALLOWED"
    )


    return (
        ToolGuardrailFunctionOutput.allow(

            output_info={

                "active_timeout":
                    timeout
            }
        )
    )


# ============================================================
# BONUS B:
# SECOND SENSITIVE TOOL
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
    Trigger a complete 500-test HIL regression.

    This consumes engineering resources and always requires
    explicit human approval.

    Args:
        reason:
            Engineering reason for running the full regression.
    """

    timeout = (
        wrapper.context[
            "hil_config"
        ][
            "flashing_timeout_seconds"
        ]
    )


    # --------------------------------------------------------
    # SIMULATED POST-CHANGE BEHAVIOR
    # --------------------------------------------------------

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
            "HIL_VALIDATION_AFTER_SDK_CHANGE",

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
        "SDK TOOL EXECUTED: trigger_full_regression",
        {
            "reason": reason
        },
        result
    )


    return result


# ============================================================
# STRUCTURED FINAL OUTPUT
# ============================================================

class GovernedMissionResult(
    BaseModel
):

    mission_status: Literal[
        "COMPLETED",
        "STOPPED_BY_HUMAN"
    ]


    verified_root_cause: str


    confidence: float = Field(
        ge=0,
        le=1
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
# AGENT INSTRUCTIONS
# ============================================================

AGENT_INSTRUCTIONS = """
You are an autonomous but governed ADAS HIL validation
and remediation agent.

Your purpose is to investigate an engineering regression,
validate the dominant mechanism, and propose a justified
remediation.

You may NOT bypass application guardrails or human approval.

PHASE 1 — INVESTIGATION

1. Start with record_plan.

2. Retrieve the latest regression summary and failure groups.

3. Calculate:
   - overall_failure_rate
   - dominant_failure_share

4. Inspect detailed logs for the dominant and residual groups.

5. Inspect relevant build changes and known issues.

6. Do not overstate causality.

The experimentally supportable mechanism is:

- HIL flashing timeout approximately 10 seconds
- ECU boot-ready approximately 13.8 seconds
- the harness therefore aborts before the ECU becomes ready

The bootloader security/integrity check may be described as
concurrent with the latency increase, but not as its proven
cause unless direct isolating evidence exists.

PHASE 2 — TARGETED VALIDATION

7. Run a targeted validation experiment before requesting a
   configuration change.

8. Choose a reasonable timeout slightly above the observed
   13.8-second ECU boot-ready time.

9. Use the successful targeted experiment as the evidence basis
   for the proposed configuration change.

PHASE 3 — GOVERNED ACTION

10. Read the current HIL configuration.

11. If remediation is justified, call apply_timeout_change.

12. Do not assume the action will execute.

The SDK/application may:

- reject it through a guardrail
- pause for human approval
- return a human rejection
- execute it after approval

13. If a guardrail rejects the proposal, use the feedback and
    make a compliant proposal if appropriate.

14. If the human rejects a sensitive action:
    - respect the decision
    - do NOT request the same action again
    - return mission_status STOPPED_BY_HUMAN

15. If the timeout change executes successfully, call
    trigger_full_regression.

16. The full regression also requires human authorization.

17. If that approval is rejected, do not retry it.
    Return STOPPED_BY_HUMAN.

PHASE 4 — OUTCOME

18. After the full regression completes, calculate
    post_change_failure_rate.

19. Compare baseline versus post-change performance.

20. Return GovernedMissionResult.

Do not reveal private chain-of-thought.

Expose only plans, actions, evidence, policy decisions,
approvals and final conclusions.
"""


# ============================================================
# HIGH-LEVEL GOAL
# ============================================================

GOAL = """
Investigate the latest HIL regression.

Determine the dominant failure mechanism.

Experimentally validate the proposed remediation.

If supported:

1. inspect the current HIL configuration
2. propose a safe configuration change
3. respect application guardrails
4. obtain human approval before the configuration write
5. apply it only if approved
6. obtain separate human approval before a full regression
7. evaluate the full-regression outcome
8. compare pre-change and post-change failure rates

If a human rejects a sensitive action, respect the decision
and stop cleanly.
"""


# ============================================================
# CREATE GOVERNED SDK AGENT
# ============================================================

hil_agent = Agent[dict](

    name=
        "Governed ADAS HIL Agent",

    model=
        "gpt-5.6",

    instructions=
        AGENT_INSTRUCTIONS,

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

        apply_timeout_change,

        trigger_full_regression
    ],

    output_type=
        GovernedMissionResult
)


# ============================================================
# RUN CONFIGURATION
#
# Important production behavior:
#
# pre_approval_tool_input_guardrails=True
#
# means:
#
#    model proposes action
#             ↓
#       guardrail first
#             ↓
#        only if valid
#             ↓
#       human approval
#
# After approval the input guardrail runs AGAIN immediately
# before the tool executes.
#
# max_function_tool_concurrency=1 keeps the terminal demo
# easier to follow.
# ============================================================

RUN_CONFIG = RunConfig(

    tool_execution=
        ToolExecutionConfig(

            max_function_tool_concurrency=
                1,

            pre_approval_tool_input_guardrails=
                True
        )
)


# ============================================================
# DURABLE PAUSE/RESUME SNAPSHOT
# ============================================================

STATE_PATH = Path(
    ".cache/bonus_b_hitl_state.json"
)


# ============================================================
# HUMAN REVIEW FUNCTION
#
# The SDK itself pauses.
#
# This function only collects the human's decision.
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
# MAIN
# ============================================================

async def main():

    print(
        "\n"
        "============================================\n"
        " BONUS B - GOVERNED OPENAI AGENTS SDK\n"
        " GUARDRAILS + HITL + PAUSE / RESUME\n"
        "============================================"
    )


    # --------------------------------------------------------
    # INITIAL RUN
    # --------------------------------------------------------

    result = await Runner.run(

        hil_agent,

        GOAL,

        context=
            RUNTIME_CONTEXT,

        max_turns=
            20,

        run_config=
            RUN_CONFIG
    )


    # ========================================================
    # NATIVE HITL INTERRUPTION LOOP
    # ========================================================

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


        # ----------------------------------------------------
        # CAPTURE RESUMABLE RUN STATE
        # ----------------------------------------------------

        state = result.to_state()


        # ----------------------------------------------------
        # PERSIST RUN STATE
        #
        # This demonstrates that the run can survive beyond
        # the current Python call/process.
        # ----------------------------------------------------

        STATE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        STATE_PATH.write_text(

            state.to_string(),

            encoding="utf-8"
        )


        print(
            "\nPaused RunState saved to:",
            STATE_PATH
        )


        # ----------------------------------------------------
        # RELOAD THE STATE
        #
        # We deliberately reload it instead of just keeping
        # the in-memory object.
        #
        # This demonstrates true durable pause/resume.
        # ----------------------------------------------------

        stored_state = json.loads(

            STATE_PATH.read_text(
                encoding="utf-8"
            )
        )


        state = await RunState.from_json(

            hil_agent,

            stored_state
        )


        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Use interruptions belonging to the rehydrated state.
        # ----------------------------------------------------

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


            # ------------------------------------------------
            # COLLECT HUMAN DECISION WITHOUT BLOCKING
            # ASYNC RUNNER EVENT LOOP
            # ------------------------------------------------

            approved = await asyncio.to_thread(

                prompt_human_approval,

                tool_name,

                arguments
            )


            if approved:

                print(
                    "\nHuman decision: APPROVED"
                )


                # Per-call approval only.
                # We intentionally do NOT use always_approve.
                state.approve(
                    interruption,
                    always_approve=False
                )


            else:

                print(
                    "\nHuman decision: REJECTED"
                )


                # Give explicit feedback back to the agent.
                state.reject(

                    interruption,

                    always_reject=False,

                    rejection_message=(

                        "The human reviewer rejected this "
                        "sensitive action. Respect the decision. "
                        "Do not request the same action again. "
                        "Finish the mission with "
                        "mission_status STOPPED_BY_HUMAN."
                    )
                )


        print(
            "\n========== SDK RUN RESUMING =========="
        )


        # ----------------------------------------------------
        # RESUME FROM THE EXACT PAUSED RUN STATE
        # ----------------------------------------------------

        result = await Runner.run(
            hil_agent,
            state,
            run_config=RUN_CONFIG
        )


    # ========================================================
    # FINAL STRUCTURED RESULT
    # ========================================================

    final = result.final_output


    print(
        "\n"
        "============================================\n"
        " BONUS B MISSION COMPLETE\n"
        "============================================"
    )


    print(
        "\nMission status:",
        final.mission_status
    )


    print(
        "\nRoot cause:",
        final.verified_root_cause
    )


    print(
        "\nConfidence:",
        final.confidence
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


    # ========================================================
    # SDK USAGE
    # ========================================================

    usage = (
        result.context_wrapper.usage
    )


    print(
        "\n========== SDK RUN INFO =========="
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
        "\nAgent:",
        result.last_agent.name
    )


    print(
        "\nRunState snapshot:",
        STATE_PATH
    )


    print(
        "\n================== END =================="
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )