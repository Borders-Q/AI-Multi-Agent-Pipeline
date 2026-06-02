import os
import json

REGISTRY_DIR = "cloud_registry"
SKILLS_DIR = os.path.join(REGISTRY_DIR, "skills")

os.makedirs(SKILLS_DIR, exist_ok=True)

SKILLS_DATA = [
    {"id": "slack_notifier", "name": "Slack_Notifier", "icon": "💬", "desc": "Send notifications to a Slack channel."},
    {"id": "notion_sync", "name": "Notion_Page_Sync", "icon": "📓", "desc": "Sync or create content in Notion workspaces."},
    {"id": "jira_ticket", "name": "Jira_Ticket_Creator", "icon": "🎫", "desc": "Create and manage Jira tickets for agile teams."},
    {"id": "postgres_query", "name": "PostgreSQL_Query", "icon": "🐘", "desc": "Execute read-only SQL queries on production DB."},
    {"id": "mysql_analyzer", "name": "MySQL_Analyzer", "icon": "🐬", "desc": "Analyze MySQL schemas and query performance."},
    {"id": "aws_s3_manager", "name": "AWS_S3_Manager", "icon": "☁️", "desc": "List, upload, or download objects from Amazon S3."},
    {"id": "github_repo_analyzer", "name": "Github_Repo_Analyzer", "icon": "🐙", "desc": "Fetch stars, forks, and stats for a Github Repo."},
    {"id": "crypto_tracker", "name": "Crypto_Price_Tracker", "icon": "💰", "desc": "Fetch real-time USD prices for cryptocurrencies."},
    {"id": "puppeteer_scraper", "name": "Puppeteer_Scraper", "icon": "🕸️", "desc": "Run headless browser automation to scrape dynamic pages."},
    {"id": "kubernetes_pod_monitor", "name": "K8s_Pod_Monitor", "icon": "☸️", "desc": "Monitor health and logs of Kubernetes pods."},
    {"id": "docker_manager", "name": "Docker_Container_Manager", "icon": "🐳", "desc": "Manage local or remote Docker containers."},
    {"id": "google_drive_search", "name": "Google_Drive_Search", "icon": "📂", "desc": "Search for documents in Google Drive."},
    {"id": "salesforce_crm", "name": "Salesforce_Lead_Fetch", "icon": "☁️", "desc": "Fetch lead and opportunity data from Salesforce."},
    {"id": "stripe_payments", "name": "Stripe_Payments_Viewer", "icon": "💳", "desc": "View recent transactions and subscriptions on Stripe."},
    {"id": "zendesk_support", "name": "Zendesk_Ticket_Manager", "icon": "🎧", "desc": "Manage customer support tickets in Zendesk."},
    {"id": "hubspot_marketing", "name": "Hubspot_Campaign_Stats", "icon": "📈", "desc": "Retrieve marketing campaign performance from Hubspot."},
    {"id": "figma_asset_export", "name": "Figma_Asset_Exporter", "icon": "🎨", "desc": "Export design assets and tokens from Figma files."},
    {"id": "vercel_deploy", "name": "Vercel_Deploy_Trigger", "icon": "▲", "desc": "Trigger new deployments on Vercel."},
    {"id": "cloudflare_dns", "name": "Cloudflare_DNS_Manager", "icon": "☁️", "desc": "Manage DNS records via Cloudflare API."},
    {"id": "datadog_metrics", "name": "Datadog_Metrics_Viewer", "icon": "🐶", "desc": "View APM and infrastructure metrics from Datadog."},
    {"id": "pagerduty_oncall", "name": "PagerDuty_Oncall_Alert", "icon": "📟", "desc": "Trigger or acknowledge PagerDuty incidents."},
    {"id": "sentry_error_tracker", "name": "Sentry_Error_Tracker", "icon": "🐛", "desc": "Fetch latest unhandled exceptions from Sentry."},
    {"id": "elastic_search", "name": "ElasticSearch_Query", "icon": "🔍", "desc": "Query massive log indices in ElasticSearch."},
    {"id": "redis_cache_viewer", "name": "Redis_Cache_Viewer", "icon": "🔴", "desc": "View or invalidate keys in Redis cache."},
    {"id": "mongodb_document", "name": "MongoDB_Document_Finder", "icon": "🍃", "desc": "Find NoSQL documents in MongoDB clusters."},
    {"id": "gmail_sender", "name": "Gmail_Automated_Sender", "icon": "✉️", "desc": "Draft and send emails via Gmail API."},
    {"id": "calendar_scheduler", "name": "Google_Calendar_Scheduler", "icon": "📅", "desc": "Schedule meetings and check availability."},
    {"id": "zoom_meeting", "name": "Zoom_Meeting_Creator", "icon": "📹", "desc": "Generate Zoom meeting links programmatically."},
    {"id": "youtube_stats", "name": "YouTube_Video_Stats", "icon": "▶️", "desc": "Fetch view count and metrics for YouTube videos."},
    {"id": "twitter_sentiment", "name": "Twitter_Sentiment_Analyzer", "icon": "🐦", "desc": "Analyze public sentiment on specific topics."},
    {"id": "weather_radar", "name": "Global_Weather_Radar", "icon": "⛅", "desc": "Fetch high-precision weather forecasts globally."},
    {"id": "stock_market", "name": "WallStreet_Stock_Ticker", "icon": "📉", "desc": "Real-time NASDAQ/NYSE stock prices and PE ratios."}
]

catalog = []

for skill in SKILLS_DATA:
    catalog.append({
        "id": skill["id"],
        "name": skill["name"],
        "description": skill["desc"],
        "icon": skill["icon"],
        "url": f"/skills/{skill['id']}.py"
    })
    
    func_name = skill["name"].lower().replace("-", "_")
    
    code = f'''
def {func_name}(query: str = ""):
    """{skill["desc"]}"""
    import time
    return f"[Mock Success] {skill['name']} executed successfully. Target: {{query}}. System reported normal status."

SCHEMA = {{
    "name": "{func_name}",
    "description": "{skill["desc"]}",
    "parameters": {{
        "type": "object",
        "properties": {{
            "query": {{
                "type": "string",
                "description": "The primary input or ID for the operation."
            }}
        }},
        "required": []
    }}
}}
'''
    with open(os.path.join(SKILLS_DIR, f"{skill['id']}.py"), "w", encoding="utf-8") as f:
        f.write(code.strip())

with open(os.path.join(REGISTRY_DIR, "catalog.json"), "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"✅ Created massive registry with {len(catalog)} skills in {REGISTRY_DIR}")
