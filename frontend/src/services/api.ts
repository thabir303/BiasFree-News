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
};

// ============================================
// Article Processing API
// ============================================

export interface Article {
    id: number;
    source: string;
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

export interface SchedulerStatus {
    running: boolean;
    next_run?: string;
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
};
