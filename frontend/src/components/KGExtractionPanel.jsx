import React, { useState, useEffect, useRef } from 'react';

const RAG_SERVICE_URL = import.meta.env.VITE_RAG_SERVICE_URL || 'http://localhost:8002';

/**
 * Knowledge Graph Extraction Component
 * 
 * Allows users to:
 * 1. Upload PDF files
 * 2. Run Two-Stage extraction (VLM + LLM)
 * 3. View extraction progress in real-time
 * 4. Download/view extraction results
 */
const KGExtractionPanel = ({ onClose }) => {
  const [file, setFile] = useState(null);
  const [category, setCategory] = useState('Quy chế Đào tạo');
  const [pushToNeo4j, setPushToNeo4j] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  // Poll for status updates
  useEffect(() => {
    if (jobId && status?.status !== 'completed' && status?.status !== 'failed') {
      pollingRef.current = setInterval(async () => {
        try {
          const response = await fetch(`${RAG_SERVICE_URL}/v1/extraction/status/${jobId}`);
          const data = await response.json();
          setStatus(data);
          
          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(pollingRef.current);
            
            if (data.status === 'completed') {
              // Fetch result
              const resultResponse = await fetch(`${RAG_SERVICE_URL}/v1/extraction/result/${jobId}`);
              const resultData = await resultResponse.json();
              setResult(resultData);
            }
          }
        } catch (err) {
          console.error('Error polling status:', err);
        }
      }, 1000);
    }
    
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [jobId, status?.status]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Vui lòng chọn file PDF');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Vui lòng chọn file PDF');
      return;
    }

    setIsUploading(true);
    setError(null);
    setResult(null);
    setStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const url = new URL(`${RAG_SERVICE_URL}/v1/extraction/upload`);
      url.searchParams.append('category', category);
      url.searchParams.append('push_to_neo4j', pushToNeo4j);

      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setJobId(data.job_id);
      setStatus(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = () => {
    if (result) {
      const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `extraction_${jobId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleReset = () => {
    setFile(null);
    setJobId(null);
    setStatus(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getProgressColor = () => {
    if (status?.status === 'failed') return 'bg-red-500';
    if (status?.status === 'completed') return 'bg-green-500';
    return 'bg-blue-500';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Trích xuất Knowledge Graph
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Two-Stage Pipeline: VLM + LLM
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Upload Section */}
          {!status && (
            <div className="space-y-4">
              {/* File Drop Zone */}
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
                  ${file ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'}`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
                
                {file ? (
                  <div className="flex items-center justify-center gap-3">
                    <svg className="w-10 h-10 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <div className="text-left">
                      <p className="font-medium text-gray-900 dark:text-white">{file.name}</p>
                      <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <svg className="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="text-gray-600 dark:text-gray-300 mb-2">
                      Kéo thả file PDF hoặc click để chọn
                    </p>
                    <p className="text-sm text-gray-400">
                      Hỗ trợ các văn bản quy định, quy chế
                    </p>
                  </>
                )}
              </div>

              {/* Options */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Danh mục
                  </label>
                  <input
                    type="text"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Quy chế Đào tạo"
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={pushToNeo4j}
                      onChange={(e) => setPushToNeo4j(e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Đẩy lên Neo4j
                    </span>
                  </label>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}

              {/* Submit Button */}
              <button
                onClick={handleUpload}
                disabled={!file || isUploading}
                className={`w-full py-3 px-4 rounded-lg font-medium transition-all
                  ${file && !isUploading
                    ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 shadow-lg hover:shadow-xl'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                  }`}
              >
                {isUploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Đang tải lên...
                  </span>
                ) : (
                  'Bắt đầu trích xuất'
                )}
              </button>
            </div>
          )}

          {/* Processing Status */}
          {status && (
            <div className="space-y-4">
              {/* Progress Bar */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600 dark:text-gray-300">{status.current_step}</span>
                  <span className="font-medium text-gray-900 dark:text-white">{status.progress}%</span>
                </div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${getProgressColor()}`}
                    style={{ width: `${status.progress}%` }}
                  />
                </div>
              </div>

              {/* Status Badge */}
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-sm font-medium
                  ${status.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                    status.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  }`}>
                  {status.status === 'completed' ? '✓ Hoàn thành' :
                   status.status === 'failed' ? '✗ Thất bại' :
                   '⟳ Đang xử lý'}
                </span>
              </div>

              {/* Error Message */}
              {status.error && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  {status.error}
                </div>
              )}

              {/* Stats */}
              {status.stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-center">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {status.stats.pages || 0}
                    </div>
                    <div className="text-xs text-gray-500">Trang</div>
                  </div>
                  <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {status.stats.articles || 0}
                    </div>
                    <div className="text-xs text-gray-500">Điều</div>
                  </div>
                  <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {status.stats.entities || 0}
                    </div>
                    <div className="text-xs text-gray-500">Thực thể</div>
                  </div>
                  <div className="p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg text-center">
                    <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                      {status.stats.relations || 0}
                    </div>
                    <div className="text-xs text-gray-500">Quan hệ</div>
                  </div>
                </div>
              )}

              {/* Result Preview */}
              {result && (
                <div className="space-y-3">
                  <h3 className="font-medium text-gray-900 dark:text-white">Kết quả trích xuất</h3>
                  
                  {/* Entities Preview */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-2">
                      Thực thể ({result.stage2_semantic?.entities?.length || 0})
                    </h4>
                    <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
                      {result.stage2_semantic?.entities?.slice(0, 20).map((entity, idx) => (
                        <span
                          key={idx}
                          className={`px-2 py-1 rounded-full text-xs font-medium
                            ${entity.type === 'PERSON' ? 'bg-pink-100 text-pink-700' :
                              entity.type === 'ORGANIZATION' ? 'bg-blue-100 text-blue-700' :
                              entity.type === 'REGULATION' ? 'bg-purple-100 text-purple-700' :
                              entity.type === 'CONDITION' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-gray-100 text-gray-700'
                            }`}
                        >
                          {entity.text}
                        </span>
                      ))}
                      {(result.stage2_semantic?.entities?.length || 0) > 20 && (
                        <span className="px-2 py-1 text-xs text-gray-500">
                          +{result.stage2_semantic.entities.length - 20} khác
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Download Button */}
                  <div className="flex gap-3">
                    <button
                      onClick={handleDownload}
                      className="flex-1 py-2 px-4 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Tải JSON
                    </button>
                    <button
                      onClick={handleReset}
                      className="py-2 px-4 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                      Trích xuất mới
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default KGExtractionPanel;
