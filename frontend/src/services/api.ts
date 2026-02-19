import axios from 'axios';
import type {
    ArticleInput,
    FullProcessResponse,
    SignupRequest,
    SigninRequest,
    AuthResponse,
    User,
} from '../types/index';

const API_BASE_URL = 'http://localhost:8000/api';
const AUTH_BASE_URL = 'http://localhost:8000/auth';

// Token management
export const getToken = (): string | null => {
    return localStorage.getItem('auth_token');
};

export const setToken = (token: string): void => {
    localStorage.setItem('auth_token', token);
};

export const removeToken = (): void => {
    localStorage.removeItem('auth_token');
};

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 300000,  // 5 minutes for scraping operations
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response interceptor to handle 401 errors
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid, remove it
            removeToken();
            // Optionally redirect to login
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

const authClient = axios.create({
    baseURL: AUTH_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000,
});

// Request interceptor to add auth token to authClient
authClient.interceptors.request.use(
    (config) => {
        const token = getToken();
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// ============================================
// Authentication API
// ============================================

export const authApi = {
    signup: async (data: SignupRequest): Promise<AuthResponse> => {
        const response = await authClient.post<AuthResponse>('/signup', data);
        return response.data;
    },

    signin: async (data: SigninRequest): Promise<AuthResponse> => {
        const response = await authClient.post<AuthResponse>('/signin', data);
        return response.data;
    },

    getCurrentUser: async (token: string): Promise<User> => {
        const response = await authClient.get<User>('/me', {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        return response.data;
    },

    verifyToken: async (token: string): Promise<boolean> => {
        try {
            await authClient.get('/verify', {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });
            return true;
        } catch {
            return false;
        }
    },

    verifyEmail: async (token: string): Promise<{ message: string }> => {
        const response = await authClient.post<{ message: string }>(`/verify-email/${token}`);
        return response.data;
    },

    resendVerification: async (email: string): Promise<{ message: string; verification_token: string }> => {
        const response = await authClient.post<{ message: string; verification_token: string }>(`/resend-verification/${email}`);
        return response.data;
    },

    getCategoryPreferences: async (): Promise<{ categories: string[] }> => {
        const response = await authClient.get<{ categories: string[] }>('/preferences');
        return response.data;
    },

    updateCategoryPreferences: async (categories: string[]): Promise<{ categories: string[]; message?: string }> => {
        const response = await authClient.put<{ categories: string[]; message?: string }>('/preferences', { categories });
        return response.data;
    },

    // Save manual analysis result
    saveAnalysis: async (data: {
        title?: string;
        original_content: string;
        is_biased?: boolean;
        bias_score?: number;
        bias_summary?: string;
        biased_terms?: any[];
        confidence?: number;
        debiased_content?: string;
        changes_made?: any[];
        total_changes?: number;
        generated_headlines?: string[];
        recommended_headline?: string;
        headline_reasoning?: string;
        processing_time?: number;
    }): Promise<UserAnalysis> => {
        const response = await authClient.post<UserAnalysis>('/analyses', data);
        return response.data;
    },

    // Get user's manual analyses
    getMyAnalyses: async (params?: { limit?: number; skip?: number }): Promise<{ analyses: UserAnalysis[]; total: number }> => {
        const response = await authClient.get<{ analyses: UserAnalysis[]; total: number }>('/analyses', { params });
        return response.data;
    },

    // Delete a manual analysis
    deleteAnalysis: async (id: number): Promise<void> => {
        await authClient.delete(`/analyses/${id}`);
    },
};

// ============================================
// Article Processing API
// ============================================

export interface Article {
    id: number;
    source: string;
    category: string | null;
    url: string;
    title: string;
    original_content: string;
    published_date: string | null;
    scraped_at: string;
    is_biased: boolean;
    bias_score: number;
    bias_summary: string;
    biased_terms: any[];
    debiased_content: string;
    changes_made: ChangeDetail[];
    total_changes: number;
    recommended_headline: string;
    processed: boolean;
    processed_at: string | null;
    processing_error: string | null;
    cluster_id: number | null;
    cluster_info: ClusterInfo | null;
}

export interface MergedArticle {
    id: number;
    title: string;
    source: string;
    category: string | null;
    url: string;
    original_content: string;
    is_biased: boolean;
    bias_score: number;
    processed: boolean;
    scraped_at: string | null;
    similarity_percent: number | null;
}

export interface ClusterInfo {
    cluster_id: number;
    cluster_label: string;
    article_count: number;
    avg_similarity: number | null;
    sources: string[];
    category: string | null;
    unified_content: string | null;
    unified_headline: string | null;
    merged_articles: MergedArticle[];
}

export interface ChangeDetail {
    original: string;
    debiased: string;
    reason: string;
}

export interface ArticlesResponse {
    total: number;
    skip: number;
    limit: number;
    articles: Article[];
}

export interface Statistics {
    total_articles: number;
    processed_count: number;
    biased_count: number;
    processed_articles: number;
    biased_articles: number;
    unprocessed_articles: number;
    by_source: Record<string, number>;
}

export interface Newspaper {
    key: string;
    name: string;
    base_url: string;
    url?: string;
    language: string;
    enabled: boolean;
}

// ============================================
// Cluster Types
// ============================================

export interface ClusterArticlePreview {
    id: number;
    title: string;
    source: string;
    is_biased: boolean | null;
    bias_score: number | null;
}

export interface ArticleCluster {
    id: number;
    cluster_label: string;
    representative_title: string | null;
    article_count: number;
    avg_similarity: number | null;
    sources: string[];
    category: string | null;
    has_unified: boolean;
    created_at: string;
    article_previews: ClusterArticlePreview[];
}

export interface ClusterArticleDetail {
    id: number;
    title: string;
    source: string;
    category: string | null;
    url: string;
    original_content: string;
    is_biased: boolean | null;
    bias_score: number | null;
    processed: boolean;
    published_date: string | null;
    scraped_at: string | null;
}

export interface PairwiseSimilarity {
    article_a: number;
    article_b: number;
    similarity: number;
}

export interface ClusterDetail {
    id: number;
    cluster_label: string;
    representative_title: string | null;
    article_count: number;
    avg_similarity: number | null;
    sources: string[];
    category: string | null;
    unified_content: string | null;
    unified_headline: string | null;
    debiased_unified_content: string | null;
    created_at: string;
    articles: ClusterArticleDetail[];
    pairwise_similarities: PairwiseSimilarity[];
}

export interface ClustersResponse {
    clusters: ArticleCluster[];
    total: number;
    skip: number;
    limit: number;
}

export interface ClusteringStats {
    total_clusters: number;
    total_articles_clustered: number;
    total_articles_unclustered: number;
    total_articles: number;
    clustering_coverage: number;
    avg_cluster_size: number;
    multi_source_clusters: number;
    single_source_clusters: number;
    model: string;
    similarity_threshold: number;
}

export interface UserAnalysis {
    id: number;
    user_id: number;
    title: string | null;
    original_content: string;
    is_biased: boolean | null;
    bias_score: number | null;
    bias_summary: string | null;
    biased_terms: any[] | null;
    confidence: number | null;
    debiased_content: string | null;
    changes_made: any[] | null;
    total_changes: number | null;
    generated_headlines: string[] | null;
    recommended_headline: string | null;
    headline_reasoning: string | null;
    processing_time: number | null;
    created_at: string;
}

export interface SchedulerStatus {
    running: boolean;
    next_run?: string;
    schedule?: string;
    jobs: Array<{
        id: string;
        name: string;
        next_run: string | null;
    }>;
    last_run?: {
        job_name: string;
        status: string;
        started_at: string | null;
        completed_at: string | null;
        articles_scraped: number;
        articles_processed: number;
        errors: string[] | null;
        error_message: string | null;
    };
}

export interface ManualScrapeRequest {
    sources?: string[];
    start_date?: string;
    end_date?: string;
}

export const api = {
    // Existing endpoint
    fullProcess: async (data: ArticleInput): Promise<FullProcessResponse> => {
        const response = await apiClient.post<FullProcessResponse>('/full-process', data);
        return response.data;
    },

    // Get articles with filters
    getArticles: async (params?: {
        source?: string;
        category?: string;
        is_biased?: boolean;
        processed?: boolean;
        skip?: number;
        limit?: number;
    }): Promise<ArticlesResponse> => {
        const response = await apiClient.get<ArticlesResponse>('/articles', { params });
        return response.data;
    },

    // Get single article
    getArticle: async (id: number): Promise<Article> => {
        const response = await apiClient.get<Article>(`/articles/${id}`);
        return response.data;
    },

    // Get statistics
    getStatistics: async (): Promise<Statistics> => {
        const response = await apiClient.get<Statistics>('/statistics');
        return response.data;
    },

    // Get newspapers
    getNewspapers: async (): Promise<{ newspapers: Newspaper[] }> => {
        const response = await apiClient.get<{ newspapers: Newspaper[] }>('/newspapers');
        return response.data;
    },

    // Get scheduler status
    getSchedulerStatus: async (): Promise<SchedulerStatus> => {
        const response = await apiClient.get<SchedulerStatus>('/scheduler/status');
        return response.data;
    },
    
    // Update scheduler time (Admin only)
    updateScheduler: async (hour: number, minute: number): Promise<any> => {
        const response = await apiClient.post(`/scheduler/update?hour=${hour}&minute=${minute}`);
        return response.data;
    },

    // Manual scraping
    manualScrape: async (data: ManualScrapeRequest): Promise<any> => {
        const response = await apiClient.post('/scrape/manual', null, { params: data });
        return response.data;
    },

    // Get scraping job status
    getScrapingStatus: async (jobId: string): Promise<any> => {
        const response = await apiClient.get(`/scrape/status/${jobId}`);
        return response.data;
    },

    // Get all scraping jobs
    getScrapingJobs: async (): Promise<any> => {
        const response = await apiClient.get('/scrape/jobs');
        return response.data;
    },

    // Process single article for bias detection
    processArticle: async (id: number): Promise<Article> => {
        const response = await apiClient.post<Article>(`/articles/${id}/process`);
        return response.data;
    },

    // ============================================
    // Cluster APIs
    // ============================================

    // Get list of clusters
    getClusters: async (params?: {
        skip?: number;
        limit?: number;
        category?: string;
        min_articles?: number;
    }): Promise<ClustersResponse> => {
        const response = await apiClient.get<ClustersResponse>('/clusters', { params });
        return response.data;
    },

    // Get cluster detail
    getClusterDetail: async (id: number): Promise<ClusterDetail> => {
        const response = await apiClient.get<ClusterDetail>(`/clusters/${id}`);
        return response.data;
    },

    // Get clustering stats
    getClusteringStats: async (): Promise<ClusteringStats> => {
        const response = await apiClient.get<ClusteringStats>('/clusters/stats');
        return response.data;
    },

    // Trigger clustering (admin only)
    generateClusters: async (params?: {
        days_back?: number;
        re_cluster?: boolean;
    }): Promise<any> => {
        const response = await apiClient.post('/clusters/generate', null, { params });
        return response.data;
    },

    // Debias unified cluster content
    debiasUnifiedContent: async (clusterId: number): Promise<any> => {
        const response = await apiClient.post(`/clusters/${clusterId}/debias-unified`);
        return response.data;
    },
};
