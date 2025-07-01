import os
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import logging

logger = logging.getLogger(__name__)

_async_client: Optional[AsyncIOMotorClient] = None
_sync_client: Optional[MongoClient] = None


class DatabaseConfig:
    
    def __init__(self):
        self.host = os.getenv("MONGODB_HOST", "localhost")
        self.port = int(os.getenv("MONGODB_PORT", "27017"))
        self.username = os.getenv("MONGODB_USERNAME")
        self.password = os.getenv("MONGODB_PASSWORD")
        self.database_name = os.getenv("MONGODB_DATABASE", "job_search")
        self.auth_database = os.getenv("MONGODB_AUTH_DATABASE", "admin")
        
        self.max_pool_size = int(os.getenv("MONGODB_MAX_POOL_SIZE", "10"))
        self.min_pool_size = int(os.getenv("MONGODB_MIN_POOL_SIZE", "1"))
        self.server_selection_timeout = int(os.getenv("MONGODB_TIMEOUT", "5000"))
        
    def get_connection_string(self) -> str:
        if self.username and self.password:
            return (
                f"mongodb://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.auth_database}"
                f"?maxPoolSize={self.max_pool_size}"
                f"&minPoolSize={self.min_pool_size}"
                f"&serverSelectionTimeoutMS={self.server_selection_timeout}"
            )
        else:
            return (
                f"mongodb://{self.host}:{self.port}"
                f"?maxPoolSize={self.max_pool_size}"
                f"&minPoolSize={self.min_pool_size}"
                f"&serverSelectionTimeoutMS={self.server_selection_timeout}"
            )


_config = DatabaseConfig()


async def get_async_client() -> AsyncIOMotorClient:
    global _async_client
    
    if _async_client is None:
        connection_string = _config.get_connection_string()
        _async_client = AsyncIOMotorClient(connection_string)
        
        try:
            await _async_client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB at {_config.host}:{_config.port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    return _async_client


def get_sync_client() -> MongoClient:
    """Get sync MongoDB client (singleton)"""
    global _sync_client
    
    if _sync_client is None:
        connection_string = _config.get_connection_string()
        _sync_client = MongoClient(connection_string)
        
        # Test connection
        try:
            _sync_client.admin.command('ping')
            logger.info(f"✅ Connected to MongoDB at {_config.host}:{_config.port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    return _sync_client


async def get_async_database() -> AsyncIOMotorDatabase:
    """Get async database instance"""
    client = await get_async_client()
    return client[_config.database_name]


def get_database() -> Database:
    """Get sync database instance"""
    client = get_sync_client()
    return client[_config.database_name]


async def get_async_collection(collection_name: str) -> AsyncIOMotorCollection:
    """Get async collection instance"""
    db = await get_async_database()
    return db[collection_name]


def get_collection(collection_name: str) -> Collection:
    """Get sync collection instance"""
    db = get_database()
    return db[collection_name]


async def close_connections():
    """Close all database connections"""
    global _async_client, _sync_client
    
    if _async_client:
        _async_client.close()
        _async_client = None
    
    if _sync_client:
        _sync_client.close()
        _sync_client = None
    
    logger.info("🔌 Database connections closed")


async def setup_database():
    """Setup database with indexes and initial configuration"""
    db = await get_async_database()
    
    # Create collections with indexes
    collections_setup = {
        "jobs": [
            ("url", 1),  # Unique job URL
            ("title", "text"),  # Text search on title
            ("company", 1),  # Company filter
            ("location", 1),  # Location filter
            ("source", 1),  # Source filter
            ("language", 1),  # Language filter
            ("created_at", -1),  # Sort by date
            ([("title", "text"), ("description", "text"), ("company", "text")], None),  # Full text search
        ],
        "training_examples": [
            ("example_id", 1),  # Unique example ID
            ("source", 1),  # Data source
            ("created_at", -1),  # Sort by date
            ("language", 1),  # Language filter
        ],
        "user_interactions": [
            ("user_id", 1),  # User filter
            ("session_id", 1),  # Session filter
            ("timestamp", -1),  # Sort by time
            ("message", "text"),  # Text search
        ],
        "models": [
            ("name", 1),  # Model name
            ("version", 1),  # Model version
            ("created_at", -1),  # Sort by date
            ("languages", 1),  # Language support
        ],
        "scraping_sessions": [
            ("source", 1),  # Source filter
            ("started_at", -1),  # Sort by date
            ("status", 1),  # Status filter
        ]
    }
    
    for collection_name, indexes in collections_setup.items():
        collection = db[collection_name]
        
        for index in indexes:
            try:
                if isinstance(index, tuple) and len(index) == 2:
                    index_spec, index_type = index
                    if index_type == "text":
                        await collection.create_index([(index_spec, "text")])
                    elif isinstance(index_spec, list):
                        # Compound text index
                        await collection.create_index(index_spec)
                    else:
                        await collection.create_index(index_spec)
                else:
                    await collection.create_index(index)
            except Exception as e:
                logger.warning(f"Index creation failed for {collection_name}: {e}")
    
    logger.info("📊 Database setup completed")


async def get_database_stats():
    """Get database statistics"""
    db = await get_async_database()
    
    stats = {
        "database": _config.database_name,
        "collections": {}
    }
    
    collection_names = ["jobs", "training_examples", "user_interactions", "models", "scraping_sessions"]
    
    for collection_name in collection_names:
        try:
            collection = db[collection_name]
            count = await collection.count_documents({})
            stats["collections"][collection_name] = {
                "count": count,
                "indexes": len(await collection.list_indexes().to_list(None))
            }
        except Exception as e:
            stats["collections"][collection_name] = {"error": str(e)}
    
    return stats


def print_database_info():
    """Print database connection information"""
    print("🗄️ MongoDB Configuration")
    print("=" * 40)
    print(f"📍 Host: {_config.host}:{_config.port}")
    print(f"📊 Database: {_config.database_name}")
    print(f"👤 Authentication: {'Yes' if _config.username else 'No'}")
    print(f"🔗 Max Pool Size: {_config.max_pool_size}")
    print(f"⏱️ Timeout: {_config.server_selection_timeout}ms")


if __name__ == "__main__":
    # Test connection
    async def test_connection():
        print_database_info()
        try:
            db = await get_async_database()
            result = await db.command('ping')
            print("✅ Connection test successful!")
            
            stats = await get_database_stats()
            print(f"\n📊 Database Stats:")
            for collection, info in stats["collections"].items():
                if "error" not in info:
                    print(f"   {collection}: {info['count']} documents, {info['indexes']} indexes")
                else:
                    print(f"   {collection}: Error - {info['error']}")
                    
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
        finally:
            await close_connections()
    
    asyncio.run(test_connection()) 