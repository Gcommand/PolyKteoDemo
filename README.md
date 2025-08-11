# PolyU KTEO Patent Search & Analysis System

A comprehensive patent search and analysis platform built for The Hong Kong Polytechnic University's Knowledge Transfer and Enterprise Office (KTEO). This system provides intelligent semantic search, data processing, and analysis capabilities for patent portfolio management.

## 🎯 Overview

The PolyU KTEO system is designed to help researchers, administrators, and stakeholders discover, analyze, and manage patent information effectively. It combines AI-powered semantic search with structured data management to provide actionable insights into patent portfolios.

## ✨ Key Features

### 📊 **Comprehensive Data Pipeline & Processing**
- **Large-Scale Patent Database**: Successfully imported and processed over **2,000 patent records** (expanded from initial 900) from The Hong Kong Polytechnic University patent portfolio
- **Sophisticated N8N Workflow Automation**: 
  - Automated data ingestion pipeline with quality assurance agents
  - OpenRouter AI integration for intelligent content processing
  - Multi-step workflow orchestration with error handling and retry mechanisms
  - Batch processing capabilities for large-scale patent data operations
- **Multi-Source Data Integration**: 
  - **PolyU Technology Website Parsing**: Custom JavaScript parsers for extracting project information from PolyU technology showcase websites
  - **Google Patents Integration**: Enhanced metadata extraction including patent imagery and standardized classifications
  - **PDF Patent Document Processing**: Automated parsing of PDF patent documents with structured data extraction
- **AI-Enhanced Content Generation**: 
  - Automated AI summary generation with quality assurance validation
  - Structured output parsing for consistent data formatting
  - Confidence scoring for extraction quality assessment
  - Multi-model AI processing through OpenRouter integration

### 🔍 **Advanced Semantic Search & Discovery**
- **Vector-Based Semantic Search**: Intelligent AI-powered search using OpenAI embeddings for contextual understanding beyond keyword matching
- **Multi-Dimensional Filtering System**: 
  - **Department-Based Filtering**: Search across 30+ PolyU faculties, schools, and departments with standardized abbreviation mapping
  - **Technology Sector Classification**: Precise filtering across 34 technical domains including Biotech, ICT, Material Science, Healthcare, and Green Tech
  - **Assignee & Inventor Management**: Search by specific researchers, patent holders, and PolyU affiliations
  - **Temporal Filtering**: Date-based filtering with flexible range selection
- **Intelligent Search Features**:
  - **Multi-language support** (English/Chinese) with automatic language detection
  - **Confidence-based ranking** with adjustable similarity thresholds (default 0.7)
  - **Advanced sorting options**: Relevance, date, department (A-Z/Z-A), title alphabetical
  - **Pagination support** for large result sets with configurable page sizes

### 🗂️ **Robust Data Management Architecture**
- **PostgreSQL + pgvector Database**: High-performance vector storage with semantic similarity indexing
- **Structured Relationship Management**:
  - Many-to-many relationships between patents, departments, tech sectors, and assignees
  - Normalized department dictionary with abbreviation standardization
  - Technology sector hierarchical classification system
- **Data Quality & Integrity**:
  - **Duplicate Detection & Prevention**: Intelligent record validation preventing data duplication
  - **Metadata Enrichment**: Enhanced patent records with AI-generated summaries, image URLs, and standardized classifications
  - **Migration Framework**: Comprehensive migration scripts for data normalization and schema updates
  - **Incremental Updates**: Support for ongoing data updates and new patent additions

### 🤖 **Advanced AI Integration & Processing**
- **OpenAI Embeddings Integration**: Direct Azure OpenAI API integration for high-quality vector embeddings
- **Automatic Embedding Generation**: Real-time embedding creation for new patent content with batch processing capabilities
- **AI-Powered Content Enhancement**:
  - Quality assurance agents for content validation
  - Summarization chains for improved readability
  - Language-aware processing based on query language
  - Structured output parsing with confidence scoring

### 🔄 **Automated Workflow & Processing Systems**
- **N8N Workflow Engine**: 
  - Complete automation pipeline from data ingestion to processed output
  - Loop processing for large datasets with batch management
  - HTTP request handling for external API integrations
  - Conditional logic for quality control and error handling
- **Technology Website Parsers**: 
  - Custom JavaScript modules for PolyU technology showcase extraction
  - Event URL extraction and project structure analysis
  - Rich text HTML processing and content standardization
  - Multi-pattern recognition for diverse website structures
- **Batch Processing Capabilities**:
  - Large-scale patent processing with memory optimization
  - Parallel processing for improved performance
  - Error recovery and retry mechanisms
  - Progress tracking and logging

### 🛡️ **Enterprise Security & Performance**
- **Comprehensive Security Hardening**: 
  - Protection against SQL injection, XSS, and LDAP injection attacks
  - Path manipulation and directory traversal prevention
  - Input validation and sanitization across all endpoints
- **Performance Optimization**:
  - **Rate limiting** (100 requests/minute per IP) with automatic cleanup
  - Connection pooling and database optimization
  - Caching strategies for improved response times
  - Memory-efficient processing for large datasets
- **Security Headers & Monitoring**:
  - Content Security Policy implementation
  - XSS Protection and Frame Options
  - HTTPS enforcement and security monitoring
  - Comprehensive logging with sanitized error responses
- **Enterprise-Grade Reliability**:
  - Error handling with graceful degradation
  - Health check endpoints for system monitoring
  - Multi-environment deployment support (Development, UAT, Production)
  - Docker containerization for scalable deployment

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

# Check embedding content
python check_embedding_content.py
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
│   └── postgres_embedding.py     # Database models & embedding functions
├── 🗂️ migrations/
│   ├── migrate_tech_sectors.py   # Tech sector data migration
│   ├── migrate_department_*.sql  # Department normalization
│   └── run_department_migration.py # Migration runner
├── 🗂️ n8n-version/
│   └── code/                     # JavaScript processing modules
├── 🗂️ studio-integration-version/
│   └── pydantic_ai_expert_endpoint.py # Legacy integration files
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