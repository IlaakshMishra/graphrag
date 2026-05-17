import axios, { AxiosError } from "axios";
import type {
  ChatApiRequest,
  ChatApiResponse,
  EvaluateApiRequest,
  EvaluateApiResponse,
  PipelineEvaluateApiRequest,
  PipelineEvaluateApiResponse,
  UploadApiResponse,
} from "../types";

const baseURL =
  (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env
    .VITE_API_BASE_URL || "/api";

export const http = axios.create({
  baseURL,
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
});

function asError(err: unknown): Error {
  if (err instanceof AxiosError) {
    const detail = err.response?.data?.detail || err.response?.data?.error;
    return new Error(
      typeof detail === "string" ? detail : err.message || "request failed"
    );
  }
  if (err instanceof Error) return err;
  return new Error("unknown error");
}

export async function uploadDocument(
  file: File,
  onProgress?: (pct: number) => void
): Promise<UploadApiResponse> {
  const fd = new FormData();
  fd.append("file", file);
  try {
    const { data } = await http.post<UploadApiResponse>("/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    });
    return data;
  } catch (err) {
    throw asError(err);
  }
}

export async function postChat(
  payload: ChatApiRequest
): Promise<ChatApiResponse> {
  try {
    const { data } = await http.post<ChatApiResponse>("/chat", payload);
    return data;
  } catch (err) {
    throw asError(err);
  }
}

export async function postEvaluate(
  payload: EvaluateApiRequest
): Promise<EvaluateApiResponse> {
  try {
    const { data } = await http.post<EvaluateApiResponse>("/evaluate", payload);
    return data;
  } catch (err) {
    throw asError(err);
  }
}

export async function postEvaluatePipeline(
  payload: PipelineEvaluateApiRequest
): Promise<PipelineEvaluateApiResponse> {
  try {
    const { data } = await http.post<PipelineEvaluateApiResponse>(
      "/evaluate/pipeline",
      payload
    );
    return data;
  } catch (err) {
    throw asError(err);
  }
}
