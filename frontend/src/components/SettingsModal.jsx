import React, { useState } from 'react';
import { X, Save } from 'lucide-react';

const SettingsModal = ({ isOpen, onClose, settings, onSave }) => {
  const [localSettings, setLocalSettings] = useState(settings);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(localSettings);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 p-4">
          <h2 className="text-xl font-semibold">Cài đặt</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Use RAG */}
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localSettings.useRag}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, useRag: e.target.checked })
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium">Sử dụng RAG (tìm kiếm tài liệu)</span>
            </label>
            <p className="ml-6 text-xs text-gray-500 mt-1">
              Tìm kiếm và sử dụng tài liệu liên quan để trả lời chính xác hơn
            </p>
          </div>

          {/* Top K */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Số tài liệu tìm kiếm: {localSettings.ragTopK}
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={localSettings.ragTopK}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, ragTopK: parseInt(e.target.value) })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Số lượng tài liệu tham khảo khi tìm kiếm (1-10)
            </p>
          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Temperature: {localSettings.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={localSettings.temperature}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, temperature: parseFloat(e.target.value) })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Độ sáng tạo của câu trả lời (0 = chính xác, 2 = sáng tạo)
            </p>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Độ dài tối đa: {localSettings.maxTokens}
            </label>
            <input
              type="range"
              min="500"
              max="4000"
              step="100"
              value={localSettings.maxTokens}
              onChange={(e) =>
                setLocalSettings({ ...localSettings, maxTokens: parseInt(e.target.value) })
              }
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Độ dài tối đa của câu trả lời (500-4000 tokens)
            </p>
          </div>

          {/* Show RAG Context */}
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={localSettings.showRAGContext}
                onChange={(e) =>
                  setLocalSettings({ ...localSettings, showRAGContext: e.target.checked })
                }
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm font-medium">Hiển thị tài liệu tham khảo</span>
            </label>
            <p className="ml-6 text-xs text-gray-500 mt-1">
              Hiển thị panel tài liệu được sử dụng để trả lời
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-gray-200 p-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
          >
            Hủy
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Save className="h-4 w-4" />
            Lưu
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
