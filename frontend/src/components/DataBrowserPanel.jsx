import React, { useState, useEffect, useCallback } from 'react';
import {
  getNeo4jStats,
  getNeo4jArticles,
  getNeo4jArticleDetail,
  getNeo4jEntities,
  getNeo4jRelations,
  getNeo4jCategories,
} from '../services/api';

/**
 * DataBrowserPanel - Component to browse extracted data from Neo4j
 * Shows Articles, Entities, Relations, and Categories
 */
const DataBrowserPanel = ({ onClose }) => {
  // Tab state
  const [activeTab, setActiveTab] = useState('overview');
  
  // Loading states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Data states
  const [stats, setStats] = useState(null);
  const [articles, setArticles] = useState([]);
  const [articlesTotal, setArticlesTotal] = useState(0);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [entities, setEntities] = useState([]);
  const [entitiesTotal, setEntitiesTotal] = useState(0);
  const [entityTypes, setEntityTypes] = useState([]);
  const [relations, setRelations] = useState([]);
  const [relationsTotal, setRelationsTotal] = useState(0);
  const [relationTypes, setRelationTypes] = useState([]);
  const [categories, setCategories] = useState([]);
  
  // Filter states
  const [articleSearch, setArticleSearch] = useState('');
  const [articleCategory, setArticleCategory] = useState('');
  const [articlePage, setArticlePage] = useState(0);
  
  const [entitySearch, setEntitySearch] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [entityPage, setEntityPage] = useState(0);
  
  const [relationTypeFilter, setRelationTypeFilter] = useState('');
  const [relationPage, setRelationPage] = useState(0);

  const PAGE_SIZE = 20;

  // Fetch initial stats
  const fetchStats = useCallback(async () => {
    try {
      const data = await getNeo4jStats();
      if (data.status === 'connected') {
        setStats(data.stats);
      } else {
        setError(data.error || 'Failed to connect to Neo4j');
      }
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // Fetch categories
  const fetchCategories = useCallback(async () => {
    try {
      const data = await getNeo4jCategories();
      if (data.status === 'success') {
        setCategories(data.categories || []);
      }
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  }, []);

  // Fetch articles
  const fetchArticles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNeo4jArticles({
        skip: articlePage * PAGE_SIZE,
        limit: PAGE_SIZE,
        search: articleSearch,
        category: articleCategory,
      });
      if (data.status === 'success') {
        setArticles(data.articles || []);
        setArticlesTotal(data.total || 0);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [articlePage, articleSearch, articleCategory]);

  // Fetch article detail
  const fetchArticleDetail = useCallback(async (articleId) => {
    setLoading(true);
    try {
      const data = await getNeo4jArticleDetail(articleId);
      if (data.status === 'success') {
        setSelectedArticle(data.article);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch entities
  const fetchEntities = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNeo4jEntities({
        skip: entityPage * PAGE_SIZE,
        limit: PAGE_SIZE,
        entityType: entityTypeFilter,
        search: entitySearch,
      });
      if (data.status === 'success') {
        setEntities(data.entities || []);
        setEntitiesTotal(data.total || 0);
        setEntityTypes(data.entity_types || []);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [entityPage, entityTypeFilter, entitySearch]);

  // Fetch relations
  const fetchRelations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNeo4jRelations({
        skip: relationPage * PAGE_SIZE,
        limit: PAGE_SIZE,
        relationType: relationTypeFilter,
      });
      if (data.status === 'success') {
        setRelations(data.relations || []);
        setRelationsTotal(data.total || 0);
        setRelationTypes(data.relation_types || []);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [relationPage, relationTypeFilter]);

  // Initial load
  useEffect(() => {
    fetchStats();
    fetchCategories();
  }, [fetchStats, fetchCategories]);

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === 'articles') {
      fetchArticles();
    } else if (activeTab === 'entities') {
      fetchEntities();
    } else if (activeTab === 'relations') {
      fetchRelations();
    }
  }, [activeTab, fetchArticles, fetchEntities, fetchRelations]);

  // Tab buttons
  const tabs = [
    { id: 'overview', label: 'Tổng quan', icon: '📊' },
    { id: 'articles', label: 'Điều khoản', icon: '📄' },
    { id: 'entities', label: 'Thực thể', icon: '🏷️' },
    { id: 'relations', label: 'Quan hệ', icon: '🔗' },
  ];

  // Pagination component
  const Pagination = ({ total, page, setPage }) => {
    const totalPages = Math.ceil(total / PAGE_SIZE);
    return (
      <div className="flex items-center justify-between mt-4 text-sm">
        <span className="text-gray-400">
          Hiển thị {page * PAGE_SIZE + 1} - {Math.min((page + 1) * PAGE_SIZE, total)} / {total}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-3 py-1 bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
          >
            ← Trước
          </button>
          <span className="px-3 py-1">
            Trang {page + 1} / {totalPages || 1}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1 bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
          >
            Sau →
          </button>
        </div>
      </div>
    );
  };

  // Render Overview tab
  const renderOverview = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-blue-400">📊 Thống kê cơ sở dữ liệu</h3>
      
      {stats ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-blue-400">{stats.docs || 0}</div>
            <div className="text-gray-400 text-sm">Tài liệu</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-green-400">{stats.articles || 0}</div>
            <div className="text-gray-400 text-sm">Điều khoản</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-yellow-400">{stats.clauses || 0}</div>
            <div className="text-gray-400 text-sm">Khoản</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-purple-400">{stats.entities || 0}</div>
            <div className="text-gray-400 text-sm">Thực thể</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-pink-400">{stats.mentions || 0}</div>
            <div className="text-gray-400 text-sm">Liên kết</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4 text-center">
            <div className="text-3xl font-bold text-orange-400">{stats.total_rels || 0}</div>
            <div className="text-gray-400 text-sm">Tổng quan hệ</div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-400 py-8">
          {error ? `Lỗi: ${error}` : 'Đang tải...'}
        </div>
      )}

      {/* Categories */}
      {categories.length > 0 && (
        <div className="mt-6">
          <h4 className="text-md font-semibold text-gray-300 mb-3">📁 Danh mục</h4>
          <div className="space-y-2">
            {categories.map((cat, idx) => (
              <div key={idx} className="bg-gray-800 rounded-lg p-3 flex justify-between items-center">
                <span className="text-white">{cat.name}</span>
                <div className="flex gap-4 text-sm text-gray-400">
                  <span>{cat.article_count || 0} điều</span>
                  <span>{cat.chapter_count || 0} chương</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  // Render Articles tab
  const renderArticles = () => (
    <div className="space-y-4">
      {/* Search and Filter */}
      <div className="flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Tìm kiếm điều khoản..."
          value={articleSearch}
          onChange={(e) => {
            setArticleSearch(e.target.value);
            setArticlePage(0);
          }}
          className="flex-1 min-w-48 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white"
        />
        <select
          value={articleCategory}
          onChange={(e) => {
            setArticleCategory(e.target.value);
            setArticlePage(0);
          }}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white"
        >
          <option value="">Tất cả danh mục</option>
          {categories.map((cat, idx) => (
            <option key={idx} value={cat.name}>{cat.name}</option>
          ))}
        </select>
        <button
          onClick={fetchArticles}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          🔍 Tìm
        </button>
      </div>

      {/* Articles List */}
      {loading ? (
        <div className="text-center py-8 text-gray-400">Đang tải...</div>
      ) : selectedArticle ? (
        // Article Detail View
        <div className="bg-gray-800 rounded-lg p-4">
          <button
            onClick={() => setSelectedArticle(null)}
            className="mb-4 text-blue-400 hover:text-blue-300"
          >
            ← Quay lại danh sách
          </button>
          
          <h3 className="text-xl font-bold text-white mb-2">{selectedArticle.title}</h3>
          <div className="text-sm text-gray-400 mb-4">
            ID: {selectedArticle.id} | Danh mục: {selectedArticle.category || 'N/A'}
          </div>
          
          {/* Full Text */}
          <div className="bg-gray-900 rounded-lg p-4 mb-4 max-h-64 overflow-y-auto">
            <h4 className="text-sm font-semibold text-gray-400 mb-2">Nội dung:</h4>
            <pre className="whitespace-pre-wrap text-gray-300 text-sm">
              {selectedArticle.full_text}
            </pre>
          </div>
          
          {/* Clauses */}
          {selectedArticle.clauses?.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-400 mb-2">
                Các khoản ({selectedArticle.clauses.length}):
              </h4>
              <div className="space-y-2">
                {selectedArticle.clauses.map((clause, idx) => (
                  <div key={idx} className="bg-gray-900 rounded p-3 text-sm">
                    <div className="font-medium text-yellow-400">{clause.title}</div>
                    <div className="text-gray-400 mt-1 line-clamp-3">{clause.full_text}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Entities */}
          {selectedArticle.entities?.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-400 mb-2">
                Thực thể liên quan ({selectedArticle.entities.length}):
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedArticle.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-purple-900/50 text-purple-300 rounded text-xs"
                    title={`Type: ${entity.type}`}
                  >
                    {entity.text || entity.normalized_text}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        // Articles List View
        <div className="space-y-2">
          {articles.length === 0 ? (
            <div className="text-center py-8 text-gray-400">Không có dữ liệu</div>
          ) : (
            articles.map((article, idx) => (
              <div
                key={idx}
                onClick={() => fetchArticleDetail(article.id)}
                className="bg-gray-800 rounded-lg p-4 cursor-pointer hover:bg-gray-750 transition-colors border border-transparent hover:border-blue-500"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-white">{article.title}</h4>
                    <p className="text-sm text-gray-400 mt-1 line-clamp-2">{article.preview}</p>
                  </div>
                  <span className="text-xs text-gray-500 whitespace-nowrap ml-4">
                    {article.category || 'N/A'}
                  </span>
                </div>
              </div>
            ))
          )}
          
          <Pagination total={articlesTotal} page={articlePage} setPage={setArticlePage} />
        </div>
      )}
    </div>
  );

  // Render Entities tab
  const renderEntities = () => (
    <div className="space-y-4">
      {/* Search and Filter */}
      <div className="flex gap-4 flex-wrap">
        <input
          type="text"
          placeholder="Tìm kiếm thực thể..."
          value={entitySearch}
          onChange={(e) => {
            setEntitySearch(e.target.value);
            setEntityPage(0);
          }}
          className="flex-1 min-w-48 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white"
        />
        <select
          value={entityTypeFilter}
          onChange={(e) => {
            setEntityTypeFilter(e.target.value);
            setEntityPage(0);
          }}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white"
        >
          <option value="">Tất cả loại</option>
          {entityTypes.map((type, idx) => (
            <option key={idx} value={type}>{type}</option>
          ))}
        </select>
        <button
          onClick={fetchEntities}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          🔍 Tìm
        </button>
      </div>

      {/* Entities List */}
      {loading ? (
        <div className="text-center py-8 text-gray-400">Đang tải...</div>
      ) : entities.length === 0 ? (
        <div className="text-center py-8 text-gray-400">Không có dữ liệu</div>
      ) : (
        <>
          <div className="grid gap-2">
            {entities.map((entity, idx) => (
              <div
                key={idx}
                className="bg-gray-800 rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    getEntityTypeColor(entity.type)
                  }`}>
                    {entity.type}
                  </span>
                  <div>
                    <div className="text-white">{entity.text}</div>
                    {entity.normalized_text !== entity.text && (
                      <div className="text-xs text-gray-400">
                        Chuẩn hóa: {entity.normalized_text}
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-sm text-gray-400">
                  {entity.article_mentions || entity.stored_mentions || 0} điều đề cập
                </div>
              </div>
            ))}
          </div>
          
          <Pagination total={entitiesTotal} page={entityPage} setPage={setEntityPage} />
        </>
      )}
    </div>
  );

  // Render Relations tab
  const renderRelations = () => (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex gap-4 flex-wrap">
        <select
          value={relationTypeFilter}
          onChange={(e) => {
            setRelationTypeFilter(e.target.value);
            setRelationPage(0);
          }}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500 text-white"
        >
          <option value="">Tất cả loại quan hệ</option>
          {relationTypes.map((type, idx) => (
            <option key={idx} value={type}>{type}</option>
          ))}
        </select>
        <button
          onClick={fetchRelations}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          🔍 Lọc
        </button>
      </div>

      {/* Relations List */}
      {loading ? (
        <div className="text-center py-8 text-gray-400">Đang tải...</div>
      ) : relations.length === 0 ? (
        <div className="text-center py-8 text-gray-400">Không có dữ liệu quan hệ ngữ nghĩa</div>
      ) : (
        <>
          <div className="space-y-2">
            {relations.map((rel, idx) => (
              <div
                key={idx}
                className="bg-gray-800 rounded-lg p-3 flex items-center gap-3 flex-wrap"
              >
                {/* Source */}
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs ${getEntityTypeColor(rel.source_type)}`}>
                    {rel.source_type}
                  </span>
                  <span className="text-white">{rel.source_text}</span>
                </div>
                
                {/* Relation */}
                <div className="px-3 py-1 bg-blue-900/50 text-blue-300 rounded-full text-sm font-medium">
                  → {rel.relation_type} →
                </div>
                
                {/* Target */}
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs ${getEntityTypeColor(rel.target_type)}`}>
                    {rel.target_type}
                  </span>
                  <span className="text-white">{rel.target_text}</span>
                </div>
                
                {rel.confidence && (
                  <span className="text-xs text-gray-500 ml-auto">
                    {(rel.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            ))}
          </div>
          
          <Pagination total={relationsTotal} page={relationPage} setPage={setRelationPage} />
        </>
      )}
    </div>
  );

  // Helper to get entity type color
  const getEntityTypeColor = (type) => {
    const colors = {
      PERSON: 'bg-green-900/50 text-green-300',
      ORGANIZATION: 'bg-blue-900/50 text-blue-300',
      REGULATION: 'bg-yellow-900/50 text-yellow-300',
      CONCEPT: 'bg-purple-900/50 text-purple-300',
      TIME: 'bg-pink-900/50 text-pink-300',
      LOCATION: 'bg-orange-900/50 text-orange-300',
      NUMBER: 'bg-cyan-900/50 text-cyan-300',
      CONDITION: 'bg-red-900/50 text-red-300',
    };
    return colors[type] || 'bg-gray-700 text-gray-300';
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            📚 Dữ liệu đã trích xuất
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-700 px-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'articles' && renderArticles()}
          {activeTab === 'entities' && renderEntities()}
          {activeTab === 'relations' && renderRelations()}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-700 flex justify-between items-center">
          <div className="text-sm text-gray-400">
            Dữ liệu được lưu trữ trong Neo4j Knowledge Graph
          </div>
          <button
            onClick={() => {
              fetchStats();
              if (activeTab === 'articles') fetchArticles();
              if (activeTab === 'entities') fetchEntities();
              if (activeTab === 'relations') fetchRelations();
            }}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
          >
            🔄 Làm mới
          </button>
        </div>
      </div>
    </div>
  );
};

export default DataBrowserPanel;
