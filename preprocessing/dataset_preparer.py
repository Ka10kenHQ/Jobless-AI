import json
import random
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import pandas as pd
from datasets import Dataset, DatasetDict
import re
from pathlib import Path


@dataclass
class JobSearchExample:
    user_message: str
    extracted_requirements: Dict[str, Any]
    response: str
    task_type: str 


class JobSearchDatasetPreparer:
    def __init__(self, config):
        self.config = config
        
        self.requirement_templates = [
            "I'm looking for a {experience_level} {job_title} position in {location}",
            "Find me {job_title} jobs in {location} with {skills} experience",
            "I want a {job_type} {job_title} role focusing on {skills}",
            "Looking for {experience_level} {job_title} opportunities in {location}",
            "I need a {job_title} position that involves {skills} and {additional_skills}",
            "Can you help me find {job_type} {job_title} jobs in {location}?",
            "I'm searching for a {job_title} role with {years_experience} years experience",
        ]
        
        self.job_titles = [
            "Software Engineer", "Data Scientist", "Product Manager", "UX Designer",
            "DevOps Engineer", "Frontend Developer", "Backend Developer", 
            "Full Stack Developer", "Machine Learning Engineer", "Data Analyst",
            "Technical Writer", "Engineering Manager", "Solutions Architect",
            "Mobile Developer", "Security Engineer", "Database Administrator"
        ]
        
        self.locations = [
            "New York", "San Francisco", "London", "Berlin", "Toronto", "Remote",
            "Seattle", "Austin", "Boston", "Los Angeles", "Chicago", "Amsterdam",
            "Paris", "Sydney", "Tokyo", "Singapore", "Bangalore", "Tel Aviv", "Tbilisi",
            "Kutaisi", "Batumi", "Rustavi", "Zugdidi", "Kaspi"

        ]
        
        self.skills = {
            "programming": ["Python", "JavaScript", "Java", "C++", "Go", "Rust", "TypeScript"],
            "web": ["React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "Express"],
            "data": ["SQL", "PostgreSQL", "MongoDB", "Pandas", "NumPy", "TensorFlow", "PyTorch"],
            "cloud": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform"],
            "tools": ["Git", "Jenkins", "Jira", "Figma", "Sketch", "Photoshop"]
        }
        
        self.experience_levels = ["entry-level", "junior", "mid-level", "senior", "lead", "principal"]
        self.job_types = ["full-time", "part-time", "contract", "remote", "hybrid"]
    
    def generate_synthetic_training_data(self, num_samples: int = 5000) -> List[JobSearchExample]:
        """Generate synthetic training data for job search tasks"""
        examples = []
        
        for _ in range(num_samples):
            # Generate requirement extraction examples
            if random.random() < 0.4:
                examples.append(self._generate_requirement_extraction_example())
            
            # Generate job matching examples
            elif random.random() < 0.3:
                examples.append(self._generate_job_matching_example())
            
            # Generate conversation examples
            else:
                examples.append(self._generate_conversation_example())
        
        return examples
    
    def _generate_requirement_extraction_example(self) -> JobSearchExample:
        """Generate a requirement extraction training example"""
        job_title = random.choice(self.job_titles)
        location = random.choice(self.locations)
        experience_level = random.choice(self.experience_levels)
        job_type = random.choice(self.job_types)
        
        # Select random skills
        selected_skills = []
        for category, skill_list in self.skills.items():
            if random.random() < 0.6:  # 60% chance to include skills from each category
                selected_skills.extend(random.sample(skill_list, min(2, len(skill_list))))
        
        # Generate user message
        template = random.choice(self.requirement_templates)
        user_message = template.format(
            job_title=job_title,
            location=location,
            experience_level=experience_level,
            job_type=job_type,
            skills=", ".join(selected_skills[:2]) if selected_skills else "programming",
            additional_skills=", ".join(selected_skills[2:4]) if len(selected_skills) > 2 else "development",
            years_experience=random.choice(["2-3", "3-5", "5+", "7+"])
        )
        
        # Create structured requirements
        requirements = {
            "keywords": job_title.lower(),
            "location": location,
            "experience_level": experience_level,
            "job_type": job_type,
            "skills": selected_skills[:4],
            "company_type": "any"
        }
        
        # Generate response
        response = f"I'll help you find {job_title} positions. Let me search for {experience_level} roles in {location}."
        
        return JobSearchExample(
            user_message=user_message,
            extracted_requirements=requirements,
            response=response,
            task_type="requirement_extraction"
        )
    
    def _generate_job_matching_example(self) -> JobSearchExample:
        """Generate a job matching training example"""
        job_title = random.choice(self.job_titles)
        company = f"{random.choice(['Tech', 'Innovation', 'Digital', 'Smart', 'Future'])} {random.choice(['Corp', 'Solutions', 'Systems', 'Labs', 'Inc'])}"
        location = random.choice(self.locations)
        
        user_message = f"Is this {job_title} position at {company} in {location} a good match for me?"
        
        requirements = {
            "keywords": job_title.lower(),
            "location": location,
            "experience_level": "any",
            "job_type": "any",
            "skills": random.sample([skill for skills in self.skills.values() for skill in skills], 3),
            "company_type": "any"
        }
        
        match_score = random.uniform(0.6, 0.95)
        response = f"This {job_title} position at {company} looks like a {int(match_score*100)}% match based on your requirements. The location matches your preference for {location}."
        
        return JobSearchExample(
            user_message=user_message,
            extracted_requirements=requirements,
            response=response,
            task_type="job_matching"
        )
    
    def _generate_conversation_example(self) -> JobSearchExample:
        """Generate conversational training examples"""
        conversation_types = [
            "follow_up", "clarification", "refinement", "feedback"
        ]
        
        conv_type = random.choice(conversation_types)
        
        if conv_type == "follow_up":
            user_message = random.choice([
                "Can you show me more details about the first job?",
                "What other similar positions are available?",
                "Are there any remote options?",
                "Can you find jobs at larger companies?"
            ])
            response = "I'll search for additional opportunities that match your criteria."
        
        elif conv_type == "clarification":
            user_message = random.choice([
                "I prefer remote work, can you update the search?",
                "Actually, I'm open to contract positions too",
                "I'd like to focus on senior-level roles only",
                "Can you include part-time opportunities?"
            ])
            response = "I've updated your preferences. Let me search again with the new criteria."
        
        elif conv_type == "refinement":
            user_message = random.choice([
                "I want to add machine learning to my skill requirements",
                "Please exclude positions that require 10+ years experience",
                "I'm also interested in startup companies",
                "Can you focus on companies with good work-life balance?"
            ])
            response = "I've refined your search criteria. Here are the updated results."
        
        else:  # feedback
            user_message = random.choice([
                "These matches look great, thank you!",
                "The first few jobs seem perfect for me",
                "This is exactly what I was looking for",
                "Can you help me understand why these jobs match my profile?"
            ])
            response = "I'm glad these opportunities match what you're looking for! The matching algorithm considers your skills, experience, and location preferences."
        
        return JobSearchExample(
            user_message=user_message,
            extracted_requirements={},
            response=response,
            task_type="conversation"
        )
    
    def create_training_dataset(self, examples: List[JobSearchExample]) -> DatasetDict:
        """Convert examples to HuggingFace dataset format"""
        
        # Prepare data for different tasks
        requirement_examples = []
        conversation_examples = []
        
        for example in examples:
            if example.task_type == "requirement_extraction":
                # Format for requirement extraction task
                prompt = f"Extract job requirements from: {example.user_message}\nRequirements:"
                target = json.dumps(example.extracted_requirements)
                
                requirement_examples.append({
                    "input": prompt,
                    "output": target,
                    "task": "requirement_extraction"
                })
            
            else:
                # Format for conversational task
                prompt = f"User: {example.user_message}\nAssistant:"
                target = example.response
                
                conversation_examples.append({
                    "input": prompt,
                    "output": target,
                    "task": "conversation"
                })
        
        # Combine all examples
        all_examples = requirement_examples + conversation_examples
        random.shuffle(all_examples)
        
        # Split into train/eval/test
        total_size = len(all_examples)
        train_size = int(total_size * self.config.train_split_ratio)
        eval_size = int(total_size * self.config.eval_split_ratio)
        
        train_data = all_examples[:train_size]
        eval_data = all_examples[train_size:train_size + eval_size]
        test_data = all_examples[train_size + eval_size:]
        
        # Create datasets
        dataset_dict = DatasetDict({
            "train": Dataset.from_list(train_data),
            "validation": Dataset.from_list(eval_data),
            "test": Dataset.from_list(test_data)
        })
        
        return dataset_dict
    
    def load_real_job_data(self, job_data_path: str = None) -> List[JobSearchExample]:
        """Load and process real job data if available"""
        examples = []
        
        if job_data_path and Path(job_data_path).exists():
            with open(job_data_path, 'r') as f:
                job_data = json.load(f)
            
            for job in job_data:
                # Create training examples from real job postings
                example = self._job_posting_to_example(job)
                if example:
                    examples.append(example)
        
        return examples
    
    def _job_posting_to_example(self, job: Dict) -> JobSearchExample:
        """Convert a job posting to a training example"""
        try:
            # Extract key information
            title = job.get('title', '')
            company = job.get('company', '')
            location = job.get('location', '')
            description = job.get('description', '')
            
            # Generate a user query based on the job
            user_message = f"I'm looking for a {title} position similar to the one at {company}"
            
            # Extract requirements from job description
            requirements = self._extract_requirements_from_description(description, title, location)
            
            response = f"I found a {title} position at {company} in {location} that matches your criteria."
            
            return JobSearchExample(
                user_message=user_message,
                extracted_requirements=requirements,
                response=response,
                task_type="job_matching"
            )
        except Exception as e:
            print(f"Error processing job posting: {e}")
            return None
    
    def _extract_requirements_from_description(self, description: str, title: str, location: str) -> Dict:
        """Extract structured requirements from job description"""
        requirements = {
            "keywords": title.lower(),
            "location": location,
            "experience_level": "any",
            "job_type": "full-time",
            "skills": [],
            "company_type": "any"
        }
        
        description_lower = description.lower()
        
        # Extract experience level
        if any(term in description_lower for term in ["senior", "lead", "principal", "staff"]):
            requirements["experience_level"] = "senior"
        elif any(term in description_lower for term in ["junior", "entry", "associate"]):
            requirements["experience_level"] = "entry"
        else:
            requirements["experience_level"] = "mid"
        
        # Extract skills
        found_skills = []
        for category, skill_list in self.skills.items():
            for skill in skill_list:
                if skill.lower() in description_lower:
                    found_skills.append(skill)
        
        requirements["skills"] = found_skills[:6]  # Limit to 6 skills
        
        # Extract job type
        if "remote" in description_lower:
            requirements["job_type"] = "remote"
        elif "contract" in description_lower:
            requirements["job_type"] = "contract"
        elif "part-time" in description_lower or "part time" in description_lower:
            requirements["job_type"] = "part-time"
        
        return requirements
    
    def save_dataset(self, dataset: DatasetDict, path: str):
        """Save the prepared dataset"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        dataset.save_to_disk(path)
        print(f"Dataset saved to {path}")
    
    def prepare_full_dataset(self, num_synthetic: int = 5000, real_data_path: str = None) -> DatasetDict:
        """Prepare the complete training dataset"""
        print("🔄 Generating synthetic training data...")
        synthetic_examples = self.generate_synthetic_training_data(num_synthetic)
        
        print("📊 Loading real job data...")
        real_examples = self.load_real_job_data(real_data_path) if real_data_path else []
        
        all_examples = synthetic_examples + real_examples
        print(f"📝 Total examples: {len(all_examples)}")
        
        print("🔧 Creating training dataset...")
        dataset = self.create_training_dataset(all_examples)
        
        print("💾 Saving synthetic data...")
        with open(self.config.synthetic_data_path, 'w') as f:
            json.dump([{
                "user_message": ex.user_message,
                "extracted_requirements": ex.extracted_requirements,
                "response": ex.response,
                "task_type": ex.task_type
            } for ex in all_examples], f, indent=2)
        
        return dataset
