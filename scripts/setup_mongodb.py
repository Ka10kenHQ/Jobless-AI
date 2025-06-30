#!/usr/bin/env python3
"""
MongoDB setup script for job search AI system
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
import pymongo

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


def check_mongodb_installed():
    """Check if MongoDB is installed"""
    try:
        result = subprocess.run(['mongod', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ MongoDB is already installed")
            return True
        else:
            print("❌ MongoDB not found")
            return False
    except FileNotFoundError:
        print("❌ MongoDB not found")
        return False


def install_mongodb_ubuntu():
    """Install MongoDB on Ubuntu/Debian"""
    print("🔧 Installing MongoDB on Ubuntu/Debian...")
    
    commands = [
        # Import public key
        "sudo apt-get install -y gnupg curl",
        "curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor",
        
        # Add repository
        'echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list',
        
        # Update and install
        "sudo apt-get update",
        "sudo apt-get install -y mongodb-org",
        
        # Start and enable MongoDB
        "sudo systemctl start mongod",
        "sudo systemctl enable mongod"
    ]
    
    for cmd in commands:
        print(f"   Running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"   ❌ Command failed: {cmd}")
            return False
    
    print("✅ MongoDB installed successfully")
    return True


def install_mongodb_arch():
    """Install MongoDB on Arch Linux"""
    print("🔧 Installing MongoDB on Arch Linux...")
    
    commands = [
        # Install from AUR (assuming yay is available)
        "yay -S --noconfirm mongodb-bin",
        
        # Start and enable MongoDB
        "sudo systemctl start mongodb",
        "sudo systemctl enable mongodb"
    ]
    
    for cmd in commands:
        print(f"   Running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"   ❌ Command failed: {cmd}")
            return False
    
    print("✅ MongoDB installed successfully")
    return True


def detect_os():
    """Detect operating system"""
    if os.path.exists("/etc/arch-release"):
        return "arch"
    elif os.path.exists("/etc/ubuntu-release") or os.path.exists("/etc/debian_version"):
        return "ubuntu"
    else:
        return "unknown"


def start_mongodb():
    """Start MongoDB service"""
    os_type = detect_os()
    
    if os_type == "arch":
        service_name = "mongodb"
    else:
        service_name = "mongod"
    
    try:
        # Check if already running
        result = subprocess.run(['sudo', 'systemctl', 'is-active', service_name], 
                              capture_output=True, text=True)
        
        if result.stdout.strip() == "active":
            print(f"✅ MongoDB service ({service_name}) is already running")
            return True
        
        # Start the service
        print(f"🚀 Starting MongoDB service ({service_name})...")
        result = subprocess.run(['sudo', 'systemctl', 'start', service_name])
        
        if result.returncode == 0:
            print(f"✅ MongoDB service started successfully")
            return True
        else:
            print(f"❌ Failed to start MongoDB service")
            return False
            
    except Exception as e:
        print(f"❌ Error starting MongoDB: {e}")
        return False


async def setup_database():
    """Setup database with indexes and collections"""
    try:
        from database.connection import setup_database, get_database_stats
        
        print("🔧 Setting up database collections and indexes...")
        await setup_database()
        
        print("📊 Database setup completed. Current stats:")
        stats = await get_database_stats()
        for collection, info in stats["collections"].items():
            if "error" not in info:
                print(f"   {collection}: {info['count']} documents, {info['indexes']} indexes")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def install_python_dependencies():
    """Install required Python packages"""
    print("📦 Installing Python dependencies...")
    
    try:
        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            pip_cmd = "pip"
        else:
            pip_cmd = "pip3"
        
        dependencies = ["pymongo>=4.6.0", "motor>=3.3.0", "dnspython>=2.4.0"]
        
        for dep in dependencies:
            print(f"   Installing {dep}...")
            result = subprocess.run([pip_cmd, "install", dep])
            if result.returncode != 0:
                print(f"   ❌ Failed to install {dep}")
                return False
        
        print("✅ Python dependencies installed")
        return True
        
    except Exception as e:
        print(f"❌ Failed to install Python dependencies: {e}")
        return False


async def test_connection():
    """Test MongoDB connection"""
    try:
        from database.connection import get_async_database, close_connections
        
        print("🔍 Testing MongoDB connection...")
        db = await get_async_database()
        result = await db.command('ping')
        
        if result.get('ok') == 1:
            print("✅ MongoDB connection test successful!")
            
            # Show some info
            server_info = await db.command('serverStatus')
            print(f"   MongoDB version: {server_info.get('version', 'Unknown')}")
            print(f"   Host: {server_info.get('host', 'Unknown')}")
            
            await close_connections()
            return True
        else:
            print("❌ MongoDB connection test failed")
            await close_connections()
            return False
            
    except Exception as e:
        print(f"❌ MongoDB connection test failed: {e}")
        return False


def create_env_file():
    """Create .env file with MongoDB configuration"""
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("📝 Creating .env file...")
    
    env_content = """# MongoDB Configuration
                        MONGODB_HOST=localhost
                        MONGODB_PORT=27017
                        MONGODB_USERNAME=
                        MONGODB_PASSWORD=
                        MONGODB_DATABASE=job_search_ai
                        MONGODB_AUTH_DATABASE=admin
                        MONGODB_MAX_POOL_SIZE=10
                        MONGODB_MIN_POOL_SIZE=1
                        MONGODB_TIMEOUT=5000

                        # API Configuration
                        FASTAPI_HOST=0.0.0.0
                        FASTAPI_PORT=8000
                        DEBUG=false

                        # Training Configuration
                        MODEL_CACHE_DIR=./cache
                        LOGS_DIR=./logs
                        MODELS_DIR=./models

                        # Scraping Configuration
                        SCRAPING_DELAY_SECONDS=2
                        MAX_RETRIES=3
                        REQUEST_TIMEOUT=30
                  """
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created")


async def setup_indexes():
    """Setup MongoDB indexes for optimal performance"""
    print("📊 Setting up database indexes...")
    
    # Get database connection
    db = await get_database()
    
    # Job postings indexes
    jobs_collection = db.jobs
    await jobs_collection.create_index([("url", pymongo.ASCENDING)], unique=True)
    await jobs_collection.create_index([("source", pymongo.ASCENDING)])
    await jobs_collection.create_index([("language", pymongo.ASCENDING)])
    await jobs_collection.create_index([("created_at", pymongo.DESCENDING)])
    await jobs_collection.create_index([("title", pymongo.TEXT), ("description", pymongo.TEXT), ("company", pymongo.TEXT)])
    print("  ✅ Job postings indexes created")
    
    # Training examples indexes
    training_collection = db.training_examples
    await training_collection.create_index([("example_id", pymongo.ASCENDING)], unique=True)
    await training_collection.create_index([("language", pymongo.ASCENDING)])
    await training_collection.create_index([("source", pymongo.ASCENDING)])
    await training_collection.create_index([("task_type", pymongo.ASCENDING)])
    print("  ✅ Training examples indexes created")
    
    # User interactions indexes
    interactions_collection = db.user_interactions
    await interactions_collection.create_index([("user_id", pymongo.ASCENDING)])
    await interactions_collection.create_index([("session_id", pymongo.ASCENDING)])
    await interactions_collection.create_index([("timestamp", pymongo.DESCENDING)])
    print("  ✅ User interactions indexes created")
    
    # Model info indexes
    models_collection = db.models
    await models_collection.create_index([("name", pymongo.ASCENDING), ("version", pymongo.ASCENDING)], unique=True)
    await models_collection.create_index([("is_active", pymongo.ASCENDING)])
    await models_collection.create_index([("created_at", pymongo.DESCENDING)])
    print("  ✅ Model info indexes created")
    
    # Scraping sessions indexes
    scraping_collection = db.scraping_sessions
    await scraping_collection.create_index([("source", pymongo.ASCENDING)])
    await scraping_collection.create_index([("started_at", pymongo.DESCENDING)])
    await scraping_collection.create_index([("status", pymongo.ASCENDING)])
    print("  ✅ Scraping sessions indexes created")
    
    # Chat histories indexes
    chat_collection = db.chat_histories
    await chat_collection.create_index([("chat_id", pymongo.ASCENDING)], unique=True)
    await chat_collection.create_index([("user_id", pymongo.ASCENDING)])
    await chat_collection.create_index([("user_id", pymongo.ASCENDING), ("last_activity", pymongo.DESCENDING)])
    await chat_collection.create_index([("user_id", pymongo.ASCENDING), ("is_archived", pymongo.ASCENDING)])
    await chat_collection.create_index([("title", pymongo.TEXT), ("messages.content", pymongo.TEXT)])
    await chat_collection.create_index([("created_at", pymongo.DESCENDING)])
    await chat_collection.create_index([("last_activity", pymongo.DESCENDING)])
    print("  ✅ Chat histories indexes created")
    
    print("📊 All database indexes created successfully!")


async def main():
    """Main setup function"""
    print("🚀 MongoDB Setup for Job Search AI")
    print("=" * 50)
    
    # Create .env file
    create_env_file()
    
    # Install Python dependencies first
    if not install_python_dependencies():
        print("❌ Setup failed - couldn't install Python dependencies")
        return
    
    # Check if MongoDB is installed
    if not check_mongodb_installed():
        os_type = detect_os()
        
        if os_type == "ubuntu":
            if not install_mongodb_ubuntu():
                print("❌ Setup failed - couldn't install MongoDB")
                return
        elif os_type == "arch":
            if not install_mongodb_arch():
                print("❌ Setup failed - couldn't install MongoDB")
                return
        else:
            print("❌ Unsupported OS. Please install MongoDB manually:")
            print("   Ubuntu/Debian: https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/")
            print("   Arch Linux: yay -S mongodb-bin")
            print("   Other: https://docs.mongodb.com/manual/installation/")
            return
    
    # Start MongoDB
    if not start_mongodb():
        print("❌ Setup failed - couldn't start MongoDB")
        return
    
    # Wait a moment for MongoDB to start
    print("⏳ Waiting for MongoDB to start...")
    await asyncio.sleep(3)
    
    # Test connection
    if not await test_connection():
        print("❌ Setup failed - couldn't connect to MongoDB")
        return
    
    # Setup database
    if not await setup_database():
        print("❌ Setup failed - couldn't setup database")
        return
    
    # Setup indexes
    await setup_indexes()
    
    print("\n🎉 MongoDB setup completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Run migration: python scripts/migrate_to_mongodb.py")
    print("   2. Test the system: python -c \"from database.connection import print_database_info; print_database_info()\"")
    print("   3. Start training with MongoDB: python scripts/train.py --languages georgian english")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc() 