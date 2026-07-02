"""
Industry-grade ATS scoring engine that computes:
1. Keyword match density (30% weight) against a pre-compiled skills database
2. Semantic cosine similarity using embeddings (30% weight)
3. Target title and role fit (10% weight)
4. Recruiter Quality & Impact Audit (30% weight) checking active verbs, metrics, and bullet depth
"""

import re
import numpy as np
from chromadb.utils import embedding_functions

# Initialize the default embedding function (SentenceTransformers)
emb_fn = embedding_functions.DefaultEmbeddingFunction()

# Pre-compiled database of technical skills, languages, frameworks, methodologies, and concepts
TECH_WORDS = {
    # Languages
    "python", "javascript", "typescript", "golang", "go", "java", "cpp", "c++", "c#", "rust", "scala", "ruby", "php", "bash", "shell", "sql", "nosql", "html", "css", "r", "julia", "swift", "kotlin", "objective-c",
    
    # ML/AI/Data Science
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy", "scipy", "transformers", "huggingface", "langchain", "llama", "openai", "anthropic", "spacy", "nltk", "gensim", "xgboost", "lightgbm", "opencv", "llm", "llms", "rag", "vector database", "chromadb", "pinecone", "qdrant", "milvus", "weaviate", "semantic search", "embeddings", "deep learning", "machine learning", "computer vision", "nlp", "neural networks", "reinforcement learning", "data science", "prompt engineering", "fine-tuning", "finetuning", "rlhf", "model deployment", "model monitoring", "bert", "gpt", "reinforcement",
    
    # Web / Backend / Frontend
    "django", "flask", "fastapi", "express", "next.js", "nextjs", "react", "react.js", "reactjs", "angular", "vue", "vue.js", "nodejs", "node.js", "node", "svelte", "spring", "springboot", "rails", "gin", "fiber", "echo", "uvicorn", "gunicorn", "graphql", "rest api", "restful api", "grpc", "microservices", "websockets", "html5", "css3", "tailwind", "bootstrap",
    
    # Databases / Messaging / Big Data
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "cassandra", "elasticsearch", "dynamodb", "mariadb", "oracle", "redshift", "snowflake", "clickhouse", "bigquery", "presto", "hive", "spark", "hadoop", "kafka", "rabbitmq", "celery", "airflow", "db2",
    
    # Cloud / DevOps / Infra
    "aws", "amazon web services", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins", "gitlab ci", "github actions", "ci/cd", "cicd", "prometheus", "grafana", "elk", "splunk", "datadog", "nginx", "apache", "git", "linux", "unix", "bash", "ec2", "s3", "lambda", "ecs", "eks", "fargate", "cloudformation",
    
    # Core Engineering Concepts & Methodologies
    "agile", "scrum", "kanban", "oop", "design patterns", "unit testing", "tdd", "system design", "scalability", "high availability", "concurrency", "multithreading", "load balancing", "api gateway", "distributed systems", "distributed training", "parallel processing", "data structures", "algorithms"
}

STRONG_VERBS = {
    "spearheaded", "architected", "engineered", "designed", "optimized", "scaled", 
    "built", "developed", "implemented", "pioneered", "led", "managed", "refactored", 
    "automated", "formulated", "created", "deployed", "launched", "accelerated", 
    "overhauled", "structured", "customized", "integrated", "orchestrated"
}

def tokenize(text: str) -> set[str]:
    """Extracts meaningful terms and phrase bigrams for comparison."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#./_-]{2,}", text.lower())
    tokens = set(words)
    word_list = [w for w in words if len(w) > 3]
    for i in range(len(word_list) - 1):
        tokens.add(f"{word_list[i]} {word_list[i+1]}")
    return tokens


def calculate_semantic_similarity(text_a: str, text_b: str) -> float:
    """Computes semantic cosine similarity between two texts using Chroma embeddings."""
    try:
        emb_a = np.array(emb_fn([text_a])[0])
        emb_b = np.array(emb_fn([text_b])[0])
        
        dot_product = np.dot(emb_a, emb_b)
        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.5
            
        similarity = dot_product / (norm_a * norm_b)
        # Cosine similarity for resumes usually ranges from 0.40 to 0.60. Scale this range to [0, 1].
        scaled = (similarity - 0.40) / 0.20
        return float(min(1.0, max(0.0, scaled)))
    except Exception as e:
        print(f"[ATS Scorer] Semantic similarity calculation failed: {e}")
        return 0.8  # Safe default fallback


def calculate_keyword_match(resume_text: str, jd_text: str) -> tuple[int, list[str], list[str]]:
    """Calculates keyword density overlap score against tech skills DB."""
    jd_tokens = tokenize(jd_text)
    res_tokens = tokenize(resume_text)
    
    # Filter tokens to only include tech keywords
    jd_keywords = {t for t in jd_tokens if t in TECH_WORDS}
    res_keywords = {t for t in res_tokens if t in TECH_WORDS}
    
    if not jd_keywords:
        # Fallback to standard token filter if no keywords matched the DB
        STOP = {"the", "and", "for", "with", "this", "that", "will", "have",
                "are", "you", "your", "our", "their", "from", "not", "but",
                "has", "can", "all", "any", "also", "more", "such", "been"}
        jd_keywords = {t for t in jd_tokens if t not in STOP and len(t) > 3}
        res_keywords = res_tokens
        
    matched = sorted(list(jd_keywords & res_keywords))
    missing = sorted(list(jd_keywords - res_keywords))
    
    phrase_matches = sum(1 for m in matched if " " in m)
    word_matches = sum(1 for m in matched if " " not in m)
    
    weighted_match = word_matches + (phrase_matches * 2)
    total_weighted = len([t for t in jd_keywords if " " not in t]) + \
                     len([t for t in jd_keywords if " " in t]) * 2
                     
    score = int((weighted_match / max(total_weighted, 1)) * 100)
    return min(100, score), matched, missing


def calculate_title_fit(resume_text: str, target_title: str) -> int:
    """Evaluates how closely the candidate's previous titles match the target title."""
    if not target_title:
        return 80
        
    # Check if target title matches anywhere in the professional summary
    summary_match = re.search(re.escape(target_title), resume_text, re.IGNORECASE)
    
    job_headers = re.findall(r"^[^\n•|]+?\|[^\n•|]+?\|[^\n•|]+?$", resume_text, re.MULTILINE)
    candidate_titles = []
    for header in job_headers:
        parts = header.split("|")
        if len(parts) >= 2:
            candidate_titles.append(parts[1].strip().lower())
            
    if not candidate_titles:
        return 80 if summary_match else 50
        
    target_words = set(re.findall(r"\w+", target_title.lower()))
    max_fit = 0
    
    for title in candidate_titles:
        title_words = set(re.findall(r"\w+", title))
        overlap = title_words & target_words
        if not target_words:
            continue
        fit = int((len(overlap) / len(target_words)) * 100)
        if fit > max_fit:
            max_fit = fit
            
    # If the target title is explicitly in the professional summary, we boost the title score
    boosted_fit = max_fit
    if summary_match:
        boosted_fit = max(boosted_fit, 90)
        
    return min(100, max(50, boosted_fit))


def calculate_quality_audit(resume_text: str) -> dict:
    """
    Performs a recruiter quality audit checking for metric density, verb usage, and bullet depth.
    Returns a score out of 100 and breakdown metrics.
    """
    # Extract experience bullet lines
    bullets = [line.strip().lstrip("•-*· ").strip() for line in resume_text.splitlines() if line.strip().startswith(("•", "-", "*", "·"))]
    
    if not bullets:
        return {"score": 40, "metric_density": 0, "verb_density": 0, "depth_density": 0}
        
    metric_count = 0
    verb_count = 0
    depth_count = 0
    
    for b in bullets:
        # Check depth (character length >= 45)
        if len(b) >= 45:
            depth_count += 1
            
        # Check metrics (contains a number)
        if re.search(r"\b\d+\b|%|\d+x|\d+k|\d+m", b, re.IGNORECASE):
            metric_count += 1
            
        # Check starting verb
        first_word = re.findall(r"^[a-zA-Z]+", b)
        if first_word and first_word[0].lower() in STRONG_VERBS:
            verb_count += 1
            
    total = len(bullets)
    metric_pct = int((metric_count / total) * 100)
    verb_pct = int((verb_count / total) * 100)
    depth_pct = int((depth_count / total) * 100)
    
    # Composite audit score (40% metrics, 40% verbs, 20% depth)
    audit_score = min(100, int((metric_pct * 0.4) + (verb_pct * 0.4) + (depth_pct * 0.2)))
    
    # Recruiter minimum baseline: if no metrics are present, penalize heavily
    if metric_count == 0:
        audit_score = max(0, audit_score - 30)
        
    return {
        "score": audit_score,
        "metric_density": metric_pct,
        "verb_density": verb_pct,
        "depth_density": depth_pct
    }


def calculate_industry_score(resume_text: str, jd_text: str, target_title: str = "") -> dict:
    """
    Computes a composite industry-grade ATS score with a Recruiter Quality Audit.
    Returns: { score: int, matched: list[str], missing: list[str], breakdown: dict }
    """
    kw_score, matched, missing = calculate_keyword_match(resume_text, jd_text)
    
    semantic_sim = calculate_semantic_similarity(resume_text, jd_text)
    semantic_score = int(semantic_sim * 100)
    
    title_score = calculate_title_fit(resume_text, target_title)
    
    audit_res = calculate_quality_audit(resume_text)
    
    # Weights: 30% Keywords, 30% Semantic Embeddings, 10% Title Fit, 30% Quality Audit
    composite = (kw_score * 0.3) + (semantic_score * 0.3) + (title_score * 0.1) + (audit_res["score"] * 0.3)
    final_score = min(100, max(0, int(composite)))
    
    return {
        "score": final_score,
        "matched": matched,
        "missing": missing,
        "breakdown": {
            "keyword_density": kw_score,
            "semantic_similarity": semantic_score,
            "title_fit": title_score,
            "quality_audit": audit_res["score"]
        }
    }
