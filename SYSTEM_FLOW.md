# Smart Prompt Parser & Canonicalisation Engine - Complete System Flow

## Main System Flowchart

```mermaid
flowchart TB
    %% Entry Points
    Start([System Start]) --> Entry{Entry Point}
    Entry -->|User Input| Frontend[Frontend UI<br/>Submit Prompt Form]
    Entry -->|Batch Processing| Dataset[Dataset Folder<br/>Read Files]
    Entry -->|API Call| ExternalAPI[External API Client]
    
    %% Frontend Flow
    Frontend -->|POST /api/v1/prompts| APIGateway[API Gateway<br/>FastAPI]
    Dataset -->|POST /api/v1/dataset/ingest| APIGateway
    ExternalAPI -->|REST API| APIGateway
    
    %% Middleware Stack
    APIGateway --> Auth[Authentication Middleware<br/>API Key Check]
    Auth -->|Skip for Web| RateLimit[Rate Limiting<br/>Redis-based]
    Auth -->|Require Key| RateLimit
    RateLimit --> Logging[Request Logging<br/>Structured Logs]
    Logging --> Pipeline[Processing Pipeline]
    
    %% Pipeline Step 1: Moderation
    Pipeline --> Moderation[1. Moderation Service]
    Moderation -->|Call| PortkeyMod["Portkey AI<br/>text-moderation-latest"]
    PortkeyMod -->|Result| ModCheck{Content Safe?}
    ModCheck -->|Flagged| Reject[Reject Prompt<br/>Return 400 Error]
    ModCheck -->|Safe| EmbeddingStep[2. Embedding Service]
    
    %% Pipeline Step 2: Embedding
    EmbeddingStep --> EmbedCache{Check Redis Cache}
    EmbedCache -->|Hit| UseCached[Use Cached Embedding]
    EmbedCache -->|Miss| GenerateEmbed[Generate Embedding]
    GenerateEmbed -->|Call| PortkeyEmbed["Portkey AI<br/>text-embedding-3-small<br/>Fallback: text-embedding-3-large"]
    PortkeyEmbed -->|Vector| StoreEmbedCache[Store in Redis Cache<br/>TTL: 7 days]
    StoreEmbedCache --> StorePrompt[Store Prompt in PostgreSQL]
    UseCached --> StorePrompt
    
    %% Pipeline Step 3: Clustering
    StorePrompt --> ClusteringStep[3. Clustering Service]
    ClusteringStep --> SimilaritySearch[Similarity Search Service]
    SimilaritySearch -->|Query| QdrantDB[(Qdrant Vector DB<br/>ANN Search)]
    QdrantDB -->|Top K Results| CalcSimilarity[Calculate Cosine Similarity]
    CalcSimilarity --> SimilarityCache{Check Redis Cache}
    SimilarityCache -->|Hit| UseCachedSim[Use Cached Score]
    SimilarityCache -->|Miss| UseCalcSim[Use Calculated Score]
    UseCachedSim --> ClusterDecision{Similarity > Threshold?<br/>Default: 0.85}
    UseCalcSim --> ClusterDecision
    
    %% Cluster Assignment Decision
    ClusterDecision -->|Yes, Match Found| AssignExisting[Assign to Existing Cluster]
    ClusterDecision -->|No Match| CreateNew[Create New Cluster]
    
    AssignExisting --> StoreAssignment[Store ClusterAssignment<br/>in PostgreSQL]
    CreateNew --> StoreCluster[Store Cluster<br/>in PostgreSQL]
    
    StoreAssignment --> StoreVector[Store Embedding Vector<br/>in Qdrant with Cluster ID]
    StoreCluster --> StoreVectorNew[Store Embedding Vector<br/>in Qdrant]
    
    StoreVector --> ReturnResult[Return Assignment Result]
    StoreVectorNew --> TriggerTemplate[Trigger Template Extraction]
    
    %% Pipeline Step 4: Template Extraction
    TriggerTemplate --> CanonicalStep[4. Canonicalization Service]
    CanonicalStep --> ModelRouter[Model Router<br/>Content Analysis]
    ModelRouter --> CodeCheck{Code Heavy?}
    CodeCheck -->|Yes| ClaudeModel["Claude Model<br/>claude-3-5-sonnet-latest"]
    CodeCheck -->|No| GPT4Model["GPT-4 Model<br/>gpt-4o-2024-08-06"]
    
    ClaudeModel -->|Extract| ExtractTemplate[Extract Canonical Template<br/>with JSON Schema]
    GPT4Model -->|Extract| ExtractTemplate
    
    ExtractTemplate --> DetectSlots[Detect Variable Slots<br/>Regex + AI Analysis]
    DetectSlots --> StoreTemplate[Store Template v1.0.0<br/>in PostgreSQL]
    StoreTemplate --> StoreSlots[Store Template Slots<br/>in PostgreSQL]
    
    %% Versioning Flow
    StoreTemplate --> Versioning[Template Versioning Service]
    Versioning --> ChangeDetect{Change Detected?}
    ChangeDetect -->|Major| MajorVer[Major Version<br/>2.0.0]
    ChangeDetect -->|Minor| MinorVer[Minor Version<br/>1.1.0]
    ChangeDetect -->|Patch| PatchVer[Patch Version<br/>1.0.1]
    
    MajorVer --> EvolutionEvent[Record Evolution Event]
    MinorVer --> EvolutionEvent
    PatchVer --> EvolutionEvent
    
    %% Evolution Tracking
    EvolutionEvent --> EvolutionService[Evolution Tracking Service]
    EvolutionService --> StoreEvolution[Store Event<br/>in PostgreSQL]
    
    %% Drift Detection Flow
    StoreEvolution --> DriftCheck[Drift Detection Service<br/>Periodic Check]
    DriftCheck -->|Get Recent Prompts| QdrantDB
    QdrantDB -->|Prompts| DriftAnalysis["o1-mini<br/>Reasoning Model"]
    DriftAnalysis -->|Analysis| DriftDecision{Drift Detected?}
    DriftDecision -->|Yes| RecordDrift[Record Drift Event]
    DriftDecision -->|No| NoAction1[No Action]
    RecordDrift --> StoreEvolution
    
    %% Family Tracking Flow
    StoreCluster --> FamilyMapping[Family Tracking Service]
    FamilyMapping --> FamilyCheck[Check Family Relationships]
    FamilyCheck -->|Complex Decision| ReasoningModel["o1-mini<br/>Split/Merge Analysis"]
    ReasoningModel -->|Decision| FamilyAction{Split/Merge?}
    FamilyAction -->|Split| CreateChild[Create Child Family]
    FamilyAction -->|Merge| MergeFam[Merge Families]
    FamilyAction -->|None| NoAction2[No Action]
    
    CreateChild --> StoreFamily[Store Family Mapping<br/>in PostgreSQL]
    MergeFam --> StoreFamily
    
    %% Return Flow
    ReturnResult --> Response[API Response]
    StoreSlots --> Response
    StoreEvolution --> Response
    Response --> Frontend
    Response --> ExternalAPI
    
    %% View Endpoints Flow
    Frontend -->|GET /clusters| ViewClusters[Clusters View Endpoint]
    Frontend -->|GET /templates| ViewTemplates[Templates View Endpoint]
    Frontend -->|GET /evolution| ViewEvolution[Evolution View Endpoint]
    
    ViewClusters -->|Query| PostgreSQL[(PostgreSQL<br/>Metadata)]
    ViewTemplates -->|Query| PostgreSQL
    ViewEvolution -->|Query| PostgreSQL
    
    PostgreSQL -->|Data| RenderView[Render HTML Template]
    RenderView --> Frontend
    
    %% Observability
    Logging -->|Logs| CloudWatch[CloudWatch<br/>Structured Logs]
    Pipeline -->|Metrics| Prometheus[Prometheus<br/>Metrics Collection]
    Prometheus -->|Endpoint| MetricsAPI[/metrics endpoint]
    
    %% Styling
    classDef entry fill:#e3f2fd,stroke:#0277bd,stroke-width:3px
    classDef middleware fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef processing fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef ai fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef decision fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    
    class Frontend,Dataset,ExternalAPI,Start entry
    class Auth,RateLimit,Logging middleware
    class Moderation,EmbeddingStep,ClusteringStep,CanonicalStep,Versioning,EvolutionService,DriftCheck,FamilyMapping processing
    class PostgreSQL,QdrantDB,Redis storage
    class PortkeyMod,PortkeyEmbed,ClaudeModel,GPT4Model,DriftAnalysis,ReasoningModel ai
    class ModCheck,EmbedCache,ClusterDecision,CodeCheck,ChangeDetect,DriftDecision,FamilyAction decision
```

## Complete Data Flow Diagram

```mermaid
flowchart LR
    subgraph Input["📥 INPUT LAYER"]
        I1[Frontend Form<br/>User Prompt]
        I2[Dataset Folder<br/>Batch Files]
        I3[API Clients<br/>REST API]
    end
    
    subgraph API["🌐 API LAYER"]
        A1[FastAPI Application]
        A2[Middleware Stack<br/>Auth, Rate Limit, Logging]
        A3[Route Handlers<br/>/api/v1/*]
    end
    
    subgraph Process["⚙️ PROCESSING LAYER"]
        P1[Moderation<br/>Content Safety]
        P2[Embedding<br/>Vector Generation]
        P3[Clustering<br/>Similarity Matching]
        P4[Canonicalization<br/>Template Extraction]
        P5[Versioning<br/>Semantic Versioning]
        P6[Evolution<br/>Change Tracking]
        P7[Drift Detection<br/>Semantic Shift]
        P8[Family Tracking<br/>Relationships]
    end
    
    subgraph Storage["💾 STORAGE LAYER"]
        S1[(PostgreSQL<br/>Structured Data)]
        S2[(Qdrant<br/>Vector Embeddings)]
        S3[(Redis<br/>Cache Layer)]
    end
    
    subgraph AI["🤖 AI MODELS"]
        M1["text-moderation-latest"]
        M2["text-embedding-3-small"]
        M3["gpt-4o"]
        M4["claude-3-5-sonnet"]
        M5["o1-mini"]
    end
    
    subgraph Output["📤 OUTPUT LAYER"]
        O1[Clusters View<br/>/clusters]
        O2[Templates View<br/>/templates]
        O3[Evolution View<br/>/evolution]
        O4[API Responses<br/>JSON]
    end
    
    I1 --> A1
    I2 --> A1
    I3 --> A1
    
    A1 --> A2
    A2 --> A3
    
    A3 --> P1
    P1 --> M1
    M1 --> P2
    
    P2 --> S3
    P2 --> M2
    M2 --> P3
    
    P3 --> S2
    P3 --> S1
    P3 --> P4
    
    P4 --> P5
    P4 --> M3
    P4 --> M4
    P5 --> P6
    
    P6 --> S1
    P6 --> P7
    P7 --> M5
    P7 --> P8
    P8 --> M5
    
    S1 --> O1
    S1 --> O2
    S1 --> O3
    S2 --> O1
    A3 --> O4
    
    style Input fill:#e1f5ff
    style API fill:#f3e5f5
    style Process fill:#e8f5e9
    style Storage fill:#fff3e0
    style AI fill:#fce4ec
    style Output fill:#e0f2f1
```

## Detailed Processing Pipeline

```mermaid
sequenceDiagram
    autonumber
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
    
    Note over API: Middleware: Auth, Rate Limit, Logging
    
    API->>Moderation: Check Content Safety
    Moderation->>PortkeyAI: text-moderation-latest
    PortkeyAI-->>Moderation: Moderation Result
    
    alt Content Flagged
        Moderation-->>API: Reject (400)
        API-->>Frontend: Error Response
    else Content Safe
        Moderation->>Embedding: Generate Embedding
        
        Embedding->>Redis: Check Cache (hash key)
        alt Cache Hit
            Redis-->>Embedding: Return Cached Vector
        else Cache Miss
            Embedding->>PortkeyAI: text-embedding-3-small
            PortkeyAI-->>Embedding: Embedding Vector [1536 dim]
            Embedding->>Redis: Store in Cache (TTL: 7 days)
        end
        
        Embedding->>PostgreSQL: INSERT INTO prompts
        Embedding->>Clustering: Assign to Cluster
        
        Clustering->>Qdrant: Search Similar Vectors (ANN)
        Qdrant-->>Clustering: Top K Candidates
        
        Clustering->>Redis: Check Similarity Cache
        alt Cache Hit
            Redis-->>Clustering: Cached Similarity Score
        else Cache Miss
            Clustering->>Clustering: Calculate Cosine Similarity
            Clustering->>Redis: Store Score (TTL: 1 day)
        end
        
        alt Similarity > 0.85
            Clustering->>PostgreSQL: INSERT INTO cluster_assignments
            Clustering->>Qdrant: Upsert Vector with cluster_id
            Clustering-->>API: Assignment Result
        else No Match
            Clustering->>PostgreSQL: INSERT INTO clusters
            Clustering->>Qdrant: Upsert Vector
            Clustering->>Canonicalization: Extract Template
            
            Canonicalization->>Clustering: Get Cluster Prompts
            Clustering-->>Canonicalization: Prompt List
            
            Canonicalization->>Canonicalization: Detect Code Content
            alt Code Heavy
                Canonicalization->>PortkeyAI: claude-3-5-sonnet
            else General
                Canonicalization->>PortkeyAI: gpt-4o
            end
            
            PortkeyAI-->>Canonicalization: Template + Slots (JSON)
            Canonicalization->>PostgreSQL: INSERT INTO canonical_templates
            Canonicalization->>PostgreSQL: INSERT INTO template_slots
            Canonicalization->>PostgreSQL: INSERT INTO evolution_events (CREATED)
            
            Canonicalization-->>Clustering: Template Created
            Clustering-->>API: Assignment + Template Result
        end
        
        API-->>Frontend: Success Response
        Frontend-->>User: Show Result
    end
```

## Dataset Processing Flow

```mermaid
flowchart TD
    Start([Start Dataset Processing]) --> ListFiles[List Files in Dataset/]
    ListFiles --> FileList{Files Found?}
    FileList -->|No| NoFiles[Return: No Files]
    FileList -->|Yes| ProcessFile[For Each File]
    
    ProcessFile --> CheckCheckpoint[Check Redis Checkpoint]
    CheckCheckpoint --> CheckpointExists{Checkpoint Exists?}
    CheckpointExists -->|Yes| SkipProcessed[Skip Processed Prompts]
    CheckpointExists -->|No| StartFromBeginning[Start from Beginning]
    
    SkipProcessed --> ReadFile[Read File<br/>JSON/CSV/TXT/JSONL]
    StartFromBeginning --> ReadFile
    
    ReadFile --> ExtractPrompts[Extract Prompts<br/>Generator Pattern]
    ExtractPrompts --> BatchProcess[Process in Batches<br/>Default: 100]
    
    BatchProcess --> ProcessPrompt[For Each Prompt]
    ProcessPrompt --> Pipeline[Full Processing Pipeline<br/>Moderation → Embedding → Clustering]
    
    Pipeline --> SaveCheckpoint[Save Checkpoint<br/>Redis: Last Processed Index]
    SaveCheckpoint --> MorePrompts{More Prompts?}
    MorePrompts -->|Yes| ProcessPrompt
    MorePrompts -->|No| NextFile{More Files?}
    
    NextFile -->|Yes| ProcessFile
    NextFile -->|No| CommitDB[Commit All Changes<br/>PostgreSQL]
    
    CommitDB --> CalculateStats[Calculate Statistics<br/>Files, Prompts, Clusters, Templates]
    CalculateStats --> ReturnSummary[Return Summary]
    ReturnSummary --> End([End])
    
    style Start fill:#e3f2fd
    style End fill:#e8f5e9
    style Pipeline fill:#fff3e0
```

## View Endpoints Flow

```mermaid
flowchart LR
    User[User] -->|Navigate| Frontend[Frontend]
    
    Frontend -->|GET /clusters| ClustersAPI[Clusters API]
    Frontend -->|GET /templates| TemplatesAPI[Templates API]
    Frontend -->|GET /evolution| EvolutionAPI[Evolution API]
    
    ClustersAPI --> QueryClusters[Query PostgreSQL<br/>SELECT clusters + assignments]
    TemplatesAPI --> QueryTemplates[Query PostgreSQL<br/>SELECT templates + slots]
    EvolutionAPI --> QueryEvolution[Query PostgreSQL<br/>SELECT evolution_events]
    
    QueryClusters --> JoinPrompts[JOIN prompts<br/>Get prompt count]
    QueryTemplates --> JoinSlots[JOIN template_slots]
    QueryEvolution --> JoinTemplates[JOIN canonical_templates]
    
    JoinPrompts --> RenderClusters[Render clusters.html]
    JoinSlots --> RenderTemplates[Render templates.html]
    JoinTemplates --> RenderEvolution[Render evolution.html]
    
    RenderClusters --> Frontend
    RenderTemplates --> Frontend
    RenderEvolution --> Frontend
    
    Frontend -->|Display| User
    
    style User fill:#e3f2fd
    style Frontend fill:#f3e5f5
    style QueryClusters,QueryTemplates,QueryEvolution fill:#fff3e0
```

## Component Interaction Matrix

```mermaid
graph TB
    subgraph Clients["Client Layer"]
        PortkeyClient[Portkey AI Client<br/>Retry Logic, Virtual Keys]
        RedisClient[Redis Client<br/>Async Operations]
        QdrantClient[Qdrant Client<br/>Vector Operations]
    end
    
    subgraph Services["Service Layer"]
        ModerationSvc[Moderation Service]
        EmbeddingSvc[Embedding Service]
        ClusteringSvc[Clustering Service]
        CanonicalSvc[Canonicalization Service]
        SimilaritySvc[Similarity Service]
        EvolutionSvc[Evolution Service]
        DriftSvc[Drift Detection Service]
        FamilySvc[Family Tracking Service]
        ReasoningSvc[Reasoning Service]
        VersioningSvc[Template Versioning Service]
    end
    
    ModerationSvc --> PortkeyClient
    EmbeddingSvc --> PortkeyClient
    EmbeddingSvc --> RedisClient
    ClusteringSvc --> SimilaritySvc
    ClusteringSvc --> QdrantClient
    ClusteringSvc --> RedisClient
    SimilaritySvc --> QdrantClient
    CanonicalSvc --> PortkeyClient
    CanonicalSvc --> VersioningSvc
    VersioningSvc --> EvolutionSvc
    DriftSvc --> PortkeyClient
    DriftSvc --> EvolutionSvc
    FamilySvc --> PortkeyClient
    FamilySvc --> ReasoningSvc
    ReasoningSvc --> PortkeyClient
```

## Database Operations Flow

```mermaid
flowchart TD
    PromptIngestion[Prompt Ingestion] --> StorePrompt[INSERT INTO prompts<br/>id, content, moderation_status]
    
    StorePrompt --> ClusterAssignment[Cluster Assignment]
    ClusterAssignment -->|New Cluster| CreateCluster[INSERT INTO clusters<br/>id, name, similarity_threshold]
    ClusterAssignment -->|Existing Cluster| AssignCluster[INSERT INTO cluster_assignments<br/>prompt_id, cluster_id, similarity_score]
    
    CreateCluster --> TemplateExtraction[Template Extraction]
    TemplateExtraction --> StoreTemplate[INSERT INTO canonical_templates<br/>cluster_id, template_content, version]
    StoreTemplate --> StoreSlots[INSERT INTO template_slots<br/>template_id, slot_name, slot_type]
    
    StoreTemplate --> VersionCheck[Version Check]
    VersionCheck -->|Change Detected| StoreEvolution[INSERT INTO evolution_events<br/>template_id, event_type, versions]
    
    CreateCluster --> FamilyMapping[Family Mapping]
    FamilyMapping --> StoreFamily[INSERT INTO prompt_families<br/>name, description, parent_id]
    StoreFamily --> MapFamily[INSERT INTO family_cluster_mappings<br/>family_id, cluster_id]
    
    StorePrompt --> StoreVector[Store in Qdrant<br/>Point: id, vector, payload]
    StoreVector --> StoreCache[Store in Redis<br/>Key: embedding hash, Value: vector]
    
    style StorePrompt fill:#e3f2fd
    style CreateCluster fill:#e8f5e9
    style StoreTemplate fill:#fff3e0
    style StoreEvolution fill:#fce4ec
```

