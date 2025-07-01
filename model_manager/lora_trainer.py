import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    EarlyStoppingCallback,
)
from peft.mapping import get_peft_model
from peft.tuners.lora import LoraConfig
from peft.peft_model import PeftModel
from peft.utils.peft_types import TaskType
from datasets import DatasetDict
import os
import json
from pathlib import Path


class JobSearchLoRATrainer:
    def __init__(self, config):
        self.config = config
        self.tokenizer = None
        self.model = None
        self.peft_model = None
        self.trainer = None

        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.logging_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)

    def setup_model_and_tokenizer(self):
        print(f"🔧 Loading base model: {self.config.base_model}")
        print("💾 Optimizing for RTX 4050 (6GB VRAM)...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model,
            cache_dir=self.config.cache_dir,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            cache_dir=self.config.cache_dir,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
            offload_folder="./offload",
        )

        self.model.resize_token_embeddings(len(self.tokenizer))

        if hasattr(self.model, "gradient_checkpointing_enable"):
            try:
                # Try newer PyTorch version with use_reentrant=False
                self.model.gradient_checkpointing_enable(use_reentrant=False)
            except TypeError:
                # Fall back to older PyTorch version without use_reentrant
                self.model.gradient_checkpointing_enable()

        print(f"✅ Model loaded with memory optimizations for 6GB VRAM")

    def setup_lora_config(self):
        print("🔧 Setting up LoRA configuration...")

        if "gpt" in self.config.base_model.lower():
            target_modules = ["c_attn", "c_proj"]
        elif "llama" in self.config.base_model.lower():
            target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]
        else:
            target_modules = self.config.lora_target_modules

        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=target_modules,
            bias="none",
        )

        self.peft_model = get_peft_model(self.model, lora_config)
        self.peft_model.print_trainable_parameters()

        print("✅ LoRA configuration applied")
        return lora_config

    def preprocess_dataset(self, dataset: DatasetDict) -> DatasetDict:
        print("🔄 Preprocessing dataset...")

        def tokenize_function(examples):
            texts = []
            for inp, out in zip(examples["input"], examples["output"]):
                text = f"{inp} {out}{self.tokenizer.eos_token}"
                texts.append(text)

            tokenized = self.tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=self.config.model_max_length,
                return_tensors="pt",
            )

            tokenized["labels"] = tokenized["input_ids"].clone()

            return tokenized

        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset["train"].column_names,
            desc="Tokenizing dataset",
        )

        print("✅ Dataset preprocessed")
        return tokenized_dataset

    def setup_trainer(self, tokenized_dataset: DatasetDict):
        print("🔧 Setting up trainer...")

        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            max_grad_norm=self.config.max_grad_norm,
            evaluation_strategy="steps",
            eval_steps=self.config.eval_steps,
            save_steps=self.config.save_steps,
            save_total_limit=self.config.save_total_limit,
            load_best_model_at_end=self.config.load_best_model_at_end,
            metric_for_best_model=self.config.metric_for_best_model,
            greater_is_better=self.config.greater_is_better,
            logging_dir=self.config.logging_dir,
            logging_steps=self.config.logging_steps,
            report_to=["tensorboard"],
            # Memory optimizations for 6GB VRAM
            dataloader_pin_memory=False,  # Disable to save memory
            remove_unused_columns=False,
            bf16=True,  # Use BF16 instead of FP16 for better stability
            gradient_checkpointing=True,  # Enable gradient checkpointing
            dataloader_num_workers=0,  # Reduce CPU overhead
            group_by_length=True,  # Group sequences by length for efficiency
            # Additional memory optimizations
            save_safetensors=True,  # Use safer tensor format
            torch_compile=False,  # Disable for compatibility
        )

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # We're doing causal LM, not masked LM
        )

        self.trainer = Trainer(
            model=self.peft_model,
            args=training_args,
            train_dataset=tokenized_dataset["train"],
            eval_dataset=tokenized_dataset["validation"],
            data_collator=data_collator,
            tokenizer=self.tokenizer,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
        )

        print("✅ Trainer initialized")

    def train(self, dataset: DatasetDict):
        print("🚀 Starting training...")

        self.setup_model_and_tokenizer()

        lora_config = self.setup_lora_config()

        tokenized_dataset = self.preprocess_dataset(dataset)

        self.setup_trainer(tokenized_dataset)

        print("🔥 Training in progress...")
        train_result = self.trainer.train()

        self.save_model()

        self.save_training_metrics(train_result)

        print("✅ Training completed!")
        return train_result

    def save_model(self):
        print("💾 Saving model...")

        self.peft_model.save_pretrained(self.config.output_dir)

        self.tokenizer.save_pretrained(self.config.output_dir)

        config_path = os.path.join(self.config.output_dir, "training_config.json")
        with open(config_path, "w") as f:
            config_dict = {
                attr: getattr(self.config, attr)
                for attr in dir(self.config)
                if not attr.startswith("_")
            }
            json.dump(config_dict, f, indent=2)

        print(f"✅ Model saved to {self.config.output_dir}")

    def save_training_metrics(self, train_result):
        metrics_path = os.path.join(self.config.output_dir, "training_metrics.json")

        metrics = {
            "train_runtime": train_result.metrics.get("train_runtime", 0),
            "train_samples_per_second": train_result.metrics.get(
                "train_samples_per_second", 0
            ),
            "train_steps_per_second": train_result.metrics.get(
                "train_steps_per_second", 0
            ),
            "train_loss": train_result.metrics.get("train_loss", 0),
            "total_flos": train_result.metrics.get("total_flos", 0),
        }

        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        print(f"📊 Training metrics saved to {metrics_path}")

    def evaluate(self, dataset: DatasetDict = None):
        if self.trainer is None:
            print("❌ No trainer available. Train the model first.")
            return None

        print("📊 Evaluating model...")
        eval_result = self.trainer.evaluate()

        print("✅ Evaluation completed")
        print(f"Evaluation loss: {eval_result['eval_loss']:.4f}")

        return eval_result

    @classmethod
    def load_trained_model(cls, model_path: str, base_model: str = None):
        print(f"🔄 Loading trained model from {model_path}")

        config_path = os.path.join(model_path, "training_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config_dict = json.load(f)
                base_model = config_dict.get("base_model", base_model)

        if not base_model:
            raise ValueError("Base model not specified and not found in config")

        tokenizer = AutoTokenizer.from_pretrained(model_path)

        model = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=torch.float16, device_map="auto"
        )

        model = PeftModel.from_pretrained(model, model_path)

        print("✅ Trained model loaded successfully")
        return model, tokenizer

    def generate_response(self, prompt: str, max_length: int = 256) -> str:
        if self.peft_model is None or self.tokenizer is None:
            raise ValueError("Model not trained yet")

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.peft_model.device)

        with torch.no_grad():
            outputs = self.peft_model.generate(
                **inputs,
                max_length=max_length,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        response = response[len(prompt) :].strip()

        return response
