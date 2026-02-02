import React, { useState, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  FileText,
  Scale,
  FileCode,
  ScrollText,
} from 'lucide-react';

/**
 * Document Structure Tree Component
 * Displays the hierarchical structure of a legal document
 */
const DocumentStructureTree = ({ documentNumber, onSelectNode }) => {
  const [tree, setTree] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  const RAG_SERVICE_URL = import.meta.env.VITE_RAG_SERVICE_URL || 'http://localhost:8000';

  // Node type configuration
  const nodeTypeConfig = {
    'Luật': { color: '#3B82F6', icon: Scale },
    'Nghị định': { color: '#8B5CF6', icon: FileCode },
    'Thông tư': { color: '#10B981', icon: ScrollText },
    'Chương': { color: '#F59E0B', icon: FileText },
    'Mục': { color: '#EC4899', icon: FileText },
    'Điều': { color: '#06B6D4', icon: FileText },
    'Khoản': { color: '#84CC16', icon: FileText },
    'Điểm': { color: '#F97316', icon: FileText },
  };

  useEffect(() => {
    if (documentNumber) {
      loadTree();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentNumber]);

  const loadTree = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `${RAG_SERVICE_URL}/v1/kg/document/structure?document_number=${encodeURIComponent(documentNumber)}`
      );
      if (response.ok) {
        const data = await response.json();
        // Handle both formats
        const treeData = data.tree || (data.id ? data : null);
        setTree(treeData);
        // Auto-expand root
        if (treeData?.id) {
          setExpandedNodes(new Set([treeData.id]));
        }
      }
    } catch (error) {
      console.error('Error loading tree:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleExpand = (nodeId) => {
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

  const handleNodeClick = (node) => {
    setSelectedNodeId(node.id);
    onSelectNode?.(node);
  };

  const renderNode = (node, depth = 0) => {
    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    const isSelected = selectedNodeId === node.id;
    const config = nodeTypeConfig[node.type] || { color: '#6B7280', icon: FileText };
    const Icon = config.icon;

    return (
      <div key={node.id}>
        <div
          onClick={() => {
            handleNodeClick(node);
            if (hasChildren) toggleExpand(node.id);
          }}
          className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
            isSelected
              ? 'bg-blue-100 dark:bg-blue-900/30'
              : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'
          }`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400" />
              )
            ) : null}
          </div>

          <div
            className="w-6 h-6 rounded flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: `${config.color}20` }}
          >
            <Icon className="w-3.5 h-3.5" style={{ color: config.color }} />
          </div>

          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {node.name}
            </span>
          </div>
        </div>

        {hasChildren && isExpanded && (
          <div className="ml-4 border-l border-gray-200 dark:border-gray-700">
            {node.children.map((child) => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="text-center py-8 text-gray-500">
        Đang tải cấu trúc...
      </div>
    );
  }

  if (!tree) {
    return (
      <div className="text-center py-8 text-gray-500">
        Không có dữ liệu cấu trúc
      </div>
    );
  }

  return <div className="space-y-1">{renderNode(tree)}</div>;
};

export default DocumentStructureTree;
