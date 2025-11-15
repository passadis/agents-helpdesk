# app/services/analytics.py
"""
Analytics agent for querying helpdesk data from Azure Table Storage.
This agent can answer natural language questions about tickets, categories, priorities, etc.
"""
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from collections import Counter
from pydantic import Field

from azure.data.tables import TableServiceClient
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient


# Azure Table Storage client
def get_table_client():
    """Get Azure Table Storage client."""
    conn_str = os.getenv("AZURE_TABLE_CONN_STR")
    table_name = os.getenv("AZURE_TABLE_NAME", "HelpdeskRequests")
    
    if not conn_str:
        raise ValueError("AZURE_TABLE_CONN_STR not configured")
    
    service_client = TableServiceClient.from_connection_string(conn_str)
    return service_client.get_table_client(table_name)


# ===== QUERY TOOLS =====
# These are the functions the agent can call to query the data

def count_tickets_by_category(
    category: Annotated[Optional[str], Field(description="Optional specific category to count (HR, IT, Finance, Operations, Other). Leave empty for all categories.")] = None
) -> str:
    """Count helpdesk requests by category. If category is specified, count only that category. Otherwise, return counts for all categories."""
    try:
        table_client = get_table_client()
        entities = list(table_client.list_entities())
        
        if category:
            # Count specific category (case-insensitive)
            count = sum(1 for e in entities if e.get('PartitionKey', '').lower() == category.lower())
            result = {category: count, "total": len(entities)}
        else:
            # Count all categories
            categories = [e.get('PartitionKey', 'Unknown') for e in entities]
            counts = dict(Counter(categories))
            result = {**counts, "total": len(entities)}
        
        return json.dumps(result)
    except Exception as ex:
        return json.dumps({"error": str(ex)})


def count_tickets_by_priority(
    priority: Annotated[Optional[str], Field(description="Optional specific priority to count (Low, Normal, High). Leave empty for all priorities.")] = None
) -> str:
    """Count helpdesk requests by priority level (Low, Normal, High)."""
    try:
        table_client = get_table_client()
        entities = list(table_client.list_entities())
        
        if priority:
            count = sum(1 for e in entities if e.get('Priority', '').lower() == priority.lower())
            result = {priority: count, "total": len(entities)}
        else:
            priorities = [e.get('Priority', 'Unknown') for e in entities]
            counts = dict(Counter(priorities))
            result = {**counts, "total": len(entities)}
        
        return json.dumps(result)
    except Exception as ex:
        return json.dumps({"error": str(ex)})


def get_recent_tickets(
    days: Annotated[int, Field(description="Number of days to look back. Use 1 for today, 7 for this week, 30 for this month.")] = 7,
    limit: Annotated[int, Field(description="Maximum number of requests to return")] = 10
) -> str:
    """Get recent helpdesk requests from the last N days."""
    try:
        table_client = get_table_client()
        entities = list(table_client.list_entities())
        
        # Calculate cutoff date (make it timezone-aware)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Filter and sort by timestamp
        recent = []
        for e in entities:
            # Try both Timestamp (auto-generated) and CreatedAt (our field)
            timestamp = e.get('Timestamp') or e.get('CreatedAt')
            
            # Handle different timestamp formats
            if timestamp:
                # If it's a string (ISO format from CreatedAt), parse it
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        continue
                
                # Make sure timestamp is timezone-aware
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                
                # Check if within date range
                if timestamp >= cutoff_date:
                    recent.append({
                        "title": e.get('Title', 'No title'),
                        "category": e.get('PartitionKey', 'Unknown'),
                        "priority": e.get('Priority', 'Unknown'),
                        "timestamp": timestamp.isoformat() if timestamp else None,
                        "actionHint": e.get('ActionHint', 'store-only')
                    })
        
        # Sort by timestamp descending
        recent.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        result = {
            "requests": recent[:limit],
            "total_found": len(recent),
            "days": days,
            "limit": limit
        }
        
        return json.dumps(result, default=str)
    except Exception as ex:
        return json.dumps({"error": str(ex)})


def count_tickets_by_action(
    action: Annotated[Optional[str], Field(description="Optional specific action to count (notify-team, create-task, create-ticket, store-only). Leave empty for all actions.")] = None
) -> str:
    """Count helpdesk requests by action type. Actions are: notify-team (Teams notification), create-task (Planner task), create-ticket (Power Automate ticket), or store-only (no action)."""
    try:
        table_client = get_table_client()
        entities = list(table_client.list_entities())
        
        if action:
            count = sum(1 for e in entities if e.get('ActionHint', '').lower() == action.lower())
            result = {
                action: count, 
                "total_requests": len(entities),
                "description": f"Requests with action '{action}'"
            }
        else:
            actions = [e.get('ActionHint', 'store-only') if e.get('ActionHint') else 'store-only' for e in entities]
            counts = dict(Counter(actions))
            result = {
                "action_breakdown": counts,
                "total_requests": len(entities),
                "description": "All action types: notify-team=Teams notification, create-task=Planner task, create-ticket=Power Automate ticket, store-only=no action"
            }
        
        return json.dumps(result)
    except Exception as ex:
        return json.dumps({"error": str(ex)})


def get_total_ticket_count() -> str:
    """Get the total count of all helpdesk requests in the system."""
    try:
        table_client = get_table_client()
        entities = list(table_client.list_entities())
        result = {"total_tickets": len(entities)}
        return json.dumps(result)
    except Exception as ex:
        return json.dumps({"error": str(ex)})


# ===== ANALYTICS AGENT =====

async def ask_analytics_agent(question: str) -> str:
    """
    Main entry point for the analytics agent.
    Takes a natural language question and returns an answer based on helpdesk data.
    
    Args:
        question: Natural language question about helpdesk data
    
    Returns:
        Natural language answer with insights
    """
    try:
        # Set up Azure OpenAI chat client
        chat_client = AzureOpenAIChatClient()
        
        # Define tools that the agent can use (just pass the functions directly)
        tools = [
            count_tickets_by_category,
            count_tickets_by_priority,
            get_recent_tickets,
            count_tickets_by_action,
            get_total_ticket_count
        ]
        
        # Create the analytics agent
        instructions = """You are a helpdesk analytics assistant. You help users understand their helpdesk request data by answering questions.

IMPORTANT TERMINOLOGY:
- Use "requests" not "tickets" as the general term
- Different action types exist based on ActionHint:
  * "notify-team": requests that notify Teams channel
  * "create-task": requests that create Planner tasks
  * "create-ticket": requests that create support tickets via Power Automate
  * "store-only": requests that are just stored without actions
- Only use "ticket" when specifically referring to "create-ticket" action type

Available data includes:
- Categories: HR, IT, Finance, Operations, Other
- Priority levels: Low, Normal, High
- Action types (ActionHint): notify-team, create-task, create-ticket, store-only
- Timestamps and recent activity

When answering:
1. Use the provided tools to query the data
2. Be precise with terminology - distinguish between requests, tasks, and tickets
3. Provide clear, specific numbers and breakdowns
4. Format responses in a friendly, conversational way
5. If asked about trends or comparisons, provide context
6. If multiple tools are needed, use them to build a complete answer

Be helpful, accurate, and insightful!"""
        
        agent = ChatAgent(
            name="HelpdeskAnalytics",
            chat_client=chat_client,
            instructions=instructions,
            tools=tools
        )
        
        # Run the agent with the user's question
        result = await agent.run(question)
        
        return result.text.strip()
        
    except Exception as ex:
        print(f"Analytics agent error: {ex}")
        return f"I encountered an error while analyzing the data: {str(ex)}. Please try rephrasing your question."
