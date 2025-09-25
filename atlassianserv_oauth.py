from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools.adapters.mcp_adapter import MCPServerAdapter
from mcp import StdioServerParameters
import os
import json
from dotenv import load_dotenv
from atlassian_oauth import AtlassianOAuthClient

# Load environment variables
load_dotenv()

llm = LLM(
model= "azure/gpt4o-qa-agentic-framework-dev",
base_url="https://eastus2.api.cognitive.microsoft.com",
api_key=os.getenv("AZURE_OPENAI_API_KEY", "6315b4d5c3fd4589aa81179e98194ccc"),
)

# Get OAuth token first
print("Setting up OAuth authentication...")
oauth_client = AtlassianOAuthClient()
token = oauth_client.get_valid_token()

# Load token details
with open('atlassian_token.json', 'r') as f:
    token_data = json.load(f)

print(f"Using OAuth token: {token_data['access_token'][:20]}...")

# Alternative approach: Use the MCP remote with authentication headers
# You might need to check if the MCP server supports OAuth in headers
server_params = StdioServerParameters(
command="npx.cmd",
args=[
    "-y", "mcp-remote", 
    "https://mcp.atlassian.com/v1/sse",
    "-v",
    "--header", f"Authorization=Bearer {token_data['access_token']}"
],
env={
    "UV_PYTHON": "3.12", 
    "ATLASSIAN_ACCESS_TOKEN": token_data['access_token'],
    **os.environ
},
timeout_seconds=120
)

try:
    with MCPServerAdapter(server_params) as tools:
        print("Available MCP Tools:",[tool.name for tool in tools])
        
        if not tools:
            print("No tools available. The MCP server might not be properly authenticated.")
            print("Please check if the server supports OAuth 2.1 authentication.")
            exit(1)
            
        atlassian_agent = Agent(
        role="Atlassian helper",
        goal="Interact with Jira/Confluence using OAuth 2.1 authentication",
        backstory="A helpful assistant for Atlassian documentation with proper OAuth authentication.",
        llm=llm,
        tools=tools
        )
        
        atlassian_task= Task(
        description="{question}",
        agent=atlassian_agent,
        expected_output="Return results from authenticated Atlassian APIs",
        output_file="output/atlassian_results.md",
        llm=llm
        )

        crew = Crew(
        agents=[atlassian_agent],
        tasks=[atlassian_task],
        verbose=True,
        )

        result = crew.kickoff(inputs={"question": input("What would you like to query Confluence/JIRA? ")})
        print("\nFinal Output:\n",result)
        
except Exception as e:
    print(f"Error connecting to MCP server: {e}")
    print("\nTroubleshooting steps:")
    print("1. Verify the MCP server supports OAuth 2.1 authentication")
    print("2. Check if the server expects different authentication format")
    print("3. Confirm your OAuth scopes include the necessary permissions")
    print("4. Try connecting directly to Atlassian APIs to test your token")
