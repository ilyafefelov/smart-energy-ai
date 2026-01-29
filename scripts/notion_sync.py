"""
Notion Sync - Mirror git commits and markdown docs to Notion
Simplified version - queues content for manual review
"""

import subprocess
import os
from pathlib import Path
from datetime import datetime


class NotionSync:
    """Sync git commits and markdown docs to Notion"""

    @staticmethod
    def get_recent_commits(count=15):
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

    @staticmethod
    def get_markdown_files(directory="."):
        """Get all markdown files in project"""
        markdown_files = []
        for root, dirs, files in os.walk(directory):
            # Skip node_modules, .git, __pycache__, etc
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.env', '.venv', 'data', 'logs']]
            
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

    @staticmethod
    def generate_notion_content(commits, markdown_files):
        """Generate content summary for Notion"""
        content = []
        
        # Commit history
        content.append("## 📝 Recent Commits\n")
        for commit in commits:
            content.append(f"- `{commit['hash']}` - {commit['message']} ({commit['date']})")
            if commit['body'].strip():
                content.append(f"  - {commit['body'][:100]}...")
        
        content.append("\n## 📚 Documentation Files\n")
        for doc in markdown_files:
            content.append(f"- **{doc['name']}** ({len(doc['content'])} bytes)")
        
        return "\n".join(content)

    @staticmethod
    def sync_summary(project_name="smart energy"):
        """Generate sync summary (manual posting to Notion)"""
        print(f"🔄 Generating Notion sync summary for {project_name}...")
        
        commits = NotionSync.get_recent_commits(count=15)
        markdown_files = NotionSync.get_markdown_files()
        
        print(f"✓ Found {len(commits)} commits")
        print(f"✓ Found {len(markdown_files)} markdown files")
        
        # Generate summary
        summary = NotionSync.generate_notion_content(commits, markdown_files)
        
        # Save to file for manual review
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_file = f"notion_sync_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Notion Sync Summary - {timestamp}\n")
            f.write(f"Project: {project_name}\n")
            f.write("=" * 60 + "\n\n")
            f.write(summary)
        
        print(f"\n✅ Sync summary saved: {output_file}")
        print(f"\nTo update Notion:")
        print(f"1. Open your Notion page for {project_name}")
        print(f"2. Create a new page or update existing with:")
        print(f"\n{summary}")
        
        return summary


def main():
    """Main entry point"""
    NotionSync.sync_summary(project_name="smart energy")


if __name__ == "__main__":
    main()
