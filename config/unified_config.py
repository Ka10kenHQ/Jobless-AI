from dataclasses import dataclass, field
from typing import List, Dict, Any
from .gpu_detector import GPUDetector


@dataclass
class UnifiedJobSearchConfig:
    """Unified configuration that automatically optimizes for your hardware"""

    base_models: Dict[str, str] = field(
        default_factory=lambda: {
            "english_small": "microsoft/DialoGPT-small",  # 117M params, good for 6GB
            "english_medium": "microsoft/DialoGPT-medium",  # 345M params, needs 8GB+
            "multilingual_small": "ai-forever/mGPT",  # 1.3B params, Georgian support
            "multilingual_medium": "facebook/xglm-564M",  # 564M params, multilingual
            "multilingual_large": "facebook/xglm-1.7B",  # 1.7B params, needs 12GB+
            "georgian_optimized": "ai-forever/mGPT",  # Best Georgian support for mid-range GPUs
        }
    )

    languages: List[str] = field(default_factory=lambda: ["english", "georgian"])
    primary_language: str = "english"

    num_train_epochs: int = 3
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_steps: int = 100
    max_grad_norm: float = 1.0

    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: List[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )

    max_samples_train: int = 1000
    max_samples_eval: int = 200
    train_test_split: float = 0.8

    eval_steps: int = 50
    save_steps: int = 100
    save_total_limit: int = 3
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False

    logging_steps: int = 10
    report_to: List[str] = field(default_factory=list)  # ["wandb"] if API key available

    per_device_train_batch_size: int = 1  # Will be auto-set
    per_device_eval_batch_size: int = 1  # Will be auto-set
    gradient_accumulation_steps: int = 16  # Will be auto-set
    model_max_length: int = 512  # Will be auto-set

    cache_dir: str = "./cache"
    output_dir: str = "./models/job_search_model"
    logging_dir: str = "./logs"

    def get_optimal_model(self) -> str:
        """Get the best model for current GPU and language requirements"""
        profile = GPUDetector.get_optimal_profile()
        actual_vram = GPUDetector.get_gpu_memory()  # Get actual available VRAM

        if "georgian" in self.languages:
            if actual_vram >= 12:
                return self.base_models["multilingual_large"]
            elif actual_vram >= 6.5:
                return self.base_models["georgian_optimized"]  # mGPT
            else:
                return self.base_models["multilingual_medium"]  # XGLM-564M as fallback
        else:
            if actual_vram >= 8:
                return self.base_models["english_medium"]
            else:
                return self.base_models["english_small"]

    def get_optimized_config(self) -> Dict[str, Any]:
        """Get GPU-optimized configuration"""
        base_config = {
            "base_model": self.get_optimal_model(),
            "num_train_epochs": self.num_train_epochs,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "warmup_steps": self.warmup_steps,
            "max_grad_norm": self.max_grad_norm,
            # LoRA settings
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "lora_target_modules": self.lora_target_modules,
            # Data settings
            "max_samples_train": self.max_samples_train,
            "max_samples_eval": self.max_samples_eval,
            "train_test_split": self.train_test_split,
            # Evaluation
            "eval_steps": self.eval_steps,
            "save_steps": self.save_steps,
            "save_total_limit": self.save_total_limit,
            "load_best_model_at_end": self.load_best_model_at_end,
            "metric_for_best_model": self.metric_for_best_model,
            "greater_is_better": self.greater_is_better,
            # Logging
            "logging_steps": self.logging_steps,
            "report_to": self.report_to,
            # Paths
            "cache_dir": self.cache_dir,
            "output_dir": self.output_dir,
            "logging_dir": self.logging_dir,
            # Trainer paths
            "training_data_path": "./data/job_search_training_data.json",
            "synthetic_data_path": "./data/synthetic_job_data.json",
            
            # Training splits and limits (from old hyperparameters)
            "train_split_ratio": 0.8,
            "eval_split_ratio": 0.1, 
            "test_split_ratio": 0.1,
            "max_samples": None,
            
            # Feature flags (from old hyperparameters)
            "job_requirement_extraction": True,
            "skill_classification": True,
            "experience_level_classification": True,
            "location_parsing": True,
            
            # Language settings
            "languages": self.languages,
            "primary_language": self.primary_language,
        }

        return GPUDetector.create_training_config(base_config)

    def print_config_summary(self):
        """Print configuration summary"""
        config = self.get_optimized_config()
        model = config["base_model"]

        print("🚀 Job Search Model Configuration")
        print("=" * 50)
        print(f"🤖 Model: {model}")
        print(f"🌍 Languages: {', '.join(self.languages)}")
        print(f"🎯 Primary: {self.primary_language}")
        print(f"📊 Batch size: {config['per_device_train_batch_size']}")
        print(f"🔄 Gradient accumulation: {config['gradient_accumulation_steps']}")
        print(f"📏 Max length: {config['model_max_length']}")
        print(f"🎯 Precision: {config.get('torch_dtype', 'auto')}")
        print(f"⚡ 4-bit quantization: {config.get('use_4bit_quantization', False)}")
        print(f"💾 Gradient checkpointing: {config['gradient_checkpointing']}")

        effective_batch = (
            config["per_device_train_batch_size"]
            * config["gradient_accumulation_steps"]
        )
        print(f"🎪 Effective batch size: {effective_batch}")

        # Estimate training time
        samples = self.max_samples_train
        steps_per_epoch = samples // effective_batch
        total_steps = steps_per_epoch * self.num_train_epochs
        minutes_estimate = total_steps * 0.5  # Rough estimate: 0.5 min per step

        print(f"⏱️ Estimated training time: {minutes_estimate:.0f} minutes")


MULTILINGUAL_MODELS = {
    "ai-forever/mGPT": {
        "name": "mGPT (Multilingual GPT)",
        "size": "1.3B parameters",
        "languages": [
            "English",
            "Georgian",
            "Russian",
            "Armenian",
            "Azerbaijani",
            "+50 more",
        ],
        "vram_required": "6GB (with optimizations)",
        "description": "Excellent Georgian support, trained on diverse Georgian texts",
        "min_vram_gb": 6,
    },
    "facebook/xglm-564M": {
        "name": "XGLM-564M",
        "size": "564M parameters",
        "languages": ["English", "Georgian", "+30 languages"],
        "vram_required": "4GB",
        "description": "Smaller multilingual model, good Georgian coverage",
        "min_vram_gb": 4,
    },
    "facebook/xglm-1.7B": {
        "name": "XGLM-1.7B",
        "size": "1.7B parameters",
        "languages": ["English", "Georgian", "+30 languages"],
        "vram_required": "8GB+",
        "description": "Larger model with better quality",
        "min_vram_gb": 8,
    },
}


def print_multilingual_options():
    print("🌍 Multilingual Model Options for Georgian Support")
    print("=" * 60)

    current_vram = GPUDetector.get_gpu_memory()

    for model_id, info in MULTILINGUAL_MODELS.items():
        compat = "✅" if current_vram >= info["min_vram_gb"] else "❌"
        print(f"\n{compat} {info['name']}")
        print(f"   📦 Size: {info['size']}")
        print(f"   💾 VRAM: {info['vram_required']}")
        print(f"   🌍 Languages: {', '.join(info['languages'][:3])}...")
        print(f"   📝 {info['description']}")
        if current_vram < info["min_vram_gb"]:
            print(
                f"   ⚠️  Requires {info['min_vram_gb']}GB VRAM (you have {current_vram:.1f}GB)"
            )


if __name__ == "__main__":
    print_multilingual_options()
    print("\n")

    config = UnifiedJobSearchConfig(
        languages=["english", "georgian"], primary_language="english"
    )
    config.print_config_summary()

