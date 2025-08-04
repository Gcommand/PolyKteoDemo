# PolyU KTEO Patent Search & Analysis System

A comprehensive patent search and analysis platform built for The Hong Kong Polytechnic University's Knowledge Transfer and Enterprise Office (KTEO). This system provides intelligent semantic search, data processing, and analysis capabilities for patent portfolio management.

## 🎯 Overview

The PolyU KTEO system is designed to help researchers, administrators, and stakeholders discover, analyze, and manage patent information effectively. It combines AI-powered semantic search with structured data management to provide actionable insights into patent portfolios.

## ✨ Key Features

### 🔍 Advanced Search Capabilities
- **Vector-based semantic search** using OpenAI embeddings
- **Multi-language support** (English/Chinese) with automatic detection
- **Intelligent filtering** by departments, tech sectors, assignees, and dates
- **Flexible sorting** options (relevance, date, title, etc.)
- **Pagination** for large result sets

### 🗂️ Data Management
- **Structured patent database** with PostgreSQL + pgvector
- **Department categorization** with abbreviation mapping
- **Technology sector classification** for research areas
- **Assignee management** with PolyU affiliation tracking
- **Metadata preservation** with JSON support

### 🤖 AI Integration
- **Pydantic AI expert** for intelligent patent analysis
- **Automatic embedding generation** for new patent content
- **Language-aware summaries** based on query language
- **Conversation history** for interactive sessions

### 🔄 Data Processing
- **Migration scripts** for data normalization and cleanup
- **N8N workflow integration** for automated processing
- **Batch processing** for large-scale operations

### 🛡️ Security & Performance
- **Comprehensive security hardening** against common vulnerabilities
- **Rate limiting** (100 requests/minute per IP)
- **Input validation** and sanitization
- **Security headers** and monitoring
- **Error handling** with sanitized responses

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Frontend Web   │    │   Flask API     │    │   PostgreSQL    │
│    (Separate    │◄──►│   (Backend)     │◄──►│   + pgvector    │
│   Repository)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                       │
                      ┌─────────────────┐               │
                      │   Azure OpenAI  │               │
                      │   (Embeddings)  │               │
                      └─────────────────┘               │
                                                         │
┌─────────────────┐                        ┌─────────────────┐
│   N8N Workflows │                        │   Migration     │
│   (Automation)  │                        │   Scripts       │
└─────────────────┘                        └─────────────────┘
```

## 📋 Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+** with pgvector extension
- **Azure OpenAI** account and API access
- **Node.js 18+** (for N8N workflows, optional)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd PolyKteoDemo
```

### 2. Set Up Python Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Database Configuration
AZURE_POSTGRES_CONNECTION=postgresql://username:password@host:port/database

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_API_VERSION=2024-02-01

# Security Configuration (Optional)
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 4. Database Setup
Execute the SQL schema files to set up the database:
```bash
# Core schema setup
psql -d your_database -f site_pages.sql
psql -d your_database -f site_pages_poly_kteo.sql

# Tech sectors setup
psql -d your_database -f tech_sectors_insert.sql
```

### 5. Run Database Migrations
```bash
# Migrate tech sectors
python migrations/migrate_tech_sectors.py

# Migrate departments with dictionary
python migrations/run_department_migration.py
```

## 🖥️ Usage

### Frontend Web Interface
The frontend web interface is located in a separate repository: **`polykteodemofrontend`**

Please refer to that repository for frontend setup and usage instructions.

### API Server (Flask)
```bash
python app.py
# or for production
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```
API available at `http://localhost:5000`

### Standalone Processing
```bash
# Generate embeddings for all patents
python regenerate_embeddings.py

# Debug similarity calculations
python debug_similarity.py
```

## 📡 API Endpoints

### Search & Retrieval
- `GET /search` - Semantic patent search with filtering
- `GET /search_page` - Web interface for patent search
- `GET /health` - System health check

### Filter Options
- `GET /assignees` - Get all assignees
- `GET /poly_assignees` - Get PolyU-affiliated assignees
- `GET /departments` - Get all departments
- `GET /tech_sectors` - Get all technology sectors

### Data Management
- `POST /update_embedding` - Update patent embeddings (authenticated)

See `swagger/PolyU_BN_API.yaml` for complete API documentation.

## 🗄️ Database Schema

### Core Tables
- **`patents_list`** - Main patent records with content and metadata
- **`departments`** - University departments with abbreviations
- **`tech_sectors`** - Technology classification categories
- **`assignees`** - Patent assignees and inventors

### Relationship Tables
- **`patent_departments`** - Many-to-many: patents ↔ departments
- **`patent_tech_sectors`** - Many-to-many: patents ↔ tech sectors
- **`patent_assignees`** - Many-to-many: patents ↔ assignees

### Utility Tables
- **`search_logs`** - Query tracking and analytics
- **`department_dictionary`** - Department name normalization

## 🔧 Configuration

### Chunking Parameters
Adjust in `src/postgres_embedding.py`:
```python
chunk_size = 5000  # Characters per chunk
overlap = 200      # Overlap between chunks
```

### Search Configuration
Modify in `app.py`:
```python
DEFAULT_LIMIT = 50      # Results per page
MAX_QUERY_LENGTH = 1000 # Maximum query length
SIMILARITY_THRESHOLD = 0.7  # Minimum similarity score
```

### Security Settings
Configure in `app.py`:
```python
RATE_LIMIT_REQUESTS = 100  # Requests per window
RATE_LIMIT_WINDOW = 60     # Window duration (seconds)
```

## 📁 Project Structure

```
PolyKteoDemo/
├── 📄 app.py                     # Main Flask API server
├── 🗂️ src/
│   ├── postgres_embedding.py     # Database models & embedding functions
│   └── pydantic_ai_expert.py     # AI agent for patent analysis
├── 🗂️ migrations/
│   ├── migrate_tech_sectors.py   # Tech sector data migration
│   ├── migrate_department_*.sql  # Department normalization
│   └── run_department_migration.py # Migration runner
├── 🗂️ n8n-version/
│   └── code/                     # JavaScript processing modules
├── 🗂️ studio-integration-version/
│   └── pydantic_ai_expert_endpoint.py # Production API endpoint
├── 🗂️ swagger/
│   └── PolyU_BN_API.yaml         # API documentation
├── 🗂️ tests/
│   └── test_search_sorting.py    # Test suite
├── 📄 *.sql                      # Database schema files
└── 📄 requirements.txt           # Python dependencies
```

## 🔒 Security Features

### Input Validation
- SQL injection prevention
- XSS attack mitigation
- Parameter sanitization
- Length validation

### Rate Limiting
- Per-IP request throttling
- Automatic cleanup of expired entries
- Configurable limits

### Security Headers
- Content Security Policy
- XSS Protection
- Frame Options
- HTTPS enforcement

### Monitoring
- Comprehensive logging
- Suspicious activity detection
- Error sanitization
- Performance monitoring

## 🧪 Testing

```bash
# Run the test suite
pytest tests/

# Test search functionality
python tests/test_search_sorting.py

# Security testing
python security_test.py
```

## 🚀 Deployment

### Prerequisites
- **GlobalConnect VPN** access to PolyU network
- **SSH access** to PolyU backend servers
- **Docker** installed locally for building images
- **Proper hostnames** and credentials for UAT/PROD environments

### Deployment Process

#### 1. Local Docker Build
```bash
# Build the Docker image locally
docker build -t polyu-kteo-api:latest .

# Save the image to a tar file for transfer
docker save polyu-kteo-api:latest -o polyu-kteo-api.tar
```

#### 2. Connect to PolyU Network
```bash
# Connect via GlobalConnect VPN to PolyU network
# Ensure VPN connection is established before proceeding
```

#### 3. Deploy to UAT Environment
```bash
# SSH to UAT server
ssh username@uat-hostname.polyu.edu.hk

# Upload Docker tar file
scp polyu-kteo-api.tar username@uat-hostname.polyu.edu.hk:/path/to/deployment/

# On UAT server: Load and run the image
docker load -i polyu-kteo-api.tar
docker stop polyu-kteo-api-uat || true
docker rm polyu-kteo-api-uat || true
docker run -d --name polyu-kteo-api-uat \
  -p 5000:5000 \
  --env-file .env.uat \
  polyu-kteo-api:latest
```

#### 4. Deploy to PROD Environment
```bash
# SSH to PROD server
ssh username@prod-hostname.polyu.edu.hk

# Upload Docker tar file
scp polyu-kteo-api.tar username@prod-hostname.polyu.edu.hk:/path/to/deployment/

# On PROD server: Load and run the image
docker load -i polyu-kteo-api.tar
docker stop polyu-kteo-api-prod || true
docker rm polyu-kteo-api-prod || true
docker run -d --name polyu-kteo-api-prod \
  -p 5000:5000 \
  --env-file .env.prod \
  polyu-kteo-api:latest
```

#### 5. Verify Deployment
```bash
# Check container status
docker ps | grep polyu-kteo-api

# Check logs
docker logs polyu-kteo-api-[uat|prod]

# Test API endpoint
curl http://localhost:5000/health
```

### Environment Configuration
- **UAT**: `.env.uat` with UAT database and API configurations
- **PROD**: `.env.prod` with production database and API configurations
- Ensure environment-specific variables are properly configured on each server

## 📊 Monitoring & Analytics

### Search Analytics
- Query patterns and frequency
- Response time monitoring
- Result relevance tracking
- User engagement metrics

### System Health
- Database connectivity
- API response times
- Error rates
- Resource utilization

## 🤝 Contributing

1. **Code Style**: Follow PEP 8 guidelines
2. **Testing**: Add tests for new features
3. **Documentation**: Update API docs and comments
4. **Security**: Follow security best practices

## 📝 License

This project is proprietary to The Hong Kong Polytechnic University KTEO.

## 🆘 Support

For technical support or questions:
- Check the API documentation in `swagger/`
- Review the security report in `SECURITY_FIXES_SUMMARY.md`
- Examine test cases in `tests/`

---

**Built with ❤️ for PolyU KTEO**