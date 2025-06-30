"""
MongoDB-based job data collector
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import hashlib

from database.models import JobPosting, ScrapingSession
from database.operations import JobOperations, ScrapingOperations


@dataclass
class ScrapedJob:
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str
    salary: str = ""
    job_type: str = ""
    experience_level: str = ""
    skills: List[str] = None
    remote_friendly: bool = False
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []


class MongoJobDataCollector:
    """MongoDB-based job data collector"""
    
    def __init__(self):
        self.job_ops = JobOperations()
        self.scraping_ops = ScrapingOperations()
        self.logger = logging.getLogger(__name__)
    
    async def collect_from_scraper(
        self, 
        scraped_jobs: List[Dict], 
        source: str,
        keywords: List[str] = None,
        location: str = None
    ) -> Dict[str, int]:
        """Collect jobs from scraper and save to MongoDB"""
        
        if not scraped_jobs:
            self.logger.warning("No jobs provided to collect")
            return {"jobs_found": 0, "jobs_saved": 0, "duplicates_skipped": 0, "errors": 0}
        
        # Start scraping session
        session = ScrapingSession(
            source=source,
            keywords=keywords or [],
            location=location,
            status="running"
        )
        session_id = await self.scraping_ops.start_scraping_session(session)
        
        jobs_saved = 0
        duplicates_skipped = 0
        errors = 0
        
        self.logger.info(f"Processing {len(scraped_jobs)} jobs from {source}")
        
        for job_data in scraped_jobs:
            try:
                # Convert to our JobPosting model
                job_posting = await self._convert_scraped_job(job_data, source)
                
                if job_posting:
                    # Try to save job (will handle duplicates)
                    existing_job = await self.job_ops.get_job_by_url(job_posting.url)
                    
                    if existing_job:
                        duplicates_skipped += 1
                        self.logger.debug(f"Duplicate job skipped: {job_posting.title} at {job_posting.company}")
                    else:
                        job_id = await self.job_ops.create_job(job_posting)
                        jobs_saved += 1
                        
                        if jobs_saved % 10 == 0:
                            self.logger.info(f"Saved {jobs_saved} jobs so far...")
                
            except Exception as e:
                errors += 1
                self.logger.error(f"Error processing job: {e}")
                continue
        
        # Complete scraping session
        await self.scraping_ops.complete_scraping_session(
            session_id=session_id,
            jobs_found=len(scraped_jobs),
            jobs_saved=jobs_saved,
            errors_count=errors
        )
        
        results = {
            "jobs_found": len(scraped_jobs),
            "jobs_saved": jobs_saved,
            "duplicates_skipped": duplicates_skipped,
            "errors": errors,
            "session_id": session_id
        }
        
        self.logger.info(f"Collection completed: {results}")
        return results
    
    async def _convert_scraped_job(self, job_data: Dict, source: str) -> Optional[JobPosting]:
        """Convert scraped job data to JobPosting model"""
        
        # Validate required fields
        title = job_data.get('title', '').strip()
        company = job_data.get('company', '').strip()
        url = job_data.get('url', '').strip()
        
        if not all([title, company, url]):
            self.logger.warning(f"Missing required fields: title={title}, company={company}, url={url}")
            return None
        
        # Extract skills from description if not provided
        skills = job_data.get('skills', [])
        if not skills and job_data.get('description'):
            skills = self._extract_skills_from_description(job_data['description'])
        
        # Determine language based on source
        language = self._determine_language(source)
        
        # Create JobPosting
        job_posting = JobPosting(
            url=url,
            title=title,
            company=company,
            location=job_data.get('location', '').strip(),
            description=job_data.get('description', '').strip(),
            salary=job_data.get('salary', ''),
            requirements=job_data.get('requirements', []),
            skills=skills,
            experience_level=job_data.get('experience_level', ''),
            job_type=job_data.get('job_type', ''),
            remote=job_data.get('remote_friendly', None),
            source=source,
            language=language,
            country=job_data.get('country', self._determine_country(source)),
            created_at=datetime.utcnow(),
            scraped_at=datetime.utcnow()
        )
        
        return job_posting
    
    def _extract_skills_from_description(self, description: str) -> List[str]:
        """Extract skills from job description"""
        # Common skills to look for
        common_skills = [
            'python', 'javascript', 'java', 'react', 'node.js', 'sql', 'html', 'css',
            'git', 'docker', 'kubernetes', 'aws', 'azure', 'mongodb', 'postgresql',
            'machine learning', 'data analysis', 'project management', 'agile', 'scrum'
        ]
        
        description_lower = description.lower()
        found_skills = []
        
        for skill in common_skills:
            if skill in description_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def _determine_language(self, source: str) -> str:
        """Determine language based on job source"""
        georgian_sources = ['hr.ge', 'jobs.ge']
        if source in georgian_sources:
            return 'georgian'
        return 'english'
    
    def _determine_country(self, source: str) -> str:
        """Determine country based on job source"""
        country_mapping = {
            'hr.ge': 'Georgia',
            'jobs.ge': 'Georgia',
            'linkedin': 'Various',
            'indeed': 'Various',
            'glassdoor': 'Various'
        }
        return country_mapping.get(source, 'Unknown')
    
    async def get_recent_jobs(
        self, 
        hours: int = 24, 
        sources: List[str] = None,
        languages: List[str] = None,
        limit: int = 100
    ) -> List[JobPosting]:
        """Get recent jobs from MongoDB"""
        
        return await self.job_ops.get_recent_jobs(hours=hours, limit=limit)
    
    async def search_jobs(
        self, 
        query: str = "",
        languages: List[str] = None,
        location: str = None,
        limit: int = 20
    ) -> List[JobPosting]:
        """Search jobs in MongoDB"""
        
        return await self.job_ops.search_jobs(
            query=query,
            languages=languages or ["english"],
            limit=limit
        )
    
    async def get_collection_stats(self) -> Dict:
        """Get collection statistics from MongoDB"""
        
        stats = await self.job_ops.get_job_stats()
        recent_sessions = await self.scraping_ops.get_recent_scraping_sessions(5)
        
        return {
            "total_jobs": stats.get("total_jobs", 0),
            "sources": stats.get("sources", []),
            "languages": stats.get("languages", []),
            "latest_job": stats.get("latest_job"),
            "average_quality": stats.get("avg_quality"),
            "recent_sessions": len(recent_sessions),
            "last_scraping": recent_sessions[0].started_at if recent_sessions else None
        }
    
    async def export_for_training(self, languages: List[str] = None) -> List[Dict[str, str]]:
        """Export job data for training"""
        
        # Get recent high-quality jobs
        recent_jobs = await self.get_recent_jobs(hours=24*7, limit=1000)  # Last week
        
        training_data = []
        for job in recent_jobs:
            if languages and job.language not in languages:
                continue
            
            # Create training examples
            training_data.append({
                "input": f"Find jobs for: {job.title}",
                "output": f"Job: {job.title} at {job.company} in {job.location}\nDescription: {job.description[:200]}..."
            })
            
            if job.requirements:
                training_data.append({
                    "input": f"What are the requirements for {job.title} position?",
                    "output": f"Requirements: {', '.join(job.requirements)}"
                })
        
        return training_data
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old job data (placeholder - would need implementation)"""
        # Would implement deletion of old jobs here
        self.logger.info(f"Cleanup not implemented yet. Would keep jobs from last {days_to_keep} days")


# Async wrapper functions for backwards compatibility
async def collect_jobs_async(scraped_jobs: List[Dict], source: str, **kwargs) -> Dict[str, int]:
    """Async function to collect jobs"""
    collector = MongoJobDataCollector()
    return await collector.collect_from_scraper(scraped_jobs, source, **kwargs)


def collect_jobs_sync(scraped_jobs: List[Dict], source: str, **kwargs) -> Dict[str, int]:
    """Sync wrapper for job collection"""
    return asyncio.run(collect_jobs_async(scraped_jobs, source, **kwargs))


# Example usage
if __name__ == "__main__":
    async def test_collector():
        collector = MongoJobDataCollector()
        
        # Test data
        test_jobs = [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "location": "Tbilisi, Georgia",
                "url": "https://example.com/job1",
                "description": "Looking for a Python developer with React experience",
                "salary": "$50,000",
                "skills": ["Python", "React", "Git"]
            },
            {
                "title": "Data Analyst", 
                "company": "Data Inc",
                "location": "Remote",
                "url": "https://example.com/job2",
                "description": "Analyze data using SQL and Python",
                "requirements": ["SQL", "Python", "Statistics"]
            }
        ]
        
        # Collect jobs
        results = await collector.collect_from_scraper(
            scraped_jobs=test_jobs,
            source="test_source",
            keywords=["python", "developer"]
        )
        
        print(f"Collection results: {results}")
        
        # Get stats
        stats = await collector.get_collection_stats()
        print(f"Collection stats: {stats}")
    
    # Run test
    asyncio.run(test_collector()) 