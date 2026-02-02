/**
 * Knowledge Graph Flow Visualization
 * 
 * Displays the knowledge graph as an interactive node-edge diagram
 * using React Flow. Shows relationships between legal document entities.
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  RefreshCw,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  Filter,
  Info,
  X,
} from 'lucide-react';

const RAG_SERVICE_URL = import.meta.env.VITE_RAG_SERVICE_URL || 'http://localhost:8000';

// Node colors by type
const nodeColors = {
  'Luật': { bg: '#3B82F6', border: '#1D4ED8', text: '#FFFFFF' },
  'Nghị định': { bg: '#8B5CF6', border: '#6D28D9', text: '#FFFFFF' },
  'Thông tư': { bg: '#10B981', border: '#059669', text: '#FFFFFF' },
  'Chương': { bg: '#F59E0B', border: '#D97706', text: '#000000' },
  'Mục': { bg: '#EC4899', border: '#DB2777', text: '#FFFFFF' },
  'Điều': { bg: '#06B6D4', border: '#0891B2', text: '#FFFFFF' },
  'Khoản': { bg: '#84CC16', border: '#65A30D', text: '#000000' },
  'Điểm': { bg: '#F97316', border: '#EA580C', text: '#FFFFFF' },
  'Khái niệm': { bg: '#EF4444', border: '#DC2626', text: '#FFFFFF' },
  'Hành vi cấm': { bg: '#7C3AED', border: '#5B21B6', text: '#FFFFFF' },
  'Chế tài': { bg: '#DB2777', border: '#BE185D', text: '#FFFFFF' },
  'default': { bg: '#6B7280', border: '#4B5563', text: '#FFFFFF' },
};

// Edge colors by relationship type
const edgeColors = {
  'THUOC_VE': '#64748B',
  'CHUA': '#10B981',
  'THAM_CHIEU': '#F59E0B',
  'DINH_NGHIA': '#8B5CF6',
  'AP_DUNG_CHO': '#3B82F6',
  'BI_XU_LY': '#EF4444',
  'THAY_THE': '#EC4899',
  'SUA_DOI': '#F97316',
  'BO_SUNG': '#84CC16',
  'BAI_BO': '#DC2626',
  'default': '#94A3B8',
};

// Relationship labels (Vietnamese)
const relationshipLabels = {
  'THUOC_VE': 'thuộc về',
  'CHUA': 'chứa',
  'THAM_CHIEU': 'tham chiếu',
  'DINH_NGHIA': 'định nghĩa',
  'AP_DUNG_CHO': 'áp dụng cho',
  'BI_XU_LY': 'bị xử lý',
  'THAY_THE': 'thay thế',
  'SUA_DOI': 'sửa đổi',
  'BO_SUNG': 'bổ sung',
  'BAI_BO': 'bãi bỏ',
  'KE_TIEP': 'kế tiếp',
  'YEU_CAU': 'yêu cầu',
};

/**
 * Custom node component for legal entities
 */
const LegalNode = ({ data, selected }) => {
  const colors = nodeColors[data.type] || nodeColors.default;
  
  return (
    <div
      className={`px-3 py-2 rounded-lg shadow-lg border-2 transition-all cursor-pointer ${
        selected ? 'ring-2 ring-offset-2 ring-blue-500' : ''
      }`}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
        color: colors.text,
        minWidth: '120px',
        maxWidth: '200px',
      }}
    >
      <div className="text-[10px] opacity-80 uppercase tracking-wide mb-1">
        {data.type}
      </div>
      <div className="text-sm font-medium truncate" title={data.label}>
        {data.label}
      </div>
      {data.number && (
        <div className="text-xs opacity-80 mt-1">
          {data.number}
        </div>
      )}
    </div>
  );
};

const nodeTypes = {
  legal: LegalNode,
};

/**
 * Main Knowledge Graph Flow Component
 */
const KnowledgeGraphFlow = ({ selectedDocument, documents, onSelectDocument }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [filterTypes, setFilterTypes] = useState(['Luật', 'Chương', 'Điều']);
  const [showFilters, setShowFilters] = useState(false);

  // All available node types
  const allNodeTypes = ['Luật', 'Nghị định', 'Thông tư', 'Chương', 'Mục', 'Điều', 'Khoản', 'Điểm', 'Khái niệm'];

  const loadGraphData = useCallback(async (documentNumber) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${RAG_SERVICE_URL}/v1/kg/graph?document_number=${encodeURIComponent(documentNumber)}&limit=500`
      );

      if (!response.ok) {
        throw new Error(`Failed to load graph: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform to React Flow format
      const { flowNodes, flowEdges } = transformToFlowData(data.nodes, data.relationships);
      
      console.log('Graph data loaded:', {
        apiNodes: data.nodes?.length,
        apiRelationships: data.relationships?.length,
        flowNodes: flowNodes.length,
        flowEdges: flowEdges.length,
        sampleEdge: flowEdges[0],
      });
      
      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      console.error('Error loading graph:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [setNodes, setEdges]);

  // Load graph data when document changes
  useEffect(() => {
    if (selectedDocument?.document_number) {
      loadGraphData(selectedDocument.document_number);
    }
  }, [selectedDocument, loadGraphData]);

  // Transform API data to React Flow format
  const transformToFlowData = (apiNodes, apiRelationships) => {
    if (!apiNodes || apiNodes.length === 0) {
      return { flowNodes: [], flowEdges: [] };
    }

    // Group nodes by type for layout
    const nodesByType = {};
    apiNodes.forEach(node => {
      const type = node.type || 'default';
      if (!nodesByType[type]) nodesByType[type] = [];
      nodesByType[type].push(node);
    });

    // Remove duplicates - use node.id (Neo4j element_id) for deduplication
    // This is important because relationships use node.id for source/target
    const uniqueNodes = [];
    const seenIds = new Set();
    apiNodes.forEach(node => {
      const nodeKey = node.id; // Use Neo4j element_id, NOT properties.id
      if (!seenIds.has(nodeKey)) {
        seenIds.add(nodeKey);
        uniqueNodes.push(node);
      }
    });

    // Create flow nodes with hierarchical layout
    const flowNodes = [];
    const nodeIdMap = new Map(); // Map Neo4j element_id to flow ID
    
    // Layout configuration
    const levelY = {
      'Luật': 0, 'Nghị định': 0, 'Thông tư': 0,
      'Chương': 150,
      'Mục': 300,
      'Điều': 300,
      'Khoản': 450,
      'Điểm': 600,
      'Khái niệm': 450,
      'Hành vi cấm': 450,
      'Chế tài': 450,
    };

    const typeCounters = {};
    
    uniqueNodes.forEach((node, index) => {
      const type = node.type || 'default';
      if (!typeCounters[type]) typeCounters[type] = 0;
      
      const flowId = `node-${index}`;
      // Map Neo4j element_id (node.id) to flowId - this is what relationships use
      nodeIdMap.set(node.id, flowId);
      
      // Calculate position
      const y = levelY[type] ?? 300;
      const nodesOfType = uniqueNodes.filter(n => n.type === type).length;
      const x = (typeCounters[type] - nodesOfType / 2) * 220 + 400;
      typeCounters[type]++;

      flowNodes.push({
        id: flowId,
        type: 'legal',
        position: { x, y },
        data: {
          label: node.name || node.properties?.name || type,
          type: type,
          number: node.number || node.properties?.chapter_number || node.properties?.article_number,
          content: node.properties?.content,
          originalId: node.id, // Neo4j element_id
          properties: node.properties,
        },
      });
    });

    // Create flow edges
    const flowEdges = [];
    const seenEdges = new Set();
    
    // Debug: log nodeIdMap
    console.log('nodeIdMap size:', nodeIdMap.size);
    console.log('Sample nodeIdMap entries:', Array.from(nodeIdMap.entries()).slice(0, 3));
    
    if (apiRelationships && apiRelationships.length > 0) {
      console.log('Processing relationships:', apiRelationships.length);
      
      apiRelationships.forEach((rel, index) => {
        const sourceId = nodeIdMap.get(rel.source);
        const targetId = nodeIdMap.get(rel.target);
        
        if (index < 3) {
          console.log(`Rel ${index}: source=${rel.source} -> ${sourceId}, target=${rel.target} -> ${targetId}`);
        }
        
        if (sourceId && targetId) {
          const edgeKey = `${sourceId}-${targetId}-${rel.type}`;
          if (!seenEdges.has(edgeKey)) {
            seenEdges.add(edgeKey);
            
            const color = edgeColors[rel.type] || edgeColors.default;
            
            flowEdges.push({
              id: `edge-${index}`,
              source: sourceId,
              target: targetId,
              type: 'smoothstep',
              animated: rel.type === 'THAM_CHIEU',
              label: relationshipLabels[rel.type] || rel.type,
              labelStyle: { fontSize: 10, fill: color },
              style: { stroke: color, strokeWidth: 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: color,
              },
              data: { type: rel.type },
            });
          }
        }
      });
      
      console.log('Created flowEdges:', flowEdges.length);
    }

    return { flowNodes, flowEdges };
  };

  // Filter nodes and edges based on selected types
  const filteredData = useMemo(() => {
    const filteredNodes = nodes.filter(node => filterTypes.includes(node.data.type));
    const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = edges.filter(
      edge => filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target)
    );
    console.log('Filtered:', { 
      totalNodes: nodes.length, 
      filteredNodes: filteredNodes.length,
      totalEdges: edges.length,
      filteredEdges: filteredEdges.length,
      filterTypes 
    });
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [nodes, edges, filterTypes]);

  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node.data);
  }, []);

  // Toggle node type filter
  const toggleFilter = (type) => {
    setFilterTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 ${
      isFullscreen ? 'fixed inset-4 z-50' : ''
    }`}>
      {/* Header */}
      <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="5" r="3" />
              <circle cx="5" cy="19" r="3" />
              <circle cx="19" cy="19" r="3" />
              <line x1="12" y1="8" x2="5" y2="16" />
              <line x1="12" y1="8" x2="19" y2="16" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Đồ thị tri thức
            </h2>
            <p className="text-sm text-gray-500">
              {selectedDocument?.document_number || 'Chọn văn bản để xem đồ thị'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Document Selector */}
          <select
            value={selectedDocument?.document_number || ''}
            onChange={(e) => {
              const doc = documents?.find(d => d.document_number === e.target.value);
              if (doc) onSelectDocument(doc);
            }}
            className="px-3 py-1.5 text-sm border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700"
          >
            <option value="">Chọn văn bản...</option>
            {documents?.map((doc) => (
              <option key={doc.document_number} value={doc.document_number}>
                {doc.document_number} - {doc.name}
              </option>
            ))}
          </select>

          {/* Filter Button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 rounded-lg transition-colors ${
              showFilters ? 'bg-blue-100 text-blue-600' : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            title="Lọc loại node"
          >
            <Filter className="w-5 h-5" />
          </button>

          {/* Refresh */}
          <button
            onClick={() => loadGraphData(selectedDocument?.document_number)}
            disabled={isLoading || !selectedDocument}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Tải lại"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {/* Fullscreen */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            {isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="p-4 border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Hiển thị loại node:</p>
          <div className="flex flex-wrap gap-2">
            {allNodeTypes.map(type => {
              const colors = nodeColors[type] || nodeColors.default;
              const isActive = filterTypes.includes(type);
              return (
                <button
                  key={type}
                  onClick={() => toggleFilter(type)}
                  className={`px-3 py-1 text-sm rounded-full border-2 transition-all ${
                    isActive ? 'opacity-100' : 'opacity-40'
                  }`}
                  style={{
                    backgroundColor: isActive ? colors.bg : 'transparent',
                    borderColor: colors.border,
                    color: isActive ? colors.text : colors.bg,
                  }}
                >
                  {type}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Graph Container */}
      <div style={{ height: isFullscreen ? 'calc(100vh - 200px)' : '500px' }} className="relative">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto" />
              <p className="mt-2 text-gray-500">Đang tải đồ thị...</p>
            </div>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-red-500">
              <p className="font-medium">Lỗi tải đồ thị</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        ) : !selectedDocument ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <svg className="w-16 h-16 mx-auto mb-4 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="5" r="3" />
                <circle cx="5" cy="19" r="3" />
                <circle cx="19" cy="19" r="3" />
                <line x1="12" y1="8" x2="5" y2="16" />
                <line x1="12" y1="8" x2="19" y2="16" />
              </svg>
              <p>Chọn một văn bản để xem đồ thị tri thức</p>
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={filteredData.nodes}
            edges={filteredData.edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.1}
            maxZoom={2}
          >
            <Background color="#94a3b8" gap={20} />
            <Controls />
            <MiniMap 
              nodeColor={(node) => {
                const colors = nodeColors[node.data?.type] || nodeColors.default;
                return colors.bg;
              }}
              maskColor="rgba(0,0,0,0.1)"
            />
            
            {/* Stats Panel */}
            <Panel position="top-left" className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 m-2">
              <div className="text-sm space-y-1">
                <div className="font-medium text-gray-900 dark:text-white">
                  {selectedDocument?.name}
                </div>
                <div className="text-gray-500 text-xs">
                  {filteredData.nodes.length} nodes • {filteredData.edges.length} edges
                </div>
              </div>
            </Panel>

            {/* Legend */}
            <Panel position="bottom-left" className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 m-2">
              <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Chú thích quan hệ:</div>
              <div className="space-y-1 text-xs">
                {Object.entries(relationshipLabels).slice(0, 5).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2">
                    <div className="w-4 h-0.5" style={{ backgroundColor: edgeColors[key] || edgeColors.default }} />
                    <span className="text-gray-600 dark:text-gray-400">{label}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </ReactFlow>
        )}

        {/* Selected Node Detail */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border dark:border-gray-700 overflow-hidden">
            <div className="p-3 border-b dark:border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: (nodeColors[selectedNode.type] || nodeColors.default).bg }}
                />
                <span className="font-medium text-gray-900 dark:text-white">{selectedNode.type}</span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            <div className="p-3 max-h-64 overflow-y-auto">
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                {selectedNode.label}
              </h4>
              {selectedNode.number && (
                <p className="text-sm text-gray-500 mb-2">Số: {selectedNode.number}</p>
              )}
              {selectedNode.content && (
                <div className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 p-2 rounded max-h-32 overflow-y-auto">
                  {selectedNode.content.substring(0, 300)}
                  {selectedNode.content.length > 300 && '...'}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraphFlow;
