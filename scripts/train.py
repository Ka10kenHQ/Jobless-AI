#!/usr/bin/env python3
import sys
import os
import argparse
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.unified_config import UnifiedJobSearchConfig
from config.gpu_detector import GPUDetector, get_gpu_info
from training.trainer import JobSearchModelTrainer
from database.operations import TrainingOperations, JobOperations
from database.models import TrainingExample


async def prepare_training_data_from_mongodb(languages, num_samples):
    print("📊 Preparing training data from MongoDB...")
    
    training_ops = TrainingOperations()
    job_ops = JobOperations()
    
    existing_examples = await training_ops.get_training_dataset(languages)
    print(f"📚 Found {len(existing_examples)} existing training examples")
    
    if len(existing_examples) < num_samples:
        print(f"📝 Generating additional training examples from job data...")
        
        recent_jobs = await job_ops.get_recent_jobs(hours=24*365, limit=500)  # Last year
        print(f"🏢 Found {len(recent_jobs)} jobs in database")
        
        new_examples = []
        
        georgia_examples = [
            {
                "example_id": "georgia_context_1",
                "input_text": "Find jobs in Georgia",
                "output_text": "Searching for jobs in Georgia (country), also known as საქართველო. I'll look for positions in Tbilisi, Batumi, Kutaisi, and other Georgian cities. Georgian job market includes IT, tourism, agriculture, and finance sectors.",
                "source": "georgia_context",
                "language": "english",
                "task_type": "location_clarification"
            },
            {
                "example_id": "georgia_context_2", 
                "input_text": "I want to work in Georgia",
                "output_text": "Looking for job opportunities in Georgia (country). Major cities include Tbilisi (capital), Batumi (Black Sea coast), Kutaisi, and Rustavi. Popular industries: IT/tech, tourism, wine production, agriculture, banking, and telecommunications.",
                "source": "georgia_context",
                "language": "english", 
                "task_type": "location_clarification"
            },
            {
                "example_id": "georgia_context_3",
                "input_text": "Georgia jobs for software developer",
                "output_text": "Searching for software developer jobs in Georgia (country). Tbilisi has a growing tech scene with companies like TBC Bank, Bank of Georgia, and many international IT companies. Georgian lari (GEL) is the currency. Key tech hubs: Tbilisi, some opportunities in Batumi.",
                "source": "georgia_context",
                "language": "english",
                "task_type": "job_search_with_context"
            },
            {
                "example_id": "georgia_context_4",
                "input_text": "Remote work opportunities Georgia",
                "output_text": "Remote job opportunities for residents of Georgia (country). Time zone: Georgia Standard Time (GET, UTC+4). Many Georgian professionals work remotely for international companies. Growing digital nomad community in Tbilisi.",
                "source": "georgia_context",
                "language": "english",
                "task_type": "remote_work_context"
            },
            {
                "example_id": "georgia_context_5",
                "input_text": "Jobs in Tbilisi",
                "output_text": "Job opportunities in Tbilisi, the capital of Georgia (country). Major employers include banks (TBC, BOG), tech companies, government institutions, and international organizations. Languages: Georgian (ქართული), often English required for tech/international roles.",
                "source": "georgia_context", 
                "language": "english",
                "task_type": "city_specific_search"
            },
            {
                "example_id": "georgia_context_6",
                "input_text": "Georgian companies hiring",
                "output_text": "Georgian companies actively hiring include: TBC Bank (tech/banking), Bank of Georgia (finance/IT), Wissol (energy), Tegeta Motors (automotive), PSP (pharmaceuticals), and many growing startups in Tbilisi's tech district.",
                "source": "georgia_context",
                "language": "english",
                "task_type": "company_information"
            },
            {
                "example_id": "georgia_context_7",
                "input_text": "IT jobs Georgia country",
                "output_text": "IT sector is booming in Georgia (country). Major tech companies: TBC Pay, BOG (banking tech), Space International, Redberry, Singular, and many others. Government supports IT with tax incentives. Main programming languages: JavaScript, Python, Java, C#.",
                "source": "georgia_context",
                "language": "english", 
                "task_type": "industry_specific"
            },
            {
                "example_id": "georgia_context_8",
                "input_text": "Work permit Georgia",
                "output_text": "For working in Georgia (country): EU citizens can work visa-free for 365 days. Other nationals may need work permits. Georgia offers status of international higher education institution (IHEI) for some positions. Check with House of Justice for latest requirements.",
                "source": "georgia_context",
                "language": "english",
                "task_type": "legal_information"
            }
        ]
        
        # Add these Georgia-specific examples
        for example_data in georgia_examples:
            example = TrainingExample(**example_data)
            new_examples.append(example)
        
        # Generate examples from actual job data
        for i, job in enumerate(recent_jobs):
            if len(new_examples) >= (num_samples - len(existing_examples)):
                break
                
            if job.language in languages:
                # Enhance location context for Georgian jobs
                location_context = job.location
                if any(city in job.location.lower() for city in ['tbilisi', 'batumi', 'kutaisi', 'rustavi', 'gori']):
                    location_context = f"{job.location}, Georgia (country)"
                elif 'georgia' in job.location.lower() and 'atlanta' not in job.location.lower():
                    location_context = f"{job.location} (Georgia country, not US state)"
                
                example = TrainingExample(
                    example_id=f"mongodb_job_{job.id}_{i}",
                    input_text=f"Find jobs for: {job.title}",
                    output_text=f"Job: {job.title} at {job.company} in {location_context}\nDescription: {job.description[:200] if job.description else 'No description available'}",
                    source="mongodb_jobs",
                    language=job.language,
                    task_type="job_matching",
                    job_id=job.id
                )
                new_examples.append(example)
                
                if job.requirements:
                    req_example = TrainingExample(
                        example_id=f"mongodb_req_{job.id}_{i}",
                        input_text=f"Extract requirements for {job.title} position",
                        output_text=f"Requirements: {', '.join(job.requirements)}",
                        source="mongodb_jobs",
                        language=job.language,
                        task_type="requirement_extraction",
                        job_id=job.id
                    )
                    new_examples.append(req_example)
        
        if new_examples:
            saved_count = await training_ops.bulk_create_training_examples(new_examples)
            print(f"💾 Saved {saved_count} new training examples to MongoDB (including {len(georgia_examples)} Georgia-specific examples)")
        
        training_data = await training_ops.get_training_dataset(languages)
    else:
        training_data = existing_examples
    
    print(f"✅ Total training examples: {len(training_data)}")
    return training_data


def main():
    print("🚀 Unified Job Search Model Training (MongoDB-Powered)")
    print("🔧 Auto-detects your GPU and optimizes accordingly")
    print("🌍 Supports multilingual training (Georgian + English)")
    print("🗄️ Uses MongoDB for scalable data management")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(description="Train job search model with MongoDB data and automatic GPU optimization")
    parser.add_argument("--languages", nargs="+", default=["english"], 
                       choices=["english", "georgian"],
                       help="Languages to support (default: english)")
    parser.add_argument("--synthetic-samples", type=int, default=1000,
                       help="Number of training samples to generate from MongoDB data (default: 1000)")
    parser.add_argument("--no-real-data", action="store_true",
                       help="Use only existing training examples (skip generating new ones)")
    parser.add_argument("--quick-test", action="store_true",
                       help="Run a quick test with minimal data (50 samples)")
    parser.add_argument("--show-gpu-info", action="store_true",
                       help="Show detailed GPU information")
    
    args = parser.parse_args()
    
    if args.show_gpu_info:
        get_gpu_info()
    
    profile = GPUDetector.get_optimal_profile()
    print(f"🎮 Detected: {profile.name} ({profile.vram_gb}GB VRAM)")
    
    config = UnifiedJobSearchConfig(
        languages=args.languages,
        primary_language=args.languages[0] if args.languages else "english"
    )
    
    print("\n📋 Training Configuration:")
    config.print_config_summary()
    
    if args.quick_test:
        print("\n🧪 Quick test mode enabled")
        num_samples = 50
        generate_new = False
    else:
        num_samples = args.synthetic_samples
        generate_new = not args.no_real_data
    
    print(f"\n📊 Training Details:")
    print(f"   🌍 Languages: {', '.join(args.languages)}")
    print(f"   📝 Training samples: {num_samples}")
    print(f"   🗄️ Data source: MongoDB")
    print(f"   ⚡ Generate new examples: {generate_new}")
    print(f"   🤖 Model: {config.get_optimal_model()}")
    
    if "georgian" in args.languages:
        print(f"\n🇬🇪 Georgian Features Enabled:")
        print(f"   • Georgian job site scraping (hr.ge, jobs.ge)")
        print(f"   • Multilingual model with Georgian support")
        print(f"   • Cross-language job matching")
    
    if profile.vram_gb <= 8:
        print(f"\n💡 Memory Optimization Active:")
        print(f"   • BF16 precision for stability")
        print(f"   • Gradient checkpointing enabled")
        print(f"   • Batch size: {profile.batch_size}")
        print(f"   • 4-bit quantization: {profile.use_4bit}")
    
    print(f"\n🏁 Starting training...")
    print("=" * 60)
    
    try:
        training_data = asyncio.run(prepare_training_data_from_mongodb(args.languages, num_samples))
        
        if not training_data:
            print("❌ No training data available in MongoDB!")
            print("💡 Run migration first: python scripts/migrate_to_mongodb.py")
            sys.exit(1)
        
        print(f"📊 Using {len(training_data)} training examples from MongoDB")
        
    except Exception as e:
        print(f"❌ Error accessing MongoDB: {e}")
        print("💡 Make sure MongoDB is running and migration is complete")
        sys.exit(1)
    
    trainer = JobSearchModelTrainer()
    
    optimized_config = config.get_optimized_config()
    
    # Convert MongoDB training data to HuggingFace dataset format
    print("🔄 Converting MongoDB data to training format...")
    
    from datasets import Dataset, DatasetDict
    
    # Convert training data to the expected format
    formatted_data = []
    for item in training_data:
        formatted_data.append({
            "input": item["input"],
            "output": item["output"]
        })
    
    if not formatted_data:
        print("❌ No training data available!")
        sys.exit(1)
    
    # Create HuggingFace dataset
    dataset = Dataset.from_list(formatted_data)
    
    # Split into train/validation (90/10)
    split_dataset = dataset.train_test_split(test_size=0.1, seed=42)
    dataset_dict = DatasetDict({
        'train': split_dataset['train'],
        'validation': split_dataset['test']
    })
    
    print(f"📊 Dataset created:")
    print(f"   Train: {len(dataset_dict['train'])} examples")
    print(f"   Validation: {len(dataset_dict['validation'])} examples")
    
    # Save dataset to disk for the trainer
    dataset_path = os.path.join(optimized_config['output_dir'], 'mongodb_dataset')
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
    dataset_dict.save_to_disk(dataset_path)
    print(f"💾 Dataset saved to: {dataset_path}")
    
    # Train model directly with our prepared dataset
    print("🚀 Starting model training with MongoDB data...")
    
    try:
        # Initialize trainer components with optimized config
        trainer.config = type("Config", (), optimized_config)()
        for key, value in optimized_config.items():
            setattr(trainer.config, key, value)
        
        # Initialize trainer components
        from preprocessing.dataset_preparer import JobSearchDatasetPreparer
        from model_manager.lora_trainer import JobSearchLoRATrainer
        
        trainer.dataset_preparer = JobSearchDatasetPreparer(trainer.config)
        trainer.lora_trainer = JobSearchLoRATrainer(trainer.config)
        trainer._setup_directories()
        
        # Train model directly with our dataset
        train_result, eval_result = trainer.train_model(dataset=dataset_dict)
        
        # Test the trained model
        print("\n🧪 Testing trained model...")
        trainer.test_trained_model()
        
        success = True
        print("✅ MongoDB-powered training completed successfully!")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    if success:
        print("\n🎉 Training completed successfully!")
        print("🎯 Your MongoDB-powered model is optimized for:")
        print(f"   • GPU: {profile.name}")
        print(f"   • Languages: {', '.join(args.languages)}")
        print(f"   • Memory: {profile.vram_gb}GB VRAM")
        print(f"   • Training data: {len(training_data)} examples from MongoDB")
        
        print("\n📝 Next steps:")
        print("   1. Start trained server: python scripts/serve_trained.py")
        print("   2. Open chatbox: http://localhost:8000/chatbox")
        print("   3. Add more jobs: Use MongoDB collectors for new job data")
        if "georgian" in args.languages:
            print("   4. Test Georgian: Try job searches in Georgian language")
        
        print(f"\n💾 Model saved to: {optimized_config['output_dir']}")
        print(f"🗄️ Training data from: MongoDB (job_search_ai database)")
    else:
        print("\n❌ Training failed. Check the logs for details.")
        print(f"\n💡 Troubleshooting for {profile.name}:")
        print("   • MongoDB issues:")
        print("     - Check MongoDB is running: sudo systemctl status mongodb")
        print("     - Verify migration: python scripts/migrate_to_mongodb.py")
        print("     - Test connection: python test_mongodb_system.py")
        if profile.vram_gb <= 6:
            print("   • GPU memory issues:")
            print("     - Try --quick-test for minimal resource usage")
            print("     - Close other GPU applications (browsers, games)")
            print("     - Monitor GPU memory: watch -n 1 nvidia-smi")
        print("   • Check logs for specific error details")
        sys.exit(1)


if __name__ == "__main__":
    main()
