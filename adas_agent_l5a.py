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
            "Measured ECU boot-ready time increased from approximately 7.1 s to 13.8 s.",
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

        if any(word in searchable_text for word in words):

            matches.append(issue)

    return matches


def calculate_percentage(part, total, metric_name):

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
        "metric": metric_name
    }


# ============================================================
# TOOL DEFINITIONS FOR THE LLM
# ============================================================

tools = [

    # --------------------------------------------------------
    # PLAN TOOL
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "record_plan",

        "description":
            "Record a short task-level action plan before investigating. "
            "The plan should contain observable actions, not hidden reasoning.",

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
            "Inspect detailed log evidence for a specific failure group.",

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
            "Inspect relevant changes introduced in a software build.",

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
            "Search known engineering issues related to an observed symptom.",

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

                "metric_name": {
                    "type": "string",
                    "description":
                        "Human-readable name of the percentage being calculated."
                }
            },

            "required": [
                "part",
                "total",
                "metric_name"
            ]
        }
    },


    # --------------------------------------------------------
    # FINISH TOOL
    # --------------------------------------------------------

    {
        "type": "function",

        "name": "finish_investigation",

        "description":
            "Call this only when the investigation is complete and sufficient "
            "evidence supports the conclusion.",

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

def execute_tool(name, args):

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
            args["metric_name"]
        )


    else:

        return {
            "error": f"Unknown tool: {name}"
        }


# ============================================================
# LEVEL 5A AGENT INSTRUCTIONS
# ============================================================

agent_instructions = """
You are an autonomous ADAS HIL validation investigation agent.

You receive a high-level engineering goal rather than a fixed workflow.

Your job is to dynamically decide which tools to use and in what order.

Rules:

1. Start by calling record_plan with a concise task-level plan.

2. Gather ground-truth data using tools.

3. Do not assume regression values, failure counts, logs or build changes.

4. Inspect enough evidence to identify the dominant failure mechanism.

5. Calculate:
   - overall regression failure rate
   - percentage of failures belonging to the dominant failure group

6. Give each percentage calculation a clear human-readable metric name.

7. Correlate logs with build changes or known issues where useful.

8. Investigate residual failure groups sufficiently to ensure they do not
   challenge the dominant root-cause conclusion.

9. Adapt the investigation if evidence contradicts the current hypothesis.

10. Do not stop merely because you have a plausible explanation.

11. Call finish_investigation only when you believe the goal has been achieved.

12. Include evidence IDs supporting the conclusion.

13. Confidence must be between 0 and 1.

14. Do not invent tool results.

15. Do not reveal private chain-of-thought.
    Use only concise observable plans, actions, evidence and conclusions.
"""


# ============================================================
# HIGH-LEVEL GOAL
# ============================================================

goal = """
Investigate the latest HIL regression.

Determine the dominant root cause of the failures.

Calculate:
1. the overall regression failure rate
2. how much of the failure population is explained by the dominant root cause

Investigate the remaining failure groups sufficiently to determine whether
they challenge the dominant root-cause conclusion.

Recommend the next engineering action.

Use evidence before reaching a conclusion.
"""


# ============================================================
# FIRST MODEL CALL
# ============================================================

response = client.responses.create(

    model="gpt-5.6",

    instructions=agent_instructions,

    input=goal,

    tools=tools
)


# ============================================================
# AUTONOMOUS AGENT LOOP
# ============================================================

MAX_AGENT_TURNS = 12

finished = False


for turn in range(
    1,
    MAX_AGENT_TURNS + 1
):

    print(
        f"\n========== Autonomous Turn {turn} =========="
    )


    tool_outputs = []

    finish_payload = None


    for item in response.output:


        if item.type == "function_call":

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


            # ------------------------------------------------
            # COMPLETION SIGNAL
            # ------------------------------------------------

            if item.name == "finish_investigation":

                finish_payload = args

                continue


            # ------------------------------------------------
            # EXECUTE TOOL
            # ------------------------------------------------

            result = execute_tool(
                item.name,
                args
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
    # AGENT DECLARED COMPLETION
    # ========================================================

    if finish_payload is not None:

        print(
            "\n========== INVESTIGATION COMPLETE =========="
        )


        print(
            "\nRoot cause:",
            finish_payload["root_cause"]
        )


        print(
            "\nConfidence:",
            finish_payload["confidence"]
        )


        print(
            "\nRegression failure rate:",
            finish_payload["failure_rate_percent"],
            "%"
        )


        print(
            "\nDominant cause share:",
            finish_payload["dominant_cause_share_percent"],
            "%"
        )


        print(
            "\nEvidence:",
            finish_payload["evidence_ids"]
        )


        print(
            "\nRecommended action:",
            finish_payload["recommended_action"]
        )


        print(
            "\nSummary:",
            finish_payload["summary"]
        )


        finished = True

        break


    # ========================================================
    # CONTINUE AUTONOMOUS LOOP
    # ========================================================

    if tool_outputs:

        response = client.responses.create(

            model="gpt-5.6",

            instructions=agent_instructions,

            previous_response_id=response.id,

            input=tool_outputs,

            tools=tools
        )


    else:

        # Model stopped without declaring completion.

        response = client.responses.create(

            model="gpt-5.6",

            instructions=agent_instructions,

            previous_response_id=response.id,

            input="""
The investigation is not complete yet.

Continue gathering evidence or,
if all success criteria are satisfied,
call finish_investigation.
""",

            tools=tools
        )


# ============================================================
# SAFETY STOP
# ============================================================

if not finished:

    print(
        "\nAgent stopped because MAX_AGENT_TURNS was reached."
    )