"""
Notion Sprint Documentation - Smart Energy AI V2
Creates and manages Notion pages for sprint tracking
"""

import requests
import os
from datetime import datetime

NOTION_TOKEN = "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"
NOTION_VERSION = "2025-09-03"


class NotionSprintDoc:
    """Create Notion documentation for sprint"""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }

    def search_workspace(self, query):
        """Search for pages/databases"""
        url = "https://api.notion.com/v1/search"
        payload = {"query": query}
        
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None

    def create_page(self, parent_page_id, title, content):
        """Create a new Notion page"""
        url = "https://api.notion.com/v1/pages"
        
        payload = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": content}}]
                    }
                }
            ]
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error creating page: {response.status_code}")
            print(response.text)
            return None

    def create_sprint_overview(self, workspace_page_id):
        """Create sprint overview page"""
        content = f"""Smart Energy AI V2 - 3 Week Sprint
        
Timeline: 3 weeks (University Capstone)
Start Date: 2026-01-29
Status: Week 1 In Progress

Sprint Goals:
- Week 1: Data pipeline + PostgreSQL
- Week 2: RL agent + Airflow DAG
- Week 3: Testing + Presentation

Team: Illya F (@full_iron) + Cloud (AI)
"""
        
        return self.create_page(workspace_page_id, "📊 Sprint Overview", content)

    def create_week1_log(self, workspace_page_id):
        """Create Week 1 progress tracking"""
        content = f"""Week 1: Data Pipeline + PostgreSQL
        
Completed (Days 1-4):
✅ PostgreSQL setup + ORM models
✅ Weather API integration (Open-Meteo)
✅ Price API integration (OREE)
✅ Pydantic validation models
✅ Connection pooling + health checks
✅ 2 verbose commits

In Progress (Days 5-7):
⏳ Unit tests (test_pipeline.py)
⏳ Real API testing (7 days data)
⏳ Sample dataset generation
⏳ Week 1 PR + merge

Commits:
1. feat(data-pipeline): Add PostgreSQL setup, ORM models, weather ingestion
2. feat(data-pipeline): Add price ingestion and data validation

Branch: feature/week1-data-pipeline
"""
        
        return self.create_page(workspace_page_id, "📝 Week 1 Log", content)

    def create_technical_decisions(self, workspace_page_id):
        """Create technical decisions log"""
        content = """Technical Decisions - Smart Energy AI V2

Decision 1: PostgreSQL Now (Not CSV)
- Chosen: PostgreSQL local + AWS free tier later
- Reason: Better for capstone, easier production migration
- Status: Confirmed, setup guide created

Decision 2: Orchestration Tool
- Chosen: Airflow (production-grade)
- Alternative: Prefect (simpler), APScheduler (lightweight)
- Reason: Best for university project + future scaling

Decision 3: RL Algorithm
- Chosen: PPO (Proximal Policy Optimization)
- Library: Stable-Baselines3
- Reason: Stable, sample-efficient, handles mixed actions

Decision 4: Data Sources
- Weather: Open-Meteo API (free, no auth)
- Prices: OREE Ukraine (real DAM prices)
- IoT: Simulated (no real sensors yet)

Decision 5: Notion Documentation
- Created: 2026-01-29 16:00 GMT+2
- Tool: Notion API (via Python)
- Sync: After each major commit
"""
        
        return self.create_page(workspace_page_id, "🎯 Technical Decisions", content)


def main():
    """Main entry point"""
    doc = NotionSprintDoc()
    
    print("🔍 Searching Notion workspace...")
    results = doc.search_workspace("smart energy")
    
    if results and results.get('results'):
        print(f"Found {len(results['results'])} items:")
        for item in results['results']:
            print(f"  - {item['object']}: {item.get('title', 'Untitled')}")
            if item['object'] == 'page':
                page_id = item['id']
                print(f"    ID: {page_id}")
                
                # Create sprint documentation
                print("\nCreating sprint pages...")
                
                overview = doc.create_sprint_overview(page_id)
                if overview:
                    print("✓ Created Sprint Overview")
                
                week1 = doc.create_week1_log(page_id)
                if week1:
                    print("✓ Created Week 1 Log")
                
                decisions = doc.create_technical_decisions(page_id)
                if decisions:
                    print("✓ Created Technical Decisions")
                
                break
    else:
        print("No pages found. Please create a 'Smart Energy AI' page in Notion first.")
        print("Then run this script again to create sub-pages.")


if __name__ == "__main__":
    main()
