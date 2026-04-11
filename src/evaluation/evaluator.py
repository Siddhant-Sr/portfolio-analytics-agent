import json
import logging
import ast
from pathlib import Path
from src.agent.langgraph_workflow import agent
from src.database.db_connection import get_sql_database


logger = logging.getLogger(__name__)




# -----------------------------
# Extract Tool Output
# -----------------------------
def extract_tool_output(messages):

    for msg in messages:
        if msg.type == "tool":
            try:
                payload = json.loads(msg.content)
                return payload.get("sql_query"), payload.get("result")
            except Exception:
                return None, None

    return None, None

# -----------------------------
# Normalize Results
# -----------------------------
def normalize_result(result):
    """
    Normalize SQL results so they can be compared reliably.
    Handles:
    - list vs tuple
    - stringified SQL results
    - ordering differences
    """

    if result is None:
        return []

    # Convert string results like "[[13]]"
    if isinstance(result, str):
        try:
            result = ast.literal_eval(result)
        except Exception:
            return []

    normalized = []

    for row in result:
        if isinstance(row, (list, tuple)):
            normalized.append(tuple(row))
        else:
            normalized.append((row,))

    return sorted(normalized)
# -----------------------------
# Compare Results
# -----------------------------
def compare_results(agent_result, expected_result):

    agent_norm = normalize_result(agent_result)
    expected_norm = normalize_result(expected_result)

    return agent_norm == expected_norm


# -----------------------------
# Run Evaluation
# -----------------------------
def run_evaluation():

    base_dir = Path(__file__).resolve().parents[2]

    dataset_path = base_dir / "data" / "ground_truth_dataset.json"

    logger.info("Loading dataset from %s", dataset_path)

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    questions = dataset["questions"]

    db = get_sql_database()

    total = len(questions)
    correct = 0

    logger.info("Starting evaluation for %d questions", total)

    print("\n" + "=" * 80)
    print("PORTFOLIO AGENT EVALUATION")
    print("=" * 80)

    for item in questions:

        qid = item["id"]
        question = item["question"]
        ground_truth_sql = item["ground_truth"]["sql_query"]

        logger.info("Evaluating Question %s", qid)

        # -----------------------------
        # Run Agent
        # -----------------------------
        response = agent.invoke(
            {"messages": [("user", question)]}
        )

        generated_sql, agent_result = extract_tool_output(response["messages"])

        # -----------------------------
        # Run Ground Truth SQL
        # -----------------------------
        try:
            expected_result = db.run(ground_truth_sql)
            expected_result = ast.literal_eval(expected_result)
        except Exception as e:
            logger.error("Ground truth SQL execution failed: %s", str(e))
            expected_result = []

        # -----------------------------
        # Compare Results
        # -----------------------------
        is_correct = compare_results(agent_result, expected_result)

        if is_correct:
            correct += 1

        # -----------------------------
        # Print Comparison
        # -----------------------------
        print("\n" + "-" * 80)
        print(f"Question {qid}: {question}")

        print("\nGenerated SQL:")
        print(generated_sql)

        print("\nGround Truth SQL:")
        print(ground_truth_sql)

        print("\nAgent Result:")
        print(agent_result)

        print("\nExpected Result:")
        print(expected_result)

        print("\nResult:", "Correct" if is_correct else "Incorrect")

    # -----------------------------
    # Summary
    # -----------------------------
    accuracy = (correct / total) * 100

    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    print(f"Total Questions : {total}")
    print(f"Correct Answers : {correct}")
    print(f"Accuracy        : {accuracy:.2f}%")

    logger.info("Evaluation completed")