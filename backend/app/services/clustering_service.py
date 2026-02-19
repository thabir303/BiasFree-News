"""
Article Clustering Service — Improved Multi-Stage Pipeline.

Detects when multiple newspapers cover the SAME event using:
  Stage 1: Category-aware grouping (only compare articles in same category)
  Stage 2: Title similarity (strong signal — weighted 0.4)
  Stage 3: Content similarity (supporting signal — weighted 0.6)
  Stage 4: Combined similarity with Agglomerative Clustering

Then generates extractive unified summaries using sumy (LSA + TextRank).
"""
import logging
import re
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.database.models import Article, ArticleCluster

logger = logging.getLogger(__name__)

# ── Singleton model holder ──────────────────────────────────────────
_model: Optional[SentenceTransformer] = None

# ── Tuned thresholds ────────────────────────────────────────────────
# Title similarity threshold (titles matching ≥ this are almost certainly same event)
TITLE_SIM_THRESHOLD = 0.80
# Combined similarity threshold for clustering
COMBINED_SIM_THRESHOLD = 0.58
# Weights for combined similarity
TITLE_WEIGHT = 0.35
CONTENT_WEIGHT = 0.65
# Weight given to keyword overlap when building the effective similarity
KEYWORD_WEIGHT = 0.50        # Effective = (1 - KW_W) * embedding_sim  +  KW_W * kw_overlap
EMBEDDING_WEIGHT = 1 - KEYWORD_WEIGHT
# Distance threshold for AgglomerativeClustering
DISTANCE_THRESHOLD = 1 - COMBINED_SIM_THRESHOLD
# Minimum content length (characters) to consider an article valid
MIN_CONTENT_LENGTH = 80
# Max content chars for embedding (more context = better matching)
MAX_CONTENT_CHARS = 2000


def get_embedding_model() -> SentenceTransformer:
    """
    Get or load the multilingual sentence transformer model.
    Uses singleton pattern — model loads once (~120 MB, ~3 s) then reuses.
    """
    global _model
    if _model is None:
        logger.info("Loading paraphrase-multilingual-MiniLM-L12-v2 model …")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        logger.info("Embedding model loaded successfully (384-dim, multilingual)")
    return _model


# ── Bengali text helpers ────────────────────────────────────────────
_BN_PUNCTUATION = re.compile(r"[।,;:\"'!?—\-–\(\)\[\]{}«»\u200c\u200d]+")
_MULTI_SPACE = re.compile(r"\s+")

# Common Bengali stop-phrases that don't carry topical meaning
_BN_STOPWORDS = {
    "এবং", "ও", "এই", "এর", "তার", "যে", "সে", "তা", "একটি", "হয়",
    "হয়েছে", "করে", "করা", "হচ্ছে", "বলে", "থেকে", "নিয়ে", "জন্য",
    "পরে", "আগে", "মধ্যে", "সাথে", "দিয়ে", "কিন্তু", "তবে", "যখন",
    "তখন", "আর", "না", "নেই", "হবে", "করেছে", "করেন", "বলেন",
    "জানান", "জানিয়েছেন", "প্রতিবেদক", "সংবাদদাতা", "নিজস্ব",
    "বিশেষ", "প্রতিনিধি", "ডেস্ক", "অনলাইন", "রিপোর্ট",
}


def normalize_bengali(text: str) -> str:
    """Light normalisation: strip reporter tags, punctuation, extra spaces."""
    text = _BN_PUNCTUATION.sub(" ", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    return text


def clean_for_embedding(text: str) -> str:
    """Remove stop-words that add noise to embeddings."""
    words = text.split()
    return " ".join(w for w in words if w not in _BN_STOPWORDS)


def extract_keywords(text: str, min_word_len: int = 2) -> set:
    """
    Extract meaningful keywords from Bengali text.
    Removes stop-words and very short tokens,
    returns a set of unique content words.
    """
    text = normalize_bengali(text)
    words = text.split()
    return {
        w for w in words
        if w not in _BN_STOPWORDS and len(w) >= min_word_len
    }


def keyword_overlap_score(text_a: str, text_b: str) -> float:
    """
    Compute Jaccard-like keyword overlap between two texts.
    Returns value in [0, 1].  Higher = more shared keywords.
    """
    kw_a = extract_keywords(text_a)
    kw_b = extract_keywords(text_b)
    if not kw_a or not kw_b:
        return 0.0
    intersection = kw_a & kw_b
    union = kw_a | kw_b
    return len(intersection) / len(union) if union else 0.0


# Minimum keyword overlap required to confirm a cluster pair
MIN_KEYWORD_OVERLAP = 0.12


class ClusteringService:
    """
    Improved clustering with category-aware multi-stage similarity.

    Pipeline:
    1. Fetch unclustered articles from DB (with time-window)
    2. Group by category (only compare within same category)
    3. Generate SEPARATE title embeddings and content embeddings
    4. Compute combined similarity = 0.45·title_sim + 0.55·content_sim
    5. Apply Agglomerative Clustering (complete linkage, distance_threshold)
    6. Post-filter: require ≥2 unique sources per cluster (cross-newspaper)
    7. Post-filter: verify keyword overlap (Jaccard ≥ 0.12)
    8. Generate extractive unified summary via sumy (LSA + TextRank)
    9. Store ArticleCluster records
    """

    def __init__(self, db: Session):
        self.db = db
        self.model = get_embedding_model()

    # ── Embedding helpers ───────────────────────────────────────────

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate a 384-dim embedding for a single text."""
        return self.model.encode(text, show_progress_bar=False)

    def generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Batch encoding for efficiency."""
        return self.model.encode(texts, show_progress_bar=False, batch_size=32)

    def _get_title_text(self, article: Article) -> str:
        """
        Extract and clean title for embedding.
        Title is the strongest signal for same-event detection.
        """
        title = article.title or ""
        title = normalize_bengali(title)
        return clean_for_embedding(title) if title else ""

    def _get_content_text(self, article: Article) -> str:
        """
        Extract content — use more text (up to 2000 chars) for richer context.
        Prepend title once so the embedding captures the topic.
        """
        title = normalize_bengali(article.title or "")
        content = normalize_bengali((article.original_content or "")[:MAX_CONTENT_CHARS])
        combined = f"{title} {content}".strip()
        return clean_for_embedding(combined) if combined else ""

    # ── Main clustering pipeline ────────────────────────────────────

    def cluster_articles(
        self,
        days_back: int = 3,
        re_cluster_all: bool = False,
        auto_summarize: bool = True,
    ) -> Dict:
        """
        Main clustering pipeline — clusters articles within a time window.

        Args:
            days_back: How many days back to look (default 3)
            re_cluster_all: Re-cluster ALL articles (removes existing cluster_id)
            auto_summarize: Automatically generate unified summaries for new clusters

        Returns:
            Statistics dict
        """
        started_at = datetime.utcnow()
        logger.info(
            f"Starting article clustering (days_back={days_back}, "
            f"re_cluster_all={re_cluster_all})"
        )

        # 1. Fetch articles ──────────────────────────────────────────
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        if re_cluster_all:
            articles = (
                self.db.query(Article)
                .filter(Article.created_at >= cutoff_date)
                .all()
            )
            # Clear existing cluster assignments
            for a in articles:
                a.cluster_id = None
            # Delete old clusters in range
            self.db.query(ArticleCluster).filter(
                ArticleCluster.created_at >= cutoff_date
            ).delete(synchronize_session="fetch")
            self.db.flush()
        else:
            articles = (
                self.db.query(Article)
                .filter(
                    Article.cluster_id.is_(None),
                    Article.created_at >= cutoff_date,
                )
                .all()
            )

        # Filter out articles with too little content
        articles = [
            a for a in articles
            if a.original_content and len(a.original_content) >= MIN_CONTENT_LENGTH
        ]

        if len(articles) < 2:
            logger.info(f"Not enough articles to cluster ({len(articles)} found, need ≥2)")
            return {
                "status": "skipped",
                "reason": f"Only {len(articles)} valid unclustered articles (need ≥2)",
                "articles_checked": len(articles),
                "clusters_created": 0,
                "articles_clustered": 0,
                "time_seconds": (datetime.utcnow() - started_at).total_seconds(),
            }

        logger.info(f"Found {len(articles)} articles to cluster")

        # 2. Group by category ───────────────────────────────────────
        category_groups: Dict[str, List[int]] = defaultdict(list)
        for idx, a in enumerate(articles):
            cat = (a.category or "unknown").strip()
            category_groups[cat].append(idx)

        logger.info(
            f"Category groups: { {k: len(v) for k, v in category_groups.items()} }"
        )

        # 3. Generate separate title & content embeddings ────────────
        title_texts = [self._get_title_text(a) for a in articles]
        content_texts = [self._get_content_text(a) for a in articles]

        logger.info("Generating title embeddings …")
        title_embeddings = self.generate_embeddings_batch(title_texts)

        logger.info("Generating content embeddings …")
        content_embeddings = self.generate_embeddings_batch(content_texts)

        # Store content embeddings in DB for later retrieval
        for article, emb in zip(articles, content_embeddings):
            article.embedding = emb.tobytes()

        logger.info(
            f"Embeddings ready — titles: {title_embeddings.shape}, "
            f"content: {content_embeddings.shape}"
        )

        # 4. Cluster within each category ────────────────────────────
        all_clusters_created = 0
        all_articles_clustered = 0
        all_singletons = 0

        for cat, indices in category_groups.items():
            if len(indices) < 2:
                all_singletons += len(indices)
                continue

            idx_arr = np.array(indices)
            cat_title_embs = title_embeddings[idx_arr]
            cat_content_embs = content_embeddings[idx_arr]

            # Pairwise cosine similarities for title & content
            title_sim = cosine_similarity(cat_title_embs)
            content_sim = cosine_similarity(cat_content_embs)

            # Embedding-only combined similarity
            embedding_sim = TITLE_WEIGHT * title_sim + CONTENT_WEIGHT * content_sim
            embedding_sim = np.clip(embedding_sim, 0.0, 1.0)

            # Title-boost: if title sim ≥ TITLE_SIM_THRESHOLD, push embedding_sim up
            title_boost_mask = title_sim >= TITLE_SIM_THRESHOLD
            embedding_sim = np.where(
                title_boost_mask,
                np.maximum(embedding_sim, (title_sim + embedding_sim) / 2),
                embedding_sim,
            )

            # ── Keyword overlap matrix (lexical confirmation) ───────
            # Bengali embeddings give very high similarity (~0.97+) for
            # unrelated articles in the same category.  Keyword overlap
            # acts as a lexical anchor: pairs that share no keywords are
            # almost certainly about different events.
            n_cat = len(indices)
            cat_kw_texts = [
                f"{articles[indices[k]].title or ''} "
                f"{(articles[indices[k]].original_content or '')[:1000]}"
                for k in range(n_cat)
            ]
            kw_matrix = np.zeros((n_cat, n_cat), dtype=np.float32)
            for ii in range(n_cat):
                kw_matrix[ii, ii] = 1.0
                for jj in range(ii + 1, n_cat):
                    kw_score = keyword_overlap_score(cat_kw_texts[ii], cat_kw_texts[jj])
                    kw_matrix[ii, jj] = kw_score
                    kw_matrix[jj, ii] = kw_score

            # ── Effective similarity = blend of embedding + keyword ──
            combined_sim = EMBEDDING_WEIGHT * embedding_sim + KEYWORD_WEIGHT * kw_matrix
            combined_sim = np.clip(combined_sim, 0.0, 1.0)
            np.fill_diagonal(combined_sim, 1.0)

            logger.info(
                f"  [{cat}] embedding_sim range=[{embedding_sim[np.triu_indices(n_cat, k=1)].min():.3f}, "
                f"{embedding_sim[np.triu_indices(n_cat, k=1)].max():.3f}], "
                f"kw_overlap range=[{kw_matrix[np.triu_indices(n_cat, k=1)].min():.3f}, "
                f"{kw_matrix[np.triu_indices(n_cat, k=1)].max():.3f}], "
                f"effective_sim range=[{combined_sim[np.triu_indices(n_cat, k=1)].min():.3f}, "
                f"{combined_sim[np.triu_indices(n_cat, k=1)].max():.3f}]"
            )

            # Distance matrix
            distance_matrix = 1 - combined_sim
            np.fill_diagonal(distance_matrix, 0.0)
            distance_matrix = np.clip(distance_matrix, 0.0, None)

            # Agglomerative clustering with *complete* linkage
            # (every pair in the cluster must satisfy threshold → tighter clusters)
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=DISTANCE_THRESHOLD,
                metric="precomputed",
                linkage="complete",
            )
            labels = clustering.fit_predict(distance_matrix)

            # Group by label
            label_groups: Dict[int, List[int]] = defaultdict(list)
            for local_idx, label in enumerate(labels):
                label_groups[label].append(local_idx)

            # 5. Create clusters (only multi-article groups) ─────────
            for label, local_indices in label_groups.items():
                if len(local_indices) < 2:
                    all_singletons += 1
                    continue

                cluster_articles = [articles[idx_arr[li]] for li in local_indices]
                cluster_title_embs = cat_title_embs[local_indices]
                cluster_content_embs = cat_content_embs[local_indices]

                # Post-filter: REQUIRE at least 2 unique sources (cross-newspaper).
                # Same-newspaper clusters are not meaningful for bias comparison.
                sources = list(set(a.source for a in cluster_articles))
                if len(sources) < 2:
                    all_singletons += len(local_indices)
                    logger.debug(
                        f"  Skipped same-source group in '{cat}': "
                        f"{len(cluster_articles)} articles from {sources}"
                    )
                    continue

                # Compute avg pairwise combined similarity
                local_combined = combined_sim[np.ix_(local_indices, local_indices)]
                triu_idx = np.triu_indices(len(local_combined), k=1)
                avg_sim = float(np.mean(local_combined[triu_idx])) if len(triu_idx[0]) > 0 else 1.0

                # Metadata
                categories = [a.category for a in cluster_articles if a.category]
                dominant_category = (
                    Counter(categories).most_common(1)[0][0] if categories else cat
                )

                # Representative article = highest avg similarity to others
                local_avg_sims = local_combined.mean(axis=1)
                rep_local_idx = int(np.argmax(local_avg_sims))
                representative = cluster_articles[rep_local_idx]

                # Cluster label = representative title
                titles = [a.title for a in cluster_articles if a.title]
                cluster_label = representative.title or (titles[0] if titles else "Untitled Cluster")

                # Create cluster record
                cluster = ArticleCluster(
                    cluster_label=cluster_label,
                    representative_title=representative.title,
                    article_count=len(cluster_articles),
                    avg_similarity=round(avg_sim, 4),
                    sources=sources,
                    category=dominant_category,
                    created_at=datetime.utcnow(),
                )
                self.db.add(cluster)
                self.db.flush()  # Get cluster.id

                for article in cluster_articles:
                    article.cluster_id = cluster.id

                all_clusters_created += 1
                all_articles_clustered += len(cluster_articles)

                logger.info(
                    f"  Cluster #{cluster.id} [{cat}]: "
                    f"{len(cluster_articles)} articles, avg_sim={avg_sim:.3f}, "
                    f"sources={sources}, cross_source={len(sources) >= 2}"
                )

                # 6. Auto-generate unified summary ──────────────────
                if auto_summarize:
                    try:
                        self._generate_unified_summary(cluster, cluster_articles)
                    except Exception as e:
                        logger.warning(
                            f"  Unified summary failed for cluster #{cluster.id}: {e}"
                        )

        self.db.commit()
        elapsed = (datetime.utcnow() - started_at).total_seconds()

        stats = {
            "status": "success",
            "articles_checked": len(articles),
            "clusters_created": all_clusters_created,
            "articles_clustered": all_articles_clustered,
            "singletons": all_singletons,
            "similarity_threshold": COMBINED_SIM_THRESHOLD,
            "title_weight": TITLE_WEIGHT,
            "content_weight": CONTENT_WEIGHT,
            "keyword_weight": KEYWORD_WEIGHT,
            "time_seconds": round(elapsed, 2),
        }

        logger.info(f"Clustering complete: {stats}")
        return stats

    # ── Extractive summarisation via sumy ───────────────────────────

    def _generate_unified_summary(
        self,
        cluster: ArticleCluster,
        cluster_articles: List[Article],
        sentences_count: int = 8,
    ) -> None:
        """
        Generate a merged extractive summary for a cluster using sumy
        (LSA + TextRank ensemble).

        Strategy:
        - Combine all article texts into one mega-document
        - Run LSA and TextRank separately
        - Take union of top sentences from both, ranked by combined score
        - Store as unified_content on the cluster record
        - Use _pick_best_headline to set unified_headline
        """
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lsa import LsaSummarizer
        from sumy.summarizers.text_rank import TextRankSummarizer
        from sumy.nlp.stemmers import Stemmer
        from sumy.utils import get_stop_words

        # ---- 1. Build mega-document with source markers ----
        mega_parts: List[str] = []
        for a in cluster_articles:
            content = (a.original_content or "").strip()
            if not content:
                continue
            # Light cleanup: remove reporter tags like "নিজস্ব প্রতিবেদক,"
            content = re.sub(
                r"^(নিজস্ব প্রতিবেদক|অনলাইন ডেস্ক|স্টাফ রিপোর্টার|বিশেষ প্রতিনিধি|প্রকাশ:)[,।\s]*",
                "",
                content,
            )
            mega_parts.append(content)

        if not mega_parts:
            return

        mega_text = "\n".join(mega_parts)

        # ---- 2. Parse with sumy (use English tokenizer — works for sentence splitting) ----
        # Bengali doesn't have a dedicated sumy tokenizer, but the plaintext parser
        # with "english" tokenizer still splits on "।" and "." correctly enough.
        try:
            parser = PlaintextParser.from_string(mega_text, Tokenizer("english"))
        except Exception:
            # Fallback: manual sentence split on Bengali danda
            parser = PlaintextParser.from_string(
                mega_text.replace("।", ". "), Tokenizer("english")
            )

        total_sentences = sum(len(p.sentences) for p in parser.document.paragraphs)
        if total_sentences == 0:
            return

        # Adaptive sentence count: at least 5, at most 12, ~30% of original
        target_count = max(5, min(sentences_count, int(total_sentences * 0.30), 12))

        # ---- 3. Run LSA ----
        try:
            lsa = LsaSummarizer()
            # Use English stemmer as fallback (it at least won't crash)
            lsa.stop_words = get_stop_words("english")
            lsa_sentences = lsa(parser.document, target_count)
        except Exception as e:
            logger.debug(f"LSA failed, falling back to TextRank only: {e}")
            lsa_sentences = []

        # ---- 4. Run TextRank ----
        try:
            tr = TextRankSummarizer()
            tr.stop_words = get_stop_words("english")
            tr_sentences = tr(parser.document, target_count)
        except Exception as e:
            logger.debug(f"TextRank failed, using LSA only: {e}")
            tr_sentences = []

        # ---- 5. Combine: union with score-based ranking ----
        # Score each sentence: +1 for appearing in LSA, +1 for TextRank
        sentence_scores: Dict[str, float] = {}
        sentence_order: Dict[str, int] = {}

        # Track original order for coherence
        order_idx = 0
        for para in parser.document.paragraphs:
            for sent in para.sentences:
                key = str(sent).strip()
                if key and key not in sentence_order:
                    sentence_order[key] = order_idx
                    order_idx += 1

        for rank, sent in enumerate(lsa_sentences):
            key = str(sent).strip()
            if not key:
                continue
            # Higher rank (earlier) → higher score
            score = 1.0 + (target_count - rank) / target_count
            sentence_scores[key] = sentence_scores.get(key, 0) + score

        for rank, sent in enumerate(tr_sentences):
            key = str(sent).strip()
            if not key:
                continue
            score = 1.0 + (target_count - rank) / target_count
            sentence_scores[key] = sentence_scores.get(key, 0) + score

        if not sentence_scores:
            # Absolute fallback: first N sentences
            all_sents = []
            for para in parser.document.paragraphs:
                for sent in para.sentences:
                    all_sents.append(str(sent).strip())
            unified = " ".join(all_sents[:target_count])
        else:
            # Sort by score descending, then by original order for coherence
            ranked = sorted(
                sentence_scores.items(),
                key=lambda x: (-x[1], sentence_order.get(x[0], 9999)),
            )
            top_sentences = [s for s, _ in ranked[:target_count]]

            # Re-order by original document order for readability
            top_sentences.sort(key=lambda s: sentence_order.get(s, 9999))
            unified = " ".join(top_sentences)

        # ---- 6. Store ----
        cluster.unified_content = unified.strip()
        cluster.unified_headline = self._pick_best_headline(cluster_articles)

        logger.info(
            f"  Unified summary for cluster #{cluster.id}: "
            f"{len(unified.split())} words, {target_count} sentences "
            f"(from {total_sentences} total)"
        )

    def _pick_best_headline(self, cluster_articles: List[Article]) -> str:
        """
        Pick the best headline from cluster articles.
        Strategy: choose the title most semantically similar to all other titles
        (i.e. the most representative / consensus headline).
        """
        titles = [a.title for a in cluster_articles if a.title]
        if not titles:
            return "শিরোনাম নেই"
        if len(titles) == 1:
            return titles[0]

        title_embs = self.generate_embeddings_batch(titles)
        sim = cosine_similarity(title_embs)
        avg_sims = sim.mean(axis=1)
        best_idx = int(np.argmax(avg_sims))
        return titles[best_idx]

    def regenerate_summary(self, cluster_id: int) -> Optional[Dict]:
        """
        Regenerate unified summary for a specific cluster.
        Useful when articles are added/removed.
        """
        cluster = (
            self.db.query(ArticleCluster)
            .filter(ArticleCluster.id == cluster_id)
            .first()
        )
        if not cluster:
            return None

        cluster_articles = (
            self.db.query(Article).filter(Article.cluster_id == cluster_id).all()
        )
        if len(cluster_articles) < 2:
            return {"error": "Cluster has fewer than 2 articles"}

        self._generate_unified_summary(cluster, cluster_articles)
        self.db.commit()

        return {
            "cluster_id": cluster.id,
            "unified_headline": cluster.unified_headline,
            "unified_content": cluster.unified_content,
            "article_count": len(cluster_articles),
        }

    def get_cluster_detail(self, cluster_id: int) -> Optional[Dict]:
        """Get detailed information about a specific cluster with all its articles."""
        cluster = self.db.query(ArticleCluster).filter(ArticleCluster.id == cluster_id).first()
        if not cluster:
            return None

        articles = self.db.query(Article).filter(Article.cluster_id == cluster_id).all()

        # Compute pairwise similarities if embeddings exist
        similarities = []
        article_embeddings = []
        for a in articles:
            if a.embedding:
                article_embeddings.append(np.frombuffer(a.embedding, dtype=np.float32))

        if len(article_embeddings) >= 2:
            emb_matrix = np.array(article_embeddings)
            sim_matrix = cosine_similarity(emb_matrix)
            for i in range(len(sim_matrix)):
                for j in range(i + 1, len(sim_matrix)):
                    similarities.append({
                        "article_a": articles[i].id,
                        "article_b": articles[j].id,
                        "similarity": round(float(sim_matrix[i][j]), 4)
                    })

        return {
            "id": cluster.id,
            "cluster_label": cluster.cluster_label,
            "representative_title": cluster.representative_title,
            "article_count": cluster.article_count,
            "avg_similarity": cluster.avg_similarity,
            "sources": cluster.sources or [],
            "category": cluster.category,
            "unified_content": cluster.unified_content,
            "unified_headline": cluster.unified_headline,
            "debiased_unified_content": cluster.debiased_unified_content,
            "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "source": a.source,
                    "category": a.category,
                    "url": a.url,
                    "original_content": a.original_content[:500] + "..." if a.original_content and len(a.original_content) > 500 else a.original_content,
                    "is_biased": a.is_biased,
                    "bias_score": a.bias_score,
                    "processed": a.processed,
                    "published_date": a.published_date.isoformat() if a.published_date else None,
                    "scraped_at": a.scraped_at.isoformat() if a.scraped_at else None,
                }
                for a in articles
            ],
            "pairwise_similarities": similarities
        }

    def get_all_clusters(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
        min_articles: int = 2
    ) -> Tuple[List[Dict], int]:
        """
        Get paginated list of article clusters.

        Args:
            skip: Pagination offset
            limit: Max clusters to return
            category: Filter by category
            min_articles: Minimum articles in cluster

        Returns:
            Tuple of (clusters list, total count)
        """
        query = self.db.query(ArticleCluster).filter(
            ArticleCluster.article_count >= min_articles
        )

        if category:
            query = query.filter(ArticleCluster.category == category)

        total = query.count()
        clusters = query.order_by(ArticleCluster.created_at.desc()).offset(skip).limit(limit).all()

        result = []
        for cluster in clusters:
            # Get source labels for preview
            article_previews = self.db.query(Article).filter(
                Article.cluster_id == cluster.id
            ).limit(5).all()

            result.append({
                "id": cluster.id,
                "cluster_label": cluster.cluster_label,
                "representative_title": cluster.representative_title,
                "article_count": cluster.article_count,
                "avg_similarity": cluster.avg_similarity,
                "sources": cluster.sources or [],
                "category": cluster.category,
                "has_unified": cluster.unified_content is not None,
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
                "article_previews": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "source": a.source,
                        "is_biased": a.is_biased,
                        "bias_score": a.bias_score,
                    }
                    for a in article_previews
                ]
            })

        return result, total

    def get_clustering_stats(self) -> Dict:
        """Get overall clustering statistics."""
        total_clusters = self.db.query(ArticleCluster).count()
        total_clustered = self.db.query(Article).filter(Article.cluster_id.isnot(None)).count()
        total_unclustered = self.db.query(Article).filter(Article.cluster_id.is_(None)).count()
        total_articles = self.db.query(Article).count()

        # Average cluster size
        avg_size = 0
        if total_clusters > 0:
            from sqlalchemy import func
            result = self.db.query(func.avg(ArticleCluster.article_count)).scalar()
            avg_size = round(float(result), 1) if result else 0

        # Clusters by source count (multi-source vs single-source)
        multi_source_count = 0
        clusters = self.db.query(ArticleCluster).all()
        for c in clusters:
            if c.sources and len(c.sources) > 1:
                multi_source_count += 1

        return {
            "total_clusters": total_clusters,
            "total_articles_clustered": total_clustered,
            "total_articles_unclustered": total_unclustered,
            "total_articles": total_articles,
            "clustering_coverage": round((total_clustered / total_articles * 100) if total_articles > 0 else 0, 1),
            "avg_cluster_size": avg_size,
            "multi_source_clusters": multi_source_count,
            "single_source_clusters": total_clusters - multi_source_count,
            "model": "paraphrase-multilingual-MiniLM-L12-v2",
            "similarity_threshold": COMBINED_SIM_THRESHOLD,
            "title_weight": TITLE_WEIGHT,
            "content_weight": CONTENT_WEIGHT,
            "unified_summaries": self.db.query(ArticleCluster).filter(
                ArticleCluster.unified_content.isnot(None)
            ).count(),
        }
