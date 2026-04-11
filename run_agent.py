from src.agent.langgraph_workflow import agent

while True:

    user_input = input("\nAsk a question (or type 'exit'): ")

    if user_input.lower() == "exit":
        break

    response = agent.invoke(
        {
            "messages": [
                ("user", user_input)
            ]
        }
    )

    print("\nAnswer:\n")
    print(response["messages"][-1].content)