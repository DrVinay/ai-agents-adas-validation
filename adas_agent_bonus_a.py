from typing import Literal

from pydantic import BaseModel, Field

from agents import Agent, Runner
from agents.decorators import tool

import threading
PRINT_LOCK = threading.Lock()

# ============================================================
# SIMULATED HIL ENVIRONMENT
# ============================================================

REGRESSION_SUMMARY = {
    "run_id": "HIL_NIGHTLY_2026_10_26",
    "build": "4821",
    "total_tests": 500,
    "passed_tests": 463,
    "failed_tests": 37,
    "duration_minutes": 142,
    "status": "COMPLETED"
}


FAILURE_GROUPS = {

    "G1": {
        "subsystem": "ECU flashing",
        "failure_count": 30,
        "symptom":
            "UDS programming session timeout after ECU reboot",
        "example_tests": [
            "HIL_FLASH_014",
            "HIL_FLASH_027",
            "HIL_FLASH_031"
        ]
    },

    "G2": {
        "subsystem": "Camera synchronization",
        "failure_count": 5,
        "symptom":
            "Camera timestamp synchronization error",
        "example_tests": [
            "CAM_SYNC_007",
            "CAM_SYNC_011"
        ]
    },

    "G3": {
        "subsystem": "Perception",
        "failure_count": 2,
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
        "evidence_id": "E_LOG_FLASH",
        "observation":
            "30 failures occur approximately 10 seconds "
            "after ECU reset. The flashing harness aborts "
            "after 10 seconds, while ECU boot-ready is "
            "observed at approximately 13.8 seconds."
    },

    "G2": {
        "evidence_id": "E_LOG_CAMERA",
        "observation":
            "Camera PTP offset reached 45 ms. "
            "Four of five tests passed when rerun."
    },

    "G3": {
        "evidence_id": "E_LOG_PERCEPTION",
        "observation":
            "Two isolated perception-confidence mismatches "
            "occurred close to the configured decision threshold."
    }
}


BUILD_CHANGES = {

    "4821": {
        "evidence_id": "E_BUILD_4821",
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
        "issue_id": "KI-204",
        "evidence_id": "E_KNOWN_204",
        "title":
            "Programming-session timeout after ECU reboot",
        "description":
            "A flashing timeout can occur when ECU boot-ready "
            "time exceeds the HIL harness timeout. "
            "Reported on build 4821.",
        "status": "OPEN"
    },

    {
        "issue_id": "KI-188",
        "evidence_id": "E_KNOWN_188",
        "title":
            "Intermittent camera PTP synchronization",
        "description":
            "Occasional timestamp offset during bench startup.",
        "status": "MONITORING"
    }
]


# ============================================================
# TERMINAL DISPLAY HELPER
# ============================================================

def show_tool_result(
    tool_name,
    arguments,
    result
):

    with PRINT_LOCK:

        print(
            f"\n========== SDK TOOL: {tool_name} =========="
        )

        print(
            "Arguments:",
            arguments
        )

        print(
            "Observation:",
            result
        )


# ============================================================
# FUNCTION TOOLS
#
# In Level 5A we manually wrote JSON tool schemas.
#
# Here the Agents SDK automatically creates the tool schema
# from the Python function signature and docstring.
# ============================================================


@tool
def record_plan(
    steps: list[str],
    success_criteria: list[str]
) -> dict:

    """
    Record the agent's concise task-level investigation plan.

    Args:
        steps:
            Observable investigation steps.

        success_criteria:
            Conditions that define successful completion.
    """

    result = {
        "plan_recorded": True,
        "steps": steps,
        "success_criteria": success_criteria
    }

    show_tool_result(
        "record_plan",
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

    show_tool_result(
        "get_latest_regression_summary",
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

    show_tool_result(
        "get_failure_groups",
        {},
        result
    )

    return result


@tool
def get_failure_log(
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

        result = FAILURE_LOGS[group_id]


    show_tool_result(
        "get_failure_log",
        {
            "group_id": group_id
        },
        result
    )

    return result


@tool
def get_build_changes(
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
                f"No build information found for build {build}"
        }

    else:

        result = BUILD_CHANGES[build]


    show_tool_result(
        "get_build_changes",
        {
            "build": build
        },
        result
    )

    return result


@tool
def search_known_issues(
    keyword: str
) -> list[dict]:

    """
    Search known engineering issues using symptom keywords.

    Args:
        keyword:
            Search phrase describing the observed problem.
    """

    keyword_lower = keyword.lower()

    words = [
        word
        for word in keyword_lower.split()
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


    show_tool_result(
        "search_known_issues",
        {
            "keyword": keyword
        },
        matches
    )

    return matches


@tool
def calculate_percentage(
    part: float,
    total: float,
    metric_key: Literal[
        "overall_failure_rate",
        "dominant_failure_share"
    ],
    metric_name: str
) -> dict:

    """
    Calculate a named engineering percentage.

    Args:
        part:
            Numerator.

        total:
            Denominator.

        metric_key:
            Stable machine-readable metric identifier.

        metric_name:
            Human-readable explanation of the metric.
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
            "part": part,
            "total": total,
            "percentage": percentage,
            "metric_key": metric_key,
            "metric": metric_name
        }


    show_tool_result(
        "calculate_percentage",
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
# STRUCTURED FINAL OUTPUT
#
# This replaces our manual finish_investigation tool.
# ============================================================

class InvestigationResult(BaseModel):

    root_cause: str

    confidence: float = Field(
        ge=0,
        le=1
    )

    failure_rate_percent: float

    dominant_cause_share_percent: float

    evidence_ids: list[str]

    recommended_action: str

    summary: str


# ============================================================
# AGENT INSTRUCTIONS
# ============================================================

AGENT_INSTRUCTIONS = """
You are an autonomous ADAS HIL validation investigation agent.

You receive a high-level engineering goal rather than
a fixed workflow.

You must dynamically decide which tools to use and
in what order.

INVESTIGATION RULES

1. Start by calling record_plan.

2. Gather ground-truth regression data using tools.

3. Do not assume failure counts, logs, build changes
   or known issues.

4. Identify the dominant failure group.

5. Calculate:

   - overall_failure_rate
   - dominant_failure_share

6. Give every percentage a meaningful human-readable
   metric name.

7. Inspect detailed evidence for the dominant group.

8. Inspect the residual groups sufficiently to determine
   whether they challenge the dominant conclusion.

9. Correlate observed failures with relevant build changes
   and known engineering issues.

10. Do not stop merely because an explanation appears plausible.

11. Do not invent evidence or tool results.

CAUSALITY RULE

The experimentally observed evidence supports a timing mismatch
between:

- a 10-second HIL flashing harness timeout
- approximately 13.8-second ECU boot-ready time

Do NOT state that the new bootloader integrity/security check
caused the increased boot-ready latency unless evidence directly
isolates that causal relationship.

The security check may be described as concurrent with,
correlated with, or introduced in the same build as the
latency increase.

FINAL RESULT

When you have enough evidence, return the structured
InvestigationResult.

The final result must include:

- root cause
- confidence from 0 to 1
- overall regression failure rate
- dominant failure share
- supporting evidence IDs
- recommended engineering action
- concise engineering summary

Do not reveal private chain-of-thought.

Expose only observable plans, tool actions,
evidence and conclusions.
"""


# ============================================================
# HIGH-LEVEL GOAL
# ============================================================

GOAL = """
Investigate the latest HIL regression.

Determine the dominant failure mechanism.

Calculate:

1. overall regression failure rate

2. percentage of the failure population represented
   by the dominant failure group

Investigate residual failure groups sufficiently to
determine whether they challenge the dominant conclusion.

Recommend the next engineering action.

Use evidence before reaching a conclusion.
"""


# ============================================================
# CREATE AGENT
# ============================================================

hil_agent = Agent(

    name=
        "ADAS HIL Autonomous Investigator",

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
        calculate_percentage
    ],

    output_type=
        InvestigationResult
)


# ============================================================
# RUN AGENT
#
# No manual while loop.
# No previous_response_id management.
# No manual function-call routing.
#
# Runner handles the autonomous agent loop.
# ============================================================

print(
    "\n"
    "============================================\n"
    " BONUS A - OPENAI AGENTS SDK\n"
    " ADAS HIL AUTONOMOUS INVESTIGATION\n"
    "============================================"
)


result = Runner.run_sync(

    hil_agent,

    GOAL,

    max_turns=12
)


# ============================================================
# FINAL STRUCTURED RESULT
# ============================================================

final = result.final_output


print(
    "\n========== SDK INVESTIGATION COMPLETE =========="
)


print(
    "\nRoot cause:",
    final.root_cause
)


print(
    "\nConfidence:",
    final.confidence
)


print(
    "\nRegression failure rate:",
    final.failure_rate_percent,
    "%"
)


print(
    "\nDominant failure share:",
    final.dominant_cause_share_percent,
    "%"
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
    "\nRecommended action:",
    final.recommended_action
)


print(
    "\nSummary:",
    final.summary
)


# ============================================================
# SDK USAGE INFORMATION
# ============================================================

usage = result.context_wrapper.usage


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
    "\n==================END====================="
)