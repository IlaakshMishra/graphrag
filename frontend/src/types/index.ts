export type Role = "user" | "assistant";

export interface SourceCitation {
  source: string;
  page?: number | null;
  chunk_index?: number | null;
  score?: number | null;
  snippet?: string | null;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  sources?: SourceCitation[];
  pending?: boolean;
  error?: string;
}

export interface UploadedDoc {
  filename: string;
  namespace: string;
  chunks_indexed: number;
  bytes_processed: number;
  uploaded_at: number;
}

export interface ChatApiRequest {
  question: string;
  namespace: string;
  session_id: string;
  chat_history: { role: Role; content: string }[];
}

export interface ChatApiResponse {
  answer: string;
  sources: SourceCitation[];
  session_id: string;
  namespace: string;
  used_documents: number;
}

export interface UploadApiResponse {
  namespace: string;
  filename: string;
  chunks_indexed: number;
  bytes_processed: number;
}

export interface EvaluateApiRequest {
  questions: string[];
  answers: string[];
  contexts: string[][];
  ground_truths: string[];
}

export interface EvaluateApiResponse {
  scores: Record<string, number>;
  sample_count: number;
  metrics_used: string[];
  relevancy_score: number;
  relevancy_breakdown?: {
    components?: Record<string, number>;
    weights_applied?: Record<string, number>;
    description?: string;
  };
  per_sample?: Array<{
    index: number;
    scores: Record<string, number>;
    relevancy_score: number;
  }>;
}

export interface PipelineEvaluateApiRequest {
  namespace: string;
  questions: string[];
  ground_truths?: string[];
  session_id?: string;
}

export interface PipelineEvaluateApiResponse {
  namespace: string;
  relevancy_score: number;
  aggregate_scores: Record<string, number>;
  relevancy_breakdown?: EvaluateApiResponse["relevancy_breakdown"];
  metrics_used: string[];
  sample_count: number;
  per_question: Array<{
    question: string;
    answer: string;
    ground_truth?: string | null;
    contexts_used: number;
    retrieved_count: number;
    relevant_count_after_grader: number;
    scores: Record<string, number>;
    relevancy_score: number;
  }>;
  per_sample?: EvaluateApiResponse["per_sample"];
}
