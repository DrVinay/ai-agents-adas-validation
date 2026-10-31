from openai import OpenAI

import json
import uuid

from datetime import datetime


client = OpenAI()


# ============================================================
# SESSION / AUDIT
# ============================================================

SESSION_ID = str(uuid.uuid4())

AUDIT_FILE = "l5c_audit_log.jsonl"


def audit_event(event_type, data):

    entry = {

        "timestamp":
            datetime.now().isoformat(),

        "session_id":
            SESSION_ID,

        "event_type":
            event_type,

        "data":
            data
    }


    with open(
        AUDIT_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(entry)
            + "\n"
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
# SIMULATED REAL HIL CONFIGURATION
# ============================================================

HIL_CONFIG = {

    "flashing_timeout_seconds":
        10,

    "config_version":
        1
}


# ============================================================
# LEVEL 5C STATE
# ============================================================

investigation_verified = False

human_rejection_occurred = False

configuration_changed = False

full_regression_completed = False


# ============================================================
# READ-ONLY / INVESTIGATION TOOLS
# ============================================================

def record_plan(
    steps,
    success_criteria
):

    return {

        "plan_recorded":
            True,

        "steps":
            steps,

        "success_criteria":
            success_criteria
    }


def get_latest_regression_summary():

    return REGRESSION_SUMMARY


def get_failure_groups():

    return FAILURE_GROUPS


def get_failure_log(group_id):

    if group_id not in FAILURE_LOGS:

        return {
            "error":
                f"Unknown failure group: {group_id}"
        }


    return FAILURE_LOGS[group_id]


def get_build_changes(build):

    if build not in BUILD_CHANGES:

        return {
            "error":
                f"No build information found for build {build}"
        }


    return BUILD_CHANGES[build]


def search_known_issues(keyword):

    keyword = keyword.lower()

    matches = []


    for issue in KNOWN_ISSUES:

        searchable_text = (

            issue["title"]
            + " "
            + issue["description"]

        ).lower()


        words = keyword.split()


        if any(
            word in searchable_text
            for word in words
        ):

            matches.append(issue)


    return matches


def calculate_percentage(
    part,
    total,
    metric_key,
    metric_name
):

    if total == 0:

        return {
            "error":
                "Total cannot be zero."
        }


    percentage = round(
        (part / total) * 100,
        2
    )


    return {

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


# ============================================================
# TARGETED EXPERIMENT
# ============================================================

def run_targeted_validation(
    group_id,
    timeout_seconds
):

    if group_id != "G1":

        return {

            "error":
                "Targeted timeout validation is only "
                "configured for G1."
        }


    if timeout_seconds <= 13.8:

        return {

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
                "The timeout remains shorter than "
                "the observed 13.8 s boot-ready time."
        }


    return {

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
            "the timeout was extended beyond "
            "the ECU boot-ready time."
    }


# ============================================================
# CONFIG READ TOOL
# ============================================================

def get_hil_config():

    return {

        "evidence_id":
            "E_CONFIG_CURRENT",

        "flashing_timeout_seconds":
            HIL_CONFIG[
                "flashing_timeout_seconds"
            ],

        "config_version":
            HIL_CONFIG[
                "config_version"
            ]
    }


# ============================================================
# SIDE-EFFECT IMPLEMENTATION
#
# IMPORTANT:
# These functions are NOT called directly by the LLM router.
#
# They may only be reached through:
#
# guardrails
#      ↓
# human approval
#      ↓
# controlled execution
# ============================================================

def _apply_timeout_change(
    new_timeout_seconds,
    reason
):

    global configuration_changed


    previous_timeout = (
        HIL_CONFIG[
            "flashing_timeout_seconds"
        ]
    )


    HIL_CONFIG[
        "flashing_timeout_seconds"
    ] = new_timeout_seconds


    HIL_CONFIG[
        "config_version"
    ] += 1


    configuration_changed = True


    return {

        "evidence_id":
            "E_CONFIG_TIMEOUT_APPLIED",

        "status":
            "CONFIGURATION_CHANGED",

        "previous_timeout_seconds":
            previous_timeout,

        "new_timeout_seconds":
            new_timeout_seconds,

        "config_version":
            HIL_CONFIG[
                "config_version"
            ],

        "reason":
            reason
    }


def _trigger_full_regression(
    reason
):

    global full_regression_completed


    timeout = (
        HIL_CONFIG[
            "flashing_timeout_seconds"
        ]
    )


    # --------------------------------------------------------
    # SIMULATED SYSTEM RESPONSE
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


    full_regression_completed = True


    return {

        "evidence_id":
            "E_FULL_REGRESSION_POST_CHANGE",

        "run_id":
            "HIL_VALIDATION_AFTER_AGENT_CHANGE",

        "build":
            "4821",

        "configuration": {

            "flashing_timeout_seconds":
                timeout,

            "config_version":
                HIL_CONFIG[
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


# ============================================================
# OBSERVATION MEMORY
# ============================================================

observed_evidence = {}

observed_metrics = {}


def collect_observation(
    tool_name,
    result
):

    if isinstance(
        result,
        dict
    ):

        if "evidence_id" in result:

            evidence_id = (
                result["evidence_id"]
            )


            observed_evidence[
                evidence_id
            ] = {

                "source_tool":
                    tool_name,

                "data":
                    result
            }


        if (
            "metric_key" in result
            and
            "percentage" in result
        ):

            observed_metrics[
                result["metric_key"]
            ] = result["percentage"]


    elif isinstance(
        result,
        list
    ):

        for entry in result:

            if (
                isinstance(
                    entry,
                    dict
                )
                and
                "evidence_id" in entry
            ):

                evidence_id = (
                    entry["evidence_id"]
                )


                observed_evidence[
                    evidence_id
                ] = {

                    "source_tool":
                        tool_name,

                    "data":
                        entry
                }


# ============================================================
# LEVEL 5B DETERMINISTIC VERIFIER
# ============================================================

def deterministic_verification(
    candidate
):

    issues = []


    expected_failure_rate = (
        observed_metrics.get(
            "overall_failure_rate"
        )
    )


    if expected_failure_rate is None:

        issues.append(
            "Overall regression failure rate "
            "was not calculated."
        )


    elif abs(
        candidate[
            "failure_rate_percent"
        ]
        - expected_failure_rate
    ) > 0.01:

        issues.append(
            "Reported failure rate does not "
            "match the calculated result."
        )


    expected_dominant_share = (
        observed_metrics.get(
            "dominant_failure_share"
        )
    )


    if expected_dominant_share is None:

        issues.append(
            "Dominant failure share "
            "was not calculated."
        )


    elif abs(
        candidate[
            "dominant_cause_share_percent"
        ]
        - expected_dominant_share
    ) > 0.01:

        issues.append(
            "Reported dominant share does not "
            "match the calculated result."
        )


    for evidence_id in candidate[
        "evidence_ids"
    ]:

        if (
            evidence_id
            not in observed_evidence
        ):

            issues.append(
                f"Evidence {evidence_id} "
                "was not observed."
            )


    required_experiment = (
        "E_RERUN_FLASH_EXTENDED_TIMEOUT"
    )


    if (
        required_experiment
        not in observed_evidence
    ):

        issues.append(
            "The timeout hypothesis has not "
            "been experimentally confirmed."
        )


    elif (
        required_experiment
        not in candidate[
            "evidence_ids"
        ]
    ):

        issues.append(
            "Experimental rerun evidence exists "
            "but was not cited."
        )


    return issues


# ============================================================
# INDEPENDENT LLM VERIFIER
# ============================================================

def verify_candidate(candidate):

    deterministic_issues = (
        deterministic_verification(
            candidate
        )
    )


    package = {

        "candidate":
            candidate,

        "observed_evidence":
            observed_evidence,

        "observed_metrics":
            observed_metrics,

        "deterministic_issues":
            deterministic_issues
    }


    verifier_instructions = """
You are an independent ADAS HIL validation QA reviewer.

Evaluate whether the investigator's proposed technical
conclusion is supported by the supplied evidence.

Check:

1. Mathematical values.
2. Evidence IDs.
3. Direct root-cause support.
4. Experimental confirmation.
5. Residual failure groups.
6. Contradictory evidence.
7. Confidence.
8. Recommended engineering action.

Rules:

If deterministic_issues is non-empty,
approved MUST be false.

For this exercise, successful targeted rerun of all
30 affected flashing tests using a timeout above
13.8 seconds is sufficient experimental confirmation.

A full regression is an important engineering follow-up,
but is NOT required for investigation approval.

Residual camera and perception failures may remain
unresolved if they are clearly separate mechanisms.

The experimentally confirmed mechanism is the mismatch between
the 10-second HIL harness timeout and the approximately
13.8-second ECU boot-ready time.

The bootloader integrity/security check may be described only
as correlated with, concurrent with, or introduced in the same
build as the increased boot-ready latency unless direct causal
evidence is available.

If the candidate incorrectly states that the security check
caused the boot-time increase, approved MUST be false and the
candidate must revise the causal wording.

Do not invent additional approval requirements.

Do not invent evidence.

Return only the requested structured result.
"""


    verifier_response = (
        client.responses.create(

            model=
                "gpt-5.6",

            instructions=
                verifier_instructions,

            input=
                json.dumps(package),

            text={

                "format": {

                    "type":
                        "json_schema",

                    "name":
                        "verification_result",

                    "strict":
                        True,

                    "schema": {

                        "type":
                            "object",

                        "properties": {

                            "approved": {
                                "type":
                                    "boolean"
                            },

                            "score": {
                                "type":
                                    "number",
                                "minimum":
                                    0,
                                "maximum":
                                    1
                            },

                            "issues": {

                                "type":
                                    "array",

                                "items": {
                                    "type":
                                        "string"
                                }
                            },

                            "required_actions": {

                                "type":
                                    "array",

                                "items": {
                                    "type":
                                        "string"
                                }
                            },

                            "feedback": {
                                "type":
                                    "string"
                            }
                        },

                        "required": [
                            "approved",
                            "score",
                            "issues",
                            "required_actions",
                            "feedback"
                        ],

                        "additionalProperties":
                            False
                    }
                }
            }
        )
    )


    verdict = json.loads(
        verifier_response.output_text
    )


    if deterministic_issues:

        verdict[
            "approved"
        ] = False


        for issue in deterministic_issues:

            if issue not in verdict["issues"]:

                verdict[
                    "issues"
                ].append(issue)


    return verdict


# ============================================================
# LEVEL 5C GUARDRAILS
# ============================================================

SENSITIVE_TOOLS = {

    "apply_timeout_change":
        "CONFIG_WRITE",

    "trigger_full_regression":
        "EXECUTION"
}


def evaluate_action_guardrails(
    tool_name,
    args
):

    issues = []


    # --------------------------------------------------------
    # CHANGE CONFIGURATION
    # --------------------------------------------------------

    if tool_name == "apply_timeout_change":

        new_timeout = (
            args[
                "new_timeout_seconds"
            ]
        )


        if not investigation_verified:

            issues.append(
                "Investigation has not passed "
                "independent verification."
            )


        if not (
            14
            <= new_timeout
            <= 30
        ):

            issues.append(
                "Timeout must remain within "
                "approved engineering bounds "
                "of 14 to 30 seconds."
            )


        if (
            new_timeout
            <= HIL_CONFIG[
                "flashing_timeout_seconds"
            ]
        ):

            issues.append(
                "Requested timeout must be greater "
                "than the current timeout."
            )


        supplied_evidence = (
            args[
                "evidence_ids"
            ]
        )


        for evidence_id in supplied_evidence:

            if (
                evidence_id
                not in observed_evidence
            ):

                issues.append(
                    f"Action references unknown evidence "
                    f"{evidence_id}."
                )


        if (
            "E_RERUN_FLASH_EXTENDED_TIMEOUT"
            not in supplied_evidence
        ):

            issues.append(
                "Successful targeted rerun evidence "
                "is required before configuration change."
            )


    # --------------------------------------------------------
    # TRIGGER FULL REGRESSION
    # --------------------------------------------------------

    elif tool_name == "trigger_full_regression":

        if not investigation_verified:

            issues.append(
                "Investigation is not verified."
            )


        if not configuration_changed:

            issues.append(
                "Approved timeout configuration "
                "has not been applied."
            )


        if (
            HIL_CONFIG[
                "flashing_timeout_seconds"
            ]
            <= 13.8
        ):

            issues.append(
                "Current timeout is not above "
                "ECU boot-ready time."
            )


        if (
            "E_CONFIG_TIMEOUT_APPLIED"
            not in observed_evidence
        ):

            issues.append(
                "No observed evidence confirms "
                "the configuration change."
            )


    else:

        issues.append(
            "Tool is not registered as "
            "a sensitive action."
        )


    return {

        "allowed":
            len(issues) == 0,

        "risk_level":
            SENSITIVE_TOOLS.get(
                tool_name,
                "UNKNOWN"
            ),

        "issues":
            issues
    }


# ============================================================
# HUMAN APPROVAL GATE
# ============================================================

def request_human_approval(
    tool_name,
    args,
    guardrail_result
):

    global human_rejection_occurred


    print(
        "\n========== HUMAN APPROVAL REQUIRED =========="
    )


    print(
        "\nSensitive action:",
        tool_name
    )


    print(
        "Risk level:",
        guardrail_result[
            "risk_level"
        ]
    )


    print(
        "\nProposed arguments:"
    )


    print(
        json.dumps(
            args,
            indent=2
        )
    )


    audit_event(

        "APPROVAL_REQUESTED",

        {

            "tool":
                tool_name,

            "arguments":
                args,

            "risk_level":
                guardrail_result[
                    "risk_level"
                ]
        }
    )


    while True:

        decision = input(

            "\nType APPROVE or REJECT: "

        ).strip().upper()


        if decision == "APPROVE":

            audit_event(

                "HUMAN_APPROVED",

                {

                    "tool":
                        tool_name,

                    "arguments":
                        args
                }
            )


            print(
                "\nHuman decision: APPROVED"
            )


            return {

                "approved":
                    True,

                "decision":
                    "APPROVE"
            }


        elif decision == "REJECT":

            reason = input(
                "Optional rejection reason: "
            ).strip()


            human_rejection_occurred = True


            audit_event(

                "HUMAN_REJECTED",

                {

                    "tool":
                        tool_name,

                    "arguments":
                        args,

                    "reason":
                        reason
                }
            )


            print(
                "\nHuman decision: REJECTED"
            )


            return {

                "approved":
                    False,

                "decision":
                    "REJECT",

                "reason":
                    reason
            }


        else:

            print(
                "Please type APPROVE or REJECT."
            )


# ============================================================
# GUARDED SENSITIVE TOOL EXECUTION
# ============================================================

def execute_sensitive_tool(
    tool_name,
    args
):

    guardrail_result = (
        evaluate_action_guardrails(
            tool_name,
            args
        )
    )


    # --------------------------------------------------------
    # FAIL CLOSED
    # --------------------------------------------------------

    if not guardrail_result[
        "allowed"
    ]:

        audit_event(

            "ACTION_BLOCKED_BY_GUARDRAIL",

            {

                "tool":
                    tool_name,

                "arguments":
                    args,

                "issues":
                    guardrail_result[
                        "issues"
                    ]
            }
        )


        return {

            "status":
                "BLOCKED_BY_GUARDRAIL",

            "issues":
                guardrail_result[
                    "issues"
                ]
        }


    # --------------------------------------------------------
    # HUMAN AUTHORIZATION
    # --------------------------------------------------------

    approval = request_human_approval(

        tool_name,
        args,
        guardrail_result
    )


    if not approval[
        "approved"
    ]:

        return {

            "status":
                "HUMAN_REJECTED",

            "reason":
                approval.get(
                    "reason",
                    ""
                )
        }


    # --------------------------------------------------------
    # EXECUTE CONFIG CHANGE
    # --------------------------------------------------------

    if tool_name == "apply_timeout_change":

        result = _apply_timeout_change(

            args[
                "new_timeout_seconds"
            ],

            args[
                "reason"
            ]
        )


    # --------------------------------------------------------
    # EXECUTE FULL REGRESSION
    # --------------------------------------------------------

    elif tool_name == "trigger_full_regression":

        result = _trigger_full_regression(

            args[
                "reason"
            ]
        )


    else:

        return {

            "status":
                "UNKNOWN_SENSITIVE_TOOL"
        }


    audit_event(

        "ACTION_EXECUTED",

        {

            "tool":
                tool_name,

            "result":
                result
        }
    )


    return result


# ============================================================
# TOOL ROUTER
# ============================================================

def execute_tool(
    name,
    args
):

    if name == "record_plan":

        return record_plan(
            args["steps"],
            args["success_criteria"]
        )


    elif name == "get_latest_regression_summary":

        return get_latest_regression_summary()


    elif name == "get_failure_groups":

        return get_failure_groups()


    elif name == "get_failure_log":

        return get_failure_log(
            args["group_id"]
        )


    elif name == "get_build_changes":

        return get_build_changes(
            args["build"]
        )


    elif name == "search_known_issues":

        return search_known_issues(
            args["keyword"]
        )


    elif name == "calculate_percentage":

        return calculate_percentage(

            args["part"],

            args["total"],

            args["metric_key"],

            args["metric_name"]
        )


    elif name == "run_targeted_validation":

        return run_targeted_validation(

            args["group_id"],

            args["timeout_seconds"]
        )


    elif name == "get_hil_config":

        return get_hil_config()


    elif name in SENSITIVE_TOOLS:

        return execute_sensitive_tool(
            name,
            args
        )


    return {

        "error":
            f"Unknown tool: {name}"
    }


# ============================================================
# TOOL DEFINITIONS
# ============================================================

tools = [

    {
        "type":
            "function",

        "name":
            "record_plan",

        "description":
            "Record a concise task-level plan.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "steps": {

                    "type":
                        "array",

                    "items": {
                        "type":
                            "string"
                    }
                },

                "success_criteria": {

                    "type":
                        "array",

                    "items": {
                        "type":
                            "string"
                    }
                }
            },

            "required": [
                "steps",
                "success_criteria"
            ]
        }
    },


    {
        "type":
            "function",

        "name":
            "get_latest_regression_summary",

        "description":
            "Get latest completed HIL regression.",

        "parameters": {
            "type":
                "object",
            "properties": {}
        }
    },


    {
        "type":
            "function",

        "name":
            "get_failure_groups",

        "description":
            "Get grouped regression failures.",

        "parameters": {
            "type":
                "object",
            "properties": {}
        }
    },


    {
        "type":
            "function",

        "name":
            "get_failure_log",

        "description":
            "Inspect detailed evidence for a failure group.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "group_id": {
                    "type":
                        "string"
                }
            },

            "required": [
                "group_id"
            ]
        }
    },


    {
        "type":
            "function",

        "name":
            "get_build_changes",

        "description":
            "Inspect changes introduced in a build.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "build": {
                    "type":
                        "string"
                }
            },

            "required": [
                "build"
            ]
        }
    },


    {
        "type":
            "function",

        "name":
            "search_known_issues",

        "description":
            "Search known engineering issues.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "keyword": {
                    "type":
                        "string"
                }
            },

            "required": [
                "keyword"
            ]
        }
    },


    {
        "type":
            "function",

        "name":
            "calculate_percentage",

        "description":
            "Calculate a named percentage metric.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "part": {
                    "type":
                        "number"
                },

                "total": {
                    "type":
                        "number"
                },

                "metric_key": {

                    "type":
                        "string",

                    "enum": [

                        "overall_failure_rate",

                        "dominant_failure_share",

                        "post_change_failure_rate"
                    ]
                },

                "metric_name": {
                    "type":
                        "string"
                }
            },

            "required": [
                "part",
                "total",
                "metric_key",
                "metric_name"
            ]
        }
    },


    {
        "type":
            "function",

        "name":
            "run_targeted_validation",

        "description":
            "Run targeted validation of the flashing "
            "timeout hypothesis.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "group_id": {
                    "type":
                        "string"
                },

                "timeout_seconds": {
                    "type":
                        "number"
                }
            },

            "required": [
                "group_id",
                "timeout_seconds"
            ]
        }
    },


    {
        "type":
            "function",

        "name":
            "finish_investigation",

        "description":
            "Submit the technical investigation "
            "for independent verification.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "root_cause": {
                    "type":
                        "string"
                },

                "confidence": {
                    "type":
                        "number"
                },

                "failure_rate_percent": {
                    "type":
                        "number"
                },

                "dominant_cause_share_percent": {
                    "type":
                        "number"
                },

                "evidence_ids": {

                    "type":
                        "array",

                    "items": {
                        "type":
                            "string"
                    }
                },

                "recommended_action": {
                    "type":
                        "string"
                },

                "summary": {
                    "type":
                        "string"
                }
            },

            "required": [

                "root_cause",

                "confidence",

                "failure_rate_percent",

                "dominant_cause_share_percent",

                "evidence_ids",

                "recommended_action",

                "summary"
            ]
        }
    },


    # ========================================================
    # 5C READ CURRENT CONFIG
    # ========================================================

    {
        "type":
            "function",

        "name":
            "get_hil_config",

        "description":
            "Read the current HIL configuration. "
            "This tool is read-only.",

        "parameters": {
            "type":
                "object",
            "properties": {}
        }
    },


    # ========================================================
    # 5C SIDE EFFECT 1
    # ========================================================

    {
        "type":
            "function",

        "name":
            "apply_timeout_change",

        "description":
            "Apply a change to the HIL flashing timeout. "
            "This is a side-effecting configuration write "
            "and requires application guardrails and "
            "explicit human approval.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "new_timeout_seconds": {
                    "type":
                        "number"
                },

                "reason": {
                    "type":
                        "string"
                },

                "evidence_ids": {

                    "type":
                        "array",

                    "items": {
                        "type":
                            "string"
                    }
                }
            },

            "required": [

                "new_timeout_seconds",

                "reason",

                "evidence_ids"
            ]
        }
    },


    # ========================================================
    # 5C SIDE EFFECT 2
    # ========================================================

    {
        "type":
            "function",

        "name":
            "trigger_full_regression",

        "description":
            "Trigger a complete HIL regression using "
            "the current configuration. This consumes "
            "engineering resources and therefore requires "
            "explicit human approval.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "reason": {
                    "type":
                        "string"
                }
            },

            "required": [
                "reason"
            ]
        }
    },


    # ========================================================
    # FINAL LEVEL 5C COMPLETION
    # ========================================================

    {
        "type":
            "function",

        "name":
            "finish_mission",

        "description":
            "Finish the complete Level 5C mission after "
            "verified investigation and authorized action, "
            "or after a human explicitly rejects the action.",

        "parameters": {

            "type":
                "object",

            "properties": {

                "mission_status": {

                    "type":
                        "string",

                    "enum": [

                        "COMPLETED",

                        "STOPPED_BY_HUMAN"
                    ]
                },

                "verified_root_cause": {
                    "type":
                        "string"
                },

                "action_summary": {
                    "type":
                        "string"
                },

                "pre_change_failure_rate_percent": {
                    "type":
                        "number"
                },

                "post_change_failure_rate_percent": {
                    "type":
                        "number"
                },

                "post_change_failed_tests": {
                    "type":
                        "integer"
                },

                "evidence_ids": {

                    "type":
                        "array",

                    "items": {
                        "type":
                            "string"
                    }
                },

                "summary": {
                    "type":
                        "string"
                }
            },

            "required": [

                "mission_status",

                "verified_root_cause",

                "action_summary",

                "pre_change_failure_rate_percent",

                "post_change_failure_rate_percent",

                "post_change_failed_tests",

                "evidence_ids",

                "summary"
            ]
        }
    }
]


# ============================================================
# FINAL MISSION VALIDATION
# ============================================================

def validate_finish_mission(
    payload
):

    issues = []


    if not investigation_verified:

        issues.append(
            "Investigation has not been verified."
        )


    if (
        payload[
            "mission_status"
        ]
        == "COMPLETED"
    ):

        if not configuration_changed:

            issues.append(
                "Configuration change was not executed."
            )


        if not full_regression_completed:

            issues.append(
                "Post-change full regression "
                "was not executed."
            )


        required_evidence = [

            "E_CONFIG_TIMEOUT_APPLIED",

            "E_FULL_REGRESSION_POST_CHANGE"
        ]


        for evidence_id in required_evidence:

            if (
                evidence_id
                not in observed_evidence
            ):

                issues.append(
                    f"Missing required evidence "
                    f"{evidence_id}."
                )


        expected_post_rate = (
            observed_metrics.get(
                "post_change_failure_rate"
            )
        )


        if expected_post_rate is None:

            issues.append(
                "Post-change failure rate "
                "was not calculated."
            )


        elif abs(

            payload[
                "post_change_failure_rate_percent"
            ]
            - expected_post_rate

        ) > 0.01:

            issues.append(
                "Reported post-change failure rate "
                "does not match calculated value."
            )


    elif (
        payload[
            "mission_status"
        ]
        == "STOPPED_BY_HUMAN"
    ):

        if not human_rejection_occurred:

            issues.append(
                "No recorded human rejection exists."
            )


    return issues


# ============================================================
# AGENT INSTRUCTIONS
# ============================================================

agent_instructions = """
You are an autonomous ADAS HIL validation and remediation agent.

You have three phases.

PHASE 1 — INVESTIGATE

1. Start with record_plan.
2. Gather regression evidence.
3. Calculate:
   - overall_failure_rate
   - dominant_failure_share
4. Investigate dominant and residual failures.
5. Submit finish_investigation.

PHASE 2 — VERIFY

6. The investigation is independently verified.
7. If rejected, address verifier feedback.
8. Run targeted validation when experimental evidence
   is requested.
9. Resubmit until verification succeeds.

PHASE 3 — CONTROLLED ACTION

10. After receiving INVESTIGATION_VERIFIED,
    inspect the current HIL configuration.

11. Decide whether a configuration change is justified.

12. Sensitive tools:
    - apply_timeout_change
    - trigger_full_regression

13. Sensitive tools are protected by application-level
    guardrails and human approval.

14. Never attempt to bypass a guardrail or human decision.

15. Do not repeatedly request the same rejected action.

16. If the human rejects an action, respect the decision.
    You may explain the consequence and finish with
    STOPPED_BY_HUMAN.

17. If the timeout change is approved and applied,
    request a full regression.

18. After the full regression completes:
    - inspect the result
    - calculate post_change_failure_rate
    - compare it with the original rate

19. Finish using finish_mission.

20. Do not claim that the new bootloader integrity/security check
    caused the boot-ready latency increase unless evidence directly
    isolates that causal relationship.

21. The experimentally confirmed root-cause mechanism is the
    mismatch between:
    - 10-second HIL flashing timeout
    - approximately 13.8-second ECU boot-ready time

22. The bootloader security check may be described as correlated
    with or concurrent with the increased latency, but not as its
    confirmed cause.

23. Do not invent evidence.

24. Do not reveal private chain-of-thought.
    Expose only observable plans, actions,
    evidence, approvals and conclusions.
"""


# ============================================================
# HIGH-LEVEL GOAL
# ============================================================

goal = """
Investigate the latest HIL regression.

Determine and experimentally verify the dominant root cause.

If the evidence supports remediation:

1. inspect the current HIL configuration
2. propose the appropriate configuration change
3. obtain required authorization
4. execute the change only if authorized
5. run a full validation regression only if authorized
6. evaluate the post-change result
7. report whether the intervention improved the system

Respect all guardrails and human approval decisions.
"""


# ============================================================
# INITIAL MODEL CALL
# ============================================================

response = client.responses.create(

    model=
        "gpt-5.6",

    instructions=
        agent_instructions,

    input=
        goal,

    tools=
        tools
)


# ============================================================
# AUTONOMOUS LOOP
# ============================================================

MAX_AGENT_TURNS = 25

finished = False

verification_attempt = 0


for turn in range(
    1,
    MAX_AGENT_TURNS + 1
):

    print(
        f"\n========== Autonomous Turn {turn} =========="
    )


    tool_outputs = []

    candidate_payload = None

    candidate_call_id = None

    mission_payload = None

    mission_call_id = None


    # ========================================================
    # PROCESS MODEL OUTPUT
    # ========================================================

    for item in response.output:

        if item.type != "function_call":

            continue


        print(
            "\nAgent action:",
            item.name
        )


        args = json.loads(
            item.arguments
        )


        print(
            "Arguments:",
            args
        )


        # ----------------------------------------------------
        # INVESTIGATION COMPLETION REQUEST
        # ----------------------------------------------------

        if item.name == "finish_investigation":

            candidate_payload = args

            candidate_call_id = (
                item.call_id
            )

            continue


        # ----------------------------------------------------
        # FINAL MISSION REQUEST
        # ----------------------------------------------------

        if item.name == "finish_mission":

            mission_payload = args

            mission_call_id = (
                item.call_id
            )

            continue


        # ----------------------------------------------------
        # EXECUTE NORMAL OR GUARDED TOOL
        # ----------------------------------------------------

        result = execute_tool(
            item.name,
            args
        )


        collect_observation(
            item.name,
            result
        )


        print(
            "Observation:",
            result
        )


        tool_outputs.append({

            "type":
                "function_call_output",

            "call_id":
                item.call_id,

            "output":
                json.dumps(result)
        })


    # ========================================================
    # VERIFY INVESTIGATION
    # ========================================================

    if candidate_payload is not None:

        verification_attempt += 1


        print(
            "\n========== VERIFICATION REQUESTED =========="
        )


        print(
            "\nVerification attempt:",
            verification_attempt
        )


        verdict = verify_candidate(
            candidate_payload
        )


        print(
            "\nVerifier approved:",
            verdict["approved"]
        )


        print(
            "Verifier score:",
            verdict["score"]
        )


        print(
            "\nVerifier issues:"
        )


        if verdict["issues"]:

            for issue in verdict["issues"]:

                print(
                    " -",
                    issue
                )

        else:

            print(
                " - None"
            )


        print(
            "\nRequired actions:"
        )


        if verdict[
            "required_actions"
        ]:

            for action in verdict[
                "required_actions"
            ]:

                print(
                    " -",
                    action
                )

        else:

            print(
                " - None"
            )


        print(
            "\nVerifier feedback:",
            verdict["feedback"]
        )


        # ----------------------------------------------------
        # VERIFIED
        # ----------------------------------------------------

        if verdict["approved"]:

            investigation_verified = True


            audit_event(

                "INVESTIGATION_VERIFIED",

                {

                    "candidate":
                        candidate_payload,

                    "score":
                        verdict["score"]
                }
            )


            verification_result = {

                "status":
                    "INVESTIGATION_VERIFIED",

                "score":
                    verdict["score"],

                "message":
                    "Technical investigation is verified. "
                    "Proceed to controlled-action phase. "
                    "Inspect current HIL configuration before "
                    "requesting any write action."
            }


            tool_outputs.append({

                "type":
                    "function_call_output",

                "call_id":
                    candidate_call_id,

                "output":
                    json.dumps(
                        verification_result
                    )
            })


            print(
                "\n========== INVESTIGATION VERIFIED =========="
            )


        # ----------------------------------------------------
        # REJECTED
        # ----------------------------------------------------

        else:

            rejection_result = {

                "status":
                    "REJECTED_BY_VERIFIER",

                "score":
                    verdict["score"],

                "issues":
                    verdict["issues"],

                "required_actions":
                    verdict[
                        "required_actions"
                    ],

                "feedback":
                    verdict["feedback"]
            }


            tool_outputs.append({

                "type":
                    "function_call_output",

                "call_id":
                    candidate_call_id,

                "output":
                    json.dumps(
                        rejection_result
                    )
            })


    # ========================================================
    # FINAL MISSION REQUEST
    # ========================================================

    if mission_payload is not None:

        finish_issues = (
            validate_finish_mission(
                mission_payload
            )
        )


        if finish_issues:

            print(
                "\n========== MISSION FINISH REJECTED =========="
            )


            for issue in finish_issues:

                print(
                    " -",
                    issue
                )


            tool_outputs.append({

                "type":
                    "function_call_output",

                "call_id":
                    mission_call_id,

                "output":
                    json.dumps({

                        "status":
                            "MISSION_FINISH_REJECTED",

                        "issues":
                            finish_issues
                    })
            })


        else:

            print("\n========== LEVEL 5C MISSION COMPLETE ==========")

            print(
                "\nMission status:",
                mission_payload["mission_status"]
            )

            print(
                "\nPre-change failure rate:",
                mission_payload["pre_change_failure_rate_percent"],
                "%"
            )

            print(
                "Post-change failure rate:",
                mission_payload["post_change_failure_rate_percent"],
                "%"
            )

            print(
                "\nPost-change failed tests:",
                mission_payload["post_change_failed_tests"]
            )

            config_change = observed_evidence[
                "E_CONFIG_TIMEOUT_APPLIED"
            ]["data"]
            
            print(
                "\nConfiguration:",
                f"{config_change['previous_timeout_seconds']} s -> "
                f"{config_change['new_timeout_seconds']} s"
            )

            print(
                "\nResult:",
                "ECU flashing failures: 30 -> 0"
            )

            print(
                "\nAudit log:",
                AUDIT_FILE
            )


            finished = True

            break


    # ========================================================
    # CONTINUE AGENT LOOP
    # ========================================================

    if tool_outputs:

        response = client.responses.create(

            model=
                "gpt-5.6",

            instructions=
                agent_instructions,

            previous_response_id=
                response.id,

            input=
                tool_outputs,

            tools=
                tools
        )


    else:

        response = client.responses.create(

            model=
                "gpt-5.6",

            instructions=
                agent_instructions,

            previous_response_id=
                response.id,

            input="""
Continue toward the goal.

If verification feedback exists, address it.

If investigation is verified, continue into the
controlled-action phase.

Respect all guardrails and human approval decisions.

Finish only when all required steps are complete.
""",

            tools=
                tools
        )


# ============================================================
# MAX TURN STOP
# ============================================================

if not finished:

    print(
        "\nAgent stopped because "
        "MAX_AGENT_TURNS was reached."
    )