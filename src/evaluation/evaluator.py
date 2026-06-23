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


def evaluate_dataset():

    base_dir = Path(__file__).resolve().parents[2]

    dataset_path = base_dir / "data" / "ground_truth_dataset.json"

    logger.info("Loading dataset from %s", dataset_path)

    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    questions = dataset["questions"]

    db = get_sql_database()

    total = len(questions)
    correct = 0
    rows = []

    logger.info("Starting evaluation for %d questions", total)

    for item in questions:

        qid = item["id"]
        question = item["question"]
        ground_truth_sql = item["ground_truth"]["sql_query"]

        logger.info("Evaluating Question %s", qid)

        response = agent.invoke(
            {"messages": [("user", question)]}
        )

        generated_sql, agent_result = extract_tool_output(response["messages"])

        try:
            expected_result = db.run(ground_truth_sql)
            expected_result = ast.literal_eval(expected_result)
        except Exception as e:
            logger.error("Ground truth SQL execution failed: %s", str(e))
            expected_result = []

        is_correct = compare_results(agent_result, expected_result)

        if is_correct:
            correct += 1

        rows.append(
            {
                "id": qid,
                "question": question,
                "generated_sql": generated_sql,
                "ground_truth_sql": ground_truth_sql,
                "agent_result": agent_result,
                "expected_result": expected_result,
                "is_correct": is_correct,
            }
        )

    accuracy = (correct / total) * 100 if total else 0.0

    logger.info("Evaluation completed")

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "rows": rows,
    }


# -----------------------------
# Run Evaluation
# -----------------------------
def run_evaluation():

    evaluation = evaluate_dataset()

    total = evaluation["total"]
    correct = evaluation["correct"]
    accuracy = evaluation["accuracy"]

    print("\n" + "=" * 80)
    print("PORTFOLIO AGENT EVALUATION")
    print("=" * 80)

    for row in evaluation["rows"]:

        # -----------------------------
        # Print Comparison
        # -----------------------------
        print("\n" + "-" * 80)
        print(f"Question {row['id']}: {row['question']}")

        print("\nGenerated SQL:")
        print(row["generated_sql"])

        print("\nGround Truth SQL:")
        print(row["ground_truth_sql"])

        print("\nAgent Result:")
        print(row["agent_result"])

        print("\nExpected Result:")
        print(row["expected_result"])

        print("\nResult:", "Correct" if row["is_correct"] else "Incorrect")

    # -----------------------------
    # Summary
    # -----------------------------
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)

    print(f"Total Questions : {total}")
    print(f"Correct Answers : {correct}")
    print(f"Accuracy        : {accuracy:.2f}%")