import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader,
  RefreshCw,
  Database,
  Search,
  Network,
  BarChart3,
  FileStack,
  Scale,
  FileCode,
  ScrollText,
  Trash2,
  Eye,
  GitBranch,
} from 'lucide-react';
import {
  useAllDocuments,
  useKGStats,
  useUploadDocument,
  useDeleteDocument,
  useJobStatus,
} from '../hooks/useExtraction';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';
import KnowledgeGraphFlow from './KnowledgeGraphFlow';

/**
 * Legal Document Extraction Page
 * Dedicated page for extracting and visualizing Vietnamese legal documents
 * Supports: Luật, Nghị định, Thông tư
 */
const LegalDocExtractionPage = ({ onNavigateToChat }) => {
  // Tab state
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'documents' | 'content' | 'graph' | 'stats'

  // Upload state
  const [file, setFile] = useState(null);
  const [lawId, setLawId] = useState('');
  const [pushToNeo4j, setPushToNeo4j] = useState(true);
  const [indexWeaviate, setIndexWeaviate] = useState(true);
  const [indexOpenSearch, setIndexOpenSearch] = useState(true);
  const [uploadError, setUploadError] = useState(null);

  // Current job being tracked
  const [currentJobId, setCurrentJobId] = useState(null);

  // Graph viewer
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [filterDocKind, setFilterDocKind] = useState('all');

  const fileInputRef = useRef(null);

  // ============================================================================
  // React Query Hooks
  // ============================================================================
  
  // Fetch all documents (KG + Jobs merged)
  const { 
    documents: allDocuments, 
    isLoading: isLoadingDocs, 
    refetch: refetchDocs 
  } = useAllDocuments();

  // Fetch KG statistics
  const { data: statsData } = useKGStats();
  const stats = statsData?.stats;

  // Upload mutation
  const uploadMutation = useUploadDocument();
  
  // Delete mutation
  const deleteMutation = useDeleteDocument();

  // Poll current job status
  const { data: currentJob } = useJobStatus(currentJobId, !!currentJobId);

  // Clear job tracking when completed
  if (currentJob && ['completed', 'failed'].includes(currentJob.status) && currentJobId) {
    // Use setTimeout to avoid state update during render
    setTimeout(() => {
      setCurrentJobId(null);
      refetchDocs();
    }, 1000);
  }

  // ============================================================================
  // Config
  // ============================================================================

  // Doc kind display config
  const docKindConfig = {
    LAW: {
      label: 'Luật',
      icon: Scale,
      color: 'text-blue-600 bg-blue-100',
      borderColor: 'border-blue-500',
    },
    DECREE: {
      label: 'Nghị định',
      icon: FileCode,
      color: 'text-purple-600 bg-purple-100',
      borderColor: 'border-purple-500',
    },
    CIRCULAR: {
      label: 'Thông tư',
      icon: ScrollText,
      color: 'text-green-600 bg-green-100',
      borderColor: 'border-green-500',
    },
    UNKNOWN: {
      label: 'Khác',
      icon: FileText,
      color: 'text-gray-600 bg-gray-100',
      borderColor: 'border-gray-500',
    },
  };

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const validExtensions = ['.doc', '.docx'];
      const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
      
      if (validExtensions.includes(ext)) {
        setFile(selectedFile);
        setUploadError(null);
        
        // Auto-detect law_id from filename if not set
        if (!lawId) {
          const match = selectedFile.name.match(/(\d+[-/]\d+[-/][A-Z]+\d*)/i);
          if (match) {
            setLawId(match[1]);
          }
        }
      } else {
        setUploadError('Vui lòng chọn file Word (.doc hoặc .docx)');
        setFile(null);
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setUploadError('Vui lòng chọn file');
      return;
    }

    setUploadError(null);

    try {
      const result = await uploadMutation.mutateAsync({
        file,
        options: {
          lawId: lawId || null,
          runKG: pushToNeo4j,
          runVector: indexWeaviate || indexOpenSearch,
        },
      });

      setCurrentJobId(result.job_id);
      setFile(null);
      setLawId('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      setUploadError(error.message);
    }
  };

  const handleDeleteDocument = async (documentNumber) => {
    console.log('handleDeleteDocument called with:', documentNumber);
    
    if (!documentNumber) {
      alert('Không tìm thấy mã tài liệu để xóa');
      return;
    }
    
    if (!window.confirm(`Xóa tài liệu ${documentNumber}?`)) {
      return;
    }

    try {
      console.log('Calling deleteMutation for:', documentNumber);
      await deleteMutation.mutateAsync(documentNumber);
      alert(`Đã xóa tài liệu ${documentNumber}`);
    } catch (error) {
      console.error('Error deleting document:', error);
      alert(`Lỗi khi xóa: ${error.message}`);
    }
  };

  const handleViewDocument = (doc) => {
    setSelectedDocument(doc);
    setActiveTab('content');
  };

  const handleViewGraph = (doc) => {
    setSelectedDocument(doc);
    setActiveTab('graph');
  };

  // ============================================================================
  // UI Helpers
  // ============================================================================

  const getStatusBadge = (status) => {
    const config = {
      pending: { color: 'bg-yellow-100 text-yellow-800', icon: Loader, animate: true },
      processing: { color: 'bg-blue-100 text-blue-800', icon: Loader, animate: true },
      completed: { color: 'bg-green-100 text-green-800', icon: CheckCircle, animate: false },
      failed: { color: 'bg-red-100 text-red-800', icon: AlertCircle, animate: false },
    };

    const { color, icon: Icon, animate } = config[status] || config.pending;

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
        <Icon className={`w-3.5 h-3.5 ${animate ? 'animate-spin' : ''}`} />
        {status === 'pending' && 'Đang chờ'}
        {status === 'processing' && 'Đang xử lý'}
        {status === 'completed' && 'Hoàn thành'}
        {status === 'failed' && 'Thất bại'}
      </span>
    );
  };

  const getDocKindBadge = (docKind) => {
    const config = docKindConfig[docKind] || docKindConfig.UNKNOWN;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
        <Icon className="w-3.5 h-3.5" />
        {config.label}
      </span>
    );
  };

  // Computed values using React Query data
  const isUploading = uploadMutation.isPending;
  const isLoadingJobs = isLoadingDocs;
  const jobs = allDocuments || [];
  
  // Debug log
  console.log('allDocuments:', allDocuments);
  console.log('jobs:', jobs);
  
  const filteredJobs = filterDocKind === 'all' 
    ? jobs 
    : jobs.filter(job => job.doc_kind === filterDocKind);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Network className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  Trích xuất Văn bản Pháp luật
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Luật • Nghị định • Thông tư
                </p>
              </div>
            </div>
            
            <button
              onClick={onNavigateToChat}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <span>← Quay lại Chat</span>
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white dark:bg-gray-800 border-b dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-1">
            {[
              { id: 'upload', label: 'Tải lên', icon: Upload },
              { id: 'documents', label: 'Danh sách', icon: FileStack },
              { id: 'content', label: 'Nội dung', icon: FileText },
              { id: 'graph', label: 'Đồ thị tri thức', icon: GitBranch },
              { id: 'stats', label: 'Thống kê', icon: BarChart3 },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload Card */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Upload className="w-5 h-5 text-blue-500" />
                Tải lên văn bản pháp luật
              </h2>

              {/* Document Types Info */}
              <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200 mb-3">
                  Hỗ trợ các loại văn bản:
                </p>
                <div className="flex flex-wrap gap-2">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300 rounded-lg text-sm">
                    <Scale className="w-4 h-4" />
                    Luật (QH*)
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 dark:bg-purple-800/50 text-purple-700 dark:text-purple-300 rounded-lg text-sm">
                    <FileCode className="w-4 h-4" />
                    Nghị định (NĐ-CP)
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-100 dark:bg-green-800/50 text-green-700 dark:text-green-300 rounded-lg text-sm">
                    <ScrollText className="w-4 h-4" />
                    Thông tư (TT-*)
                  </span>
                </div>
              </div>

              {/* File Upload Zone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                  file
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".doc,.docx"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {file ? (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-16 h-16 bg-blue-100 dark:bg-blue-800/50 rounded-xl flex items-center justify-center">
                      <FileText className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{file.name}</p>
                      <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                      className="text-sm text-red-500 hover:text-red-700"
                    >
                      Xóa file
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center">
                      <Upload className="w-8 h-8 text-gray-400" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-700 dark:text-gray-300">
                        Kéo thả file hoặc click để chọn
                      </p>
                      <p className="text-sm text-gray-500">Hỗ trợ .doc, .docx</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Options */}
              <div className="mt-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Số hiệu văn bản (tùy chọn)
                  </label>
                  <input
                    type="text"
                    value={lawId}
                    onChange={(e) => setLawId(e.target.value)}
                    placeholder="VD: 20/2023/QH15, 168/2024/NĐ-CP"
                    className="w-full px-4 py-2.5 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <p className="text-xs text-gray-500 mt-1">Để trống để tự động nhận diện</p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <label className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700">
                    <input
                      type="checkbox"
                      checked={pushToNeo4j}
                      onChange={(e) => setPushToNeo4j(e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">Neo4j (KG)</span>
                  </label>
                  <label className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700">
                    <input
                      type="checkbox"
                      checked={indexWeaviate}
                      onChange={(e) => setIndexWeaviate(e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">Weaviate (Vector)</span>
                  </label>
                  <label className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700">
                    <input
                      type="checkbox"
                      checked={indexOpenSearch}
                      onChange={(e) => setIndexOpenSearch(e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">OpenSearch (BM25)</span>
                  </label>
                </div>
              </div>

              {/* Error */}
              {uploadError && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-700 dark:text-red-300">{uploadError}</p>
                  </div>
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={!file || isUploading}
                className="mt-6 w-full py-3 px-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all"
              >
                {isUploading ? (
                  <>
                    <Loader className="w-5 h-5 animate-spin" />
                    Đang tải lên...
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    Bắt đầu trích xuất
                  </>
                )}
              </button>
            </div>

            {/* Current Job Status */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Loader className="w-5 h-5 text-purple-500" />
                Trạng thái xử lý
              </h2>

              {currentJob ? (
                <div className="space-y-4">
                  {/* Job Info */}
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Job ID:</span>
                      <code className="text-sm font-mono text-gray-700 dark:text-gray-300">
                        {currentJob.job_id?.slice(0, 8)}...
                      </code>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">Trạng thái:</span>
                      {getStatusBadge(currentJob.status)}
                    </div>
                    {currentJob.doc_kind && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Loại văn bản:</span>
                        {getDocKindBadge(currentJob.doc_kind)}
                      </div>
                    )}
                    {currentJob.document_number && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">Số hiệu:</span>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {currentJob.document_number}
                        </span>
                      </div>
                    )}
                    {currentJob.filename && (
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">File:</span>
                        <span className="text-sm text-gray-700 dark:text-gray-300 truncate max-w-[200px]">
                          {currentJob.filename}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Progress */}
                  {currentJob.status === 'processing' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-500">Tiến trình</span>
                        <span className="text-gray-700 dark:text-gray-300">
                          {currentJob.progress || 0}%
                        </span>
                      </div>
                      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-300"
                          style={{ width: `${currentJob.progress || 0}%` }}
                        />
                      </div>
                      {currentJob.current_step && (
                        <p className="text-sm text-gray-500">{currentJob.current_step}</p>
                      )}
                    </div>
                  )}

                  {/* Success */}
                  {currentJob.status === 'completed' && (
                    <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                      <div className="flex items-start gap-3">
                        <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-green-800 dark:text-green-200">
                            Trích xuất thành công!
                          </p>
                          {currentJob.stats && (
                            <div className="mt-2 text-sm text-green-700 dark:text-green-300 space-y-1">
                              <p>Chunks: {currentJob.stats.chunks_count || 0}</p>
                              <p>Nodes: {currentJob.stats.nodes_count || 0}</p>
                              <p>Relationships: {currentJob.stats.relationships_count || 0}</p>
                            </div>
                          )}
                          <button
                            onClick={() => handleViewDocument(currentJob)}
                            className="mt-3 inline-flex items-center gap-1.5 text-sm text-green-600 hover:text-green-800"
                          >
                            <Eye className="w-4 h-4" />
                            Xem đồ thị tri thức
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Failed */}
                  {currentJob.status === 'failed' && (
                    <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0" />
                        <div>
                          <p className="font-medium text-red-800 dark:text-red-200">
                            Trích xuất thất bại
                          </p>
                          <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                            {currentJob.error || 'Đã xảy ra lỗi'}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Clear Button */}
                  {['completed', 'failed'].includes(currentJob.status) && (
                    <button
                      onClick={() => setCurrentJobId(null)}
                      className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                    >
                      Xóa kết quả
                    </button>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-gray-500">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Chưa có job nào đang xử lý</p>
                  <p className="text-sm">Tải lên văn bản để bắt đầu</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Documents Tab */}
        {activeTab === 'documents' && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700">
            {/* Header */}
            <div className="p-4 border-b dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <FileStack className="w-5 h-5 text-blue-500" />
                Danh sách tài liệu ({filteredJobs.length})
              </h2>
              <div className="flex items-center gap-3">
                {/* Filter */}
                <select
                  value={filterDocKind}
                  onChange={(e) => setFilterDocKind(e.target.value)}
                  className="px-3 py-1.5 text-sm border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                >
                  <option value="all">Tất cả loại</option>
                  <option value="LAW">Luật</option>
                  <option value="DECREE">Nghị định</option>
                  <option value="CIRCULAR">Thông tư</option>
                </select>
                <button
                  onClick={() => refetchDocs()}
                  disabled={isLoadingJobs}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                >
                  <RefreshCw className={`w-5 h-5 ${isLoadingJobs ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            {/* Jobs List */}
            <div className="divide-y dark:divide-gray-700">
              {isLoadingJobs ? (
                <div className="p-8 text-center">
                  <Loader className="w-8 h-8 mx-auto animate-spin text-blue-500" />
                  <p className="mt-2 text-gray-500">Đang tải...</p>
                </div>
              ) : filteredJobs.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Chưa có tài liệu nào</p>
                </div>
              ) : (
                filteredJobs.map((job) => (
                  <div
                    key={job.job_id}
                    className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          docKindConfig[job.doc_kind]?.color || 'bg-gray-100 text-gray-600'
                        }`}>
                          {(() => {
                            const Icon = docKindConfig[job.doc_kind]?.icon || FileText;
                            return <Icon className="w-5 h-5" />;
                          })()}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-medium text-gray-900 dark:text-white truncate">
                              {job.document_number || job.filename || job.job_id.slice(0, 8)}
                            </h3>
                            {getDocKindBadge(job.doc_kind || 'UNKNOWN')}
                            {getStatusBadge(job.status)}
                          </div>
                          {job.filename && (
                            <p className="text-sm text-gray-500 truncate">{job.filename}</p>
                          )}
                          {job.issuer && (
                            <p className="text-xs text-gray-400 mt-1">Ban hành: {job.issuer}</p>
                          )}
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(job.created_at).toLocaleString('vi-VN')}
                          </p>
                        </div>
                      </div>
                      
                      {job.status === 'completed' && (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleViewDocument(job)}
                            className="p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg"
                            title="Xem nội dung"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleViewGraph(job)}
                            className="p-2 text-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg"
                            title="Xem đồ thị"
                          >
                            <GitBranch className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              console.log('Delete button clicked, job:', job);
                              handleDeleteDocument(job.document_number);
                            }}
                            className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                            title="Xóa"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Content Tab - Tree view of extracted content */}
        {activeTab === 'content' && (
          <KnowledgeGraphViewer
            selectedDocument={selectedDocument}
            onSelectDocument={setSelectedDocument}
            documents={jobs.filter(j => j.status === 'completed')}
          />
        )}

        {/* Graph Tab - Interactive Knowledge Graph visualization */}
        {activeTab === 'graph' && (
          <KnowledgeGraphFlow
            selectedDocument={selectedDocument}
            onSelectDocument={setSelectedDocument}
            documents={jobs.filter(j => j.status === 'completed')}
          />
        )}

        {/* Stats Tab */}
        {activeTab === 'stats' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Summary Cards */}
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Tổng văn bản</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                    {stats?.total_documents || jobs.filter(j => j.status === 'completed').length}
                  </p>
                </div>
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
                  <FileStack className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Nodes (Neo4j)</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                    {stats?.total_nodes?.toLocaleString() || '—'}
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-xl flex items-center justify-center">
                  <Database className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Relationships</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                    {stats?.total_relationships?.toLocaleString() || '—'}
                  </p>
                </div>
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center">
                  <Network className="w-6 h-6 text-green-600 dark:text-green-400" />
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Vectors (Weaviate)</p>
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                    {stats?.total_vectors?.toLocaleString() || '—'}
                  </p>
                </div>
                <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-xl flex items-center justify-center">
                  <Search className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                </div>
              </div>
            </div>

            {/* Document Types Distribution */}
            <div className="md:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Phân bố theo loại văn bản
              </h3>
              <div className="space-y-4">
                {['LAW', 'DECREE', 'CIRCULAR'].map((docKind) => {
                  const count = jobs.filter(j => j.doc_kind === docKind && j.status === 'completed').length;
                  const total = jobs.filter(j => j.status === 'completed').length || 1;
                  const percentage = Math.round((count / total) * 100);
                  const config = docKindConfig[docKind];

                  return (
                    <div key={docKind}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                          <config.icon className="w-4 h-4" />
                          {config.label}
                        </span>
                        <span className="text-sm text-gray-500">{count} ({percentage}%)</span>
                      </div>
                      <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${config.color.split(' ')[1]} transition-all duration-500`}
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Node Types */}
            <div className="md:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Phân bố nodes theo loại
              </h3>
              {stats?.node_types ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {Object.entries(stats.node_types).map(([type, count]) => (
                    <div key={type} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <p className="text-sm text-gray-500 dark:text-gray-400">{type}</p>
                      <p className="text-xl font-semibold text-gray-900 dark:text-white">
                        {count.toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Chưa có dữ liệu thống kê</p>
                  <button
                    onClick={() => refetchDocs()}
                    className="mt-3 text-sm text-blue-500 hover:text-blue-700"
                  >
                    Tải lại
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default LegalDocExtractionPage;
