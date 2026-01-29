"""
Notion Sync - Mirror git commits and markdown docs to Notion
Runs after commits to keep Notion up-to-date with project history
"""

import requests
import os
import subprocess
from datetime import datetime
from pathlib import Path

NOTION_TOKEN = "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"
NOTION_VERSION = "2025-09-03"


class NotionSync:
    """Sync git commits and markdown docs to Notion"""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }

    def search_workspace(self, query):
        """Search for Notion pages/databases"""
        url = "https://api.notion.com/v1/search"
        payload = {"query": query}
        
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()
        return None

    def add_block_to_page(self, page_id, block_type, content):
        """Add a block (paragraph, heading, etc) to a Notion page"""
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        
        if block_type == "paragraph":
            block = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": content}}]
                }
            }
        elif block_type == "heading_2":
            block = {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": content}}]
                }
            }
        elif block_type == "code":
            block = {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": content}}],
                    "language": "markdown"
                }
            }
        else:
            return None

        payload = {"children": [block]}
        response = requests.patch(url, headers=self.headers, json=payload)
        return response.status_code == 200

    def get_recent_commits(self, count=10):
        """Get recent git commits"""
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%h|%s|%an|%ad|%b", "--date=short"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                commits = []
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split('|', 4)
                    if len(parts) >= 4:
                        commits.append({
                            'hash': parts[0],
                            'message': parts[1],
                            'author': parts[2],
                            'date': parts[3],
                            'body': parts[4] if len(parts) > 4 else ""
                        })
                return commits
            return []
        except Exception as e:
            print(f"Error getting commits: {e}")
            return []

    def get_markdown_files(self, directory="."):
        """Get all markdown files in project"""
        markdown_files = []
        for root, dirs, files in os.walk(directory):
            # Skip node_modules, .git, __pycache__, etc
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.env', '.venv']]
            
            for file in files:
                if file.endswith('.md'):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            markdown_files.append({
                                'path': path,
                                'name': file,
                                'content': content
                            })
                    except:
                        pass
        
        return markdown_files

    def sync_commits_to_notion(self, page_id, commits):
        """Add commit history to Notion page"""
        self.add_block_to_page(page_id, "heading_2", "📝 Commit History")
        
        for commit in commits:
            commit_text = f"{commit['hash']} - {commit['message']} ({commit['date']}) by {commit['author']}"
            self.add_block_to_page(page_id, "paragraph", commit_text)
            
            if commit['body'].strip():
                self.add_block_to_page(page_id, "code", commit['body'])

    def sync_docs_to_notion(self, page_id, markdown_files):
        """Add markdown documentation to Notion"""
        self.add_block_to_page(page_id, "heading_2", "📚 Documentation Files")
        
        for doc in markdown_files:
            # Add filename as heading
            self.add_block_to_page(page_id, "heading_2", f"📄 {doc['name']}")
            
            # Add content (truncated if needed)
            content = doc['content']
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated in Notion, see git repo for full content)"
            
            self.add_block_to_page(page_id, "code", content)

    def sync_all(self, project_name="smart energy"):
        """Sync commits and docs to Notion"""
        print(f"🔄 Syncing {project_name} to Notion...")
        
        # Find workspace page
        results = self.search_workspace(project_name)
        if not results or not results.get('results'):
            print(f"✗ No Notion page found for '{project_name}'")
            return False
        
        # Get first page result
        page = results['results'][0]
        page_id = page['id']
        print(f"✓ Found Notion page: {page.get('title', 'Untitled')}")
        
        # Get recent commits and markdown files
        commits = self.get_recent_commits(count=15)
        markdown_files = self.get_markdown_files()
        
        print(f"  Commits: {len(commits)}")
        print(f"  Docs: {len(markdown_files)}")
        
        # Sync to Notion
        if commits:
            self.sync_commits_to_notion(page_id, commits)
            print(f"✓ Synced {len(commits)} commits")
        
        if markdown_files:
            self.sync_docs_to_notion(page_id, markdown_files)
            print(f"✓ Synced {len(markdown_files)} documentation files")
        
        print(f"✅ Notion sync complete!")
        return True


def main():
    """Main entry point"""
    sync = NotionSync()
    sync.sync_all(project_name="smart energy")


if __name__ == "__main__":
    main()
