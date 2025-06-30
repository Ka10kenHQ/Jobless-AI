#!/usr/bin/env python3

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import setup_database, get_database_stats, close_connections
from database.models import JobPosting, TrainingExample
from database.operations import JobOperations, TrainingOperations


async def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            print(f"⚠️  Unexpected data format in {file_path}")
            return []
    
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return []


async def migrate_jobs():
    print("📋 Migrating job postings...")
    
    job_ops = JobOperations()
    migrated_count = 0
    
    job_files = [
        "data/collected_jobs.json",
        "data/synthetic_job_data_small.json"
    ]
    
    for file_path in job_files:
        print(f"   📂 Processing {file_path}")
        data = await load_json_file(file_path)
        
        for item in data:
            try:
                job_data = {
                    "url": item.get("url", f"synthetic_{migrated_count}"),
                    "title": item.get("title", item.get("job_title", "Unknown")),
                    "company": item.get("company", item.get("company_name", "Unknown")),
                    "location": item.get("location", "Unknown"),
                    "description": item.get("description", item.get("job_description", "")),
                    "salary": item.get("salary", None),
                    "requirements": item.get("requirements", []),
                    "skills": item.get("skills", []),
                    "experience_level": item.get("experience_level", None),
                    "job_type": item.get("job_type", None),
                    "remote": item.get("remote", None),
                    "source": determine_source(file_path),
                    "language": item.get("language", "english"),
                    "country": item.get("country", None),
                    "created_at": datetime.utcnow(),
                    "scraped_at": datetime.utcnow()
                }
                
                # Handle different field names
                if "job_description" in item and not job_data["description"]:
                    job_data["description"] = item["job_description"]
                
                if "company_name" in item and job_data["company"] == "Unknown":
                    job_data["company"] = item["company_name"]
                
                job = JobPosting(**job_data)
                
                job_id = await job_ops.create_job(job)
                migrated_count += 1
                
                if migrated_count % 10 == 0:
                    print(f"   ✅ Migrated {migrated_count} jobs...")
                
            except Exception as e:
                print(f"   ⚠️  Error migrating job: {e}")
                continue
    
    print(f"✅ Migrated {migrated_count} job postings")
    return migrated_count


async def migrate_training_data():
    print("🎯 Migrating training data...")
    
    training_ops = TrainingOperations()
    migrated_count = 0
    
    synthetic_file = "data/synthetic_job_data_small.json"
    data = await load_json_file(synthetic_file)
    
    training_examples = []
    
    for i, item in enumerate(data):
        try:
            job_desc = item.get("description", item.get("job_description", ""))
            company = item.get("company", item.get("company_name", ""))
            title = item.get("title", item.get("job_title", ""))
            
            if job_desc and title:
                example = TrainingExample(
                    example_id=f"synthetic_job_{i}",
                    input_text=f"Find jobs for: {title} at {company}",
                    output_text=f"Job Title: {title}\nCompany: {company}\nDescription: {job_desc[:500]}...",
                    source="synthetic",
                    language="english",
                    task_type="job_matching"
                )
                training_examples.append(example)
            
            if job_desc:
                requirements = item.get("requirements", [])
                if requirements:
                    example = TrainingExample(
                        example_id=f"synthetic_req_{i}",
                        input_text=f"Extract requirements from: {job_desc[:200]}...",
                        output_text=f"Requirements: {', '.join(requirements)}",
                        source="synthetic",
                        language="english",
                        task_type="requirement_extraction"
                    )
                    training_examples.append(example)
        
        except Exception as e:
            print(f"   ⚠️  Error creating training example: {e}")
            continue
    
    if training_examples:
        migrated_count = await training_ops.bulk_create_training_examples(training_examples)
    
    print(f"✅ Migrated {migrated_count} training examples")
    return migrated_count


def determine_source(file_path: str) -> str:
    """Determine job source from file path"""
    if "synthetic" in file_path:
        return "synthetic"
    elif "collected" in file_path:
        return "scraped"
    else:
        return "unknown"


async def check_mongodb_connection():
    try:
        from database.connection import get_async_database
        db = await get_async_database()
        await db.command('ping')
        print("✅ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("💡 Make sure MongoDB is running on localhost:27017")
        print("   To start MongoDB: sudo systemctl start mongodb")
        return False


async def main():
    print("🚀 Starting MongoDB Migration")
    print("=" * 50)
    
    if not await check_mongodb_connection():
        return
    
    print("🔧 Setting up database...")
    await setup_database()
    
    # Show initial stats
    print("\n📊 Initial database state:")
    stats = await get_database_stats()
    for collection, info in stats["collections"].items():
        if "error" not in info:
            print(f"   {collection}: {info['count']} documents")
    
    # Migrate data
    print("\n🔄 Starting migration...")
    
    # Migrate jobs
    job_count = await migrate_jobs()
    
    # Migrate training data
    training_count = await migrate_training_data()
    
    # Show final stats
    print("\n📊 Final database state:")
    stats = await get_database_stats()
    for collection, info in stats["collections"].items():
        if "error" not in info:
            print(f"   {collection}: {info['count']} documents")
    
    print("\n🎉 Migration completed!")
    print(f"   📋 Jobs migrated: {job_count}")
    print(f"   🎯 Training examples: {training_count}")
    
    # Close connections
    await close_connections()


if __name__ == "__main__":
    # Run migration
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc() 