# Quick Windows Server Deployment

## Setup (5 minutes)

### 1. Configure Environment
```cmd
copy .env.example .env
```
Edit `.env` and set:
- `ATLASSIAN_CLIENT_ID` - Get from https://developer.atlassian.com/console
- `ATLASSIAN_CLIENT_SECRET` - Get from https://developer.atlassian.com/console  
- `SERVER_IP` - Your Windows server IP (use `ipconfig` to find)

### 2. Configure Windows Firewall
```cmd
# Allow port 8080 through Windows Firewall
netsh advfirewall firewall add rule name="Atlassian MCP Server" dir=in action=allow protocol=TCP localport=8080
```

### 3. Start Server
```cmd
start.bat
```

### 4. Update Atlassian OAuth App
In https://developer.atlassian.com/console, set callback URL to:
```
http://YOUR_SERVER_IP:8080/auth/callback
```

## Team Access

Share this URL with your team:
```
http://YOUR_SERVER_IP:8080
```

Team members:
1. Click "Login with Atlassian"
2. Use their existing Atlassian credentials
3. Authorize the app
4. Start collaborating!

## Troubleshooting

**Can't access from network?**
- Check Windows Firewall settings
- Verify server IP with `ipconfig`
- Test locally first: http://localhost:8080

**OAuth errors?**
- Verify callback URL in Atlassian app matches your server IP
- Check .env file has correct credentials
