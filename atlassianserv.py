
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools.adapters.mcp_adapter import MCPServerAdapter
from mcp import StdioServerParameters
import os
from dotenv import load_dotenv
from atlassian_oauth import AtlassianOAuthClient

# Load environment variables
load_dotenv()

llm = LLM(
model= "azure/gpt4o-qa-agentic-framework-dev",
base_url="https://eastus2.api.cognitive.microsoft.com", # Replace with your endpoint
api_key=os.getenv("AZURE_OPENAI_API_KEY", "6315b4d5c3fd4589aa81179e98194ccc"), # Use env var or fallback
 # Replace with KEY1 or KEY2
)

# Get OAuth token first
print("Setting up OAuth authentication...")
oauth_client = AtlassianOAuthClient()
token = oauth_client.get_valid_token()

# If running as subprocess with OAuth
server_params = StdioServerParameters(
command="npx.cmd",
args=["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse","-v"],
env={
    "UV_PYTHON": "3.12", 
    "ATLASSIAN_ACCESS_TOKEN": token['access_token'],  # Pass OAuth token
    **os.environ
},
#timeout=100  # Set timeout to 300 seconds (5 minutes)
timeout_seconds=120  # Adjust as needed, e.g., 30-60 seconds
)

with MCPServerAdapter(server_params) as tools:
    print("Available MCP Tools:",[tool.name for tool in tools])
    atlassian_agent = Agent(
    role="Atlassian helper",
    goal="Interact with Jira/Confluence",
    backstory="A helpful assistant for Atlassian documentation.",
    llm=llm,
    tools=tools
    )
    atlassian_task= Task(
    description="{question}",
    agent=atlassian_agent,
    expected_output="Return results",
    output_file="output/atlassian_results.md",
    llm=llm
    )

    crew = Crew(
    agents=[atlassian_agent],
    tasks=[atlassian_task],
    verbose=True,
    )

    result = crew.kickoff(inputs={"question": input("What would you like to query Confluence/JIRA?")})
    print("\nFinal Output:\n",result)