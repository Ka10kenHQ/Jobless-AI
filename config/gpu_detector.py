import torch
import subprocess
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class GPUProfile:
    name: str
    vram_gb: float
    batch_size: int
    gradient_accumulation_steps: int
    max_length: int
    use_4bit: bool = False
    use_gradient_checkpointing: bool = True
    precision: str = "bf16"  # bf16, fp16, or fp32


class GPUDetector:
    
    GPU_PROFILES = {
        "RTX 4090": GPUProfile("RTX 4090", 24.0, 8, 2, 2048, False, False, "bf16"),
        "RTX 4080": GPUProfile("RTX 4080", 16.0, 4, 4, 1536, False, True, "bf16"),
        "RTX 4070": GPUProfile("RTX 4070", 12.0, 2, 8, 1024, False, True, "bf16"),
        "RTX 4060": GPUProfile("RTX 4060", 8.0, 1, 16, 512, True, True, "bf16"),
        "RTX 4050": GPUProfile("RTX 4050", 6.0, 1, 16, 512, True, True, "bf16"),
        
        "RTX 3090": GPUProfile("RTX 3090", 24.0, 8, 2, 2048, False, False, "bf16"),
        "RTX 3080": GPUProfile("RTX 3080", 10.0, 2, 8, 1024, False, True, "bf16"),
        "RTX 3070": GPUProfile("RTX 3070", 8.0, 1, 16, 512, True, True, "bf16"),
        "RTX 3060": GPUProfile("RTX 3060", 12.0, 2, 8, 1024, False, True, "bf16"),
        
        "RTX 2080": GPUProfile("RTX 2080", 8.0, 1, 16, 512, True, True, "fp16"),
        "RTX 2070": GPUProfile("RTX 2070", 8.0, 1, 16, 512, True, True, "fp16"),
        "RTX 2060": GPUProfile("RTX 2060", 6.0, 1, 16, 512, True, True, "fp16"),
        
        "GTX 1080": GPUProfile("GTX 1080", 8.0, 1, 32, 256, True, True, "fp32"),
        "GTX 1070": GPUProfile("GTX 1070", 8.0, 1, 32, 256, True, True, "fp32"),
        
        "DEFAULT": GPUProfile("Unknown GPU", 6.0, 1, 16, 512, True, True, "bf16"),
    }
    
    @classmethod
    def detect_gpu(cls) -> Optional[str]:
        if not torch.cuda.is_available():
            return None
            
        try:
            gpu_name = torch.cuda.get_device_name(0)
            print(f"🔍 Detected GPU: {gpu_name}")
            
            for profile_name in cls.GPU_PROFILES.keys():
                if profile_name.replace(" ", "").lower() in gpu_name.replace(" ", "").lower():
                    return profile_name
                    
            return "DEFAULT"
            
        except Exception as e:
            print(f"⚠️ GPU detection failed: {e}")
            return "DEFAULT"
    
    @classmethod
    def get_gpu_memory(cls) -> float:
        if not torch.cuda.is_available():
            return 0.0
            
        try:
            total_memory = torch.cuda.get_device_properties(0).total_memory
            return total_memory / (1024**3)  # Convert to GB
        except:
            return 0.0
    
    @classmethod
    def get_optimal_profile(cls) -> GPUProfile:
        gpu_model = cls.detect_gpu()
        
        if gpu_model and gpu_model in cls.GPU_PROFILES:
            profile = cls.GPU_PROFILES[gpu_model]
        else:
            available_vram = cls.get_gpu_memory()
            print(f"🔧 Using memory-based profile for {available_vram:.1f}GB VRAM")
            
            if available_vram >= 20:
                profile = cls.GPU_PROFILES["RTX 4090"]
            elif available_vram >= 15:
                profile = cls.GPU_PROFILES["RTX 4080"]
            elif available_vram >= 10:
                profile = cls.GPU_PROFILES["RTX 3080"]
            elif available_vram >= 8:
                profile = cls.GPU_PROFILES["RTX 3070"]
            else:
                profile = cls.GPU_PROFILES["DEFAULT"]
        
        print(f"⚙️ Using profile: {profile.name}")
        print(f"   📊 VRAM: {profile.vram_gb}GB")
        print(f"   🔢 Batch size: {profile.batch_size}")
        print(f"   🔄 Gradient accumulation: {profile.gradient_accumulation_steps}")
        print(f"   📏 Max length: {profile.max_length}")
        print(f"   🎯 Precision: {profile.precision}")
        print(f"   ⚡ 4-bit quantization: {profile.use_4bit}")
        
        return profile
    
    @classmethod
    def create_training_config(cls, base_config: Dict[str, Any]) -> Dict[str, Any]:
        profile = cls.get_optimal_profile()
        
        optimized_config = base_config.copy()
        optimized_config.update({
            "per_device_train_batch_size": profile.batch_size,
            "per_device_eval_batch_size": profile.batch_size,
            "gradient_accumulation_steps": profile.gradient_accumulation_steps,
            "model_max_length": profile.max_length,
            "gradient_checkpointing": profile.use_gradient_checkpointing,
            "use_4bit_quantization": profile.use_4bit,
            
            "bf16": profile.precision == "bf16",
            "fp16": profile.precision == "fp16",
            "fp32": profile.precision == "fp32",
            
            "dataloader_pin_memory": not profile.use_gradient_checkpointing,
            "dataloader_num_workers": 0 if profile.vram_gb < 8 else 2,
            
            "torch_dtype": (
                "bfloat16" if profile.precision == "bf16" else
                "float16" if profile.precision == "fp16" else "float32"
            ),
            
            "cache_dir": "./cache",
            "output_dir": "./models/job_search_model",
            "logging_dir": "./logs",
        })
        
        return optimized_config


def get_gpu_info():
    print("🖥️ GPU Information:")
    print("=" * 50)
    
    if not torch.cuda.is_available():
        print("❌ CUDA not available")
        return
    
    gpu_count = torch.cuda.device_count()
    print(f"🔢 GPU Count: {gpu_count}")
    
    for i in range(gpu_count):
        props = torch.cuda.get_device_properties(i)
        memory_gb = props.total_memory / (1024**3)
        
        print(f"\n🎮 GPU {i}: {props.name}")
        print(f"   💾 Memory: {memory_gb:.1f}GB")
        print(f"   🔧 Compute Capability: {props.major}.{props.minor}")
        print(f"   🏭 Multiprocessors: {props.multi_processor_count}")
        
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(i) / (1024**3)
            cached = torch.cuda.memory_reserved(i) / (1024**3)
            print(f"   📊 Memory Used: {allocated:.2f}GB allocated, {cached:.2f}GB cached")


if __name__ == "__main__":
    get_gpu_info()
    profile = GPUDetector.get_optimal_profile()
    print(f"\n🎯 Recommended settings for your GPU:")
    print(f"   Batch size: {profile.batch_size}")
    print(f"   Gradient accumulation: {profile.gradient_accumulation_steps}")
    print(f"   Effective batch size: {profile.batch_size * profile.gradient_accumulation_steps}") 