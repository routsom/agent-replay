"""Example: LangChain agent tracing with agent-replay.

This example demonstrates using the ReplayCallbackHandler
to trace LangChain chain executions.

Usage:
    pip install agent-replay[langchain] langchain-openai
    export OPENAI_API_KEY=your-key
    python examples/langchain_agent.py
"""

from agent_replay.integrations.langchain import ReplayCallbackHandler


def main() -> None:
    # This is a skeleton — fill in with your actual LangChain setup
    handler = ReplayCallbackHandler(
        session_name="langchain-example",
        tags=["example", "langchain"],
    )

    print("LangChain ReplayCallbackHandler is ready.")
    print("Attach it to your chain with:")
    print('  chain.with_config({"callbacks": [handler]})')
    print()
    print("All LLM calls, tool calls, and chain runs will be traced automatically.")
    print()

    # Example with a simple chain (requires langchain-openai):
    # from langchain_openai import ChatOpenAI
    # from langchain_core.prompts import ChatPromptTemplate
    #
    # llm = ChatOpenAI(model="gpt-4o")
    # prompt = ChatPromptTemplate.from_messages([
    #     ("user", "{input}")
    # ])
    # chain = prompt | llm
    # result = chain.with_config({"callbacks": [handler]}).invoke(
    #     {"input": "What is 2+2?"}
    # )
    # print(f"Result: {result.content}")

    handler.end()
    print("✅ Session recorded!")


if __name__ == "__main__":
    main()
