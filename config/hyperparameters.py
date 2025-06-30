from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JobSearchTrainingConfig:
    base_model: str = "microsoft/DialoGPT-small"
    model_max_length: int = 256

    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.1
    lora_target_modules: list = field(default_factory=list)

    num_train_epochs: int = 3
    per_device_train_batch_size: int = 1
    per_device_eval_batch_size: int = 2
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_steps: int = 100
    max_grad_norm: float = 1.0

    save_steps: int = 500
    eval_steps: int = 250
    logging_steps: int = 50
    save_total_limit: int = 3
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False

    train_split_ratio: float = 0.8
    eval_split_ratio: float = 0.1
    test_split_ratio: float = 0.1
    max_samples: Optional[int] = None

    job_requirement_extraction: bool = True
    skill_classification: bool = True
    experience_level_classification: bool = True
    location_parsing: bool = True

    output_dir: str = "./models/job_search_model"
    logging_dir: str = "./logs"
    cache_dir: str = "./cache"

    training_data_path: str = "./data/job_search_training_data.json"
    synthetic_data_path: str = "./data/synthetic_job_data.json"

    def __post_init__(self):
        if not self.lora_target_modules:
            self.lora_target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


@dataclass
class JobSearchInferenceConfig:
    model_path: str = "./models/job_search_model"
    device: str = "auto"
    torch_dtype: str = "float16"
    load_in_4bit: bool = True
    max_new_tokens: int = 128
    temperature: float = 0.7
    do_sample: bool = True
    top_p: float = 0.9
    repetition_penalty: float = 1.1


TRAINING_CONFIG = JobSearchTrainingConfig()
INFERENCE_CONFIG = JobSearchInferenceConfig()
