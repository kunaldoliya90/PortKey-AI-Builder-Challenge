# Smart Prompt Parser & Canonicalisation Engine - System Architecture

## System Flow Diagram

```mermaid
flowchart TB
    %% Entry Points
    Frontend[Frontend UI<br/>Jinja2 Templates]
    DatasetFolder[Dataset Folder<br/>JSON/CSV/TXT/JSONL Files]
    API[API Clients<br/>External Services]
    
    %% API Layer
    subgraph API_Layer["API Layer (FastAPI)"]
        AuthMiddleware[Authentication Middleware<br/>API Key Validation]
        RateLimitMiddleware[Rate Limiting Middleware<br/>Redis-based]
        LoggingMiddleware[Request Logging Middleware<br/>Structured Logs]
        
        WebRoutes[Web Routes<br/>/clusters, /templates, /evolution]
        APIRoutes[API Routes<br/>/api/v1/prompts, /api/v1/clusters]
    end
    
    %% Processing Pipeline
    subgraph Processing["Processing Pipeline"]
        Moderation["Moderation Service<br/>text-moderation-latest"]
        Embedding["Embedding Service<br/>text-embedding-3-small<br/>Fallback: text-embedding-3-large"]
        Clustering["Clustering Service<br/>Semantic Similarity Matching"]
        Canonicalization["Canonicalization Service<br/>gpt-4o<br/>Fallback: claude-3-5-sonnet"]
        TemplateVersioning["Template Versioning Service<br/>Semantic Versioning"]
        EvolutionTracking["Evolution Tracking Service<br/>Event Recording"]
        DriftDetection["Drift Detection Service<br/>o1-mini"]
        FamilyTracking["Family Tracking Service<br/>o1-mini<br/>Split/Merge Logic"]
        Reasoning["Reasoning Service<br/>o1-mini<br/>Edge Case Classification"]
    end
    
    %% Data Storage
    subgraph Storage["Data Storage Layer"]
        PostgreSQL[(PostgreSQL<br/>Structured Data<br/>Prompts, Clusters, Templates)]
        Qdrant[(Qdrant<br/>Vector Database<br/>Embeddings & Similarity Search)]
        Redis[(Redis<br/>Cache Layer<br/>Embeddings, Similarity Scores)]
    end
    
    %% External Services
    subgraph External["External Services"]
        PortkeyAI[Portkey AI Gateway<br/>Model Orchestration<br/>Retry Logic, Virtual Keys]
        CloudWatch[CloudWatch<br/>Logging & Monitoring]
        Prometheus[Prometheus<br/>Metrics Collection]
    end
    
    %% Entry Flow
    Frontend -->|Submit Prompt| APIRoutes
    Frontend -->|View Results| WebRoutes
    DatasetFolder -->|Batch Processing| APIRoutes
    API -->|REST API Calls| APIRoutes
    
    %% Middleware Flow
    APIRoutes --> AuthMiddleware
    AuthMiddleware --> RateLimitMiddleware
    RateLimitMiddleware --> LoggingMiddleware
    LoggingMiddleware --> Processing
    
    %% Processing Flow - Single Prompt
    Processing -->|Step 1: Content Check| Moderation
    Moderation -->|Flagged?| Reject[Reject Prompt<br/>Return Error]
    Moderation -->|Pass| Embedding
    
    Embedding -->|Check Cache| Redis
    Redis -->|Cache Hit| UseCache[Use Cached Embedding]
    Redis -->|Cache Miss| PortkeyAI
    PortkeyAI -->|Generate Embedding| Embedding
    Embedding -->|Store in Cache| Redis
    Embedding -->|Store Prompt| PostgreSQL
    
    Embedding -->|Step 2: Find Similar| Clustering
    Clustering -->|Query Vectors| Qdrant
    Qdrant -->|Similarity Search| Clustering
    Clustering -->|Check Cache| Redis
    Clustering -->|Calculate Similarity| SimilarityService[Similarity Service<br/>Cosine Similarity]
    
    Clustering -->|Match Found?| Decision{Similarity > Threshold?}
    Decision -->|Yes| AssignCluster[Assign to Existing Cluster]
    Decision -->|No| CreateCluster[Create New Cluster]
    
    AssignCluster -->|Store Assignment| PostgreSQL
    CreateCluster -->|Store Cluster| PostgreSQL
    AssignCluster -->|Store Vector| Qdrant
    CreateCluster -->|Store Vector| Qdrant
    
    %% Template Extraction Flow
    CreateCluster -->|New Cluster?| Canonicalization
    AssignCluster -->|On Demand| Canonicalization
    
    Canonicalization -->|Route Model| ModelRouter["Model Router<br/>Code Detection"]
    ModelRouter -->|Code Heavy| ClaudeModel["Claude Model<br/>claude-3-5-sonnet"]
    ModelRouter -->|General| GPT4Model["GPT-4 Model<br/>gpt-4o"]
    
    ClaudeModel -->|Extract Template| Canonicalization
    GPT4Model -->|Extract Template| Canonicalization
    
    Canonicalization -->|Detect Slots| SlotDetection[Slot Detection<br/>Regex + AI Analysis]
    Canonicalization -->|Store Template| PostgreSQL
    SlotDetection -->|Store Slots| PostgreSQL
    
    %% Versioning Flow
    Canonicalization -->|Create Version| TemplateVersioning
    TemplateVersioning -->|Detect Changes| ChangeDetection{Change Type?}
    ChangeDetection -->|Major| MajorVersion[Major Version<br/>Breaking Changes]
    ChangeDetection -->|Minor| MinorVersion[Minor Version<br/>New Slots]
    ChangeDetection -->|Patch| PatchVersion[Patch Version<br/>Minor Updates]
    
    MajorVersion -->|Record Event| EvolutionTracking
    MinorVersion -->|Record Event| EvolutionTracking
    PatchVersion -->|Record Event| EvolutionTracking
    
    %% Evolution & Drift Detection
    EvolutionTracking -->|Store Event| PostgreSQL
    EvolutionTracking -->|Trigger Analysis| DriftDetection
    
    DriftDetection -->|Analyze Cluster| Qdrant
    Qdrant -->|Get Recent Prompts| DriftDetection
    DriftDetection -->|Reasoning Model| PortkeyAI
    PortkeyAI -->|Drift Analysis| DriftDetection
    DriftDetection -->|Record Drift Event| EvolutionTracking
    
    %% Family Tracking
    Clustering -->|Map to Family| FamilyTracking
    FamilyTracking -->|Check Relationships| PostgreSQL
    FamilyTracking -->|Split/Merge Decision| Reasoning
    Reasoning -->|Complex Analysis| PortkeyAI
    PortkeyAI -->|Reasoning Result| FamilyTracking
    FamilyTracking -->|Update Family| PostgreSQL
    
    %% Dataset Processing Flow
    subgraph DatasetProcessing["Dataset Processing Pipeline"]
        DatasetReader[Dataset Reader<br/>Read Files: JSON/CSV/TXT/JSONL]
        BatchProcessor[Batch Processor<br/>Chunk Processing]
        Checkpointing[Checkpointing<br/>Redis-based<br/>Resume on Failure]
    end
    
    DatasetFolder -->|Read Files| DatasetReader
    DatasetReader -->|Extract Prompts| BatchProcessor
    BatchProcessor -->|Process in Batches| Processing
    BatchProcessor -->|Save Checkpoint| Redis
    BatchProcessor -->|Resume from Checkpoint| Checkpointing
    
    %% View Endpoints Flow
    WebRoutes -->|Query Data| PostgreSQL
    WebRoutes -->|Query Vectors| Qdrant
    PostgreSQL -->|Return Results| WebRoutes
    Qdrant -->|Return Vectors| WebRoutes
    WebRoutes -->|Render Templates| Frontend
    
    %% Observability
    LoggingMiddleware -->|Structured Logs| CloudWatch
    Processing -->|Metrics| Prometheus
    Prometheus -->|Metrics Endpoint| API_Layer
    
    %% Styling
    classDef entryPoint fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef apiLayer fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef processing fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef external fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class Frontend,DatasetFolder,API entryPoint
    class AuthMiddleware,RateLimitMiddleware,LoggingMiddleware,WebRoutes,APIRoutes apiLayer
    class Moderation,Embedding,Clustering,Canonicalization,TemplateVersioning,EvolutionTracking,DriftDetection,FamilyTracking,Reasoning processing
    class PostgreSQL,Qdrant,Redis storage
    class PortkeyAI,CloudWatch,Prometheus external
```

## Detailed Component Flow

### 1. Prompt Ingestion Flow (Single Prompt)

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Moderation
    participant Embedding
    participant Redis
    participant Clustering
    participant Qdrant
    participant PostgreSQL
    participant Canonicalization
    participant PortkeyAI
    
    User->>Frontend: Submit Prompt
    Frontend->>API: POST /api/v1/prompts
    API->>Moderation: Check Content Safety
    Moderation->>PortkeyAI: text-moderation-latest
    PortkeyAI-->>Moderation: Moderation Result
    
    alt Content Flagged
        Moderation-->>API: Reject 400
        API-->>Frontend: Error Response
    else Content Safe
        Moderation->>Embedding: Generate Embedding
        Embedding->>Redis: Check Cache
        alt Cache Hit
            Redis-->>Embedding: Cached Embedding
        else Cache Miss
            Embedding->>PortkeyAI: text-embedding-3-small
            PortkeyAI-->>Embedding: Embedding Vector
            Embedding->>Redis: Store in Cache
        end
        
        Embedding->>PostgreSQL: Store Prompt
        Embedding->>Clustering: Assign to Cluster
        
        Clustering->>Qdrant: Search Similar Vectors
        Qdrant-->>Clustering: Candidate Clusters
        
        alt Similarity > Threshold
            Clustering->>PostgreSQL: Assign to Existing Cluster
            Clustering->>Qdrant: Store Vector with Cluster ID
        else No Match Found
            Clustering->>PostgreSQL: Create New Cluster
            Clustering->>Qdrant: Store Vector
            Clustering->>Canonicalization: Extract Template
            Canonicalization->>PortkeyAI: gpt-4o
            PortkeyAI-->>Canonicalization: Template + Slots
            Canonicalization->>PostgreSQL: Store Template
        end
        
        Clustering-->>API: Assignment Result
        API-->>Frontend: Success Response
        Frontend-->>User: Show Result
    end
```

### 2. Dataset Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant DatasetWorker
    participant DatasetReader
    participant BatchProcessor
    participant Redis
    participant ProcessingPipeline
    
    User->>Frontend: Click Process Dataset
    Frontend->>API: POST /api/v1/dataset/ingest
    API->>DatasetWorker: Start Ingestion
    
    DatasetWorker->>DatasetReader: List Files in Dataset/
    DatasetReader-->>DatasetWorker: File List
    
    loop For Each File
        DatasetWorker->>Redis: Check Checkpoint
        alt Checkpoint Exists
            Redis-->>DatasetWorker: Last Processed Index
            DatasetWorker->>DatasetReader: Skip Processed Prompts
        end
        
        DatasetReader->>DatasetReader: Read File (JSON/CSV/TXT/JSONL)
        DatasetReader-->>DatasetWorker: Prompts Generator
        
        DatasetWorker->>BatchProcessor: Process in Batches
        BatchProcessor->>ProcessingPipeline: Process Each Prompt
        ProcessingPipeline-->>BatchProcessor: Result
        
        BatchProcessor->>Redis: Save Checkpoint
    end
    
    DatasetWorker->>PostgreSQL: Commit All Changes
    DatasetWorker-->>API: Summary Statistics
    API-->>Frontend: Completion Status
    Frontend-->>User: Show Summary
```

### 3. Clustering & Similarity Flow

```mermaid
flowchart LR
    A[New Prompt<br/>+ Embedding] --> B[Query Qdrant<br/>Similarity Search]
    B --> C{Find Candidates<br/>Top K Results}
    C -->|Found| D[Calculate Similarity<br/>Cosine Distance]
    C -->|Not Found| E[Create New Cluster]
    
    D --> F{Similarity > Threshold?<br/>Default: 0.85}
    F -->|Yes| G[Assign to Cluster]
    F -->|No| E
    
    G --> H[Calculate Confidence Score]
    H --> I[Generate Reasoning]
    I --> J[Store Assignment]
    
    E --> K[Create Cluster Record]
    K --> L[Store Vector in Qdrant]
    L --> M[Trigger Template Extraction]
    
    J --> N[Store Vector in Qdrant<br/>with Cluster ID]
    N --> O[Cache Similarity Score<br/>in Redis]
    
    M --> P[Canonicalization Service]
```

### 4. Template Extraction & Versioning Flow

```mermaid
flowchart TD
    A[New Cluster Created] --> B[Canonicalization Service]
    B --> C[Model Router]
    C --> D{Detect Code?}
    D -->|Yes| E["Claude Model<br/>claude-3-5-sonnet"]
    D -->|No| F["GPT-4 Model<br/>gpt-4o"]
    
    E --> G[Extract Template<br/>with JSON Schema]
    F --> G
    
    G --> H[Detect Variable Slots<br/>Regex + AI Analysis]
    H --> I[Store Template<br/>Version 1.0.0]
    I --> J[Store Slots]
    
    K[Template Update Detected] --> L[Template Versioning Service]
    L --> M{Change Type?}
    M -->|Breaking| N[Major Version<br/>2.0.0]
    M -->|New Slots| O[Minor Version<br/>1.1.0]
    M -->|Minor Changes| P[Patch Version<br/>1.0.1]
    
    N --> Q[Record Evolution Event]
    O --> Q
    P --> Q
    Q --> R[Store in PostgreSQL]
```

### 5. Evolution & Drift Detection Flow

```mermaid
flowchart TD
    A[Periodic Drift Check] --> B[Drift Detection Service]
    B --> C[Get Cluster Prompts]
    C --> D[Get Template]
    D --> E["o1-mini<br/>Reasoning Model"]
    
    E --> F{Drift Detected?}
    F -->|Yes| G[Calculate Drift Score]
    F -->|No| H[No Action]
    
    G --> I[Record Evolution Event]
    I --> J[Update Template Version]
    J --> K[Store Event in PostgreSQL]
    
    L[Family Relationship Check] --> M[Family Tracking Service]
    M --> N["o1-mini<br/>Split/Merge Analysis"]
    N --> O{Action Required?}
    O -->|Split| P[Create Child Family]
    O -->|Merge| Q[Merge Families]
    O -->|None| R[No Action]
    
    P --> S[Update Family Mappings]
    Q --> S
    S --> T[Store in PostgreSQL]
```

### 6. Data Flow Architecture

```mermaid
flowchart TB
    subgraph Input["Input Sources"]
        I1[Frontend Form]
        I2[Dataset Folder]
        I3[API Clients]
    end
    
    subgraph Processing["Processing Layer"]
        P1[Moderation]
        P2[Embedding Generation]
        P3[Clustering]
        P4[Canonicalization]
        P5[Evolution Tracking]
    end
    
    subgraph Storage["Storage Layer"]
        S1[(PostgreSQL<br/>Metadata)]
        S2[(Qdrant<br/>Vectors)]
        S3[(Redis<br/>Cache)]
    end
    
    subgraph Output["Output/View"]
        O1[Clusters View]
        O2[Templates View]
        O3[Evolution View]
        O4[API Responses]
    end
    
    I1 --> P1
    I2 --> P1
    I3 --> P1
    
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    
    P2 --> S3
    P3 --> S2
    P3 --> S1
    P4 --> S1
    P5 --> S1
    
    S1 --> O1
    S1 --> O2
    S1 --> O3
    S2 --> O1
    S1 --> O4
```

## Component Interactions

### Service Dependencies

```mermaid
graph TD
    PromptIngestion[Prompt Ingestion API] --> ModerationService
    PromptIngestion --> EmbeddingService
    PromptIngestion --> ClusteringService
    
    ClusteringService --> SimilarityService
    ClusteringService --> QdrantClient
    ClusteringService --> RedisClient
    
    SimilarityService --> QdrantClient
    
    EmbeddingService --> PortkeyClient
    EmbeddingService --> RedisClient
    
    ModerationService --> PortkeyClient
    
    CanonicalizationService --> ModelRouter
    CanonicalizationService --> PortkeyClient
    CanonicalizationService --> TemplateVersioningService
    
    ModelRouter --> PortkeyClient
    
    TemplateVersioningService --> EvolutionService
    
    DriftDetectionService --> PortkeyClient
    DriftDetectionService --> EvolutionService
    
    FamilyTrackingService --> PortkeyClient
    FamilyTrackingService --> ReasoningService
    
    ReasoningService --> PortkeyClient
    
    DatasetWorker --> DatasetReader
    DatasetWorker --> ModerationService
    DatasetWorker --> EmbeddingService
    DatasetWorker --> ClusteringService
```

## Database Schema Relationships

```mermaid
erDiagram
    PROMPTS ||--o{ CLUSTER_ASSIGNMENTS : "assigned to"
    CLUSTERS ||--o{ CLUSTER_ASSIGNMENTS : "contains"
    CLUSTERS ||--o{ CANONICAL_TEMPLATES : "has"
    CANONICAL_TEMPLATES ||--o{ TEMPLATE_SLOTS : "contains"
    CANONICAL_TEMPLATES ||--o{ EVOLUTION_EVENTS : "tracks"
    PROMPT_FAMILIES ||--o{ FAMILY_CLUSTER_MAPPINGS : "maps"
    CLUSTERS ||--o{ FAMILY_CLUSTER_MAPPINGS : "belongs to"
    
    PROMPTS {
        uuid id PK
        text content
        string moderation_status
        timestamp created_at
    }
    
    CLUSTERS {
        uuid id PK
        string name
        float similarity_threshold
        float confidence_score
        timestamp created_at
    }
    
    CLUSTER_ASSIGNMENTS {
        uuid id PK
        uuid prompt_id FK
        uuid cluster_id FK
        float similarity_score
        float confidence_score
        text reasoning
    }
    
    CANONICAL_TEMPLATES {
        uuid id PK
        uuid cluster_id FK
        text template_content
        string version
        jsonb slots
        float confidence_score
    }
    
    TEMPLATE_SLOTS {
        uuid id PK
        uuid template_id FK
        string slot_name
        string slot_type
        jsonb example_values
        float confidence_score
    }
    
    EVOLUTION_EVENTS {
        uuid id PK
        uuid template_id FK
        string event_type
        string previous_version
        string new_version
        text change_reason
    }
    
    PROMPT_FAMILIES {
        uuid id PK
        string name
        text description
        uuid parent_family_id FK
    }
    
    FAMILY_CLUSTER_MAPPINGS {
        uuid id PK
        uuid family_id FK
        uuid cluster_id FK
    }
```

## AI Model Usage Matrix

| Service | Primary Model | Fallback Model | Use Case |
|---------|--------------|----------------|----------|
| Moderation | @openai/text-moderation-latest | - | Content safety check |
| Embedding | @openai/text-embedding-3-small | @openai/text-embedding-3-large | Vector generation |
| Canonicalization | @openai/gpt-4o | @anthropic/claude-3-5-sonnet | Template extraction |
| Drift Detection | @openai/o1-mini | - | Semantic drift analysis |
| Family Tracking | @openai/o1-mini | - | Split/merge decisions |
| Reasoning | @openai/o1-mini | - | Edge case classification |

## Key Design Patterns

1. **Incremental Processing**: Checkpoints in Redis allow resuming dataset processing
2. **Caching Strategy**: Embeddings cached in Redis (7 days), similarity scores cached (1 day)
3. **Model Routing**: Dynamic model selection based on content type (code vs. general)
4. **Semantic Versioning**: Templates versioned using semver (major.minor.patch)
5. **Event-Driven Evolution**: Evolution events trigger template version updates
6. **Confidence Scoring**: All assignments include confidence scores for explainability

