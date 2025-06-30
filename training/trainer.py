"""
Main training orchestrator for job search model
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.hyperparameters import TRAINING_CONFIG
from preprocessing.dataset_preparer import JobSearchDatasetPreparer
from model_manager.lora_trainer import JobSearchLoRATrainer
from data_collection.scraper_hr_ge import JobScraper


class JobSearchModelTrainer:
    def __init__(self, config=None):
        self.config = config or TRAINING_CONFIG
        self.dataset_preparer = JobSearchDatasetPreparer(self.config)
        self.lora_trainer = JobSearchLoRATrainer(self.config)
        self.job_scraper = JobScraper()

        self._setup_directories()

    def _setup_directories(self):
        """Create necessary directories for training"""
        directories = [
            self.config.output_dir,
            self.config.logging_dir,
            self.config.cache_dir,
            os.path.dirname(self.config.training_data_path),
            os.path.dirname(self.config.synthetic_data_path),
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def collect_training_data(self, num_jobs: int = 100):
        """Collect real job data for training"""
        print("🔍 Collecting real job data...")

        # Keywords to search for diverse job types
        search_keywords = [
            "software engineer",
            "data scientist",
            "product manager",
            "ux designer",
            "devops engineer",
            "machine learning engineer",
            "frontend developer",
            "backend developer",
            "full stack developer",
        ]

        all_jobs = []
        for keyword in search_keywords:
            print(f"  📝 Searching for: {keyword}")
            try:
                jobs = self.job_scraper.scrape_all_sources(
                    keywords=keyword,
                    location="",
                    limit_per_source=max(1, num_jobs // len(search_keywords)),
                )
                all_jobs.extend(jobs)

                if len(all_jobs) >= num_jobs:
                    break

            except Exception as e:
                print(f"  ⚠️ Error scraping {keyword}: {e}")
                continue

        # Save collected job data
        job_data_path = os.path.join(
            os.path.dirname(self.config.training_data_path), "collected_jobs.json"
        )
        with open(job_data_path, "w") as f:
            json.dump(all_jobs, f, indent=2)

        print(f"✅ Collected {len(all_jobs)} job postings")
        return job_data_path

    def prepare_training_data(
        self, num_synthetic: int = 5000, collect_real_data: bool = True
    ):
        """Prepare the complete training dataset"""
        print("📊 Preparing training dataset...")

        # Collect real job data if requested
        real_data_path = None
        if collect_real_data:
            try:
                real_data_path = self.collect_training_data()
            except Exception as e:
                print(f"⚠️ Could not collect real data: {e}")
                print("📝 Proceeding with synthetic data only")

        # Prepare dataset
        dataset = self.dataset_preparer.prepare_full_dataset(
            num_synthetic=num_synthetic, real_data_path=real_data_path
        )

        # Save dataset
        dataset_path = os.path.join(
            os.path.dirname(self.config.training_data_path), "processed_dataset"
        )
        self.dataset_preparer.save_dataset(dataset, dataset_path)

        print(
            f"✅ Training dataset prepared with {len(dataset['train'])} training examples"
        )
        return dataset, dataset_path

    def train_model(self, dataset=None, dataset_path=None):
        """Train the job search model"""
        print("🚀 Starting model training...")

        # Load dataset if not provided
        if dataset is None:
            if dataset_path and os.path.exists(dataset_path):
                from datasets import load_from_disk

                dataset = load_from_disk(dataset_path)
                print(f"📂 Loaded dataset from {dataset_path}")
            else:
                print("📊 No dataset provided, preparing new dataset...")
                dataset, _ = self.prepare_training_data()

        # Train the model
        train_result = self.lora_trainer.train(dataset)

        # Evaluate the model
        eval_result = self.lora_trainer.evaluate()

        print("✅ Model training completed!")
        return train_result, eval_result

    def test_trained_model(self):
        """Test the trained model with sample inputs"""
        print("🧪 Testing trained model...")

        test_prompts = [
            "Extract job requirements from: I'm looking for a senior Python developer job in New York with React experience\nRequirements:",
            "User: Find me remote data scientist positions\nAssistant:",
            "Extract job requirements from: I want an entry-level software engineer role in San Francisco\nRequirements:",
            "User: Can you help me find machine learning engineer jobs?\nAssistant:",
        ]

        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n📝 Test {i}: {prompt[:50]}...")
            try:
                response = self.lora_trainer.generate_response(prompt, max_length=200)
                print(f"🤖 Response: {response}")
            except Exception as e:
                print(f"❌ Error generating response: {e}")

    def full_training_pipeline(
        self,
        num_synthetic: int = 5000,
        collect_real_data: bool = True,
        test_after_training: bool = True,
        custom_config=None,
    ):
        print("🎯 Starting full job search model training pipeline")
        print("=" * 60)

        if custom_config:
            print("🔧 Using unified GPU-optimized configuration")
            self.config = type("Config", (), custom_config)()
            for key, value in custom_config.items():
                setattr(self.config, key, value)

            self.dataset_preparer = JobSearchDatasetPreparer(self.config)
            self.lora_trainer = JobSearchLoRATrainer(self.config)
            self._setup_directories()

        start_time = datetime.now()

        try:
            print("\n📊 Step 1: Data Preparation")
            dataset, dataset_path = self.prepare_training_data(
                num_synthetic=num_synthetic, collect_real_data=collect_real_data
            )

            print("\n🚀 Step 2: Model Training")
            train_result, eval_result = self.train_model(dataset)

            if test_after_training:
                print("\n🧪 Step 3: Model Testing")
                self.test_trained_model()

            end_time = datetime.now()
            duration = end_time - start_time

            print("\n" + "=" * 60)
            print("✅ Training pipeline completed successfully!")
            print(f"⏱️ Total time: {duration}")
            print(f"📁 Model saved to: {self.config.output_dir}")
            print(
                f"📊 Training loss: {train_result.metrics.get('train_loss', 'N/A'):.4f}"
            )
            print(f"📈 Evaluation loss: {eval_result.get('eval_loss', 'N/A'):.4f}")

            return True

        except Exception as e:
            print(f"\n❌ Training pipeline failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def resume_training(self, checkpoint_path: str):
        print(f"🔄 Resuming training from {checkpoint_path}")

        dataset_path = os.path.join(
            os.path.dirname(self.config.training_data_path), "processed_dataset"
        )
        if os.path.exists(dataset_path):
            from datasets import load_from_disk

            dataset = load_from_disk(dataset_path)
        else:
            print("❌ No saved dataset found. Preparing new dataset...")
            dataset, _ = self.prepare_training_data()

        self.lora_trainer.setup_model_and_tokenizer()
        self.lora_trainer.setup_lora_config()
        tokenized_dataset = self.lora_trainer.preprocess_dataset(dataset)
        self.lora_trainer.setup_trainer(tokenized_dataset)

        train_result = self.lora_trainer.trainer.train(
            resume_from_checkpoint=checkpoint_path
        )

        self.lora_trainer.save_model()
        eval_result = self.lora_trainer.evaluate()

        print("✅ Training resumed and completed!")
        return train_result, eval_result


def main():
    parser = argparse.ArgumentParser(description="Train job search model")
    parser.add_argument(
        "--num-synthetic",
        type=int,
        default=5000,
        help="Number of synthetic training examples",
    )
    parser.add_argument(
        "--no-real-data", action="store_true", help="Skip collecting real job data"
    )
    parser.add_argument(
        "--no-test", action="store_true", help="Skip testing after training"
    )
    parser.add_argument("--resume", type=str, help="Resume training from checkpoint")
    parser.add_argument("--config", type=str, help="Path to custom config file")

    args = parser.parse_args()

    config = TRAINING_CONFIG
    if args.config and os.path.exists(args.config):
        with open(args.config, "r") as f:
            custom_config = json.load(f)
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

    trainer = JobSearchModelTrainer(config)

    if args.resume:
        trainer.resume_training(args.resume)
    else:
        trainer.full_training_pipeline(
            num_synthetic=args.num_synthetic,
            collect_real_data=not args.no_real_data,
            test_after_training=not args.no_test,
        )


if __name__ == "__main__":
    main()
