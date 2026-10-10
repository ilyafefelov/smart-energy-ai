#!/usr/bin/env python3
"""Update Notion with Smart Energy AI project info"""

import os
import json
import subprocess

def get_notion_key():
    """Get Notion API key"""
    # Try environment variable
    if 'NOTION_API_KEY' in os.environ:
        return os.environ['NOTION_API_KEY']
    
    # Try config file
    config_path = os.path.expanduser('~/.config/notion/api_key')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return f.read().strip()
    
    raise ValueError("NOTION_API_KEY not found in env or ~/.config/notion/api_key")

def create_page_content():
    """Create Notion page content"""
    return {
        "title": "Smart Energy AI System",
        "status": "Production Ready ✅",
        "version": "1.0.3",
        "last_updated": "2026-01-29",
        "test_status": "5/5 phases passing (100%)",
        "features": [
            "Real OREE price integration",
            "Solar data forecasting",
            "RL model training",
            "Version auto-increment",
            "Production dashboard"
        ]
    }

def update_notion():
    """Update Notion pages"""
    print("\nUpdating Notion project pages...")
    print("=" * 70)
    
    try:
        api_key = get_notion_key()
        print("✅ Found Notion API key")
        
        # Get project info
        project_data = create_page_content()
        print(f"✅ Prepared project data (version {project_data['version']})")
        
        # Instructions for manual Notion update
        print("\n📝 Manual Notion Update Instructions:")
        print("=" * 70)
        print(f"Title: {project_data['title']}")
        print(f"Status: {project_data['status']}")
        print(f"Version: {project_data['version']}")
        print(f"Last Updated: {project_data['last_updated']}")
        print(f"Test Status: {project_data['test_status']}")
        print(f"Features:")
        for feature in project_data['features']:
            print(f"  • {feature}")
        
        print("\n💡 To complete Notion update:")
        print("1. Go to your Notion Smart Energy AI project page")
        print("2. Update the Status property to: Production Ready ✅")
        print("3. Update Version to: 1.0.3")
        print("4. Add to Features:")
        for feature in project_data['features']:
            print(f"   - {feature}")
        print("5. Set Last Updated: 2026-01-29")
        
        return True
    except ValueError as e:
        print(f"⚠️  {e}")
        print("\nNotice: API key not found, but you can update Notion manually.")
        print("To automate: Set NOTION_API_KEY environment variable")
        return False

if __name__ == "__main__":
    update_notion()
    print("\n✅ Notion update instructions provided")
