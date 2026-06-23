import pandas as pd
import streamlit as st

from src.agent.langgraph_workflow import agent
from src.evaluation.evaluator import evaluate_dataset, extract_tool_output


st.set_page_config(page_title="Portfolio SQL Agent Demo", layout="wide")

st.title("Portfolio Analytics SQL Agent")
st.caption("Ask questions, inspect generated SQL, and run evaluation from one UI.")


if "qa_history" not in st.session_state:
    st.session_state.qa_history = []


with st.sidebar:
    st.header("Demo Controls")
    if st.button("Clear Q&A History", use_container_width=True):
        st.session_state.qa_history = []
        st.success("History cleared")


ask_tab, eval_tab = st.tabs(["Ask Agent", "Evaluation"])


with ask_tab:
    st.subheader("Ask a Portfolio Question")

    question = st.text_input(
        "Question",
        placeholder="Example: What is the top 5 holdings by market value?",
    )

    if st.button("Ask", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Running agent..."):
                response = agent.invoke({"messages": [("user", question.strip())]})

                answer = response["messages"][-1].content
                generated_sql, tool_result = extract_tool_output(response["messages"])

                st.session_state.qa_history.append(
                    {
                        "question": question.strip(),
                        "answer": answer,
                        "sql": generated_sql,
                        "tool_result": tool_result,
                    }
                )

    if st.session_state.qa_history:
        st.markdown("### Q&A History")

        for idx, item in enumerate(reversed(st.session_state.qa_history), start=1):
            st.markdown(f"#### Question {idx}")
            st.write(item["question"])

            st.markdown("**Answer**")
            st.write(item["answer"])

            st.markdown("**Generated SQL**")
            if item["sql"]:
                st.code(item["sql"], language="sql")
            else:
                st.info("No SQL generated for this question (the agent may have used a non-SQL path).")

            with st.expander("Tool Result"):
                st.write(item["tool_result"])

            st.divider()


with eval_tab:
    st.subheader("Run Dataset Evaluation")

    if st.button("Run Evaluation", type="primary", use_container_width=True):
        with st.spinner("Evaluating all questions..."):
            evaluation = evaluate_dataset()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Questions", evaluation["total"])
        c2.metric("Correct", evaluation["correct"])
        c3.metric("Accuracy", f"{evaluation['accuracy']:.2f}%")

        rows = evaluation["rows"]
        df = pd.DataFrame(rows)

        if not df.empty:
            df = df.rename(
                columns={
                    "id": "ID",
                    "question": "Question",
                    "generated_sql": "Generated SQL",
                    "ground_truth_sql": "Ground Truth SQL",
                    "agent_result": "Agent Result",
                    "expected_result": "Expected Result",
                    "is_correct": "Correct",
                }
            )
            st.dataframe(df, use_container_width=True)

            st.markdown("### SQL Comparison")
            for row in rows:
                with st.expander(f"Q{row['id']} - {'Correct' if row['is_correct'] else 'Incorrect'}"):
                    st.markdown("**Question**")
                    st.write(row["question"])

                    st.markdown("**Generated SQL**")
                    st.code(row["generated_sql"] or "", language="sql")

                    st.markdown("**Ground Truth SQL**")
                    st.code(row["ground_truth_sql"] or "", language="sql")

                    st.markdown("**Agent Result**")
                    st.write(row["agent_result"])

                    st.markdown("**Expected Result**")
                    st.write(row["expected_result"])
