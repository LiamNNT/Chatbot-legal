"""
Frontend Integration Examples for Chatbot-UIT
==============================================

This file shows how to integrate with the backend API from your frontend application.
"""

# Example 1: Simple Chat
# ----------------------
# JavaScript/TypeScript (React/Vue/Next.js)
example_chat_js = """
// Chat with the bot
async function sendMessage(message, conversationId = null) {
  const response = await fetch('http://localhost:8001/api/v1/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      conversation_id: conversationId || `user-${Date.now()}`,
      agent: 'rag_agent'  // Optional: specify which agent to use
    })
  });
  
  const data = await response.json();
  return {
    response: data.response,
    conversationId: data.conversation_id,
    sources: data.sources  // RAG sources if available
  };
}

// Usage
const result = await sendMessage('Học phí UIT năm 2024 là bao nhiêu?');
console.log('Bot:', result.response);
console.log('Sources:', result.sources);
"""

# Example 2: React Component
# ---------------------------
example_react = """
import React, { useState } from 'react';

function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [conversationId] = useState(`user-${Date.now()}`);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    // Add user message to UI
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8001/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          conversation_id: conversationId,
        })
      });

      const data = await response.json();
      
      // Add bot response to UI
      const botMessage = { 
        role: 'assistant', 
        content: data.response,
        sources: data.sources 
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error:', error);
      // Handle error - show error message to user
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <p>{msg.content}</p>
            {msg.sources && (
              <div className="sources">
                <small>Sources: {msg.sources.join(', ')}</small>
              </div>
            )}
          </div>
        ))}
        {loading && <div className="loading">Đang suy nghĩ...</div>}
      </div>
      
      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Nhập câu hỏi..."
        />
        <button onClick={sendMessage} disabled={loading}>
          Gửi
        </button>
      </div>
    </div>
  );
}

export default Chatbot;
"""

# Example 3: Direct RAG Search (without agent)
# ---------------------------------------------
example_rag_search = """
// Search documents directly using RAG service
async function searchDocuments(query, topK = 5) {
  const response = await fetch('http://localhost:8000/v1/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      top_k: topK,
      search_type: 'hybrid'  // 'hybrid', 'vector', or 'keyword'
    })
  });
  
  const data = await response.json();
  return data.results;  // Array of relevant documents
}

// Usage
const docs = await searchDocuments('quy định học phí', 10);
docs.forEach(doc => {
  console.log('Document:', doc.content);
  console.log('Score:', doc.score);
});
"""

# Example 4: Conversation History
# --------------------------------
example_history = """
// Get conversation history
async function getConversations(userId) {
  const response = await fetch(
    `http://localhost:8001/api/v1/conversations?user_id=${userId}`
  );
  
  const data = await response.json();
  return data.conversations;
}

// Get specific conversation
async function getConversation(conversationId) {
  const response = await fetch(
    `http://localhost:8001/api/v1/conversations/${conversationId}`
  );
  
  const data = await response.json();
  return data.messages;
}

// Usage
const allConvos = await getConversations('user-123');
const messages = await getConversation('conv-abc-123');
"""

# Example 5: Health Check & Monitoring
# -------------------------------------
example_health = """
// Check if backend is healthy
async function checkBackendHealth() {
  try {
    const [ragHealth, orchHealth] = await Promise.all([
      fetch('http://localhost:8000/v1/health'),
      fetch('http://localhost:8001/api/v1/health')
    ]);
    
    const rag = await ragHealth.json();
    const orch = await orchHealth.json();
    
    return {
      rag: rag.status === 'ok',
      orchestrator: orch.status === 'healthy' || orch.status === 'degraded',
      overall: rag.status === 'ok' && orch.status === 'healthy'
    };
  } catch (error) {
    return { rag: false, orchestrator: false, overall: false };
  }
}

// Usage - call before rendering app
const health = await checkBackendHealth();
if (!health.overall) {
  console.warn('Backend is not fully healthy:', health);
  // Show warning to user
}
"""

# Example 6: Streaming Response (if implemented)
# -----------------------------------------------
example_streaming = """
// For future implementation - streaming responses
async function streamChat(message, conversationId, onChunk) {
  const response = await fetch('http://localhost:8001/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      conversation_id: conversationId,
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    onChunk(chunk);  // Update UI with chunk
  }
}

// Usage
await streamChat('Học phí UIT?', 'user-123', (chunk) => {
  // Update UI progressively as chunks arrive
  updateChatUI(chunk);
});
"""

# Example 7: Error Handling
# --------------------------
example_error_handling = """
async function robustSendMessage(message, conversationId) {
  try {
    const response = await fetch('http://localhost:8001/api/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, conversation_id: conversationId }),
      signal: AbortSignal.timeout(30000)  // 30s timeout
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      return { error: 'Request timeout - backend may be slow' };
    } else if (error.message.includes('Failed to fetch')) {
      return { error: 'Backend is not running. Please start it first.' };
    } else {
      return { error: error.message };
    }
  }
}

// Usage with error display
const result = await robustSendMessage('Hello', 'user-123');
if (result.error) {
  showError(result.error);
} else {
  displayResponse(result.response);
}
"""

# Example 8: TypeScript Types
# ----------------------------
example_typescript = """
// TypeScript type definitions
interface ChatRequest {
  message: string;
  conversation_id: string;
  agent?: string;
  context?: Record<string, any>;
}

interface ChatResponse {
  response: string;
  conversation_id: string;
  agent_used: string;
  sources?: string[];
  metadata?: {
    tokens_used?: number;
    processing_time?: number;
  };
}

interface RAGSearchRequest {
  query: string;
  top_k?: number;
  search_type?: 'hybrid' | 'vector' | 'keyword';
}

interface RAGDocument {
  content: string;
  score: number;
  metadata: {
    source?: string;
    title?: string;
    [key: string]: any;
  };
}

interface RAGSearchResponse {
  results: RAGDocument[];
  query: string;
  search_type: string;
}

// API Client class
class ChatbotAPI {
  private baseUrl: string;
  
  constructor(baseUrl = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
  }
  
  async chat(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  }
  
  async search(query: string, topK = 5): Promise<RAGSearchResponse> {
    const response = await fetch('http://localhost:8000/v1/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK })
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  }
}

// Usage
const api = new ChatbotAPI();
const response = await api.chat({
  message: 'Hello',
  conversation_id: 'user-123'
});
"""

# Print all examples
if __name__ == "__main__":
    print("=" * 70)
    print("Frontend Integration Examples for Chatbot-UIT Backend")
    print("=" * 70)
    
    examples = [
        ("Simple Chat (JavaScript)", example_chat_js),
        ("React Component", example_react),
        ("Direct RAG Search", example_rag_search),
        ("Conversation History", example_history),
        ("Health Check", example_health),
        ("Streaming Response", example_streaming),
        ("Error Handling", example_error_handling),
        ("TypeScript Types", example_typescript),
    ]
    
    for title, code in examples:
        print(f"\n{'='*70}")
        print(f"Example: {title}")
        print('='*70)
        print(code)
