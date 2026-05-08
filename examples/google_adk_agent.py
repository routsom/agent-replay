"""Example: Google ADK agent tracing with agent-replay.

This example demonstrates using the ReplayADKWrapper
to trace Google ADK agent invocations.

Usage:
    pip install agent-replay google-genai
    export GOOGLE_API_KEY=your-key
    python examples/google_adk_agent.py
"""

from agent_replay.integrations.google_adk import ReplayADKWrapper


def main() -> None:
    print("Google ADK ReplayADKWrapper is ready.")
    print()

    # Example with Google Generative AI:
    # import google.generativeai as genai
    #
    # genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    # model = genai.GenerativeModel("gemini-2.0-flash-exp")
    #
    # with ReplayADKWrapper(session_name="adk-example") as wrapper:
    #     result = wrapper.trace_call(
    #         func=model.generate_content,
    #         model="gemini-2.0-flash-exp",
    #         input_data={"prompt": "Hello!"},
    #         contents="What is the meaning of life?",
    #     )
    #     print(f"Response: {result.text}")
    #
    # print("✅ Session recorded!")

    with ReplayADKWrapper(session_name="adk-example") as wrapper:
        print("Wrapper session started:", wrapper._recorder.session.id)
        print("Use wrapper.trace_call() to record API calls.")

    print("\n✅ Session recorded! Run 'agent-replay list' to see it.")


if __name__ == "__main__":
    main()
