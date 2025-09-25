import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from crewai import Agent, Task, Crew, LLM
from crewai_tools.adapters.mcp_adapter import MCPServerAdapter
from mcp import StdioServerParameters
from dotenv import load_dotenv

load_dotenv()

class CrewService:
    def __init__(self):
        self.llm = LLM(
            model="azure/gpt4o-qa-agentic-framework-dev",
            base_url="https://eastus2.api.cognitive.microsoft.com",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )
        self.active_crews: Dict[str, Any] = {}
        self.user_histories: Dict[str, List[Dict[str, Any]]] = {}
    
    async def get_mcp_tools(self, access_token: str) -> List[Any]:
        """Get MCP tools with OAuth token"""
        try:
            server_params = StdioServerParameters(
                command="npx.cmd",
                args=[
                    "-y", "mcp-remote", 
                    "https://mcp.atlassian.com/v1/sse",
                    "-v",
                    "--header", f"Authorization=Bearer {access_token}"
                ],
                env={
                    "UV_PYTHON": "3.12", 
                    "ATLASSIAN_ACCESS_TOKEN": access_token,
                    **os.environ
                },
                timeout_seconds=120
            )
            
            # This would normally be in an async context manager
            # For now, we'll return a mock or handle synchronously
            adapter = MCPServerAdapter(server_params)
            tools = list(adapter.__enter__())
            return tools
            
        except Exception as e:
            print(f"Error getting MCP tools: {e}")
            return []
    
    async def create_atlassian_agent(self, user_id: str, access_token: str) -> Optional[Agent]:
        """Create Atlassian agent for user"""
        try:
            tools = await self.get_mcp_tools(access_token)
            
            if not tools:
                return None
            
            agent = Agent(
                role="Atlassian helper",
                goal="Interact with Jira/Confluence using OAuth 2.1 authentication",
                backstory=f"A helpful assistant for Atlassian documentation with proper OAuth authentication for user {user_id}.",
                llm=self.llm,
                tools=tools
            )
            
            return agent
            
        except Exception as e:
            print(f"Error creating agent for user {user_id}: {e}")
            return None
    
    async def execute_query(
        self, 
        user_id: str, 
        query: str, 
        access_token: str
    ) -> Dict[str, Any]:
        """Execute Atlassian query for user"""
        try:
            # Create agent
            agent = await self.create_atlassian_agent(user_id, access_token)
            if not agent:
                return {
                    "success": False,
                    "error": "Failed to create Atlassian agent. Please check your authentication.",
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Create task
            task = Task(
                description=query,
                agent=agent,
                expected_output="Return results from authenticated Atlassian APIs",
                llm=self.llm
            )
            
            # Create crew
            crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=False,  # Set to False for web deployment
            )
            
            # Execute
            result = await asyncio.create_task(
                asyncio.to_thread(crew.kickoff)
            )
            
            # Store in history
            history_entry = {
                "query": query,
                "result": str(result),
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
            if user_id not in self.user_histories:
                self.user_histories[user_id] = []
            
            self.user_histories[user_id].append(history_entry)
            
            # Keep only last 50 queries per user
            if len(self.user_histories[user_id]) > 50:
                self.user_histories[user_id] = self.user_histories[user_id][-50:]
            
            return {
                "success": True,
                "result": str(result),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_entry = {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
            
            if user_id not in self.user_histories:
                self.user_histories[user_id] = []
            
            self.user_histories[user_id].append(error_entry)
            
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_user_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's query history"""
        if user_id not in self.user_histories:
            return []
        
        history = self.user_histories[user_id]
        return history[-limit:] if len(history) > limit else history
    
    def clear_user_history(self, user_id: str) -> bool:
        """Clear user's query history"""
        if user_id in self.user_histories:
            del self.user_histories[user_id]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        total_users = len(self.user_histories)
        total_queries = sum(len(history) for history in self.user_histories.values())
        
        return {
            "total_users": total_users,
            "total_queries": total_queries,
            "active_crews": len(self.active_crews)
        }
