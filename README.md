# Atlassian MCP Team Server

OAuth 2.1 enabled Atlassian MCP server for team collaboration with Jira and Confluence.

## Features

- **OAuth 2.1 Authentication** with Atlassian
- **FastAPI Web Interface** for team collaboration
- **CrewAI Integration** for AI-powered workflows
- **MCP (Model Context Protocol)** support
- **Jira & Confluence** API integration

## Setup

### 1. Clone and Setup Environment

```bash
git clone https://github.com/veera-qa/pella-atlas-mcp.git
cd pella-atlas-mcp

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
ATLASSIAN_CLIENT_ID=your_client_id_here
ATLASSIAN_CLIENT_SECRET=your_client_secret_here
ATLASSIAN_CLOUD_ID=your_cloud_id_here
ATLASSIAN_SITE_URL=https://yourdomain.atlassian.net/
```

### 3. Atlassian App Setup

1. Go to [Atlassian Developer Console](https://developer.atlassian.com/console)
2. Create a new OAuth 2.0 app
3. Set the callback URL to: `http://localhost:8080/auth/callback`
4. Add required scopes:
   - `read:jira-user`
   - `read:jira-work`
   - `write:jira-work`
   - `read:confluence-content.summary`
   - `read:confluence-content.all`
   - `write:confluence-content`

### 4. Run the Server

```bash
python main.py
```

The server will start at: `http://localhost:8080`

## Usage

1. Navigate to `http://localhost:8080`
2. Click "Login with Atlassian" to authenticate
3. Use the dashboard to interact with Jira and Confluence

## Project Structure

```
atlas-mcp/
├── main.py                 # FastAPI application entry point
├── routers/                # API route handlers
│   ├── auth.py            # OAuth authentication routes
│   └── atlassian.py       # Atlassian API routes
├── services/              # Business logic services
│   ├── oauth_service.py   # OAuth token management
│   └── crew_service.py    # CrewAI integration
├── templates/             # HTML templates
├── static/               # Static assets (CSS, JS)
├── requirements.txt      # All dependencies (pip freeze)
├── requirements_direct.txt # Direct dependencies only
└── .env.example         # Environment template

```

## Security Notes

- Never commit `.env` files with real credentials
- The `atlassian_token.json` file contains OAuth tokens and is gitignored
- Always use HTTPS in production
- Regenerate `SESSION_SECRET_KEY` for production deployments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

### OAuth "Invalid state parameter" Error

This has been fixed in the latest version. Make sure:
1. Your callback URL matches exactly: `http://localhost:8080/auth/callback`
2. Clear browser cookies/session storage
3. Try in incognito mode

See `OAUTH_FIX_SUMMARY.md` for detailed fix information.

## License

MIT License - see LICENSE file for details.
