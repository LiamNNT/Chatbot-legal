import React, { useState } from 'react';
import { FileText, X, ChevronDown, ChevronUp } from 'lucide-react';
import { formatProcessingTime } from '../utils/helpers';

const RAGContextPanel = ({ ragContext }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [expandedDocs, setExpandedDocs] = useState(new Set());

  if (!ragContext || !ragContext.documents || ragContext.documents.length === 0) {
    return null;
  }

  const toggleDoc = (index) => {
    const newExpanded = new Set(expandedDocs);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedDocs(newExpanded);
  };

  return (
    <div className={`border-l border-gray-200 bg-gray-50 transition-all duration-300 ${
      isOpen ? 'w-80' : 'w-12'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white p-4">
        {isOpen ? (
          <>
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              <h3 className="font-semibold">Tài liệu tham khảo</h3>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-5 w-5" />
            </button>
          </>
        ) : (
          <button
            onClick={() => setIsOpen(true)}
            className="mx-auto text-gray-400 hover:text-gray-600"
          >
            <FileText className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Content */}
      {isOpen && (
        <div className="overflow-y-auto p-4" style={{ maxHeight: 'calc(100vh - 64px)' }}>
          {/* Metadata */}
          <div className="mb-4 rounded-lg bg-blue-50 p-3 text-sm">
            <p className="font-medium text-blue-900">
              Tìm thấy {ragContext.total_documents} tài liệu
            </p>
            {ragContext.processing_time && (
              <p className="text-blue-700">
                Thời gian: {formatProcessingTime(ragContext.processing_time)}
              </p>
            )}
            <p className="text-blue-700 capitalize">
              Chế độ: {ragContext.search_mode}
            </p>
          </div>

          {/* Documents */}
          <div className="space-y-3">
            {ragContext.documents.map((doc, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 bg-white overflow-hidden"
              >
                <button
                  onClick={() => toggleDoc(index)}
                  className="flex w-full items-center justify-between p-3 text-left hover:bg-gray-50"
                >
                  <div className="flex-1">
                    <h4 className="font-medium text-sm text-gray-900 line-clamp-2">
                      {doc.title}
                    </h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Độ liên quan: {(doc.score * 100).toFixed(1)}%
                    </p>
                  </div>
                  {expandedDocs.has(index) ? (
                    <ChevronUp className="h-4 w-4 text-gray-400 flex-shrink-0 ml-2" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0 ml-2" />
                  )}
                </button>
                
                {expandedDocs.has(index) && (
                  <div className="border-t border-gray-200 p-3 bg-gray-50">
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                      {doc.content}
                    </p>
                    {doc.metadata && Object.keys(doc.metadata).length > 0 && (
                      <div className="mt-2 pt-2 border-t border-gray-200">
                        <p className="text-xs text-gray-500 font-medium mb-1">Metadata:</p>
                        {Object.entries(doc.metadata).map(([key, value]) => (
                          <p key={key} className="text-xs text-gray-500">
                            {key}: {String(value)}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RAGContextPanel;
