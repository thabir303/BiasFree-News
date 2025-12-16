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
