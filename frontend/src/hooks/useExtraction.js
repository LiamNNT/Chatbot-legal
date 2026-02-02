/**
 * React Query hooks for Legal Document Extraction
 * 
 * Provides data fetching, caching, and state management for:
 * - KG Documents (from Neo4j)
 * - Ingest Jobs (from job store)
 * - KG Statistics
 * - Graph Data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const RAG_SERVICE_URL = import.meta.env.VITE_RAG_SERVICE_URL || 'http://localhost:8000';

// ============================================================================
// API Functions
// ============================================================================

const api = {
  // Fetch documents from Knowledge Graph (Neo4j)
  async getKGDocuments() {
    const response = await fetch(`${RAG_SERVICE_URL}/v1/kg/documents`);
    if (!response.ok) throw new Error('Failed to fetch KG documents');
    return response.json();
  },

  // Fetch ingestion jobs
  async getIngestJobs(limit = 50) {
    const response = await fetch(`${RAG_SERVICE_URL}/v1/ingest/jobs?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch jobs');
    return response.json();
  },

  // Fetch KG statistics
  async getKGStats() {
    const response = await fetch(`${RAG_SERVICE_URL}/v1/kg/stats`);
    if (!response.ok) throw new Error('Failed to fetch KG stats');
    return response.json();
  },

  // Fetch graph data for a specific document
  async getGraphData(documentNumber) {
    if (!documentNumber) return null;
    const response = await fetch(
      `${RAG_SERVICE_URL}/v1/kg/graph?document_number=${encodeURIComponent(documentNumber)}`
    );
    if (!response.ok) throw new Error('Failed to fetch graph data');
    return response.json();
  },

  // Upload and ingest a document
  async uploadDocument(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    if (options.runKG !== undefined) formData.append('run_kg', options.runKG);
    if (options.runVector !== undefined) formData.append('run_vector', options.runVector);

    const response = await fetch(`${RAG_SERVICE_URL}/v1/ingest/docx`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Upload failed');
    }
    return response.json();
  },

  // Get job status
  async getJobStatus(jobId) {
    const response = await fetch(`${RAG_SERVICE_URL}/v1/ingest/jobs/${jobId}`);
    if (!response.ok) throw new Error('Failed to fetch job status');
    return response.json();
  },

  // Delete a document from Knowledge Graph
  async deleteDocument(documentNumber) {
    const response = await fetch(`${RAG_SERVICE_URL}/v1/kg/document?document_number=${encodeURIComponent(documentNumber)}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to delete document');
    }
    return response.json();
  },
};

// ============================================================================
// Query Keys (for cache management)
// ============================================================================

export const queryKeys = {
  kgDocuments: ['kg', 'documents'],
  ingestJobs: ['ingest', 'jobs'],
  kgStats: ['kg', 'stats'],
  graphData: (docNumber) => ['kg', 'graph', docNumber],
  jobStatus: (jobId) => ['ingest', 'job', jobId],
};

// ============================================================================
// Custom Hooks
// ============================================================================

/**
 * Fetch all documents from Knowledge Graph
 * Auto-refetches on window focus
 */
export function useKGDocuments() {
  return useQuery({
    queryKey: queryKeys.kgDocuments,
    queryFn: api.getKGDocuments,
    staleTime: 30 * 1000, // 30 seconds
    refetchOnWindowFocus: true,
    select: (data) => {
      // Remove duplicates by document_number
      const uniqueDocs = [];
      const seen = new Set();
      for (const doc of data.documents || []) {
        if (!seen.has(doc.document_number)) {
          seen.add(doc.document_number);
          uniqueDocs.push(doc);
        }
      }
      return { ...data, documents: uniqueDocs };
    },
  });
}

/**
 * Fetch ingestion jobs
 */
export function useIngestJobs(limit = 50) {
  return useQuery({
    queryKey: [...queryKeys.ingestJobs, limit],
    queryFn: () => api.getIngestJobs(limit),
    staleTime: 10 * 1000, // 10 seconds
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch KG statistics
 */
export function useKGStats() {
  return useQuery({
    queryKey: queryKeys.kgStats,
    queryFn: api.getKGStats,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Fetch graph data for a specific document
 * @param {string} documentNumber - Document number to fetch
 * @param {boolean} enabled - Whether to enable the query
 */
export function useGraphData(documentNumber, enabled = true) {
  return useQuery({
    queryKey: queryKeys.graphData(documentNumber),
    queryFn: () => api.getGraphData(documentNumber),
    enabled: !!documentNumber && enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes (graph data doesn't change often)
  });
}

/**
 * Fetch job status with auto-refresh while processing
 * @param {string} jobId - Job ID to check
 * @param {boolean} enabled - Whether to enable polling
 */
export function useJobStatus(jobId, enabled = true) {
  return useQuery({
    queryKey: queryKeys.jobStatus(jobId),
    queryFn: () => api.getJobStatus(jobId),
    enabled: !!jobId && enabled,
    refetchInterval: (data) => {
      // Auto-refresh every 2s while job is processing
      if (data?.status === 'processing' || data?.status === 'pending') {
        return 2000;
      }
      return false; // Stop polling when complete/error
    },
  });
}

/**
 * Upload document mutation
 * Automatically invalidates related queries on success
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, options }) => api.uploadDocument(file, options),
    onSuccess: () => {
      // Invalidate jobs list to show new job
      queryClient.invalidateQueries({ queryKey: queryKeys.ingestJobs });
    },
  });
}

/**
 * Delete document mutation
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId) => api.deleteDocument(jobId),
    onSuccess: () => {
      // Invalidate both jobs and KG documents
      queryClient.invalidateQueries({ queryKey: queryKeys.ingestJobs });
      queryClient.invalidateQueries({ queryKey: queryKeys.kgDocuments });
    },
  });
}

/**
 * Combined hook: Get all documents (merged from KG + Jobs)
 * This provides a unified view of all documents
 */
export function useAllDocuments() {
  const kgQuery = useKGDocuments();
  const jobsQuery = useIngestJobs();

  const isLoading = kgQuery.isLoading || jobsQuery.isLoading;
  const error = kgQuery.error || jobsQuery.error;

  // Merge and deduplicate documents
  const documents = [];
  const seenIds = new Set();

  // Add KG documents first (these are confirmed in Neo4j)
  if (kgQuery.data?.documents) {
    for (const doc of kgQuery.data.documents) {
      const id = doc.document_number;
      if (!seenIds.has(id)) {
        seenIds.add(id);
        documents.push({
          ...doc,
          source: 'kg',
          status: 'completed',
        });
      }
    }
  }

  // Add jobs that aren't in KG yet (pending/processing)
  if (jobsQuery.data?.jobs) {
    for (const job of jobsQuery.data.jobs) {
      // Use law_id as the primary identifier (matches document_number)
      const docNum = job.law_id || job.document_number;
      const id = docNum || job.job_id;
      
      // Skip if already added from KG
      if (seenIds.has(id) || seenIds.has(docNum)) {
        continue;
      }
      
      seenIds.add(id);
      if (docNum) seenIds.add(docNum);
      
      documents.push({
        document_number: docNum,
        name: job.law_name || job.filename,
        doc_kind: job.doc_kind,
        job_id: job.job_id,
        status: job.status,
        source: 'jobs',
        created_at: job.created_at,
        filename: job.filename,
        ...job,
      });
    }
  }

  return {
    documents,
    isLoading,
    error,
    refetch: () => {
      kgQuery.refetch();
      jobsQuery.refetch();
    },
  };
}

// Export API for direct use if needed
export { api as extractionApi };
