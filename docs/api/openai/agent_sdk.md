Core concepts:
Agents: LLMs configured with instructions, tools, guardrails, and handoffs
Handoffs: A specialized tool call used by the Agents SDK for transferring control between agents
Guardrails: Configurable safety checks for input and output validation
Sessions: Automatic conversation history management across agent runs
Tracing: Built-in tracking of agent runs, allowing you to view, debug and optimize your workflows
Explore the examples directory to see the SDK in action, and read our documentation for more details.

Get started
To get started, set up your Python environment (Python 3.9 or newer required), and then install OpenAI Agents SDK package.

venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install openai-agents
For voice support, install with the optional voice group: pip install 'openai-agents[voice]'.

For Redis session support, install with the optional redis group: pip install 'openai-agents[redis]'.

uv
If you're familiar with uv, using the tool would be even similar:

uv init
uv add openai-agents
For voice support, install with the optional voice group: uv add 'openai-agents[voice]'.

For Redis session support, install with the optional redis group: uv add 'openai-agents[redis]'.

Hello world example
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant")

result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
print(result.final_output)

# Code within the code,
# Functions calling themselves,
# Infinite loop's dance.
(If running this, ensure you set the OPENAI_API_KEY environment variable)

(For Jupyter notebook users, see hello_world_jupyter.ipynb)

Handoffs example
from agents import Agent, Runner
import asyncio

spanish_agent = Agent(
    name="Spanish agent",
    instructions="You only speak Spanish.",
)

english_agent = Agent(
    name="English agent",
    instructions="You only speak English",
)

triage_agent = Agent(
    name="Triage agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[spanish_agent, english_agent],
)


async def main():
    result = await Runner.run(triage_agent, input="Hola, ¿cómo estás?")
    print(result.final_output)
    # ¡Hola! Estoy bien, gracias por preguntar. ¿Y tú, cómo estás?


if __name__ == "__main__":
    asyncio.run(main())
Functions example
import asyncio

from agents import Agent, Runner, function_tool


@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."


agent = Agent(
    name="Hello world",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


async def main():
    result = await Runner.run(agent, input="What's the weather in Tokyo?")
    print(result.final_output)
    # The weather in Tokyo is sunny.


if __name__ == "__main__":
    asyncio.run(main())
The agent loop
When you call Runner.run(), we run a loop until we get a final output.

We call the LLM, using the model and settings on the agent, and the message history.
The LLM returns a response, which may include tool calls.
If the response has a final output (see below for more on this), we return it and end the loop.
If the response has a handoff, we set the agent to the new agent and go back to step 1.
We process the tool calls (if any) and append the tool responses messages. Then we go to step 1.
There is a max_turns parameter that you can use to limit the number of times the loop executes.

Final output
Final output is the last thing the agent produces in the loop.

If you set an output_type on the agent, the final output is when the LLM returns something of that type. We use structured outputs for this.
If there's no output_type (i.e. plain text responses), then the first LLM response without any tool calls or handoffs is considered as the final output.
As a result, the mental model for the agent loop is:

If the current agent has an output_type, the loop runs until the agent produces structured output matching that type.
If the current agent does not have an output_type, the loop runs until the current agent produces a message without any tool calls/handoffs.
Common agent patterns
The Agents SDK is designed to be highly flexible, allowing you to model a wide range of LLM workflows including deterministic flows, iterative loops, and more. See examples in examples/agent_patterns.

Tracing
The Agents SDK automatically traces your agent runs, making it easy to track and debug the behavior of your agents. Tracing is extensible by design, supporting custom spans and a wide variety of external destinations, including Logfire, AgentOps, Braintrust, Scorecard, and Keywords AI. For more details about how to customize or disable tracing, see Tracing, which also includes a larger list of external tracing processors.

Long running agents & human-in-the-loop
You can use the Agents SDK Temporal integration to run durable, long-running workflows, including human-in-the-loop tasks. View a demo of Temporal and the Agents SDK working in action to complete long-running tasks in this video, and view docs here.

Sessions
The Agents SDK provides built-in session memory to automatically maintain conversation history across multiple agent runs, eliminating the need to manually handle .to_input_list() between turns.

Quick start
from agents import Agent, Runner, SQLiteSession

# Create agent
agent = Agent(
    name="Assistant",
    instructions="Reply very concisely.",
)

# Create a session instance
session = SQLiteSession("conversation_123")

# First turn
result = await Runner.run(
    agent,
    "What city is the Golden Gate Bridge in?",
    session=session
)
print(result.final_output)  # "San Francisco"

# Second turn - agent automatically remembers previous context
result = await Runner.run(
    agent,
    "What state is it in?",
    session=session
)
print(result.final_output)  # "California"

# Also works with synchronous runner
result = Runner.run_sync(
    agent,
    "What's the population?",
    session=session
)
print(result.final_output)  # "Approximately 39 million"
Session options
No memory (default): No session memory when session parameter is omitted
session: Session = DatabaseSession(...): Use a Session instance to manage conversation history
from agents import Agent, Runner, SQLiteSession

# SQLite - file-based or in-memory database
session = SQLiteSession("user_123", "conversations.db")

# Redis - for scalable, distributed deployments
# from agents.extensions.memory import RedisSession
# session = RedisSession.from_url("user_123", url="redis://localhost:6379/0")

agent = Agent(name="Assistant")

# Different session IDs maintain separate conversation histories
result1 = await Runner.run(
    agent,
    "Hello",
    session=session
)
result2 = await Runner.run(
    agent,
    "Hello",
    session=SQLiteSession("user_456", "conversations.db")
)
Custom session implementations
You can implement your own session memory by creating a class that follows the Session protocol:

from agents.memory import Session
from typing import List

class MyCustomSession:
    """Custom session implementation following the Session protocol."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        # Your initialization here

    async def get_items(self, limit: int | None = None) -> List[dict]:
        # Retrieve conversation history for the session
        pass

    async def add_items(self, items: List[dict]) -> None:
        # Store new items for the session
        pass

    async def pop_item(self) -> dict | None:
        # Remove and return the most recent item from the session
        pass

    async def clear_session(self) -> None:
        # Clear all items for the session
        pass

# Use your custom session
agent = Agent(name="Assistant")
result = await Runner.run(
    agent,
    "Hello",
    session=MyCustomSession("my_session")
)


Agents
Agents are the core building block in your apps. An agent is a large language model (LLM), configured with instructions and tools.

Basic configuration
The most common properties of an agent you'll configure are:

name: A required string that identifies your agent.
instructions: also known as a developer message or system prompt.
model: which LLM to use, and optional model_settings to configure model tuning parameters like temperature, top_p, etc.
tools: Tools that the agent can use to achieve its tasks.

from agents import Agent, ModelSettings, function_tool

@function_tool
def get_weather(city: str) -> str:
    """returns weather info for the specified city."""
    return f"The weather in {city} is sunny"

agent = Agent(
    name="Haiku agent",
    instructions="Always respond in haiku form",
    model="gpt-5-nano",
    tools=[get_weather],
)
Context
Agents are generic on their context type. Context is a dependency-injection tool: it's an object you create and pass to Runner.run(), that is passed to every agent, tool, handoff etc, and it serves as a grab bag of dependencies and state for the agent run. You can provide any Python object as the context.


@dataclass
class UserContext:
    name: str
    uid: str
    is_pro_user: bool

    async def fetch_purchases() -> list[Purchase]:
        return ...

agent = Agent[UserContext](
    ...,
)
Output types
By default, agents produce plain text (i.e. str) outputs. If you want the agent to produce a particular type of output, you can use the output_type parameter. A common choice is to use Pydantic objects, but we support any type that can be wrapped in a Pydantic TypeAdapter - dataclasses, lists, TypedDict, etc.


from pydantic import BaseModel
from agents import Agent


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

agent = Agent(
    name="Calendar extractor",
    instructions="Extract calendar events from text",
    output_type=CalendarEvent,
)
Note

When you pass an output_type, that tells the model to use structured outputs instead of regular plain text responses.

Multi-agent system design patterns
There are many ways to design multi‑agent systems, but we commonly see two broadly applicable patterns:

Manager (agents as tools): A central manager/orchestrator invokes specialized sub‑agents as tools and retains control of the conversation.
Handoffs: Peer agents hand off control to a specialized agent that takes over the conversation. This is decentralized.
See our practical guide to building agents for more details.

Manager (agents as tools)
The customer_facing_agent handles all user interaction and invokes specialized sub‑agents exposed as tools. Read more in the tools documentation.


from agents import Agent

booking_agent = Agent(...)
refund_agent = Agent(...)

customer_facing_agent = Agent(
    name="Customer-facing agent",
    instructions=(
        "Handle all direct user communication. "
        "Call the relevant tools when specialized expertise is needed."
    ),
    tools=[
        booking_agent.as_tool(
            tool_name="booking_expert",
            tool_description="Handles booking questions and requests.",
        ),
        refund_agent.as_tool(
            tool_name="refund_expert",
            tool_description="Handles refund questions and requests.",
        )
    ],
)
Handoffs
Handoffs are sub‑agents the agent can delegate to. When a handoff occurs, the delegated agent receives the conversation history and takes over the conversation. This pattern enables modular, specialized agents that excel at a single task. Read more in the handoffs documentation.


from agents import Agent

booking_agent = Agent(...)
refund_agent = Agent(...)

triage_agent = Agent(
    name="Triage agent",
    instructions=(
        "Help the user with their questions. "
        "If they ask about booking, hand off to the booking agent. "
        "If they ask about refunds, hand off to the refund agent."
    ),
    handoffs=[booking_agent, refund_agent],
)
Dynamic instructions
In most cases, you can provide instructions when you create the agent. However, you can also provide dynamic instructions via a function. The function will receive the agent and context, and must return the prompt. Both regular and async functions are accepted.


def dynamic_instructions(
    context: RunContextWrapper[UserContext], agent: Agent[UserContext]
) -> str:
    return f"The user's name is {context.context.name}. Help them with their questions."


agent = Agent[UserContext](
    name="Triage agent",
    instructions=dynamic_instructions,
)
Lifecycle events (hooks)
Sometimes, you want to observe the lifecycle of an agent. For example, you may want to log events, or pre-fetch data when certain events occur. You can hook into the agent lifecycle with the hooks property. Subclass the AgentHooks class, and override the methods you're interested in.

Guardrails
Guardrails allow you to run checks/validations on user input in parallel to the agent running, and on the agent's output once it is produced. For example, you could screen the user's input and agent's output for relevance. Read more in the guardrails documentation.

Cloning/copying agents
By using the clone() method on an agent, you can duplicate an Agent, and optionally change any properties you like.


pirate_agent = Agent(
    name="Pirate",
    instructions="Write like a pirate",
    model="gpt-4.1",
)

robot_agent = pirate_agent.clone(
    name="Robot",
    instructions="Write like a robot",
)
Forcing tool use
Supplying a list of tools doesn't always mean the LLM will use a tool. You can force tool use by setting ModelSettings.tool_choice. Valid values are:

auto, which allows the LLM to decide whether or not to use a tool.
required, which requires the LLM to use a tool (but it can intelligently decide which tool).
none, which requires the LLM to not use a tool.
Setting a specific string e.g. my_tool, which requires the LLM to use that specific tool.

from agents import Agent, Runner, function_tool, ModelSettings

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"

agent = Agent(
    name="Weather Agent",
    instructions="Retrieve weather details.",
    tools=[get_weather],
    model_settings=ModelSettings(tool_choice="get_weather")
)
Tool Use Behavior
The tool_use_behavior parameter in the Agent configuration controls how tool outputs are handled:

"run_llm_again": The default. Tools are run, and the LLM processes the results to produce a final response.
"stop_on_first_tool": The output of the first tool call is used as the final response, without further LLM processing.

from agents import Agent, Runner, function_tool, ModelSettings

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"

agent = Agent(
    name="Weather Agent",
    instructions="Retrieve weather details.",
    tools=[get_weather],
    tool_use_behavior="stop_on_first_tool"
)
StopAtTools(stop_at_tool_names=[...]): Stops if any specified tool is called, using its output as the final response.

from agents import Agent, Runner, function_tool
from agents.agent import StopAtTools

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"

@function_tool
def sum_numbers(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

agent = Agent(
    name="Stop At Stock Agent",
    instructions="Get weather or sum numbers.",
    tools=[get_weather, sum_numbers],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["get_weather"])
)
ToolsToFinalOutputFunction: A custom function that processes tool results and decides whether to stop or continue with the LLM.

from agents import Agent, Runner, function_tool, FunctionToolResult, RunContextWrapper
from agents.agent import ToolsToFinalOutputResult
from typing import List, Any

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"

def custom_tool_handler(
    context: RunContextWrapper[Any],
    tool_results: List[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    """Processes tool results to decide final output."""
    for result in tool_results:
        if result.output and "sunny" in result.output:
            return ToolsToFinalOutputResult(
                is_final_output=True,
                final_output=f"Final weather: {result.output}"
            )
    return ToolsToFinalOutputResult(
        is_final_output=False,
        final_output=None
    )

agent = Agent(
    name="Weather Agent",
    instructions="Retrieve weather details.",
    tools=[get_weather],
    tool_use_behavior=custom_tool_handler
)
Note

To prevent infinite loops, the framework automatically resets tool_choice to "auto" after a tool call. This behavior is configurable via agent.reset_tool_choice. The infinite loop is because tool results are sent to the LLM, which then generates another tool call because of tool_choice, ad infinitum.