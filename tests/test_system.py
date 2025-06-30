#!/usr/bin/env python3
"""
Test script for the MCP Job Search System
"""

import sys
import os
import asyncio
import json

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_collection.scraper_hr_ge import JobScraper
from inference.job_matcher import JobMatcher

async def test_job_scraping():
    """Test the job scraping functionality"""
    print("🔍 Testing Job Scraping...")
    
    scraper = JobScraper()
    
    # Test with a simple search
    print("  📝 Searching for 'Python developer' jobs...")
    try:
        jobs = scraper.scrape_indeed_jobs("Python developer", "", 5)
        print(f"  ✅ Found {len(jobs)} jobs from Indeed")
        
        if jobs:
            print("  📋 Sample job:")
            job = jobs[0]
            print(f"     Title: {job.get('title', 'N/A')}")
            print(f"     Company: {job.get('company', 'N/A')}")
            print(f"     Location: {job.get('location', 'N/A')}")
            print(f"     Source: {job.get('source', 'N/A')}")
        
    except Exception as e:
        print(f"  ❌ Error in job scraping: {e}")

def test_job_matching():
    """Test the job matching functionality"""
    print("\n🎯 Testing Job Matching...")
    
    # Sample jobs data
    sample_jobs = [
        {
            'title': 'Senior Python Developer',
            'company': 'Tech Corp',
            'location': 'New York, NY',
            'source': 'Test',
            'description': 'Python Django Flask React'
        },
        {
            'title': 'Frontend Developer',
            'company': 'Web Solutions',
            'location': 'San Francisco, CA',
            'source': 'Test',
            'description': 'React Angular JavaScript'
        },
        {
            'title': 'Data Scientist',
            'company': 'AI Company',
            'location': 'Remote',
            'source': 'Test',
            'description': 'Python Machine Learning TensorFlow'
        }
    ]
    
    # Test requirements
    requirements = {
        'keywords': 'Python developer',
        'location': 'New York',
        'skills': ['python', 'react'],
        'experience_level': 'senior'
    }
    
    matcher = JobMatcher()
    matched_jobs = matcher.match_jobs(sample_jobs, requirements)
    
    print(f"  ✅ Matched {len(matched_jobs)} jobs")
    
    for i, job in enumerate(matched_jobs, 1):
        print(f"  {i}. {job['title']} at {job['company']}")
        print(f"     Match Score: {job['match_score']:.2f}")
        print(f"     Reasons: {', '.join(job['match_reasons'])}")

def test_requirement_extraction():
    """Test requirement extraction"""
    print("\n🧠 Testing Requirement Extraction...")
    
    # Import the server class for testing
    from inference.server import MCPJobServer
    
    server = MCPJobServer()
    
    test_messages = [
        "I'm looking for a senior Python developer job in New York with React experience",
        "Find me remote data scientist positions",
        "Entry level software engineer jobs in San Francisco"
    ]
    
    for message in test_messages:
        print(f"  📝 Message: '{message}'")
        requirements = server.simple_requirement_extraction(message)
        print(f"     Extracted: {json.dumps(requirements, indent=6)}")

async def main():
    """Run all tests"""
    print("🚀 Starting MCP Job Search System Tests")
    print("=" * 50)
    
    # Test job scraping (may fail if no internet or blocked)
    await test_job_scraping()
    
    # Test job matching (should always work)
    test_job_matching()
    
    # Test requirement extraction
    test_requirement_extraction()
    
    print("\n" + "=" * 50)
    print("✅ Tests completed!")
    print("\n💡 To start the full server, run: python scripts/serve.py")

if __name__ == "__main__":
    asyncio.run(main()) 