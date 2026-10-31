from openai import OpenAI
import json

client = OpenAI()


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
        "symptom": "UDS programming session timeout after ECU reboot",
        "example_tests": [
            "HIL_FLASH_014",
            "HIL_FLASH_027",
            "HIL_FLASH_031"
        ]
    },

    "G2": {
        "subsystem": "Camera synchronization",
        "failure_count": 5,
        "symptom": "Camera timestamp synchronization error",
        "example_tests": [
            "CAM_SYNC_007",
            "CAM_SYNC_011"
        ]
    },

    "G3": {
        "subsystem": "Perception",
        "failure_count": 2,
        "symptom": "AEB scenario perception confidence mismatch",
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
            "30 failures occur approximately 10 seconds after ECU reset. "
            "The flashing harness aborts after 10 seconds, while ECU boot-ready "
            "is observed at approximately 13.8 seconds."
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
            "Two isolated perception-confidence mismatches occurred close "
            "to the configured decision threshold."
    }
}


BUILD_CHANGES = {

    "4821": {
        "evidence_id": "E_BUILD_4821",
        "changes": [
            "New bootloader integrity/security check introduced.",
            "Measured ECU boot-ready time increased from approximately "
            "7.1 s to 13.8 s.",
            "HIL flashing harness timeout remains configured at 10 s."
        ]
    }
}


KNOWN_ISSUES = [

    {
        "issue_id": "KI-204",
        "evidence_id": "E_KNOWN_204",
        "title": "Programming-session timeout after ECU reboot",
        "description":
            "A flashing timeout can occur when ECU boot-ready time exceeds "
            "the HIL harness timeout. Reported on build 4821.",
        "status": "OPEN"
    },

    {
        "issue_id": "KI-188",
        "evidence_id": "E_KNOWN_188",
        "title": "Intermittent camera PTP synchronization",
        "description":
            "Occasional timestamp offset during bench startup.",
        "status": "MONITORING"
    }
]


# ============================================================
# TOOL IMPLEMENTATIONS
# ============================================================

def record_plan(steps, success_criteria):

    return {
        "plan_recorded": True,
        "steps": steps,
        "success_criteria": success_criteria
    }


def get_latest_regression_summary():

    return REGRESSION_SUMMARY


def get_failure_groups():

    return FAILURE_GROUPS


def get_failure_log(group_id):

    if group_id not in FAILURE_LOGS:

        return {
            "error": f"Unknown failure group: {group_id}"
        }

    return FAILURE_LOGS[group_id]


def get_build_changes(build):

    if build not in BUILD_CHANGES:

        return {
            "error": f"No build information found for build {build}"
        }

    return BUILD_CHANGES[build]


def search_known_issues(keyword):

    keyword = keyword.lower()

    matches = []

    for issue in KNOWN_ISSUES:

        searchable_text = (
            issue["title"] + " " +
            issue["description"]
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
            "error": "Total cannot be zero."
        }

    percentage = round(
        (part / total) * 100,
        2
    )

    return {
        "part": part,
        "total": total,
        "percentage": percentage,
        "metric_key": metric_key,
        "metric": metric_name
    }


# ============================================================
# LEVEL 5B NEW TOOL:
# TARGETED VALIDATION EXPERIMENT
# ============================================================

def run_targeted_validation(
    group_id,
    timeout_seconds
):

    if group_id != "G1":

        return {
            "error":
                "Targeted timeout validation is only configured "
                "for flashing group G1."
        }


    # ECU becomes boot-ready at approximately 13.8 seconds.

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
                "All 30 flashing tests still failed because the "
                "configured timeout remained shorter than the "
                "observed 13.8 s ECU boot-ready time."
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
            "All 30 flashing tests passed when the harness timeout "
            "was extended beyond the observed ECU boot-ready time."
    }


# ============================================================
# TOOL DEFINITIONS
# ============================================================

tools = [

    # --------------------------------------------------------
    # PLAN
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "record_plan",

        "description":
            "Record a concise task-level investigation plan.",

        "parameters": {

            "type": "object",

            "properties": {

                "steps": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },

                "success_criteria": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },

            "required": [
                "steps",
                "success_criteria"
            ]
        }
    },


    # --------------------------------------------------------
    # REGRESSION SUMMARY
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "get_latest_regression_summary",

        "description":
            "Get the latest completed HIL regression summary.",

        "parameters": {
            "type": "object",
            "properties": {}
        }
    },


    # --------------------------------------------------------
    # FAILURE GROUPS
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "get_failure_groups",

        "description":
            "Return grouped failures from the latest HIL regression.",

        "parameters": {
            "type": "object",
            "properties": {}
        }
    },


    # --------------------------------------------------------
    # FAILURE LOG
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "get_failure_log",

        "description":
            "Inspect detailed evidence for a specific failure group.",

        "parameters": {

            "type": "object",

            "properties": {

                "group_id": {
                    "type": "string"
                }
            },

            "required": [
                "group_id"
            ]
        }
    },


    # --------------------------------------------------------
    # BUILD CHANGES
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "get_build_changes",

        "description":
            "Inspect changes introduced in a software build.",

        "parameters": {

            "type": "object",

            "properties": {

                "build": {
                    "type": "string"
                }
            },

            "required": [
                "build"
            ]
        }
    },


    # --------------------------------------------------------
    # KNOWN ISSUES
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "search_known_issues",

        "description":
            "Search known engineering issues related to a symptom.",

        "parameters": {

            "type": "object",

            "properties": {

                "keyword": {
                    "type": "string"
                }
            },

            "required": [
                "keyword"
            ]
        }
    },


    # --------------------------------------------------------
    # PERCENTAGE CALCULATOR
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "calculate_percentage",

        "description":
            "Calculate a named percentage metric.",

        "parameters": {

            "type": "object",

            "properties": {

                "part": {
                    "type": "number"
                },

                "total": {
                    "type": "number"
                },

                "metric_key": {
                    "type": "string",
                    "enum": [
                        "overall_failure_rate",
                        "dominant_failure_share"
                    ],
                    "description":
                        "Stable machine-readable identifier for the metric."
                },

                "metric_name": {
                    "type": "string",
                    "description":
                        "Human-readable name for the metric."
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


    # --------------------------------------------------------
    # TARGETED VALIDATION
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "run_targeted_validation",

        "description":
            "Run a targeted experiment to validate the suspected "
            "ECU flashing timeout root cause. Use this when the "
            "independent verifier asks for experimental confirmation.",

        "parameters": {

            "type": "object",

            "properties": {

                "group_id": {
                    "type": "string"
                },

                "timeout_seconds": {
                    "type": "number"
                }
            },

            "required": [
                "group_id",
                "timeout_seconds"
            ]
        }
    },


    # --------------------------------------------------------
    # FINISH INVESTIGATION
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "finish_investigation",

        "description":
            "Submit the proposed final investigation conclusion "
            "for independent verification.",

        "parameters": {

            "type": "object",

            "properties": {

                "root_cause": {
                    "type": "string"
                },

                "confidence": {
                    "type": "number"
                },

                "failure_rate_percent": {
                    "type": "number"
                },

                "dominant_cause_share_percent": {
                    "type": "number"
                },

                "evidence_ids": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },

                "recommended_action": {
                    "type": "string"
                },

                "summary": {
                    "type": "string"
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
    }
]


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


    return {
        "error":
            f"Unknown tool: {name}"
    }


# ============================================================
# OBSERVED EVIDENCE AND METRICS
# ============================================================

observed_evidence = {}

observed_metrics = {}


# ============================================================
# COLLECT OBSERVATIONS
# ============================================================

def collect_observation(
    tool_name,
    result
):

    # --------------------------------------------------------
    # DICTIONARY RESULT
    # --------------------------------------------------------

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
            "metric" in result
            and
            "percentage" in result
        ):

            observed_metrics[
                result["metric_key"]
            ] = result["percentage"]


    # --------------------------------------------------------
    # LIST RESULT
    # e.g. known issue search
    # --------------------------------------------------------

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
# DETERMINISTIC VERIFICATION
# ============================================================

def deterministic_verification(
    candidate
):

    issues = []


    # --------------------------------------------------------
    # CHECK FAILURE RATE
    # --------------------------------------------------------

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
            "Reported regression failure rate "
            "does not match the calculated result."
        )


    # --------------------------------------------------------
    # CHECK DOMINANT SHARE
    # --------------------------------------------------------

    expected_dominant_share = (
        observed_metrics.get(
            "dominant_failure_share"
        )
    )


    if expected_dominant_share is None:

        issues.append(
            "Dominant failure-group percentage "
            "was not calculated."
        )


    elif abs(
        candidate[
            "dominant_cause_share_percent"
        ]
        - expected_dominant_share
    ) > 0.01:

        issues.append(
            "Reported dominant cause share "
            "does not match the calculated result."
        )


    # --------------------------------------------------------
    # CHECK EVIDENCE EXISTS
    # --------------------------------------------------------

    for evidence_id in candidate[
        "evidence_ids"
    ]:

        if (
            evidence_id
            not in observed_evidence
        ):

            issues.append(
                f"Evidence {evidence_id} "
                "was not actually observed."
            )


    # --------------------------------------------------------
    # REQUIRE EXPERIMENTAL CONFIRMATION
    # --------------------------------------------------------

    rerun_evidence = (
        "E_RERUN_FLASH_EXTENDED_TIMEOUT"
    )


    if (
        rerun_evidence
        not in observed_evidence
    ):

        issues.append(
            "The timeout root-cause hypothesis "
            "has not been experimentally confirmed. "
            "Run targeted validation using a timeout "
            "safely above the observed 13.8 s "
            "ECU boot-ready time."
        )


    # --------------------------------------------------------
    # IF EXPERIMENT EXISTS, REQUIRE IT TO BE CITED
    # --------------------------------------------------------

    elif (
        rerun_evidence
        not in candidate["evidence_ids"]
    ):

        issues.append(
            "Experimental rerun evidence exists "
            "but was not included in the final "
            "evidence list."
        )


    return issues


# ============================================================
# INDEPENDENT LLM VERIFIER
# ============================================================

def verify_candidate(
    candidate
):

    deterministic_issues = (
        deterministic_verification(
            candidate
        )
    )


    verification_package = {

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

You did not perform the original investigation.

Evaluate whether the investigator's proposed conclusion is
sufficiently supported by the supplied evidence.

Check:

1. Mathematical values match the observed metrics.

2. Every cited evidence ID actually exists.

3. The proposed dominant root cause is directly supported
   by evidence.

4. Correlation is not incorrectly presented as proven causation.

5. Experimental evidence confirms the proposed mechanism.

6. Alternative or residual failure groups have been considered.

7. Contradictory evidence has been addressed.

8. Confidence is reasonable.

9. The recommended engineering action follows from the evidence.

Important rules:

- If deterministic_issues is not empty,
  approved MUST be false.

- Experimental confirmation is required before approval.

- Do not invent evidence.

- Return only the requested structured result.


For this Level 5B exercise:

A successful targeted rerun of all 30 affected flashing tests
with a timeout above 13.8 seconds is sufficient experimental
confirmation of the timeout-mismatch mechanism.

A full regression is a recommended follow-up action,
but it is NOT required for verifier approval.

Residual camera and perception failures may remain unresolved
as long as they are clearly identified as separate mechanisms
and do not challenge the dominant root-cause conclusion.

Do not create new approval requirements beyond those explicitly
defined in this verification policy.

"""


    verifier_response = (
        client.responses.create(

            model="gpt-5.6",

            instructions=
                verifier_instructions,

            input=json.dumps(
                verification_package
            ),

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


    # --------------------------------------------------------
    # PYTHON HAS FINAL AUTHORITY OVER HARD FAILURES
    # --------------------------------------------------------

    if deterministic_issues:

        verdict["approved"] = False


        for issue in deterministic_issues:

            if issue not in verdict["issues"]:

                verdict[
                    "issues"
                ].append(issue)


    return verdict


# ============================================================
# LEVEL 5B AGENT INSTRUCTIONS
# ============================================================

agent_instructions = """
You are an autonomous ADAS HIL validation investigation agent.

You receive a high-level engineering goal rather than a fixed workflow.

Your job is to dynamically decide which tools to use and in what order.

Rules:

1. Start by calling record_plan with a concise task-level plan.

2. Gather ground-truth information using tools.

3. Do not assume regression values, failure counts,
   logs, build changes or known issues.

4. Identify the dominant failure mechanism.

5. Calculate:
   - overall regression failure rate
   - dominant failure-group share

6. Give each percentage calculation a clear human-readable name.

7. Correlate logs with build changes and known issues.

8. Investigate residual failure groups sufficiently to determine
   whether they challenge the dominant conclusion.

9. When the observational investigation appears complete,
   call finish_investigation to propose a conclusion.

10. Your proposed conclusion will be evaluated by an independent
    verifier.

11. Do not run run_targeted_validation before the verifier
    requests experimental confirmation.

12. If finish_investigation is rejected, treat the verifier
    feedback as new information.

13. Address every required verifier action.

14. Use run_targeted_validation when experimental confirmation
    of the timeout hypothesis is requested.

15. Re-submit finish_investigation after addressing verifier feedback.

16. Include any new experimental evidence ID in the revised
    evidence list.

17. Do not invent evidence or tool results.

18. Do not reveal private chain-of-thought.
    Expose only observable plans, actions, evidence and conclusions.
"""


# ============================================================
# HIGH-LEVEL GOAL
# ============================================================

goal = """
Investigate the latest HIL regression.

Determine the dominant root cause of the failures.

Calculate:

1. overall regression failure rate

2. percentage of the failure population explained
   by the dominant root cause

Investigate residual failures sufficiently to determine
whether they challenge the dominant root-cause conclusion.

Recommend the next engineering action.

Use evidence before reaching a conclusion.
"""


# ============================================================
# FIRST MODEL CALL
# ============================================================

response = client.responses.create(

    model="gpt-5.6",

    instructions=
        agent_instructions,

    input=
        goal,

    tools=
        tools
)


# ============================================================
# AUTONOMOUS VERIFY / REFLECT / RETRY LOOP
# ============================================================

MAX_AGENT_TURNS = 15

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

    approved_payload = None


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
        # CANDIDATE COMPLETION
        # ----------------------------------------------------

        if item.name == "finish_investigation":

            candidate_payload = args

            candidate_call_id = (
                item.call_id
            )

            continue


        # ----------------------------------------------------
        # EXECUTE NORMAL TOOL
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


        tool_outputs.append(

            {
                "type":
                    "function_call_output",

                "call_id":
                    item.call_id,

                "output":
                    json.dumps(result)
            }

        )


    # ========================================================
    # VERIFY CANDIDATE AFTER ALL OTHER TOOL RESULTS
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


        print(
            "\nCandidate root cause:",
            candidate_payload[
                "root_cause"
            ]
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


        # ====================================================
        # APPROVED
        # ====================================================

        if verdict["approved"]:

            approved_payload = (
                candidate_payload
            )


        # ====================================================
        # REJECTED
        # ====================================================

        else:

            rejection_feedback = {

                "status":
                    "REJECTED_BY_VERIFIER",

                "verification_attempt":
                    verification_attempt,

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


            # The rejected finish call receives
            # verifier feedback as its tool result.

            tool_outputs.append(

                {
                    "type":
                        "function_call_output",

                    "call_id":
                        candidate_call_id,

                    "output":
                        json.dumps(
                            rejection_feedback
                        )
                }

            )


    # ========================================================
    # APPROVED INVESTIGATION
    # ========================================================

    if approved_payload is not None:

        print(
            "\n========== INVESTIGATION VERIFIED =========="
        )


        print(
            "\nRoot cause:",
            approved_payload[
                "root_cause"
            ]
        )


        print(
            "\nConfidence:",
            approved_payload[
                "confidence"
            ]
        )


        print(
            "\nRegression failure rate:",
            approved_payload[
                "failure_rate_percent"
            ],
            "%"
        )


        print(
            "\nDominant cause share:",
            approved_payload[
                "dominant_cause_share_percent"
            ],
            "%"
        )


        print(
            "\nEvidence:",
            approved_payload[
                "evidence_ids"
            ]
        )


        print(
            "\nRecommended action:",
            approved_payload[
                "recommended_action"
            ]
        )


        print(
            "\nSummary:",
            approved_payload[
                "summary"
            ]
        )


        print(
            "\nVerification attempts:",
            verification_attempt
        )


        finished = True

        break


    # ========================================================
    # CONTINUE AFTER TOOLS / VERIFIER REJECTION
    # ========================================================

    if tool_outputs:

        response = client.responses.create(

            model="gpt-5.6",

            instructions=
                agent_instructions,

            previous_response_id=
                response.id,

            input=
                tool_outputs,

            tools=
                tools
        )


    # ========================================================
    # MODEL PRODUCED NO TOOL CALL
    # ========================================================

    else:

        response = client.responses.create(

            model="gpt-5.6",

            instructions=
                agent_instructions,

            previous_response_id=
                response.id,

            input="""
The investigation has not been verified as complete.

Continue the investigation.

If verifier feedback exists, address it.

If all evidence and verification requirements are satisfied,
submit finish_investigation again.
""",

            tools=
                tools
        )


# ============================================================
# SAFETY STOP
# ============================================================

if not finished:

    print(
        "\nAgent stopped because MAX_AGENT_TURNS was reached."
    )