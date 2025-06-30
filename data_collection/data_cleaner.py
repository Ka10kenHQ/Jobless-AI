import re
import json
from typing import List, Dict, Set, Optional, Tuple
import logging
from pathlib import Path
from dataclasses import dataclass
import pandas as pd
from collections import Counter
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.html_cleaner import HTMLCleaner

@dataclass
class CleanedJobData:
    """Structure for cleaned job data"""
    job_id: str
    title: str
    title_normalized: str
    company: str
    company_normalized: str
    location: str
    location_normalized: str
    url: str
    source: str
    description: str
    description_cleaned: str
    scraped_at: str
    
    # Extracted/enriched fields
    salary_range: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    skills: List[str] = None
    remote_friendly: bool = False
    is_senior_role: bool = False
    tech_stack: List[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    
    # Quality metrics
    data_quality_score: float = 0.0
    has_description: bool = False
    has_requirements: bool = False
    text_length: int = 0
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.tech_stack is None:
            self.tech_stack = []


class JobDataCleaner:
    """Cleans and standardizes collected job data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.html_cleaner = HTMLCleaner()
        
        # Skill extraction patterns
        self.programming_languages = {
            'python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust', 'swift', 
            'kotlin', 'php', 'ruby', 'scala', 'r', 'matlab', 'sql', 'typescript',
            'dart', 'perl', 'shell', 'bash', 'powershell'
        }
        
        self.frameworks_libraries = {
            'react', 'angular', 'vue', 'svelte', 'node.js', 'express', 'django', 
            'flask', 'fastapi', 'spring', 'laravel', 'rails', 'asp.net', 'jquery',
            'bootstrap', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
            'keras', 'opencv', 'matplotlib', 'seaborn', 'plotly'
        }
        
        self.cloud_technologies = {
            'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins',
            'terraform', 'ansible', 'gitlab', 'github', 'bitbucket', 'jira', 'confluence'
        }
        
        self.databases = {
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
            'oracle', 'sql server', 'sqlite', 'dynamodb', 'firebase', 'snowflake'
        }
        
        # Job level indicators
        self.senior_indicators = {
            'senior', 'lead', 'principal', 'staff', 'architect', 'manager', 
            'director', 'head of', 'vp', 'vice president', 'chief', 'cto', 'ceo'
        }
        
        self.junior_indicators = {
            'junior', 'entry', 'intern', 'graduate', 'associate', 'trainee', 'entry-level'
        }
        
        # Remote work indicators
        self.remote_indicators = {
            'remote', 'work from home', 'distributed', 'anywhere', 'worldwide',
            'flexible location', 'home office', 'telecommute'
        }
        
        # Job type patterns
        self.job_type_patterns = {
            'full-time': r'\b(full.?time|permanent|fte)\b',
            'part-time': r'\b(part.?time|pto)\b',
            'contract': r'\b(contract|contractor|freelance|temporary|temp)\b',
            'intern': r'\b(intern|internship|co-op)\b'
        }
        
        # Salary patterns
        self.salary_pattern = re.compile(
            r'[\$£€¥₹]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:[-–—to]\s*[\$£€¥₹]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?))?'
            r'|(\d{1,3}(?:,\d{3})*)\s*[-–—to]\s*(\d{1,3}(?:,\d{3})*)\s*(?:USD|EUR|GBP|CAD|AUD)?'
            r'|(\d{1,3})k?\s*[-–—to]\s*(\d{1,3})k'
        )
        
    def clean_job_data(self, raw_jobs: List[Dict]) -> List[CleanedJobData]:
        """Clean and standardize a list of raw job data"""
        cleaned_jobs = []
        
        self.logger.info(f"Starting to clean {len(raw_jobs)} job postings")
        
        for raw_job in raw_jobs:
            try:
                cleaned_job = self._clean_single_job(raw_job)
                if cleaned_job and self._validate_job_quality(cleaned_job):
                    cleaned_jobs.append(cleaned_job)
            except Exception as e:
                self.logger.error(f"Error cleaning job {raw_job.get('job_id', 'unknown')}: {e}")
                continue
                
        self.logger.info(f"Successfully cleaned {len(cleaned_jobs)} out of {len(raw_jobs)} jobs")
        return cleaned_jobs
        
    def _clean_single_job(self, raw_job: Dict) -> Optional[CleanedJobData]:
        """Clean a single job posting"""
        
        # Basic field extraction and cleaning
        title = self._clean_text(raw_job.get('title', ''))
        company = self._clean_text(raw_job.get('company', ''))
        location = self._clean_text(raw_job.get('location', ''))
        description = self._clean_description(raw_job.get('description', ''))
        
        if not title or not company:
            return None
            
        # Create base cleaned job
        cleaned_job = CleanedJobData(
            job_id=raw_job.get('job_id', ''),
            title=title,
            title_normalized=self._normalize_title(title),
            company=company,
            company_normalized=self._normalize_company(company),
            location=location,
            location_normalized=self._normalize_location(location),
            url=raw_job.get('url', ''),
            source=raw_job.get('source', ''),
            description=raw_job.get('description', ''),
            description_cleaned=description,
            scraped_at=raw_job.get('scraped_at', ''),
            has_description=bool(description.strip()),
            text_length=len(description)
        )
        
        # Extract enriched information
        full_text = f"{title} {description}".lower()
        
        # Extract skills and technologies
        cleaned_job.skills = self._extract_skills(full_text)
        cleaned_job.tech_stack = self._extract_tech_stack(full_text)
        
        # Determine experience level
        cleaned_job.experience_level = self._extract_experience_level(full_text)
        cleaned_job.is_senior_role = self._is_senior_role(full_text)
        
        # Extract job type
        cleaned_job.job_type = self._extract_job_type(full_text)
        
        # Check remote friendliness
        cleaned_job.remote_friendly = self._is_remote_friendly(full_text)
        
        # Extract salary information
        salary_info = self._extract_salary(description)
        if salary_info:
            cleaned_job.salary_range = salary_info.get('range')
            cleaned_job.salary_min = salary_info.get('min')
            cleaned_job.salary_max = salary_info.get('max')
            cleaned_job.currency = salary_info.get('currency')
            
        # Calculate quality score
        cleaned_job.data_quality_score = self._calculate_quality_score(cleaned_job)
        
        return cleaned_job
        
    def _clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        if not text:
            return ""
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove special characters from titles/companies
        text = re.sub(r'[^\w\s\-&.,()]', '', text)
        
        return text
        
    def _clean_description(self, description: str) -> str:
        """Clean job description text"""
        if not description:
            return ""
            
        # Use dedicated HTML cleaner for proper HTML handling
        if self.html_cleaner.is_html_content(description):
            description = self.html_cleaner.clean_html_text(
                description, 
                preserve_formatting=False,
                max_length=None
            )
        else:
            # Still clean non-HTML text
            description = re.sub(r'http[s]?://\S+', '', description)
            description = re.sub(r'\S+@\S+\.\S+', '', description)
            description = re.sub(r'\s+', ' ', description.strip())
            description = re.sub(r'[.]{3,}', '...', description)
        
        return description
        
    def _normalize_title(self, title: str) -> str:
        """Normalize job titles"""
        title_lower = title.lower()
        
        # Common title normalizations
        normalizations = {
            'software engineer': ['software developer', 'programmer', 'software dev'],
            'data scientist': ['data analyst', 'ml engineer', 'machine learning engineer'],
            'frontend developer': ['front-end developer', 'ui developer', 'frontend engineer'],
            'backend developer': ['back-end developer', 'backend engineer', 'server developer'],
            'full stack developer': ['fullstack developer', 'full-stack developer'],
            'devops engineer': ['devops', 'sre', 'site reliability engineer'],
            'product manager': ['pm', 'product owner', 'po']
        }
        
        for normalized, variants in normalizations.items():
            if any(variant in title_lower for variant in variants):
                return normalized
                
        return title_lower
        
    def _normalize_company(self, company: str) -> str:
        """Normalize company names"""
        company_clean = company.lower()
        
        # Remove common suffixes
        suffixes = ['inc', 'corp', 'llc', 'ltd', 'corporation', 'incorporated', 'company', 'co']
        for suffix in suffixes:
            pattern = rf'\b{suffix}\.?$'
            company_clean = re.sub(pattern, '', company_clean).strip()
            
        return company_clean
        
    def _normalize_location(self, location: str) -> str:
        """Normalize location strings"""
        if not location:
            return ""
            
        location_lower = location.lower()
        
        # Check for remote indicators
        if any(indicator in location_lower for indicator in self.remote_indicators):
            return "remote"
            
        # Common location normalizations
        location_mappings = {
            'new york': ['ny', 'nyc', 'new york city'],
            'san francisco': ['sf', 'san francisco bay area'],
            'los angeles': ['la', 'los angeles, ca'],
            'london': ['london, uk', 'london, england'],
            'berlin': ['berlin, germany'],
            'toronto': ['toronto, canada', 'toronto, on']
        }
        
        for normalized, variants in location_mappings.items():
            if any(variant in location_lower for variant in variants):
                return normalized
                
        # Extract city from "City, State" format
        if ',' in location:
            return location.split(',')[0].strip().lower()
            
        return location_lower
        
    def _extract_skills(self, text: str) -> List[str]:
        """Extract technical skills from job text"""
        found_skills = set()
        
        # Combine all skill categories
        all_skills = (self.programming_languages | 
                     self.frameworks_libraries | 
                     self.cloud_technologies | 
                     self.databases)
        
        for skill in all_skills:
            # Use word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(skill.lower())}\b'
            if re.search(pattern, text):
                found_skills.add(skill)
                
        return sorted(list(found_skills))
        
    def _extract_tech_stack(self, text: str) -> List[str]:
        """Extract primary technology stack"""
        tech_stack = []
        
        # Priority order: languages, then frameworks, then tools
        for skill in self.programming_languages:
            if f' {skill} ' in f' {text} ' or f'{skill},' in text:
                tech_stack.append(skill)
                
        for framework in self.frameworks_libraries:
            if f' {framework} ' in f' {text} ' or f'{framework},' in text:
                tech_stack.append(framework)
                
        return tech_stack[:5]  # Limit to top 5
        
    def _extract_experience_level(self, text: str) -> str:
        """Extract experience level from job text"""
        
        # Check for senior indicators
        if any(indicator in text for indicator in self.senior_indicators):
            return "senior"
            
        # Check for junior indicators
        if any(indicator in text for indicator in self.junior_indicators):
            return "junior"
            
        # Look for years of experience
        years_pattern = r'(\d+)[\s\-+]*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)'
        years_match = re.search(years_pattern, text)
        
        if years_match:
            years = int(years_match.group(1))
            if years >= 5:
                return "senior"
            elif years >= 2:
                return "mid"
            else:
                return "junior"
                
        return "any"
        
    def _is_senior_role(self, text: str) -> bool:
        """Check if this is a senior-level role"""
        return any(indicator in text for indicator in self.senior_indicators)
        
    def _extract_job_type(self, text: str) -> str:
        """Extract job type (full-time, part-time, etc.)"""
        for job_type, pattern in self.job_type_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return job_type
        return "full-time"  # Default assumption
        
    def _is_remote_friendly(self, text: str) -> bool:
        """Check if job is remote-friendly"""
        return any(indicator in text for indicator in self.remote_indicators)
        
    def _extract_salary(self, text: str) -> Optional[Dict]:
        """Extract salary information from job text"""
        matches = self.salary_pattern.findall(text)
        
        if not matches:
            return None
            
        # Process the first match found
        match = matches[0]
        
        try:
            # Handle different match groups
            if match[0] and match[1]:  # $50,000 - $70,000 format
                min_sal = float(match[0].replace(',', ''))
                max_sal = float(match[1].replace(',', ''))
            elif match[2] and match[3]:  # 50000 - 70000 format
                min_sal = float(match[2].replace(',', ''))
                max_sal = float(match[3].replace(',', ''))
            elif match[4] and match[5]:  # 50k - 70k format
                min_sal = float(match[4]) * 1000
                max_sal = float(match[5]) * 1000
            else:
                return None
                
            # Detect currency
            currency = "USD"  # Default
            if "£" in text:
                currency = "GBP"
            elif "€" in text:
                currency = "EUR"
                
            return {
                'range': f"{min_sal:,.0f} - {max_sal:,.0f} {currency}",
                'min': min_sal,
                'max': max_sal,
                'currency': currency
            }
            
        except (ValueError, IndexError):
            return None
            
    def _calculate_quality_score(self, job: CleanedJobData) -> float:
        """Calculate data quality score (0-1)"""
        score = 0.0
        
        # Basic completeness (40%)
        if job.title: score += 0.1
        if job.company: score += 0.1
        if job.location: score += 0.1
        if job.has_description: score += 0.1
        
        # Rich content (30%)
        if job.skills: score += 0.1
        if job.salary_range: score += 0.1
        if job.job_type != "full-time": score += 0.05  # Non-default type
        if job.experience_level != "any": score += 0.05  # Specific level
        
        # Text quality (20%)
        if job.text_length > 100: score += 0.1
        if job.text_length > 500: score += 0.1
        
        # Uniqueness indicators (10%)
        if job.url: score += 0.05
        if len(job.tech_stack) > 0: score += 0.05
        
        return min(score, 1.0)
        
    def _validate_job_quality(self, job: CleanedJobData) -> bool:
        """Validate if job meets minimum quality standards"""
        
        # Must have basic information
        if not job.title or not job.company:
            return False
            
        # Must have reasonable quality score
        if job.data_quality_score < 0.3:
            return False
            
        # Filter out obviously bad data
        if len(job.title) < 3 or len(job.company) < 2:
            return False
            
        return True
        
    def deduplicate_jobs(self, jobs: List[CleanedJobData]) -> List[CleanedJobData]:
        """Remove duplicate jobs using fuzzy matching"""
        unique_jobs = []
        seen_combinations = set()
        
        for job in jobs:
            # Create a signature for deduplication
            signature = (
                job.title_normalized.lower(),
                job.company_normalized.lower(),
                job.location_normalized.lower()
            )
            
            if signature not in seen_combinations:
                seen_combinations.add(signature)
                unique_jobs.append(job)
                
        self.logger.info(f"Deduplicated {len(jobs)} -> {len(unique_jobs)} jobs")
        return unique_jobs
        
    def get_cleaning_stats(self, cleaned_jobs: List[CleanedJobData]) -> Dict:
        """Get statistics about the cleaning process"""
        if not cleaned_jobs:
            return {}
            
        # Calculate various statistics
        avg_quality = sum(job.data_quality_score for job in cleaned_jobs) / len(cleaned_jobs)
        
        skill_counts = Counter()
        for job in cleaned_jobs:
            skill_counts.update(job.skills)
            
        experience_levels = Counter(job.experience_level for job in cleaned_jobs)
        job_types = Counter(job.job_type for job in cleaned_jobs)
        sources = Counter(job.source for job in cleaned_jobs)
        
        return {
            'total_jobs': len(cleaned_jobs),
            'average_quality_score': round(avg_quality, 3),
            'jobs_with_salary': len([j for j in cleaned_jobs if j.salary_range]),
            'remote_jobs': len([j for j in cleaned_jobs if j.remote_friendly]),
            'senior_roles': len([j for j in cleaned_jobs if j.is_senior_role]),
            'top_skills': dict(skill_counts.most_common(10)),
            'experience_distribution': dict(experience_levels),
            'job_type_distribution': dict(job_types),
            'source_distribution': dict(sources),
            'avg_description_length': sum(job.text_length for job in cleaned_jobs) // len(cleaned_jobs)
        }
