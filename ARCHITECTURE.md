# Smart Prompt Parser & Canonicalisation Engine - System Architecture

## System Flow Diagram

```mermaid
flowchart TB
    Frontend[Frontend UI]
    DatasetFolder[Dataset Folder]
    API[API Clients]
    
    Frontend --> APIRoutes[API Routes]
    DatasetFolder --> APIRoutes
    API --> APIRoutes
    
    APIRoutes --> AuthMiddleware[Auth Middleware]
    AuthMiddleware --> RateLimitMiddleware[Rate Limit]
    RateLimitMiddleware --> LoggingMiddleware[Logging]
    LoggingMiddleware --> Processing[Processing Pipeline]
    
    Processing --> Moderation[Moderation Service]
    Moderation --> Embedding[Embedding Service]
    Embedding --> Clustering[Clustering Service]
    Clustering --> Canonicalization[Canonicalization Service]
    
    Embedding --> Redis[(Redis Cache)]
    Clustering --> Qdrant[(Qdrant Vector DB)]
    Clustering --> PostgreSQL[(PostgreSQL)]
    Canonicalization --> PostgreSQL
    
    Moderation --> PortkeyAI[Portkey AI Gateway]
    Embedding --> PortkeyAI
    Canonicalization --> PortkeyAI
```

## Detailed Component Flow

### 1. Prompt Ingestion Flow

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
    participant PortkeyAI
    
    User->>Frontend: Submit Prompt
    Frontend->>API: POST /api/v1/prompts
    API->>Moderation: Check Content
    Moderation->>PortkeyAI: text-moderation-latest
    PortkeyAI-->>Moderation: Result
    
    alt Content Flagged
        Moderation-->>API: Reject 400
        API-->>Frontend: Error
    else Content Safe
        Moderation->>Embedding: Generate Embedding
        Embedding->>Redis: Check Cache
        alt Cache Hit
            Redis-->>Embedding: Cached
        else Cache Miss
            Embedding->>PortkeyAI: text-embedding-3-small
            PortkeyAI-->>Embedding: Vector
            Embedding->>Redis: Store Cache
        end
        
        Embedding->>PostgreSQL: Store Prompt
        Embedding->>Clustering: Assign Cluster
        
        Clustering->>Qdrant: Search Vectors
        Qdrant-->>Clustering: Candidates
        
        alt Similarity > Threshold
            Clustering->>PostgreSQL: Assign Cluster
            Clustering->>Qdrant: Store Vector
        else No Match
            Clustering->>PostgreSQL: Create Cluster
            Clustering->>Qdrant: Store Vector
        end
        
        Clustering-->>API: Result
        API-->>Frontend: Success
        Frontend-->>User: Show Result
    end
```

### 2. Dataset Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Worker
    participant Reader
    participant Processor
    participant Redis
    
    User->>Frontend: Process Dataset
    Frontend->>API: POST /api/v1/dataset/ingest
    API->>Worker: Start
    
    Worker->>Reader: List Files
    Reader-->>Worker: File List
    
    loop For Each File
        Worker->>Redis: Check Checkpoint
        alt Checkpoint Exists
            Redis-->>Worker: Last Index
        end
        
        Reader->>Reader: Read File
        Reader-->>Worker: Prompts
        
        Worker->>Processor: Process Batch
        Processor-->>Worker: Results
        
        Processor->>Redis: Save Checkpoint
    end
    
    Worker->>PostgreSQL: Commit
    Worker-->>API: Summary
    API-->>Frontend: Complete
```

### 3. Clustering Flow

```mermaid
flowchart LR
    A[New Prompt] --> B[Query Qdrant]
    B --> C{Find Candidates?}
    C -->|Found| D[Calculate Similarity]
    C -->|Not Found| E[Create Cluster]
    
    D --> F{Similarity > 0.85?}
    F -->|Yes| G[Assign Cluster]
    F -->|No| E
    
    G --> H[Store Assignment]
    E --> I[Store Cluster]
    H --> J[Store Vector]
    I --> J
```

### 4. Template Extraction Flow

```mermaid
flowchart TD
    A[New Cluster] --> B[Canonicalization]
    B --> C[Model Router]
    C --> D{Code Heavy?}
    D -->|Yes| E[Claude Model]
    D -->|No| F[GPT-4 Model]
    
    E --> G[Extract Template]
    F --> G
    
    G --> H[Detect Slots]
    H --> I[Store Template]
    I --> J[Store Slots]
```

### 5. Evolution Flow

```mermaid
flowchart TD
    A[Drift Check] --> B[Get Prompts]
    B --> C[Get Template]
    C --> D[o1-mini Analysis]
    
    D --> E{Drift?}
    E -->|Yes| F[Record Event]
    E -->|No| G[No Action]
    
    F --> H[Update Version]
    H --> I[Store Event]
```

### 6. Data Flow

```mermaid
flowchart TB
    subgraph Input[Input Sources]
        I1[Frontend]
        I2[Dataset]
        I3[API]
    end
    
    subgraph Process[Processing]
        P1[Moderation]
        P2[Embedding]
        P3[Clustering]
        P4[Canonicalization]
    end
    
    subgraph Storage[Storage]
        S1[(PostgreSQL)]
        S2[(Qdrant)]
        S3[(Redis)]
    end
    
    Input --> Process
    Process --> Storage
```

## Service Dependencies

```mermaid
flowchart TD
    API[Prompt API] --> Moderation[Moderation Service]
    API --> Embedding[Embedding Service]
    API --> Clustering[Clustering Service]
    
    Clustering --> Similarity[Similarity Service]
    Clustering --> Qdrant[Qdrant Client]
    Clustering --> Redis[Redis Client]
    
    Similarity --> Qdrant
    
    Embedding --> Portkey[Portkey Client]
    Embedding --> Redis
    
    Moderation --> Portkey
    
    Canonicalization[Canonicalization] --> ModelRouter[Model Router]
    Canonicalization --> Portkey
    Canonicalization --> Versioning[Versioning Service]
    
    ModelRouter --> Portkey
    
    Versioning --> Evolution[Evolution Service]
    
    Drift[Drift Detection] --> Portkey
    Drift --> Evolution
    
    Family[Family Tracking] --> Portkey
    Family --> Reasoning[Reasoning Service]
    
    Reasoning --> Portkey
```

## Database Schema

```mermaid
erDiagram
    PROMPTS ||--o{ CLUSTER_ASSIGNMENTS : "assigned"
    CLUSTERS ||--o{ CLUSTER_ASSIGNMENTS : "contains"
    CLUSTERS ||--o{ CANONICAL_TEMPLATES : "has"
    CANONICAL_TEMPLATES ||--o{ TEMPLATE_SLOTS : "contains"
    CANONICAL_TEMPLATES ||--o{ EVOLUTION_EVENTS : "tracks"
    
    PROMPTS {
        uuid id PK
        text content
        string status
    }
    
    CLUSTERS {
        uuid id PK
        string name
        float threshold
    }
    
    CLUSTER_ASSIGNMENTS {
        uuid id PK
        uuid prompt_id FK
        uuid cluster_id FK
        float similarity
    }
    
    CANONICAL_TEMPLATES {
        uuid id PK
        uuid cluster_id FK
        text content
        string version
    }
    
    TEMPLATE_SLOTS {
        uuid id PK
        uuid template_id FK
        string name
    }
    
    EVOLUTION_EVENTS {
        uuid id PK
        uuid template_id FK
        string event_type
    }
```

## AI Model Usage

| Service | Primary Model | Fallback Model | Use Case |
|---------|--------------|----------------|----------|
| Moderation | text-moderation-latest | - | Content safety |
| Embedding | text-embedding-3-small | text-embedding-3-large | Vector generation |
| Canonicalization | gpt-4o | claude-3-5-sonnet | Template extraction |
| Drift Detection | o1-mini | - | Semantic drift |
| Family Tracking | o1-mini | - | Split/merge decisions |
| Reasoning | o1-mini | - | Edge cases |

## Key Design Patterns

1. **Incremental Processing**: Checkpoints in Redis allow resuming dataset processing
2. **Caching Strategy**: Embeddings cached in Redis (7 days), similarity scores cached (1 day)
3. **Model Routing**: Dynamic model selection based on content type (code vs. general)
4. **Semantic Versioning**: Templates versioned using semver (major.minor.patch)
5. **Event-Driven Evolution**: Evolution events trigger template version updates
6. **Confidence Scoring**: All assignments include confidence scores for explainability

