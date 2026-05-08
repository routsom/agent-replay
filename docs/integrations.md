# Integrations

agent-replay provides drop-in wrappers for popular AI frameworks. Each integration automatically records all API calls as steps.

## Anthropic

```python
from anthropic import Anthropic
from agent_replay.integrations.anthropic import ReplayClient

client = ReplayClient(Anthropic(), session_name="my-session")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain quantum computing."}],
)
client.end()
```

Install: `pip install agent-replay[anthropic]`

## OpenAI

```python
from openai import OpenAI
from agent_replay.integrations.openai import ReplayClient

client = ReplayClient(OpenAI(), session_name="chatbot")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
client.end()
```

Install: `pip install agent-replay[openai]`

## LangChain

```python
from agent_replay.integrations.langchain import ReplayCallbackHandler

handler = ReplayCallbackHandler(session_name="my-chain")
chain = my_chain.with_config({"callbacks": [handler]})
result = chain.invoke({"input": "Hello"})
handler.end()
```

Install: `pip install agent-replay[langchain]`

## Google ADK

```python
from agent_replay.integrations.google_adk import ReplayADKWrapper

with ReplayADKWrapper(session_name="adk-agent") as wrapper:
    result = wrapper.trace_call(
        func=agent.generate_content,
        model="gemini-2.0-flash-exp",
        input_data={"prompt": "Hello"},
        contents="Hello, world!",
    )
```

## CrewAI

```python
from agent_replay.integrations.crewai import ReplayCrewWrapper

with ReplayCrewWrapper(session_name="my-crew", model="gpt-4o") as wrapper:
    result = wrapper.trace_kickoff(crew)
```

## TypeScript

```typescript
import { Recorder } from 'agent-replay';

const recorder = new Recorder({ name: 'my-run', framework: 'anthropic' });
const session = await recorder.start();

const step = session.step('llm_call', { prompt });
// ... call your LLM ...
step.finish({
  output: { text: response.content[0].text },
  inputTokens: response.usage.input_tokens,
  outputTokens: response.usage.output_tokens,
});

await session.end();
```

## Custom Integration

Use the `Recorder` directly for any framework:

```python
from agent_replay import Recorder

with Recorder(name="custom", framework="my-framework", model="my-model") as r:
    step = r.step("llm_call", input={"prompt": "hello"})
    # ... your logic ...
    step.finish(output={"text": "response"}, input_tokens=10, output_tokens=20)
```
