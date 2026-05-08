"""Example: Basic Anthropic SDK tracing with agent-replay.

This example demonstrates using the ReplayClient wrapper
to automatically trace all Anthropic API calls.

Usage:
    pip install agent-replay[anthropic]
    export ANTHROPIC_API_KEY=your-key
    python examples/basic_anthropic.py
"""

from anthropic import Anthropic
from agent_replay.integrations.anthropic import ReplayClient


def main() -> None:
    # Wrap the Anthropic client — tracing is automatic
    client = ReplayClient(
        Anthropic(),
        session_name="basic-example",
        tags=["example", "anthropic"],
    )

    # Use exactly like the normal Anthropic client
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[
            {"role": "user", "content": "What is the capital of France? Answer in one sentence."}
        ],
    )

    print(f"Response: {response.content[0].text}")

    # End the session
    client.end()
    print("\n✅ Session recorded! Run 'agent-replay list' to see it.")


if __name__ == "__main__":
    main()
