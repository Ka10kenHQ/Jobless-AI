// MongoDB initialization script for MCP Job Search System
// This script runs when the MongoDB container starts for the first time

// Switch to the job_search database
db = db.getSiblingDB('job_search');

// Create a user for the application
db.createUser({
  user: 'job_search_app',
  pwd: 'app_password_change_in_production',
  roles: [
    {
      role: 'readWrite',
      db: 'job_search'
    }
  ]
});

// Create collections with indexes for better performance
db.createCollection('jobs');
db.createCollection('training_data');
db.createCollection('user_searches');
db.createCollection('system_logs');

// Create indexes for jobs collection
db.jobs.createIndex({ "title": "text", "description": "text", "company": "text" });
db.jobs.createIndex({ "location": 1 });
db.jobs.createIndex({ "posted_date": -1 });
db.jobs.createIndex({ "source": 1 });
db.jobs.createIndex({ "job_url": 1 }, { unique: true });
db.jobs.createIndex({ "skills": 1 });
db.jobs.createIndex({ "experience_level": 1 });

// Create indexes for training_data collection
db.training_data.createIndex({ "created_at": -1 });
db.training_data.createIndex({ "language": 1 });
db.training_data.createIndex({ "data_type": 1 });

// Create indexes for user_searches collection
db.user_searches.createIndex({ "user_id": 1 });
db.user_searches.createIndex({ "timestamp": -1 });
db.user_searches.createIndex({ "search_query": "text" });

// Create indexes for system_logs collection
db.system_logs.createIndex({ "timestamp": -1 });
db.system_logs.createIndex({ "level": 1 });
db.system_logs.createIndex({ "component": 1 });

// Insert some initial configuration data
db.system_config.insertOne({
  _id: "app_config",
  version: "1.0.0",
  supported_languages: ["english", "georgian"],
  default_language: "english",
  max_search_results: 100,
  cache_ttl_minutes: 60,
  scraper_config: {
    enabled_sites: ["hr.ge", "jobs.ge"],
    scrape_interval_hours: 6,
    max_jobs_per_site: 1000
  },
  created_at: new Date(),
  updated_at: new Date()
});

// Insert sample job categories
db.job_categories.insertMany([
  { name: "Software Development", name_ka: "პროგრამული უზრუნველყოფის განვითარება" },
  { name: "Data Science", name_ka: "მონაცემთა მეცნიერება" },
  { name: "Machine Learning", name_ka: "მანქანური სწავლება" },
  { name: "Web Development", name_ka: "ვებ განვითარება" },
  { name: "Mobile Development", name_ka: "მობილური განვითარება" },
  { name: "DevOps", name_ka: "DevOps" },
  { name: "Product Management", name_ka: "პროდუქტის მენეჯმენტი" },
  { name: "UI/UX Design", name_ka: "UI/UX დიზაინი" },
  { name: "Quality Assurance", name_ka: "ხარისხის უზრუნველყოფა" },
  { name: "System Administration", name_ka: "სისტემური ადმინისტრირება" }
]);

print("MongoDB initialization completed successfully!");
print("Created collections: jobs, training_data, user_searches, system_logs");
print("Created indexes for optimal performance");
print("Inserted initial configuration and categories"); 