/**
 * Legal Document Extraction Service
 * API calls for Vietnamese legal document (Luật, Nghị định, Thông tư) extraction
 */

const RAG_SERVICE_URL = import.meta.env.VITE_RAG_SERVICE_URL || 'http://localhost:8000';

/**
 * Upload DOCX file for legal document ingestion
 * Supports: Luật (LAW), Nghị định (DECREE), Thông tư (CIRCULAR)
 * @param {File} file - Word document file
 * @param {Object} options - Options for ingestion
 * @returns {Promise<Object>} Job ID and initial status
 */
export const uploadLegalDocument = async (file, options = {}) => {
  const { lawId = null, pushToNeo4j = true, indexWeaviate = true, indexOpenSearch = true } = options;

  const formData = new FormData();
  formData.append('file', file);
  
  // Backend expects Form parameters, not query parameters
  if (lawId) {
    formData.append('law_id', lawId);
  }
  formData.append('run_kg', pushToNeo4j.toString());
  formData.append('run_vector', (indexWeaviate || indexOpenSearch).toString());
  formData.append('index_namespace', 'laws_vn');

  const url = `${RAG_SERVICE_URL}/v1/ingest/docx`;

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed: ${response.status}`);
  }

  return response.json();
};

/**
 * Get ingestion job status
 * @param {string} jobId - Job ID to check
 * @returns {Promise<Object>} Job status with doc_kind, document_number, etc.
 */
export const getJobStatus = async (jobId) => {
  const response = await fetch(`${RAG_SERVICE_URL}/v1/ingest/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error(`Failed to get job status: ${response.status}`);
  }

  return response.json();
};

/**
 * Get list of all ingestion jobs
 * @param {number} limit - Max number of jobs to return
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Object>} List of jobs
 */
export const listJobs = async (limit = 50, offset = 0) => {
  const response = await fetch(`${RAG_SERVICE_URL}/v1/ingest/jobs?limit=${limit}&offset=${offset}`);

  if (!response.ok) {
    throw new Error(`Failed to list jobs: ${response.status}`);
  }

  return response.json();
};

/**
 * Get Knowledge Graph data from Neo4j
 * @param {string} documentNumber - Document number to filter (optional)
 * @param {string} docKind - Document kind (LAW, DECREE, CIRCULAR)
 * @returns {Promise<Object>} Graph data with nodes and relationships
 */
export const getKnowledgeGraph = async (documentNumber = null, docKind = null) => {
  const url = new URL(`${RAG_SERVICE_URL}/v1/kg/graph`);
  if (documentNumber) {
    url.searchParams.append('document_number', documentNumber);
  }
  if (docKind) {
    url.searchParams.append('doc_kind', docKind);
  }

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to get KG: ${response.status}`);
  }

  return response.json();
};

/**
 * Get KG statistics
 * @returns {Promise<Object>} Statistics about the knowledge graph
 */
export const getKGStatistics = async () => {
  const response = await fetch(`${RAG_SERVICE_URL}/v1/kg/stats`);

  if (!response.ok) {
    throw new Error(`Failed to get KG stats: ${response.status}`);
  }

  return response.json();
};

/**
 * Search in Knowledge Graph
 * @param {string} query - Search query
 * @param {string} docKind - Filter by document kind
 * @returns {Promise<Object>} Search results
 */
export const searchKnowledgeGraph = async (query, docKind = null) => {
  const url = new URL(`${RAG_SERVICE_URL}/v1/kg/search`);
  url.searchParams.append('query', query);
  if (docKind) {
    url.searchParams.append('doc_kind', docKind);
  }

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`);
  }

  return response.json();
};

/**
 * Get document structure tree
 * @param {string} documentNumber - Document number
 * @returns {Promise<Object>} Document structure as tree
 */
export const getDocumentStructure = async (documentNumber) => {
  const response = await fetch(`${RAG_SERVICE_URL}/v1/kg/document/structure?document_number=${encodeURIComponent(documentNumber)}`);

  if (!response.ok) {
    throw new Error(`Failed to get document structure: ${response.status}`);
  }

  return response.json();
};

/**
 * Delete a document from KG
 * @param {string} documentNumber - Document number to delete
 * @returns {Promise<Object>} Delete result
 */
export const deleteDocument = async (documentNumber) => {
  const response = await fetch(`${RAG_SERVICE_URL}/v1/kg/document?document_number=${encodeURIComponent(documentNumber)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete document: ${response.status}`);
  }

  return response.json();
};

export default {
  uploadLegalDocument,
  getJobStatus,
  listJobs,
  getKnowledgeGraph,
  getKGStatistics,
  searchKnowledgeGraph,
  getDocumentStructure,
  deleteDocument,
};
