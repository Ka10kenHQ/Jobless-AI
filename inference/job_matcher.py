import re
from typing import List, Dict, Any
from fuzzywuzzy import fuzz
import json


class JobMatcher:
    def __init__(self):
        self.skill_keywords = {
            'programming': ['python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin'],
            'web': ['react', 'angular', 'vue', 'html', 'css', 'nodejs', 'express', 'django', 'flask'],
            'data': ['sql', 'mysql', 'postgresql', 'mongodb', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'jenkins'],
            'mobile': ['android', 'ios', 'react native', 'flutter', 'swift', 'kotlin'],
            'general': ['git', 'linux', 'agile', 'scrum', 'rest api', 'microservices']
        }
        
        self.experience_levels = {
            'entry': ['junior', 'entry', 'graduate', 'intern', '0-2 years', 'new grad'],
            'mid': ['mid', 'intermediate', '2-5 years', '3-7 years'],
            'senior': ['senior', 'lead', 'principal', '5+ years', '7+ years', 'architect']
        }
    
    def match_jobs(self, jobs: List[Dict], requirements: Dict[str, Any]) -> List[Dict]:
        matched_jobs = []
        
        for job in jobs:
            score = self.calculate_match_score(job, requirements)
            if score > 0.3:  # Minimum threshold
                job_copy = job.copy()
                job_copy['match_score'] = score
                job_copy['match_reasons'] = self.get_match_reasons(job, requirements)
                matched_jobs.append(job_copy)
        
        matched_jobs.sort(key=lambda x: x['match_score'], reverse=True)
        return matched_jobs
    
    def calculate_match_score(self, job: Dict, requirements: Dict[str, Any]) -> float:
        score = 0.0
        total_weight = 0.0
        
        title_score = self.match_title_keywords(job.get('title', ''), requirements.get('keywords', ''))
        score += title_score * 0.4
        total_weight += 0.4
        
        location_score = self.match_location(job.get('location', ''), requirements.get('location', ''))
        score += location_score * 0.2
        total_weight += 0.2
        
        skills_score = self.match_skills(job, requirements.get('skills', []))
        score += skills_score * 0.25
        total_weight += 0.25
        
        exp_score = self.match_experience_level(job, requirements.get('experience_level', 'any'))
        score += exp_score * 0.15
        total_weight += 0.15
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def match_title_keywords(self, job_title: str, required_keywords) -> float:
        if not required_keywords or not job_title:
            return 0.5
        
        job_title_lower = job_title.lower()
        
        # Handle both string and list inputs
        if isinstance(required_keywords, list):
            keywords = [kw.lower() for kw in required_keywords]
            keywords_str = " ".join(keywords)
        else:
            keywords_str = str(required_keywords).lower()
            keywords = keywords_str.split()
        
        matches = 0
        for keyword in keywords:
            if keyword in job_title_lower:
                matches += 1
        
        if keywords:
            direct_score = matches / len(keywords)
        else:
            direct_score = 0.0
        
        fuzzy_score = fuzz.partial_ratio(job_title_lower, keywords_str) / 100.0
        
        return max(direct_score, fuzzy_score * 0.8)
    
    def match_location(self, job_location: str, required_location: str) -> float:
        if not required_location:
            return 1.0
        
        if not job_location:
            return 0.7
        
        job_location_lower = job_location.lower()
        required_location_lower = required_location.lower()
        
        if 'remote' in required_location_lower:
            if 'remote' in job_location_lower:
                return 1.0
            else:
                return 0.3
        
        if required_location_lower in job_location_lower:
            return 1.0
        
        fuzzy_score = fuzz.partial_ratio(job_location_lower, required_location_lower) / 100.0
        return fuzzy_score
    
    def match_skills(self, job: Dict, required_skills: List[str]) -> float:
        if not required_skills:
            return 1.0
        
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        
        matches = 0
        for skill in required_skills:
            skill_lower = skill.lower()
            if skill_lower in job_text:
                matches += 1
            else:
                for category, skills_list in self.skill_keywords.items():
                    if skill_lower in skills_list:
                        for related_skill in skills_list:
                            if related_skill in job_text:
                                matches += 0.5
                                break
        
        return min(matches / len(required_skills), 1.0) if required_skills else 1.0
    
    def match_experience_level(self, job: Dict, required_level: str) -> float:
        if required_level == 'any':
            return 1.0
        
        job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        
        for level, keywords in self.experience_levels.items():
            for keyword in keywords:
                if keyword in job_text:
                    if level == required_level:
                        return 1.0
                    elif (level == 'mid' and required_level in ['entry', 'senior']) or \
                         (level == 'entry' and required_level == 'mid') or \
                         (level == 'senior' and required_level == 'mid'):
                        return 0.7
                    else:
                        return 0.3
        
        return 0.8
    
    def get_match_reasons(self, job: Dict, requirements: Dict[str, Any]) -> List[str]:
        reasons = []
        
        if requirements.get('keywords'):
            keywords_for_display = requirements['keywords']
            if isinstance(keywords_for_display, list):
                keywords_display_str = ", ".join(keywords_for_display)
            else:
                keywords_display_str = str(keywords_for_display)
            
            title_score = self.match_title_keywords(job.get('title', ''), requirements['keywords'])
            if title_score > 0.7:
                reasons.append(f"Title closely matches '{keywords_display_str}'")
            elif title_score > 0.4:
                reasons.append(f"Title partially matches '{keywords_display_str}'")
        
        if requirements.get('location'):
            location_score = self.match_location(job.get('location', ''), requirements['location'])
            if location_score > 0.8:
                reasons.append(f"Location matches '{requirements['location']}'")
        
        if requirements.get('skills'):
            job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
            matched_skills = []
            for skill in requirements['skills']:
                if skill.lower() in job_text:
                    matched_skills.append(skill)
            
            if matched_skills:
                reasons.append(f"Mentions required skills: {', '.join(matched_skills)}")
        
        if requirements.get('experience_level') and requirements['experience_level'] != 'any':
            exp_score = self.match_experience_level(job, requirements['experience_level'])
            if exp_score > 0.8:
                reasons.append(f"Matches {requirements['experience_level']} level experience")
        
        return reasons if reasons else ["General match based on search criteria"]
    
    def filter_by_criteria(self, jobs: List[Dict], criteria: Dict[str, Any]) -> List[Dict]:
        filtered_jobs = []
        
        for job in jobs:
            if self.meets_criteria(job, criteria):
                filtered_jobs.append(job)
        
        return filtered_jobs
    
    def meets_criteria(self, job: Dict, criteria: Dict[str, Any]) -> bool:
        if criteria.get('salary_min'):
            pass
        
        if criteria.get('company_size'):
            pass
        
        if criteria.get('job_type') and criteria['job_type'] != 'any':
            job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
            job_type = criteria['job_type'].lower()
            
            if job_type == 'remote':
                if 'remote' not in job_text and 'work from home' not in job_text:
                    return False
            elif job_type == 'contract':
                if 'contract' not in job_text and 'contractor' not in job_text:
                    return False
            elif job_type == 'part-time':
                if 'part-time' not in job_text and 'part time' not in job_text:
                    return False
        
        return True 