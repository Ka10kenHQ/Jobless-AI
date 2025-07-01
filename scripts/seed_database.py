#!/usr/bin/env python3

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

sys.path.append(str(Path(__file__).parent.parent))

from database.connection import get_async_database, close_connections
from database.models import JobPosting, TrainingExample
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


async def clear_existing_data(db):
    try:
        logger.info("🧹 Clearing existing data...")
        
        collections_to_clear = [
            "job_postings", 
            "training_examples"
        ]
        
        for collection_name in collections_to_clear:
            result = await db[collection_name].delete_many({})
            logger.info(f"   Cleared {result.deleted_count} documents from {collection_name}")
        
        logger.info("✅ Existing data cleared")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear existing data: {e}")
        return False


async def load_job_postings(db) -> bool:
    try:
        logger.info("📄 Loading job postings data...")
        
        jobs_file = Path(__file__).parent.parent / "data" / "collected_jobs.json"
        if not jobs_file.exists():
            logger.warning(f"   Job postings file not found: {jobs_file}")
            return True  # Not critical, continue
        
        with open(jobs_file, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
        
        if not jobs_data:
            logger.warning("   No job data found in file")
            return True
        
        logger.info(f"   Found {len(jobs_data)} job postings")
        
        job_docs = []
        for job_data in jobs_data:
            try:
                cleaned_job = {
                    "url": job_data.get("url", ""),
                    "title": job_data.get("title", "").replace("*", ""),  # Remove asterisks
                    "company": job_data.get("company", "").replace("*", ""),
                    "location": job_data.get("location", "").replace("*", ""),
                    "description": job_data.get("description", ""),
                    "source": job_data.get("source", "LinkedIn"),
                    "language": "english",
                    "created_at": datetime.utcnow(),
                    "scraped_at": datetime.utcnow(),
                    "skills": [],
                    "requirements": [],
                    "quality_score": 0.8,  # Default quality score
                }
                
                if not cleaned_job["url"] or not cleaned_job["title"]:
                    continue
                    
                job_docs.append(cleaned_job)
                
            except Exception as e:
                logger.warning(f"   Skipping malformed job record: {e}")
                continue
        
        if job_docs:
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(job_docs), batch_size):
                batch = job_docs[i:i + batch_size]
                result = await db.job_postings.insert_many(batch)
                total_inserted += len(result.inserted_ids)
                logger.info(f"   Inserted batch {i//batch_size + 1}: {len(batch)} jobs")
            
            logger.info(f"✅ Successfully inserted {total_inserted} job postings")
        else:
            logger.warning("   No valid job postings to insert")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load job postings: {e}")
        return False


async def load_training_examples(db) -> bool:
    try:
        logger.info("🎯 Loading training examples...")
        
        training_file = Path(__file__).parent.parent / "data" / "synthetic_job_data_small.json"
        if not training_file.exists():
            logger.warning(f"   Training data file not found: {training_file}")
            return True  
        
        with open(training_file, 'r', encoding='utf-8') as f:
            training_data = json.load(f)
        
        if not training_data:
            logger.warning("   No training data found in file")
            return True
        
        logger.info(f"   Found {len(training_data)} training examples")
        
        training_docs = []
        for idx, example in enumerate(training_data):
            try:
                training_doc = {
                    "example_id": f"synthetic_{idx}",
                    "input_text": example.get("user_message", ""),
                    "output_text": example.get("response", ""),
                    "source": "synthetic",
                    "language": "english",
                    "task_type": example.get("task_type", "conversation"),
                    "created_at": datetime.utcnow(),
                    "quality_score": 0.9,  # High quality for synthetic data
                }
                
                # Add extracted requirements if available
                if example.get("extracted_requirements"):
                    training_doc["prompt_template"] = json.dumps(example["extracted_requirements"])
                
                if not training_doc["input_text"] or not training_doc["output_text"]:
                    continue
                
                training_docs.append(training_doc)
                
            except Exception as e:
                logger.warning(f"   Skipping malformed training example {idx}: {e}")
                continue
        
        if training_docs:
            batch_size = 100
            total_inserted = 0
            
            for i in range(0, len(training_docs), batch_size):
                batch = training_docs[i:i + batch_size]
                result = await db.training_examples.insert_many(batch)
                total_inserted += len(result.inserted_ids)
                logger.info(f"   Inserted batch {i//batch_size + 1}: {len(batch)} examples")
            
            logger.info(f"✅ Successfully inserted {total_inserted} training examples")
        else:
            logger.warning("   No valid training examples to insert")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to load training examples: {e}")
        return False


async def create_indexes(db) -> bool:
    try:
        logger.info("🔍 Creating database indexes...")
        
        await db.job_postings.create_index("url", unique=True)
        await db.job_postings.create_index("title")
        await db.job_postings.create_index("company")
        await db.job_postings.create_index("location")
        await db.job_postings.create_index("source")
        await db.job_postings.create_index("created_at")
        await db.job_postings.create_index([("title", "text"), ("description", "text")])
        
        await db.training_examples.create_index("example_id", unique=True)
        await db.training_examples.create_index("task_type")
        await db.training_examples.create_index("source")
        await db.training_examples.create_index("created_at")
        await db.training_examples.create_index([("input_text", "text"), ("output_text", "text")])
        
        logger.info("✅ Database indexes created")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create indexes: {e}")
        return False


async def verify_data(db) -> bool:
    try:
        logger.info("🔍 Verifying seeded data...")
        
        jobs_count = await db.job_postings.count_documents({})
        training_count = await db.training_examples.count_documents({})
        
        logger.info(f"   📄 Job postings: {jobs_count}")
        logger.info(f"   🎯 Training examples: {training_count}")
        
        if jobs_count > 0:
            sample_job = await db.job_postings.find_one()
            logger.info(f"   Sample job: {sample_job.get('title', 'N/A')} at {sample_job.get('company', 'N/A')}")
        
        if training_count > 0:
            sample_training = await db.training_examples.find_one()
            logger.info(f"   Sample training: {sample_training.get('task_type', 'N/A')} task")
        
        job_indexes = await db.job_postings.list_indexes().to_list(length=None)
        training_indexes = await db.training_examples.list_indexes().to_list(length=None)
        
        logger.info(f"   Job postings indexes: {len(job_indexes)}")
        logger.info(f"   Training examples indexes: {len(training_indexes)}")
        
        logger.info("✅ Data verification completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data verification failed: {e}")
        return False


async def main():
    logger.info("🌱 Starting database seeding...")
    
    try:
        db = await get_async_database()
        
        await db.command('ping')
        logger.info("✅ Database connection successful")
        
        if not await clear_existing_data(db):
            return False
        
        if not await load_job_postings(db):
            return False
            
        if not await load_training_examples(db):
            return False
        
        if not await create_indexes(db):
            return False
        
        if not await verify_data(db):
            return False
        
        logger.info("🎉 Database seeding completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database seeding failed: {e}")
        return False
        
    finally:
        await close_connections()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 