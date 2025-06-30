#!/usr/bin/env python3

import os
import shutil
import json
from pathlib import Path


def migrate_directories():
    print("📁 Migrating directories...")
    
    migrations = [
        ("cache_rtx4050", "cache"),
        ("logs_rtx4050", "logs"), 
        ("models/job_search_model_rtx4050", "models/job_search_model"),
    ]
    
    for old_path, new_path in migrations:
        old_dir = Path(old_path)
        new_dir = Path(new_path)
        
        if old_dir.exists():
            print(f"  📦 Moving {old_path} → {new_path}")
            
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            
            if new_dir.exists():
                print(f"    🔄 Merging with existing {new_path}")
                for item in old_dir.iterdir():
                    dest = new_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                shutil.rmtree(old_dir)
            else:
                old_dir.rename(new_dir)
        else:
            print(f"  ✅ {old_path} doesn't exist (already migrated?)")


def backup_old_configs():
    """Backup old configuration files"""
    print("💾 Backing up old configurations...")
    
    backup_dir = Path("config/backup_rtx4050_specific")
    backup_dir.mkdir(exist_ok=True)
    
    old_configs = [
        "config/rtx4050_config.py",
        "config/hyperparameters.py"
    ]
    
    for config_file in old_configs:
        config_path = Path(config_file)
        if config_path.exists():
            backup_path = backup_dir / config_path.name
            print(f"  📋 Backing up {config_file} → {backup_path}")
            shutil.copy2(config_path, backup_path)


def update_scripts():
    print("🔧 Updating scripts...")
    
    train_script = Path("scripts/train.py")
    if train_script.exists():
        print("  ⚙️ Updating train.py to use unified config")
        
        content = train_script.read_text()
        
        if "from config.rtx4050_config import RTX4050Config" in content:
            content = content.replace(
                "from config.rtx4050_config import RTX4050Config",
                "from config.unified_config import UnifiedJobSearchConfig"
            )
            content = content.replace(
                "RTX4050Config()",
                "UnifiedJobSearchConfig(languages=['english', 'georgian']).get_optimized_config()"
            )
            
            train_script.write_text(content)
            print("    ✅ Updated train.py")
    
    scripts_to_update = [
        "scripts/serve.py",
        "scripts/serve_trained.py",
    ]
    
    for script_path in scripts_to_update:
        script = Path(script_path)
        if script.exists():
            content = script.read_text()
            if "rtx4050" in content.lower():
                print(f"  🔍 Found RTX 4050 references in {script_path}")
                print(f"    💡 Manual review recommended for {script_path}")


def create_compatibility_layer():
    print("🔗 Creating compatibility layer...")
    
    compat_file = Path("config/rtx4050_config.py")
    
    compat_content = '''"""
Compatibility layer for old RTX 4050-specific imports.
This file redirects to the new unified configuration system.
"""

import warnings
from .unified_config import UnifiedJobSearchConfig

# Compatibility warning
warnings.warn(
    "RTX4050Config is deprecated. Use UnifiedJobSearchConfig instead for automatic GPU detection.",
    DeprecationWarning,
    stacklevel=2
)

class RTX4050Config:
    """Deprecated: Use UnifiedJobSearchConfig instead"""
    
    def __init__(self):
        warnings.warn(
            "RTX4050Config is deprecated. Use UnifiedJobSearchConfig().get_optimized_config() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Use unified config with Georgian support
        unified = UnifiedJobSearchConfig(languages=["english", "georgian"])
        config = unified.get_optimized_config()
        
        # Set attributes for backward compatibility
        for key, value in config.items():
            setattr(self, key, value)

# For backward compatibility
def get_rtx4050_config():
    """Deprecated: Use UnifiedJobSearchConfig instead"""
    return RTX4050Config()
'''
    
    print("  📝 Writing compatibility layer")
    compat_file.write_text(compat_content)


def test_new_system():
    """Test that the new unified system works"""
    print("🧪 Testing new unified system...")
    
    try:
        from config.gpu_detector import GPUDetector
        from config.unified_config import UnifiedJobSearchConfig
        
        # Test GPU detection
        profile = GPUDetector.get_optimal_profile()
        print(f"  ✅ GPU Detection: {profile.name} ({profile.vram_gb}GB)")
        
        # Test unified config
        config = UnifiedJobSearchConfig(languages=["english", "georgian"])
        optimized = config.get_optimized_config()
        print(f"  ✅ Unified Config: {optimized['base_model']}")
        
        print("  🎉 All tests passed!")
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False


def print_migration_summary():
    """Print summary of changes"""
    print("\n" + "="*60)
    print("🎉 MIGRATION COMPLETE!")
    print("="*60)
    print()
    print("📋 What Changed:")
    print("  ❌ OLD: GPU-specific configs (rtx4050_config.py)")
    print("  ✅ NEW: Unified auto-detection (unified_config.py)")
    print()
    print("  ❌ OLD: GPU-specific directories (cache_rtx4050/, logs_rtx4050/)")
    print("  ✅ NEW: Unified directories (cache/, logs/, models/)")
    print()
    print("  ❌ OLD: Manual GPU optimization")
    print("  ✅ NEW: Automatic GPU detection + optimization")
    print()
    print("🌍 New Features:")
    print("  🇬🇪 Georgian language support (hr.ge, jobs.ge scrapers)")
    print("  🤖 mGPT multilingual model (supports Georgian + English)")
    print("  🔧 Auto-optimization for ANY GPU (not just RTX 4050)")
    print("  📊 Better memory management")
    print()
    print("🚀 Next Steps:")
    print("  1. Train with: python scripts/train.py --quick-test")
    print("  2. Test Georgian: scrape Georgian job sites")
    print("  3. Remove backup files when satisfied: rm -rf config/backup_rtx4050_specific/")


def main():
    """Run the migration"""
    print("🔄 Starting Migration: RTX 4050-specific → Unified System")
    print("="*60)
    
    # Backup first
    backup_old_configs()
    
    # Migrate directories
    migrate_directories()
    
    # Update scripts
    update_scripts()
    
    # Create compatibility layer
    create_compatibility_layer()
    
    # Test new system
    if test_new_system():
        print_migration_summary()
        print("\n✅ Migration successful! Your system now auto-detects GPU and supports Georgian.")
    else:
        print("\n❌ Migration had issues. Check the output above.")


if __name__ == "__main__":
    main() 