import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class JobPosting:
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str
    scraped_at: str
    job_id: str = ""
    salary: str = ""
    job_type: str = ""
    experience_level: str = ""
    skills: List[str] = None
    remote_friendly: bool = False
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if not self.job_id:
            id_string = f"{self.title}_{self.company}_{self.source}".lower()
            self.job_id = hashlib.md5(id_string.encode()).hexdigest()[:12]


class JobDataCollector:
    """Collects and manages job data from multiple scraping sessions"""
    
    def __init__(self, data_dir: str = "data/collected_jobs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.raw_jobs_file = self.data_dir / "raw_jobs.json"
        self.processed_jobs_file = self.data_dir / "processed_jobs.json"
        self.metadata_file = self.data_dir / "metadata.json"
        
        self.logger = logging.getLogger(__name__)
        
    def collect_from_scraper(self, scraped_jobs: List[Dict], source_info: Dict = None) -> int:
        if not scraped_jobs:
            self.logger.warning("No jobs provided to collect")
            return 0
            
        job_postings = []
        current_time = datetime.now().isoformat()
        
        for job_data in scraped_jobs:
            try:
                job_posting = JobPosting(
                    title=job_data.get('title', '').strip(),
                    company=job_data.get('company', '').strip(),
                    location=job_data.get('location', '').strip(),
                    url=job_data.get('url', '').strip(),
                    source=job_data.get('source', 'unknown').strip(),
                    description=job_data.get('description', '').strip(),
                    scraped_at=current_time
                )
                
                if job_posting.title and job_posting.company:  # Basic validation
                    job_postings.append(job_posting)
                    
            except Exception as e:
                self.logger.error(f"Error processing job data: {job_data}, Error: {e}")
                continue
        new_jobs_count = self._save_raw_jobs(job_postings)
        
        self._update_metadata(len(job_postings), source_info)
        
        self.logger.info(f"Collected {new_jobs_count} new jobs from {len(job_postings)} total")
        return new_jobs_count
        
    def _save_raw_jobs(self, job_postings: List[JobPosting]) -> int:
        existing_jobs = self._load_raw_jobs()
        existing_ids = {job['job_id'] for job in existing_jobs}
        
        new_jobs = []
        for job in job_postings:
            if job.job_id not in existing_ids:
                new_jobs.append(asdict(job))
                existing_ids.add(job.job_id)
                
        if new_jobs:
            all_jobs = existing_jobs + new_jobs
            with open(self.raw_jobs_file, 'w', encoding='utf-8') as f:
                json.dump(all_jobs, f, indent=2, ensure_ascii=False)
                
        return len(new_jobs)
        
    def _load_raw_jobs(self) -> List[Dict]:
        if self.raw_jobs_file.exists():
            try:
                with open(self.raw_jobs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading raw jobs: {e}")
                return []
        return []
        
    def _update_metadata(self, jobs_processed: int, source_info: Dict = None):
        metadata = self._load_metadata()
        
        current_time = datetime.now().isoformat()
        session_info = {
            'timestamp': current_time,
            'jobs_processed': jobs_processed,
            'source_info': source_info or {}
        }
        
        metadata['sessions'].append(session_info)
        metadata['total_sessions'] = len(metadata['sessions'])
        metadata['last_updated'] = current_time
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
                
        return {
            'sessions': [],
            'total_sessions': 0,
            'created_at': datetime.now().isoformat(),
            'last_updated': None
        }
        
    def get_collected_jobs(self, 
                          days_back: int = 7, 
                          sources: List[str] = None,
                          min_jobs: int = None) -> List[Dict]:
        raw_jobs = self._load_raw_jobs()
        
        if not raw_jobs:
            return []
            
        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered_jobs = []
        
        for job in raw_jobs:
            try:
                job_date = datetime.fromisoformat(job['scraped_at'])
                if job_date >= cutoff_date:
                    if sources is None or job['source'] in sources:
                        filtered_jobs.append(job)
            except Exception:
                continue
                
        if min_jobs and len(filtered_jobs) < min_jobs:
            self.logger.warning(f"Only found {len(filtered_jobs)} jobs, but {min_jobs} requested")
            
        return filtered_jobs
        
    def get_collection_stats(self) -> Dict:
        raw_jobs = self._load_raw_jobs()
        metadata = self._load_metadata()
        
        if not raw_jobs:
            return {
                'total_jobs': 0,
                'sources': [],
                'sessions': 0,
                'date_range': None
            }
            
        sources = list(set(job['source'] for job in raw_jobs))
        
        dates = []
        for job in raw_jobs:
            try:
                dates.append(datetime.fromisoformat(job['scraped_at']))
            except Exception:
                continue
                
        date_range = None
        if dates:
            dates.sort()
            date_range = {
                'earliest': dates[0].isoformat(),
                'latest': dates[-1].isoformat()
            }
            
        return {
            'total_jobs': len(raw_jobs),
            'sources': sources,
            'sessions': metadata['total_sessions'],
            'date_range': date_range,
            'source_breakdown': {
                source: len([j for j in raw_jobs if j['source'] == source])
                for source in sources
            }
        }
        
    def export_for_training(self, output_file: str = None) -> str:
        jobs = self.get_collected_jobs()
        
        if not jobs:
            raise ValueError("No jobs available for export")
            
        if output_file is None:
            output_file = str(self.data_dir / f"training_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Exported {len(jobs)} jobs to {output_file}")
        return output_file
        
    def cleanup_old_data(self, days_to_keep: int = 30):
        jobs = self._load_raw_jobs()
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        recent_jobs = []
        removed_count = 0
        
        for job in jobs:
            try:
                job_date = datetime.fromisoformat(job['scraped_at'])
                if job_date >= cutoff_date:
                    recent_jobs.append(job)
                else:
                    removed_count += 1
            except Exception:
                recent_jobs.append(job)
                
        if removed_count > 0:
            with open(self.raw_jobs_file, 'w', encoding='utf-8') as f:
                json.dump(recent_jobs, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Cleaned up {removed_count} old job postings")
            
        return removed_count
