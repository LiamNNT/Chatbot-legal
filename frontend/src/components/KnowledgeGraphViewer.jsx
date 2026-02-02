import React, { useState, useEffect } from 'react';
import {
  Network,
  Maximize2,
  Minimize2,
  RefreshCw,
  FileText,
  ChevronRight,
  ChevronDown,
  Search,
  X,
  Scale,
  FileCode,
  ScrollText,
  AlertCircle,
} from 'lucide-react';

const RAG_SERVICE_URL = import.meta.env.VITE_RAG_SERVICE_URL || 'http://localhost:8000';

/**
 * Knowledge Graph Viewer Component
 * Visualizes the extracted knowledge graph with interactive features
 */
const KnowledgeGraphViewer = ({ selectedDocument, onSelectDocument, documents }) => {
  const [graphData, setGraphData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [viewMode, setViewMode] = useState('tree'); // 'tree' | 'graph' | 'list'

  // Node type configuration with Vietnamese labels
  const nodeTypeConfig = {
    'Luật': { color: '#3B82F6', icon: Scale, label: 'Luật' },
    'Nghị định': { color: '#8B5CF6', icon: FileCode, label: 'Nghị định' },
    'Thông tư': { color: '#10B981', icon: ScrollText, label: 'Thông tư' },
    'Chương': { color: '#F59E0B', icon: FileText, label: 'Chương' },
    'Mục': { color: '#EC4899', icon: FileText, label: 'Mục' },
    'Điều': { color: '#06B6D4', icon: FileText, label: 'Điều' },
    'Khoản': { color: '#84CC16', icon: FileText, label: 'Khoản' },
    'Điểm': { color: '#F97316', icon: FileText, label: 'Điểm' },
    'Khái niệm': { color: '#EF4444', icon: FileText, label: 'Khái niệm' },
    'Thuật ngữ': { color: '#A855F7', icon: FileText, label: 'Thuật ngữ' },
  };

  // Load graph data when document changes
  useEffect(() => {
    if (selectedDocument) {
      loadGraphData(selectedDocument.document_number);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDocument]);

  const loadGraphData = async (documentNumber) => {
    if (!documentNumber) return;

    setIsLoading(true);
    setError(null);

    try {
      // Use the new /document/structure endpoint for full hierarchy with content
      const response = await fetch(
        `${RAG_SERVICE_URL}/v1/kg/document/structure?document_number=${encodeURIComponent(documentNumber)}`
      );

      if (!response.ok) {
        // Fallback to old endpoint if structure endpoint fails
        const fallbackResponse = await fetch(
          `${RAG_SERVICE_URL}/v1/kg/graph?document_number=${encodeURIComponent(documentNumber)}`
        );
        
        if (!fallbackResponse.ok) {
          throw new Error(`Failed to load graph: ${fallbackResponse.status}`);
        }
        
        const data = await fallbackResponse.json();
        const treeData = transformToTree(data.nodes, data.relationships, documentNumber);
        setGraphData({
          tree: treeData,
          stats: {
            total_nodes: data.total_nodes,
            total_relationships: data.total_relationships,
          },
        });
        
        if (treeData?.id) {
          setExpandedNodes(new Set([treeData.id]));
        }
        return;
      }

      const data = await response.json();
      
      // Handle both formats: { tree: {...}, stats: {...} } or { id: ..., children: [...], stats: {...} }
      const treeData = data.tree || (data.id ? data : null);
      
      setGraphData({
        tree: treeData,
        stats: data.stats,
      });
      
      // Auto-expand root node
      if (treeData?.id) {
        setExpandedNodes(new Set([treeData.id]));
      }
    } catch (err) {
      console.error('Error loading graph:', err);
      setError(err.message);
      
      // Use mock data for demo
      setGraphData(createMockData(documentNumber));
    } finally {
      setIsLoading(false);
    }
  };

  // Transform flat nodes and relationships to hierarchical tree (fallback)
  const transformToTree = (nodes, relationships, documentNumber) => {
    if (!nodes || nodes.length === 0) return null;
    
    // Find root document node
    const docNode = nodes.find(n => 
      n.type === 'Luật' || n.type === 'Nghị định' || n.type === 'Thông tư'
    );
    
    if (!docNode) {
      // Fallback: create a virtual root
      return {
        id: `DOC=${documentNumber}`,
        type: 'Luật',
        name: `Văn bản ${documentNumber}`,
        children: nodes.slice(0, 50).map(n => ({
          id: n.id,
          type: n.type,
          name: n.name || n.properties?.name || n.type,
          content: n.properties?.content,
          children: [],
        })),
      };
    }
    
    // Group nodes by type for hierarchy
    const chapters = nodes.filter(n => n.type === 'Chương');
    const articles = nodes.filter(n => n.type === 'Điều');
    // clauses and points can be added later for deeper hierarchy
    
    // Build tree from document
    const tree = {
      id: docNode.id,
      type: docNode.type,
      name: docNode.name || docNode.properties?.name || docNode.type,
      content: docNode.properties?.content,
      document_number: docNode.document_number,
      children: [],
    };
    
    // Remove duplicates by chapter_number
    const uniqueChapters = [];
    const seenChapterNums = new Set();
    for (const ch of chapters) {
      const chNum = ch.number || ch.properties?.chapter_number;
      if (!seenChapterNums.has(chNum)) {
        seenChapterNums.add(chNum);
        uniqueChapters.push(ch);
      }
    }
    
    // Add chapters
    uniqueChapters.forEach(chapter => {
      const chapterNode = {
        id: chapter.id,
        type: chapter.type,
        name: chapter.name || `Chương ${chapter.number || chapter.properties?.chapter_number}`,
        content: chapter.properties?.title,
        children: [],
      };
      
      // Find articles in this chapter
      const chapterNum = chapter.number || chapter.properties?.chapter_number;
      const chapterArticles = articles.filter(a => {
        const aChapterNum = a.properties?.chapter_number;
        return aChapterNum === chapterNum;
      });
      
      // Add articles (limit to prevent too large tree)
      chapterArticles.slice(0, 20).forEach(article => {
        const articleNode = {
          id: article.id,
          type: article.type,
          name: article.name || `Điều ${article.number || article.properties?.article_number}`,
          content: article.properties?.content || article.properties?.title,
          children: [],
        };
        chapterNode.children.push(articleNode);
      });
      
      tree.children.push(chapterNode);
    });
    
    // Sort chapters by number
    tree.children.sort((a, b) => {
      const numA = romanToInt(a.name.match(/[IVXLC]+/)?.[0]) || 0;
      const numB = romanToInt(b.name.match(/[IVXLC]+/)?.[0]) || 0;
      return numA - numB;
    });
    
    return tree;
  };

  // Helper: Convert Roman numerals to integers
  const romanToInt = (roman) => {
    if (!roman) return 0;
    const romanMap = { I: 1, V: 5, X: 10, L: 50, C: 100 };
    let result = 0;
    for (let i = 0; i < roman.length; i++) {
      const curr = romanMap[roman[i]] || 0;
      const next = romanMap[roman[i + 1]] || 0;
      result += curr < next ? -curr : curr;
    }
    return result;
  };

  // Create mock data for demonstration
  const createMockData = (documentNumber) => {
    return {
      tree: {
        id: `DOC=${documentNumber}`,
        type: 'Luật',
        name: `Luật ${documentNumber}`,
        children: [
          {
            id: `${documentNumber}:CHUONG=I`,
            type: 'Chương',
            name: 'Chương I - QUY ĐỊNH CHUNG',
            children: [
              {
                id: `${documentNumber}:CHUONG=I:DIEU=1`,
                type: 'Điều',
                name: 'Điều 1. Phạm vi điều chỉnh',
                content: 'Luật này quy định về...',
                children: [],
              },
              {
                id: `${documentNumber}:CHUONG=I:DIEU=2`,
                type: 'Điều',
                name: 'Điều 2. Đối tượng áp dụng',
                content: 'Luật này áp dụng đối với...',
                children: [
                  { id: `${documentNumber}:CHUONG=I:DIEU=2:KHOAN=1`, type: 'Khoản', name: 'Khoản 1', content: 'Cơ quan nhà nước...' },
                  { id: `${documentNumber}:CHUONG=I:DIEU=2:KHOAN=2`, type: 'Khoản', name: 'Khoản 2', content: 'Tổ chức, cá nhân...' },
                ],
              },
              {
                id: `${documentNumber}:CHUONG=I:DIEU=3`,
                type: 'Điều',
                name: 'Điều 3. Giải thích từ ngữ',
                content: 'Trong Luật này, các từ ngữ dưới đây được hiểu như sau...',
                children: [],
              },
            ],
          },
          {
            id: `${documentNumber}:CHUONG=II`,
            type: 'Chương',
            name: 'Chương II - QUYỀN VÀ NGHĨA VỤ',
            children: [],
          },
        ],
      },
      stats: {
        total_nodes: 10,
        total_relationships: 9,
        node_types: { 'Luật': 1, 'Chương': 2, 'Điều': 3, 'Khoản': 2 },
      },
    };
  };

  const toggleNodeExpand = (nodeId) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const expandAll = () => {
    if (!graphData?.tree) return;
    
    const allIds = new Set();
    const traverse = (node) => {
      allIds.add(node.id);
      node.children?.forEach(traverse);
    };
    traverse(graphData.tree);
    setExpandedNodes(allIds);
  };

  const collapseAll = () => {
    if (!graphData?.tree) return;
    setExpandedNodes(new Set([graphData.tree.id]));
  };

  const filterNodes = (node, query) => {
    if (!query) return true;
    const lowerQuery = query.toLowerCase();
    
    if (node.name?.toLowerCase().includes(lowerQuery)) return true;
    if (node.content?.toLowerCase().includes(lowerQuery)) return true;
    if (node.children?.some(child => filterNodes(child, query))) return true;
    
    return false;
  };

  // Render tree node recursively
  const renderTreeNode = (node, depth = 0) => {
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    const isSelected = selectedNode?.id === node.id;
    const config = nodeTypeConfig[node.type] || { color: '#6B7280', label: node.type };
    const Icon = config.icon || FileText;

    // Filter check
    if (searchQuery && !filterNodes(node, searchQuery)) {
      return null;
    }

    return (
      <div key={node.id} className="select-none">
        <div
          onClick={() => {
            setSelectedNode(node);
            if (hasChildren) toggleNodeExpand(node.id);
          }}
          className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
            isSelected
              ? 'bg-blue-100 dark:bg-blue-900/30 border-l-4 border-blue-500'
              : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'
          }`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {/* Expand/Collapse Icon */}
          <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )
            ) : (
              <span className="w-4" />
            )}
          </div>

          {/* Node Icon */}
          <div
            className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: `${config.color}20` }}
          >
            <Icon className="w-3.5 h-3.5" style={{ color: config.color }} />
          </div>

          {/* Node Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span
                className="text-xs px-1.5 py-0.5 rounded font-medium"
                style={{ backgroundColor: `${config.color}20`, color: config.color }}
              >
                {config.label}
              </span>
              <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {node.name}
              </span>
            </div>
            {node.content && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                {node.content}
              </p>
            )}
          </div>
        </div>

        {/* Children */}
        {hasChildren && isExpanded && (
          <div className="ml-2 border-l border-gray-200 dark:border-gray-700">
            {node.children.map((child) => renderTreeNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  // Render node detail panel
  const renderNodeDetail = () => {
    if (!selectedNode) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <FileText className="w-12 h-12 mb-3 opacity-50" />
          <p>Chọn một node để xem chi tiết</p>
        </div>
      );
    }

    const config = nodeTypeConfig[selectedNode.type] || { color: '#6B7280', label: selectedNode.type };
    const Icon = config.icon || FileText;

    return (
      <div className="p-4 space-y-4 overflow-y-auto h-full">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: `${config.color}20` }}
          >
            <Icon className="w-6 h-6" style={{ color: config.color }} />
          </div>
          <div className="flex-1 min-w-0">
            <span
              className="text-xs px-2 py-1 rounded font-medium"
              style={{ backgroundColor: `${config.color}20`, color: config.color }}
            >
              {config.label}
            </span>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mt-1 break-words">
              {selectedNode.name}
            </h3>
            {selectedNode.title && selectedNode.title !== selectedNode.name && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {selectedNode.title}
              </p>
            )}
          </div>
        </div>

        {/* Number/Label info */}
        {(selectedNode.number || selectedNode.label) && (
          <div className="flex items-center gap-4 text-sm">
            {selectedNode.number && (
              <div>
                <span className="text-gray-500">Số: </span>
                <span className="font-medium text-gray-700 dark:text-gray-300">{selectedNode.number}</span>
              </div>
            )}
            {selectedNode.label && (
              <div>
                <span className="text-gray-500">Nhãn: </span>
                <span className="font-medium text-gray-700 dark:text-gray-300">{selectedNode.label}</span>
              </div>
            )}
          </div>
        )}

        {/* Content - Main display area */}
        {selectedNode.content && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
              Nội dung trích xuất
            </p>
            <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg text-sm text-gray-700 dark:text-gray-300 max-h-96 overflow-y-auto whitespace-pre-wrap leading-relaxed border border-gray-200 dark:border-gray-600">
              {selectedNode.content}
            </div>
          </div>
        )}

        {/* Children summary */}
        {selectedNode.children && selectedNode.children.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
              Cấu trúc con ({selectedNode.children.length})
            </p>
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {selectedNode.children.slice(0, 20).map((child, idx) => {
                const childConfig = nodeTypeConfig[child.type] || { color: '#6B7280' };
                return (
                  <div 
                    key={child.id || idx}
                    className="flex items-center gap-2 text-sm p-2 bg-gray-100 dark:bg-gray-700 rounded cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-600"
                    onClick={() => {
                      setSelectedNode(child);
                      setExpandedNodes(prev => new Set([...prev, selectedNode.id]));
                    }}
                  >
                    <div 
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: childConfig.color }}
                    />
                    <span className="text-gray-600 dark:text-gray-400 flex-shrink-0">{child.type}:</span>
                    <span className="text-gray-800 dark:text-gray-200 truncate">{child.name}</span>
                  </div>
                );
              })}
              {selectedNode.children.length > 20 && (
                <p className="text-xs text-gray-500 text-center py-1">
                  ... và {selectedNode.children.length - 20} phần tử khác
                </p>
              )}
            </div>
          </div>
        )}

        {/* Properties - Collapsible */}
        {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
          <details className="group">
            <summary className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
              Thuộc tính ({Object.keys(selectedNode.properties).length})
            </summary>
            <div className="mt-2 space-y-1 text-xs max-h-48 overflow-y-auto">
              {Object.entries(selectedNode.properties)
                .filter(([key]) => !['content', 'name', 'title'].includes(key))
                .map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 py-1 border-b border-gray-100 dark:border-gray-700">
                  <span className="text-gray-500 flex-shrink-0 font-mono">{key}:</span>
                  <span className="text-gray-700 dark:text-gray-300 break-all">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value || '—')}
                  </span>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* ID info */}
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-400 font-mono truncate" title={selectedNode.id}>
            ID: {selectedNode.id}
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 ${
      isFullscreen ? 'fixed inset-4 z-50' : ''
    }`}>
      {/* Header */}
      <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Network className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Đồ thị tri thức
            </h2>
            {selectedDocument && (
              <p className="text-sm text-gray-500">
                {selectedDocument.document_number || selectedDocument.filename}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Document Selector */}
          <select
            value={selectedDocument?.job_id || ''}
            onChange={(e) => {
              const doc = documents.find(d => d.job_id === e.target.value);
              onSelectDocument(doc);
            }}
            className="px-3 py-1.5 text-sm border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700"
          >
            <option value="">Chọn văn bản...</option>
            {documents.map((doc) => (
              <option key={doc.job_id} value={doc.job_id}>
                {doc.document_number || doc.filename}
              </option>
            ))}
          </select>

          {/* View Mode Toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('tree')}
              className={`px-3 py-1 text-sm rounded ${
                viewMode === 'tree'
                  ? 'bg-white dark:bg-gray-600 shadow-sm'
                  : 'text-gray-500'
              }`}
            >
              Cây
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 text-sm rounded ${
                viewMode === 'list'
                  ? 'bg-white dark:bg-gray-600 shadow-sm'
                  : 'text-gray-500'
              }`}
            >
              Danh sách
            </button>
          </div>

          {/* Actions */}
          <button
            onClick={expandAll}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Mở rộng tất cả"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={collapseAll}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Thu gọn tất cả"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => loadGraphData(selectedDocument?.document_number)}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Tải lại"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title={isFullscreen ? 'Thoát toàn màn hình' : 'Toàn màn hình'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="p-4 border-b dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm trong đồ thị..."
            className="w-full pl-10 pr-4 py-2 border dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex" style={{ height: isFullscreen ? 'calc(100vh - 200px)' : '500px' }}>
        {/* Tree View */}
        <div className="flex-1 overflow-y-auto border-r dark:border-gray-700 p-2">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
              <p className="mt-2 text-gray-500">Đang tải đồ thị...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-center p-4">
              <AlertCircle className="w-12 h-12 text-red-500 mb-3" />
              <p className="text-red-500 font-medium">Lỗi tải đồ thị</p>
              <p className="text-sm text-gray-500 mt-1">{error}</p>
              <button
                onClick={() => loadGraphData(selectedDocument?.document_number)}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Thử lại
              </button>
            </div>
          ) : !graphData ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Network className="w-12 h-12 mb-3 opacity-50" />
              <p>Chọn một văn bản để xem đồ thị</p>
            </div>
          ) : (
            <div>
              {graphData.tree && renderTreeNode(graphData.tree)}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="w-80 overflow-y-auto bg-gray-50 dark:bg-gray-900/50">
          {renderNodeDetail()}
        </div>
      </div>

      {/* Stats Footer */}
      {graphData?.stats && (
        <div className="p-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-6">
              <span className="text-gray-500">
                <strong className="text-gray-700 dark:text-gray-300">{graphData.stats.total_nodes}</strong> nodes
              </span>
              <span className="text-gray-500">
                <strong className="text-gray-700 dark:text-gray-300">{graphData.stats.total_relationships}</strong> relationships
              </span>
            </div>
            <div className="flex items-center gap-2">
              {Object.entries(graphData.stats.node_types || {}).slice(0, 5).map(([type, count]) => {
                const config = nodeTypeConfig[type] || { color: '#6B7280' };
                return (
                  <span
                    key={type}
                    className="text-xs px-2 py-1 rounded"
                    style={{ backgroundColor: `${config.color}20`, color: config.color }}
                  >
                    {type}: {count}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraphViewer;
