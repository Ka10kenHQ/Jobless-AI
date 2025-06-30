import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from .connection import get_async_collection, get_collection
from .models import (
    JobPosting, TrainingExample, UserInteraction, 
    ModelInfo, ScrapingSession, JobSearchRequest,
    JobSearchResponse, DatabaseStats
)


class BaseOperations:
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        return await get_async_collection(self.collection_name)
    
    def get_sync_collection(self):
        return get_collection(self.collection_name)
    
    async def count_documents(self, filter_dict: Dict = None) -> int:
        collection = await self.get_collection()
        return await collection.count_documents(filter_dict or {})


class JobOperations(BaseOperations):
    """Job posting operations"""
    
    def __init__(self):
        super().__init__("jobs")
    
    async def create_job(self, job: JobPosting) -> str:
        """Create a new job posting"""
        collection = await self.get_collection()
        
        # Check for duplicates by URL
        existing = await collection.find_one({"url": job.url})
        if existing:
            # Update existing job
            await collection.update_one(
                {"url": job.url},
                {"$set": job.dict(exclude={"id", "created_at"})}
            )
            return str(existing["_id"])
        
        # Create new job
        job_dict = job.dict(exclude={"id"})
        result = await collection.insert_one(job_dict)
        return str(result.inserted_id)
    
    async def get_job(self, job_id: str) -> Optional[JobPosting]:
        """Get job by ID"""
        collection = await self.get_collection()
        doc = await collection.find_one({"_id": ObjectId(job_id)})
        return JobPosting(**doc) if doc else None
    
    async def get_job_by_url(self, url: str) -> Optional[JobPosting]:
        """Get job by URL"""
        collection = await self.get_collection()
        doc = await collection.find_one({"url": url})
        return JobPosting(**doc) if doc else None
    
    async def search_jobs(self, request: JobSearchRequest) -> JobSearchResponse:
        """Search jobs with filters"""
        collection = await self.get_collection()
        start_time = datetime.now()
        
        # Build search query
        query = {}
        
        # Text search
        if request.query:
            query["$text"] = {"$search": request.query}
        
        # Language filter
        if request.languages:
            query["language"] = {"$in": request.languages}
        
        # Location filter
        if request.location:
            query["location"] = {"$regex": request.location, "$options": "i"}
        
        # Experience level filter
        if request.experience_level:
            query["experience_level"] = request.experience_level
        
        # Remote filter
        if request.remote_only:
            query["remote"] = True
        
        # Get total count
        total_count = await collection.count_documents(query)
        
        # Get results with pagination
        cursor = collection.find(query)
        
        # Sort by relevance (text score) if text search, otherwise by date
        if request.query:
            cursor = cursor.sort([("score", {"$meta": "textScore"})])
        else:
            cursor = cursor.sort("created_at", -1)
        
        # Apply pagination
        cursor = cursor.skip(request.offset).limit(request.limit)
        
        # Execute query
        docs = await cursor.to_list(None)
        jobs = [JobPosting(**doc) for doc in docs]
        
        # Calculate search time
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return JobSearchResponse(
            jobs=jobs,
            total_count=total_count,
            query_info={
                "query": request.query,
                "filters_applied": len([k for k, v in query.items() if v]),
                "languages": request.languages,
                "location": request.location
            },
            search_time_ms=search_time
        )
    
    async def get_jobs_by_source(self, source: str, limit: int = 100) -> List[JobPosting]:
        """Get jobs by source"""
        collection = await self.get_collection()
        cursor = collection.find({"source": source}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(None)
        return [JobPosting(**doc) for doc in docs]
    
    async def get_recent_jobs(self, hours: int = 24, limit: int = 100) -> List[JobPosting]:
        """Get recent jobs"""
        collection = await self.get_collection()
        since = datetime.utcnow() - timedelta(hours=hours)
        cursor = collection.find({"created_at": {"$gte": since}}).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(None)
        return [JobPosting(**doc) for doc in docs]
    
    async def update_job_quality_score(self, job_id: str, score: float):
        """Update job quality score"""
        collection = await self.get_collection()
        await collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"quality_score": score, "updated_at": datetime.utcnow()}}
        )
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete job"""
        collection = await self.get_collection()
        result = await collection.delete_one({"_id": ObjectId(job_id)})
        return result.deleted_count > 0
    
    async def get_job_stats(self) -> Dict[str, Any]:
        """Get job collection statistics"""
        collection = await self.get_collection()
        
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_jobs": {"$sum": 1},
                    "sources": {"$addToSet": "$source"},
                    "languages": {"$addToSet": "$language"},
                    "avg_quality": {"$avg": "$quality_score"},
                    "latest_job": {"$max": "$created_at"}
                }
            }
        ]
        
        result = await collection.aggregate(pipeline).to_list(None)
        return result[0] if result else {}


class TrainingOperations(BaseOperations):
    """Training example operations"""
    
    def __init__(self):
        super().__init__("training_examples")
    
    async def create_training_example(self, example: TrainingExample) -> str:
        """Create training example"""
        collection = await self.get_collection()
        
        # Check for duplicates by example_id
        existing = await collection.find_one({"example_id": example.example_id})
        if existing:
            return str(existing["_id"])
        
        example_dict = example.dict(exclude={"id"})
        result = await collection.insert_one(example_dict)
        return str(result.inserted_id)
    
    async def get_training_examples(
        self, 
        language: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 1000
    ) -> List[TrainingExample]:
        """Get training examples with filters"""
        collection = await self.get_collection()
        
        query = {}
        if language:
            query["language"] = language
        if source:
            query["source"] = source
        
        cursor = collection.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(None)
        return [TrainingExample(**doc) for doc in docs]
    
    async def get_training_dataset(self, languages: List[str]) -> List[Dict[str, str]]:
        """Get training dataset for model training"""
        collection = await self.get_collection()
        
        query = {"language": {"$in": languages}}
        cursor = collection.find(query, {"input_text": 1, "output_text": 1, "_id": 0})
        docs = await cursor.to_list(None)
        
        return [{"input": doc["input_text"], "output": doc["output_text"]} for doc in docs]
    
    async def bulk_create_training_examples(self, examples: List[TrainingExample]) -> int:
        """Bulk create training examples"""
        collection = await self.get_collection()
        
        # Remove duplicates
        unique_examples = []
        seen_ids = set()
        
        for example in examples:
            if example.example_id not in seen_ids:
                unique_examples.append(example.dict(exclude={"id"}))
                seen_ids.add(example.example_id)
        
        if not unique_examples:
            return 0
        
        try:
            result = await collection.insert_many(unique_examples, ordered=False)
            return len(result.inserted_ids)
        except DuplicateKeyError:
            # Handle duplicates by inserting one by one
            inserted_count = 0
            for example_dict in unique_examples:
                try:
                    await collection.insert_one(example_dict)
                    inserted_count += 1
                except DuplicateKeyError:
                    continue
            return inserted_count
    
    async def update_quality_scores(self, scores: Dict[str, float]):
        """Update quality scores for training examples"""
        collection = await self.get_collection()
        
        operations = []
        for example_id, score in scores.items():
            operations.append({
                "updateOne": {
                    "filter": {"example_id": example_id},
                    "update": {"$set": {"quality_score": score}}
                }
            })
        
        if operations:
            await collection.bulk_write(operations)


class UserOperations(BaseOperations):
    """User interaction operations"""
    
    def __init__(self):
        super().__init__("user_interactions")
    
    async def log_interaction(self, interaction: UserInteraction) -> str:
        """Log user interaction"""
        collection = await self.get_collection()
        interaction_dict = interaction.dict(exclude={"id"})
        result = await collection.insert_one(interaction_dict)
        return str(result.inserted_id)
    
    async def get_user_interactions(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[UserInteraction]:
        """Get user interactions"""
        collection = await self.get_collection()
        
        query = {"user_id": user_id}
        if session_id:
            query["session_id"] = session_id
        
        cursor = collection.find(query).sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(None)
        return [UserInteraction(**doc) for doc in docs]
    
    async def get_interaction_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get interaction statistics"""
        collection = await self.get_collection()
        since = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {
                "$group": {
                    "_id": None,
                    "total_interactions": {"$sum": 1},
                    "unique_users": {"$addToSet": "$user_id"},
                    "unique_sessions": {"$addToSet": "$session_id"},
                    "avg_response_time": {"$avg": "$response_time_ms"},
                    "languages": {"$addToSet": "$language"}
                }
            }
        ]
        
        result = await collection.aggregate(pipeline).to_list(None)
        stats = result[0] if result else {}
        
        if "unique_users" in stats:
            stats["unique_users_count"] = len(stats["unique_users"])
            stats["unique_sessions_count"] = len(stats["unique_sessions"])
            del stats["unique_users"]
            del stats["unique_sessions"]
        
        return stats


class ModelOperations(BaseOperations):
    """Model information operations"""
    
    def __init__(self):
        super().__init__("models")
    
    async def create_model_info(self, model_info: ModelInfo) -> str:
        """Create model information record"""
        collection = await self.get_collection()
        
        # Deactivate other models with same name
        await collection.update_many(
            {"name": model_info.name, "is_active": True},
            {"$set": {"is_active": False}}
        )
        
        model_dict = model_info.dict(exclude={"id"})
        result = await collection.insert_one(model_dict)
        return str(result.inserted_id)
    
    async def get_active_model(self, name: str) -> Optional[ModelInfo]:
        """Get active model by name"""
        collection = await self.get_collection()
        doc = await collection.find_one({"name": name, "is_active": True})
        return ModelInfo(**doc) if doc else None
    
    async def get_model_versions(self, name: str) -> List[ModelInfo]:
        """Get all versions of a model"""
        collection = await self.get_collection()
        cursor = collection.find({"name": name}).sort("created_at", -1)
        docs = await cursor.to_list(None)
        return [ModelInfo(**doc) for doc in docs]
    
    async def update_model_status(self, model_id: str, status: str):
        """Update model status"""
        collection = await self.get_collection()
        await collection.update_one(
            {"_id": ObjectId(model_id)},
            {"$set": {"status": status}}
        )
    
    async def set_model_performance(self, model_id: str, metrics: Dict[str, float]):
        """Set model performance metrics"""
        collection = await self.get_collection()
        await collection.update_one(
            {"_id": ObjectId(model_id)},
            {"$set": metrics}
        )


class ScrapingOperations(BaseOperations):
    """Scraping session operations"""
    
    def __init__(self):
        super().__init__("scraping_sessions")
    
    async def start_scraping_session(self, session: ScrapingSession) -> str:
        """Start new scraping session"""
        collection = await self.get_collection()
        session_dict = session.dict(exclude={"id"})
        result = await collection.insert_one(session_dict)
        return str(result.inserted_id)
    
    async def update_scraping_session(self, session_id: str, updates: Dict[str, Any]):
        """Update scraping session"""
        collection = await self.get_collection()
        await collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": updates}
        )
    
    async def complete_scraping_session(
        self, 
        session_id: str, 
        jobs_found: int,
        jobs_saved: int,
        errors_count: int = 0
    ):
        """Complete scraping session with results"""
        collection = await self.get_collection()
        
        updates = {
            "status": "completed",
            "jobs_found": jobs_found,
            "jobs_saved": jobs_saved,
            "errors_count": errors_count,
            "completed_at": datetime.utcnow()
        }
        
        # Calculate duration if session exists
        session = await collection.find_one({"_id": ObjectId(session_id)})
        if session and session.get("started_at"):
            duration = (datetime.utcnow() - session["started_at"]).total_seconds()
            updates["duration_seconds"] = duration
        
        await collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": updates}
        )
    
    async def get_recent_scraping_sessions(self, limit: int = 20) -> List[ScrapingSession]:
        """Get recent scraping sessions"""
        collection = await self.get_collection()
        cursor = collection.find().sort("started_at", -1).limit(limit)
        docs = await cursor.to_list(None)
        return [ScrapingSession(**doc) for doc in docs]


class ChatOperations(BaseOperations):
    """Chat history operations"""
    
    def __init__(self):
        super().__init__("chat_histories")
    
    async def save_chat(self, chat_data: Dict[str, Any]) -> str:
        """Save or update chat history"""
        from database.models import ChatHistory, ChatMessage
        
        collection = await self.get_collection()
        
        # Convert messages to ChatMessage objects
        messages = []
        for msg_data in chat_data.get("messages", []):
            if isinstance(msg_data, dict):
                message = ChatMessage(
                    message_id=msg_data.get("id", msg_data.get("message_id", "")),
                    content=msg_data.get("content", ""),
                    sender=msg_data.get("sender", ""),
                    timestamp=datetime.fromisoformat(msg_data["timestamp"].replace('Z', '+00:00')) if isinstance(msg_data.get("timestamp"), str) else msg_data.get("timestamp", datetime.utcnow()),
                    jobs=msg_data.get("jobs", []),
                    total_jobs=msg_data.get("total_jobs", msg_data.get("totalJobs")),
                    response_time_ms=msg_data.get("response_time_ms")
                )
                messages.append(message)
        
        # Check if chat already exists
        existing_chat = await collection.find_one({"chat_id": chat_data["id"]})
        
        if existing_chat:
            # Update existing chat
            updates = {
                "title": chat_data.get("title", "New Chat"),
                "messages": [msg.dict() for msg in messages],
                "message_count": len(messages),
                "updated_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "job_searches_count": len([m for m in messages if m.sender == "bot" and m.jobs]),
                "jobs_found_total": sum(len(m.jobs) for m in messages if m.jobs)
            }
            
            await collection.update_one(
                {"chat_id": chat_data["id"]},
                {"$set": updates}
            )
            return str(existing_chat["_id"])
        else:
            # Create new chat
            chat_history = ChatHistory(
                chat_id=chat_data["id"],
                user_id=chat_data.get("userId", "unknown"),
                title=chat_data.get("title", "New Chat"),
                messages=messages,
                message_count=len(messages),
                job_searches_count=len([m for m in messages if m.sender == "bot" and m.jobs]),
                jobs_found_total=sum(len(m.jobs) for m in messages if m.jobs)
            )
            
            chat_dict = chat_history.dict(exclude={"id"})
            result = await collection.insert_one(chat_dict)
            return str(result.inserted_id)
    
    async def get_user_chats(self, user_id: str, limit: int = 50, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get user's chat history"""
        collection = await self.get_collection()
        
        query = {"user_id": user_id}
        if not include_archived:
            query["is_archived"] = {"$ne": True}
        
        # Return simplified chat data for the UI
        projection = {
            "chat_id": 1,
            "title": 1,
            "message_count": 1,
            "last_activity": 1,
            "created_at": 1,
            "job_searches_count": 1,
            "jobs_found_total": 1,
            "messages": {"$slice": 1}  # Only get first message for preview
        }
        
        cursor = collection.find(query, projection).sort("last_activity", -1).limit(limit)
        docs = await cursor.to_list(None)
        
        # Format for frontend
        chats = []
        for doc in docs:
            chat = {
                "id": doc["chat_id"],
                "title": doc["title"],
                "timestamp": doc["last_activity"].isoformat(),
                "messages": doc.get("messages", [])
            }
            chats.append(chat)
        
        return chats
    
    async def get_chat_by_id(self, chat_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get specific chat by ID"""
        collection = await self.get_collection()
        
        chat = await collection.find_one({
            "chat_id": chat_id,
            "user_id": user_id
        })
        
        if not chat:
            return None
        
        return {
            "id": chat["chat_id"],
            "title": chat["title"],
            "timestamp": chat["last_activity"].isoformat(),
            "messages": chat.get("messages", [])
        }
    
    async def delete_chat(self, chat_id: str, user_id: str) -> bool:
        """Delete a chat"""
        collection = await self.get_collection()
        
        result = await collection.delete_one({
            "chat_id": chat_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    async def clear_user_chats(self, user_id: str) -> int:
        """Clear all chats for a user"""
        collection = await self.get_collection()
        
        result = await collection.delete_many({"user_id": user_id})
        return result.deleted_count
    
    async def archive_chat(self, chat_id: str, user_id: str) -> bool:
        """Archive a chat"""
        collection = await self.get_collection()
        
        result = await collection.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"is_archived": True, "updated_at": datetime.utcnow()}}
        )
        
        return result.modified_count > 0
    
    async def search_chats(self, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search user's chats by content"""
        collection = await self.get_collection()
        
        # Text search in title and message content
        search_query = {
            "user_id": user_id,
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"messages.content": {"$regex": query, "$options": "i"}}
            ]
        }
        
        projection = {
            "chat_id": 1,
            "title": 1,
            "last_activity": 1,
            "message_count": 1
        }
        
        cursor = collection.find(search_query, projection).sort("last_activity", -1).limit(limit)
        docs = await cursor.to_list(None)
        
        return [
            {
                "id": doc["chat_id"],
                "title": doc["title"],
                "timestamp": doc["last_activity"].isoformat(),
                "messages": []
            }
            for doc in docs
        ]
    
    async def get_chat_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get chat statistics"""
        collection = await self.get_collection()
        
        pipeline = []
        
        if user_id:
            pipeline.append({"$match": {"user_id": user_id}})
        
        pipeline.extend([
            {
                "$group": {
                    "_id": None,
                    "total_chats": {"$sum": 1},
                    "total_messages": {"$sum": "$message_count"},
                    "total_job_searches": {"$sum": "$job_searches_count"},
                    "total_jobs_found": {"$sum": "$jobs_found_total"},
                    "avg_messages_per_chat": {"$avg": "$message_count"},
                    "latest_activity": {"$max": "$last_activity"},
                    "active_chats": {
                        "$sum": {
                            "$cond": [{"$ne": ["$is_archived", True]}, 1, 0]
                        }
                    }
                }
            }
        ])
        
        result = await collection.aggregate(pipeline).to_list(None)
        return result[0] if result else {}


async def get_database_statistics() -> DatabaseStats:
    """Get comprehensive database statistics"""
    from database.models import DatabaseStats
    
    # Initialize operations
    job_ops = JobOperations()
    training_ops = TrainingOperations()
    user_ops = UserOperations()
    model_ops = ModelOperations()
    scraping_ops = ScrapingOperations()
    chat_ops = ChatOperations()
    
    # Get counts from each collection
    total_jobs = await job_ops.count_documents()
    total_training_examples = await training_ops.count_documents()
    total_interactions = await user_ops.count_documents()
    total_models = await model_ops.count_documents()
    total_scraping_sessions = await scraping_ops.count_documents()
    total_chat_histories = await chat_ops.count_documents()
    
    # Get additional stats
    job_stats = await job_ops.get_job_stats()
    chat_stats = await chat_ops.get_chat_stats()
    
    # Calculate total chat messages
    total_chat_messages = chat_stats.get("total_messages", 0)
    
    # Get recent scraping session
    recent_sessions = await scraping_ops.get_recent_scraping_sessions(limit=1)
    last_scraping_session = recent_sessions[0].started_at if recent_sessions else None
    
    return DatabaseStats(
        total_jobs=total_jobs,
        total_training_examples=total_training_examples,
        total_interactions=total_interactions,
        total_models=total_models,
        total_scraping_sessions=total_scraping_sessions,
        total_chat_histories=total_chat_histories,
        total_chat_messages=total_chat_messages,
        languages_supported=job_stats.get("languages", ["english"]),
        job_sources=job_stats.get("sources", []),
        last_scraping_session=last_scraping_session,
        database_size_mb=None  # Would need additional MongoDB query to get actual size
    ) 