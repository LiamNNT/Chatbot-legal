import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout for LLM responses
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.status, error.message);
    return Promise.reject(error);
  }
);

/**
 * Chat API - Send message to chatbot
 * Backend automatically decides RAG usage and parameters via SmartPlannerAgent
 * @param {string} query - User's message
 * @param {string} sessionId - Session ID for conversation
 * @returns {Promise} API response with chatbot reply
 */
export const sendChatMessage = async (query, sessionId) => {
  try {
    const response = await apiClient.post('/chat', {
      query,
      session_id: sessionId,
      // Let backend decide automatically via SmartPlannerAgent
      use_rag: true,  // Always enable, SmartPlanner will decide if actually needed
    });
    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

/**
 * Simple Chat API - Faster but less sophisticated responses
 * @param {string} query - User's message
 * @param {string} sessionId - Session ID for conversation
 * @param {Object} options - Additional options
 * @returns {Promise} API response with chatbot reply
 */
export const sendSimpleChatMessage = async (query, sessionId, options = {}) => {
  const {
    useRag = true,
    ragTopK = 5,
    model = null,
    temperature = 0.7,
    maxTokens = 2000,
  } = options;

  try {
    const response = await apiClient.post('/chat/simple', {
      query,
      session_id: sessionId,
      use_rag: useRag,
      rag_top_k: ragTopK,
      model,
      temperature,
      max_tokens: maxTokens,
      stream: false,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending simple chat message:', error);
    throw error;
  }
};

/**
 * Health Check API
 * @returns {Promise} Health status of all services
 */
export const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    console.error('Error checking health:', error);
    throw error;
  }
};

/**
 * Get all active conversations
 * @returns {Promise} List of active conversations
 */
export const getConversations = async () => {
  try {
    const response = await apiClient.get('/conversations');
    return response.data;
  } catch (error) {
    console.error('Error fetching conversations:', error);
    throw error;
  }
};

/**
 * Delete a conversation
 * @param {string} sessionId - Session ID to delete
 * @returns {Promise} Deletion confirmation
 */
export const deleteConversation = async (sessionId) => {
  try {
    const response = await apiClient.delete(`/conversations/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting conversation:', error);
    throw error;
  }
};

/**
 * Get agent system information
 * @returns {Promise} Information about multi-agent system
 */
export const getAgentsInfo = async () => {
  try {
    const response = await apiClient.get('/agents/info');
    return response.data;
  } catch (error) {
    console.error('Error fetching agents info:', error);
    throw error;
  }
};

/**
 * Test multi-agent system
 * @returns {Promise} Test results
 */
export const testAgents = async () => {
  try {
    const response = await apiClient.post('/agents/test');
    return response.data;
  } catch (error) {
    console.error('Error testing agents:', error);
    throw error;
  }
};

export default {
  sendChatMessage,
  sendSimpleChatMessage,
  checkHealth,
  getConversations,
  deleteConversation,
  getAgentsInfo,
  testAgents,
};
