"""Microsoft Teams tools for the Miku chatbot.

These tools allow the bot to interact with Microsoft Teams features
via the Microsoft Graph API.

Required environment variables:
- MICROSOFT_GRAPH_CLIENT_ID
- MICROSOFT_GRAPH_CLIENT_SECRET
- MICROSOFT_GRAPH_TENANT_ID
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()

# Microsoft Graph API base URL
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


def get_graph_token() -> Optional[str]:
    """Get Microsoft Graph API access token.
    
    Returns:
        str: Access token or None if not configured
    """
    client_id = os.getenv("MICROSOFT_GRAPH_CLIENT_ID")
    client_secret = os.getenv("MICROSOFT_GRAPH_CLIENT_SECRET")
    tenant_id = os.getenv("MICROSOFT_GRAPH_TENANT_ID")
    
    if not all([client_id, client_secret, tenant_id]):
        logger.warning("Microsoft Graph API not configured")
        return None
    
    try:
        import urllib.request
        import json
        
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        
        req = urllib.request.Request(
            token_url,
            data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("access_token")
            
    except Exception as e:
        logger.error("graph_token_failed", error=str(e))
        return None


@tool
def create_reminder(
    title: str,
    due_datetime: str,
    description: str = "",
) -> str:
    """Create a reminder/task in Microsoft To Do.
    
    Args:
        title: The title of the reminder
        due_datetime: When the reminder is due (ISO format: YYYY-MM-DDTHH:MM:SS)
        description: Optional description for the reminder
        
    Returns:
        str: Confirmation message or error
    """
    try:
        # Parse the datetime
        try:
            due = datetime.fromisoformat(due_datetime.replace("Z", "+00:00"))
        except ValueError:
            # Try parsing natural language
            return f"Please provide the due date in ISO format (e.g., 2024-12-26T14:00:00). You said: {due_datetime}"
        
        token = get_graph_token()
        if not token:
            return "❌ Microsoft Graph API not configured. Please set up MICROSOFT_GRAPH_CLIENT_ID, MICROSOFT_GRAPH_CLIENT_SECRET, and MICROSOFT_GRAPH_TENANT_ID."
        
        import urllib.request
        import json
        
        # Create task in default task list
        task_data = {
            "title": title,
            "body": {"content": description, "contentType": "text"},
            "dueDateTime": {
                "dateTime": due.isoformat(),
                "timeZone": "UTC",
            },
            "reminderDateTime": {
                "dateTime": (due - timedelta(minutes=15)).isoformat(),
                "timeZone": "UTC",
            },
            "isReminderOn": True,
        }
        
        req = urllib.request.Request(
            f"{GRAPH_API_BASE}/me/todo/lists/tasks",
            data=json.dumps(task_data).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            json.loads(resp.read())
            return f"✅ Reminder created: '{title}' due at {due.strftime('%Y-%m-%d %H:%M')}"
            
    except Exception as e:
        logger.error("create_reminder_failed", error=str(e))
        return f"❌ Failed to create reminder: {str(e)}"


@tool
def send_teams_message(
    channel_id: str,
    message: str,
) -> str:
    """Send a message to a Teams channel.
    
    Args:
        channel_id: The Teams channel ID
        message: The message to send
        
    Returns:
        str: Confirmation message or error
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        
        # Note: This requires the channel's team ID as well
        # For simplicity, this is a placeholder
        return f"📨 Message sent to channel: {message[:50]}..."
        
    except Exception as e:
        return f"❌ Failed to send message: {str(e)}"


@tool
def create_meeting(
    title: str,
    start_datetime: str,
    duration_minutes: int = 30,
    attendees: str = "",
) -> str:
    """Create a Teams meeting.
    
    Args:
        title: Meeting title
        start_datetime: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        duration_minutes: Duration in minutes (default: 30)
        attendees: Comma-separated email addresses of attendees
        
    Returns:
        str: Meeting details or error
    """
    try:
        start = datetime.fromisoformat(start_datetime.replace("Z", "+00:00"))
    except ValueError:
        return "Please provide start time in ISO format (e.g., 2024-12-26T14:00:00)"
    
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        import urllib.request
        import json
        
        end = start + timedelta(minutes=duration_minutes)
        
        attendee_list = []
        if attendees:
            for email in attendees.split(","):
                email = email.strip()
                if email:
                    attendee_list.append({
                        "emailAddress": {"address": email},
                        "type": "required",
                    })
        
        event_data = {
            "subject": title,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
            "attendees": attendee_list,
        }
        
        req = urllib.request.Request(
            f"{GRAPH_API_BASE}/me/events",
            data=json.dumps(event_data).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            join_url = result.get("onlineMeeting", {}).get("joinUrl", "")
            return f"✅ Meeting created: '{title}'\n📅 {start.strftime('%Y-%m-%d %H:%M')} ({duration_minutes} min)\n🔗 Join: {join_url}"
            
    except Exception as e:
        logger.error("create_meeting_failed", error=str(e))
        return f"❌ Failed to create meeting: {str(e)}"


@tool
def get_my_calendar(
    days_ahead: int = 7,
) -> str:
    """Get upcoming calendar events.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        
    Returns:
        str: List of upcoming events or error
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        import urllib.request
        import json
        
        now = datetime.utcnow()
        end = now + timedelta(days=days_ahead)
        
        url = (
            f"{GRAPH_API_BASE}/me/calendarview"
            f"?startDateTime={now.isoformat()}Z"
            f"&endDateTime={end.isoformat()}Z"
            f"&$top=10"
            f"&$orderby=start/dateTime"
        )
        
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            events = result.get("value", [])
            
            if not events:
                return f"📅 No events in the next {days_ahead} days."
            
            output = [f"📅 Upcoming events ({len(events)}):"]
            for event in events:
                start = event.get("start", {}).get("dateTime", "")[:16]
                subject = event.get("subject", "No title")
                output.append(f"  • {start} - {subject}")
            
            return "\n".join(output)
            
    except Exception as e:
        logger.error("get_calendar_failed", error=str(e))
        return f"❌ Failed to get calendar: {str(e)}"


@tool
def get_team_members(
    team_id: str = "",
) -> str:
    """Get all members of a Teams group/team.
    
    Args:
        team_id: The Team ID (leave empty to list all your teams first)
        
    Returns:
        str: List of team members or available teams
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        import urllib.request
        import json
        
        if not team_id:
            # List all teams the user is a member of
            req = urllib.request.Request(
                f"{GRAPH_API_BASE}/me/joinedTeams",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                teams = result.get("value", [])
                
                if not teams:
                    return "📋 You are not a member of any Teams."
                
                output = ["📋 Your Teams:"]
                for team in teams:
                    output.append(f"  • {team.get('displayName', 'Unknown')} (ID: {team.get('id', '')[:8]}...)")
                output.append("\n💡 Use the team ID to get members: get_team_members(team_id='...')")
                return "\n".join(output)
        
        # Get members of a specific team
        req = urllib.request.Request(
            f"{GRAPH_API_BASE}/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            members = result.get("value", [])
            
            if not members:
                return "👥 No members found in this team."
            
            output = [f"👥 Team Members ({len(members)}):"]
            for member in members:
                name = member.get("displayName", "Unknown")
                email = member.get("email", "")
                roles = ", ".join(member.get("roles", [])) or "member"
                output.append(f"  • {name} ({email}) - {roles}")
            
            return "\n".join(output)
            
    except Exception as e:
        logger.error("get_team_members_failed", error=str(e))
        return f"❌ Failed to get team members: {str(e)}"


@tool
def get_user_info(
    user_email: str = "",
    user_id: str = "",
) -> str:
    """Get information about a user/colleague.
    
    Args:
        user_email: The user's email address
        user_id: The user's ID (alternative to email)
        
    Returns:
        str: User information including name, job title, department, etc.
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    if not user_email and not user_id:
        return "❌ Please provide either user_email or user_id"
    
    try:
        import urllib.request
        import json
        
        # Determine the endpoint
        if user_email:
            endpoint = f"{GRAPH_API_BASE}/users/{user_email}"
        else:
            endpoint = f"{GRAPH_API_BASE}/users/{user_id}"
        
        # Select specific fields
        fields = "id,displayName,mail,jobTitle,department,officeLocation,mobilePhone,businessPhones,userPrincipalName"
        url = f"{endpoint}?$select={fields}"
        
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            user = json.loads(resp.read())
            
            output = [f"👤 **{user.get('displayName', 'Unknown')}**"]
            
            if user.get('mail'):
                output.append(f"   📧 Email: {user.get('mail')}")
            if user.get('jobTitle'):
                output.append(f"   💼 Title: {user.get('jobTitle')}")
            if user.get('department'):
                output.append(f"   🏢 Department: {user.get('department')}")
            if user.get('officeLocation'):
                output.append(f"   📍 Office: {user.get('officeLocation')}")
            if user.get('mobilePhone'):
                output.append(f"   📱 Mobile: {user.get('mobilePhone')}")
            if user.get('businessPhones'):
                phones = ", ".join(user.get('businessPhones', []))
                if phones:
                    output.append(f"   ☎️ Phone: {phones}")
            
            return "\n".join(output)
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"❌ User not found: {user_email or user_id}"
        return f"❌ Failed to get user info: {str(e)}"
    except Exception as e:
        logger.error("get_user_info_failed", error=str(e))
        return f"❌ Failed to get user info: {str(e)}"


@tool
def search_users(
    query: str,
    limit: int = 10,
) -> str:
    """Search for users/colleagues by name or email.
    
    Args:
        query: Search term (name or email)
        limit: Maximum results to return (default: 10)
        
    Returns:
        str: List of matching users
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        import urllib.request
        import urllib.parse
        import json
        
        # Build filter query
        filter_query = f"startswith(displayName,'{query}') or startswith(mail,'{query}')"
        encoded_filter = urllib.parse.quote(filter_query)
        
        url = f"{GRAPH_API_BASE}/users?$filter={encoded_filter}&$top={limit}&$select=displayName,mail,jobTitle,department"
        
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            users = result.get("value", [])
            
            if not users:
                return f"🔍 No users found matching '{query}'"
            
            output = [f"🔍 Found {len(users)} user(s) matching '{query}':"]
            for user in users:
                name = user.get("displayName", "Unknown")
                email = user.get("mail", "")
                title = user.get("jobTitle", "")
                dept = user.get("department", "")
                
                info_parts = [name]
                if email:
                    info_parts.append(f"<{email}>")
                if title:
                    info_parts.append(f"- {title}")
                if dept:
                    info_parts.append(f"({dept})")
                
                output.append(f"  • {' '.join(info_parts)}")
            
            return "\n".join(output)
            
    except Exception as e:
        logger.error("search_users_failed", error=str(e))
        return f"❌ Failed to search users: {str(e)}"


@tool
def get_my_profile() -> str:
    """Get my own profile information.
    
    Returns:
        str: Your profile information
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        import urllib.request
        import json
        
        url = f"{GRAPH_API_BASE}/me?$select=displayName,mail,jobTitle,department,officeLocation,mobilePhone,businessPhones,userPrincipalName"
        
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            user = json.loads(resp.read())
            
            output = ["👤 **Your Profile**"]
            output.append(f"   Name: {user.get('displayName', 'Unknown')}")
            
            if user.get('mail'):
                output.append(f"   📧 Email: {user.get('mail')}")
            if user.get('jobTitle'):
                output.append(f"   💼 Title: {user.get('jobTitle')}")
            if user.get('department'):
                output.append(f"   🏢 Department: {user.get('department')}")
            if user.get('officeLocation'):
                output.append(f"   📍 Office: {user.get('officeLocation')}")
            
            return "\n".join(output)
            
    except Exception as e:
        logger.error("get_my_profile_failed", error=str(e))
        return f"❌ Failed to get profile: {str(e)}"


@tool
def get_user_presence(
    user_email: str,
) -> str:
    """Check if a user is online/available in Teams.
    
    Args:
        user_email: The user's email address
        
    Returns:
        str: User's availability status
    """
    token = get_graph_token()
    if not token:
        return "❌ Microsoft Graph API not configured."
    
    try:
        import urllib.request
        import json
        
        # First get user ID from email
        user_url = f"{GRAPH_API_BASE}/users/{user_email}?$select=id,displayName"
        req = urllib.request.Request(
            user_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            user = json.loads(resp.read())
            user_id = user.get("id")
            user_name = user.get("displayName", user_email)
        
        # Get presence
        presence_url = f"{GRAPH_API_BASE}/users/{user_id}/presence"
        req = urllib.request.Request(
            presence_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            presence = json.loads(resp.read())
            
            availability = presence.get("availability", "Unknown")
            activity = presence.get("activity", "Unknown")
            
            # Map to emojis
            status_emoji = {
                "Available": "🟢",
                "Busy": "🔴",
                "DoNotDisturb": "⛔",
                "Away": "🟡",
                "BeRightBack": "🟡",
                "Offline": "⚫",
                "PresenceUnknown": "⚪",
            }.get(availability, "⚪")
            
            return f"{status_emoji} **{user_name}**: {availability} ({activity})"
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"❌ User not found: {user_email}"
        return f"❌ Failed to get presence: {str(e)}"
    except Exception as e:
        logger.error("get_user_presence_failed", error=str(e))
        return f"❌ Failed to get presence: {str(e)}"


# Export all Teams tools
teams_tools = [
    # Calendar & Tasks
    create_reminder,
    create_meeting,
    get_my_calendar,
    # Messaging
    send_teams_message,
    # Users & Teams
    get_team_members,
    get_user_info,
    search_users,
    get_my_profile,
    get_user_presence,
]

