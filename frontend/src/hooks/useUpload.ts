import { useCallback, useState } from "react";
import { uploadDocument } from "../api/client";
import type { UploadedDoc } from "../types";

export function useUpload() {
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [currentNamespace, setCurrentNamespace] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = useCallback(async (file: File) => {
    setIsUploading(true);
    setProgress(0);
    setError(null);
    try {
      const res = await uploadDocument(file, setProgress);
      const doc: UploadedDoc = {
        filename: res.filename,
        namespace: res.namespace,
        chunks_indexed: res.chunks_indexed,
        bytes_processed: res.bytes_processed,
        entities_indexed: res.entities_indexed,
        uploaded_at: Date.now(),
      };
      setUploadedDocs((prev) => [doc, ...prev]);
      setCurrentNamespace(doc.namespace);
      return doc;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "upload failed";
      setError(msg);
      throw err;
    } finally {
      setIsUploading(false);
    }
  }, []);

  const selectNamespace = useCallback((ns: string) => {
    setCurrentNamespace(ns);
  }, []);

  return {
    uploadedDocs,
    currentNamespace,
    isUploading,
    progress,
    error,
    uploadFile,
    selectNamespace,
  };
}
