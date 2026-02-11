// ============================================
// Authentication Types
// ============================================

export interface User {
    id: number;
    username: string;
    email: string;
    role: 'admin' | 'user';
    is_active: boolean;
    category_preferences?: string[];
}

export interface SignupRequest {
    username: string;
    email: string;
    password: string;
}

export interface SigninRequest {
    email: string;
    password: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    user: User;
    message?: string;
}

export interface AuthContextType {
    user: User | null;
    token: string | null;
    signin: (email: string, password: string) => Promise<void>;
    signup: (username: string, email: string, password: string) => Promise<string>;
    logout: () => void;
    isAuthenticated: boolean;
    isAdmin: boolean;
    loading: boolean;
}

// ============================================
// Article Processing Types
// ============================================

export interface BiasedTerm {
    term: string;
    reason: string;
    neutral_alternative: string;
    severity: 'low' | 'medium' | 'high';
}

export interface BiasAnalysisResponse {
    is_biased: boolean;
    bias_score: number;
    biased_terms: BiasedTerm[];
    summary: string;
    confidence: number;
}

export interface ContentChange {
    original: string;
    debiased: string;
    reason: string;
}

export interface DebiasResponse {
    original_content: string;
    debiased_content: string;
    changes: ContentChange[];
    total_changes: number;
}

export interface HeadlineResponse {
    original_title: string | null;
    generated_headlines: string[];
    recommended_headline: string;
    reasoning: string;
}

export interface FullProcessResponse {
    analysis: BiasAnalysisResponse;
    debiased: DebiasResponse;
    headline: HeadlineResponse;
    processing_time_seconds: number;
}

export interface ArticleInput {
    content: string;
    title?: string;
}
