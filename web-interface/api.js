/**
 * API 接口模組
 * 用於與後端服務通信的統一接口
 */

class CTFManagerAPI {
    constructor() {
        this.baseURL = this.getBaseURL();
        this.timeout = 10000; // 10 秒超時
    }

    /**
     * 取得基礎 URL
     */
    getBaseURL() {
        // 如果有環境變數或配置，可以在這裡設定
        return window.location.origin;
    }

    /**
     * 通用 HTTP 請求方法
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: this.timeout,
        };

        const config = { ...defaultOptions, ...options };

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.timeout);

            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('請求超時');
            }
            throw error;
        }
    }

    /**
     * GET 請求
     */
    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    /**
     * POST 請求
     */
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT 請求
     */
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE 請求
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // ========== CTF 管理 API 方法 ==========

    /**
     * 取得統計資料
     */
    async getStats() {
        try {
            return await this.get('/api/stats');
        } catch (error) {
            console.warn('無法載入統計資料，使用模擬資料');
            throw error;
        }
    }

    /**
     * 取得進度資料
     */
    async getProgress() {
        try {
            return await this.get('/api/progress');
        } catch (error) {
            console.warn('無法載入進度資料');
            throw error;
        }
    }

    /**
     * 取得最近活動
     */
    async getRecentActivity() {
        try {
            return await this.get('/api/activity');
        } catch (error) {
            console.warn('無法載入活動資料');
            throw error;
        }
    }

    /**
     * 取得團隊任務分配
     */
    async getTeamAssignments() {
        try {
            return await this.get('/api/assignments');
        } catch (error) {
            console.warn('無法載入任務分配');
            throw error;
        }
    }

    /**
     * 創建新題目
     */
    async createChallenge(challengeData) {
        try {
            return await this.post('/api/challenges', challengeData);
        } catch (error) {
            console.error('創建題目失敗:', error);
            throw new Error(`創建題目失敗: ${error.message}`);
        }
    }

    /**
     * 更新題目資訊
     */
    async updateChallenge(challengeId, challengeData) {
        try {
            return await this.put(`/api/challenges/${challengeId}`, challengeData);
        } catch (error) {
            console.error('更新題目失敗:', error);
            throw new Error(`更新題目失敗: ${error.message}`);
        }
    }

    /**
     * 刪除題目
     */
    async deleteChallenge(challengeId) {
        try {
            return await this.delete(`/api/challenges/${challengeId}`);
        } catch (error) {
            console.error('刪除題目失敗:', error);
            throw new Error(`刪除題目失敗: ${error.message}`);
        }
    }

    /**
     * 取得特定題目詳情
     */
    async getChallenge(challengeId) {
        try {
            return await this.get(`/api/challenges/${challengeId}`);
        } catch (error) {
            console.error('載入題目詳情失敗:', error);
            throw new Error(`載入題目詳情失敗: ${error.message}`);
        }
    }

    /**
     * 取得所有題目列表
     */
    async getChallenges() {
        try {
            return await this.get('/api/challenges');
        } catch (error) {
            console.error('載入題目列表失敗:', error);
            throw error;
        }
    }

    /**
     * 更新 README
     */
    async updateReadme() {
        try {
            return await this.post('/api/update-readme', {});
        } catch (error) {
            console.error('更新 README 失敗:', error);
            throw new Error(`更新 README 失敗: ${error.message}`);
        }
    }

    /**
     * 驗證題目
     */
    async validateChallenges() {
        try {
            return await this.post('/api/validate', {});
        } catch (error) {
            console.error('驗證題目失敗:', error);
            throw new Error(`驗證題目失敗: ${error.message}`);
        }
    }

    /**
     * 匯出資料
     */
    async exportData() {
        try {
            return await this.get('/api/export');
        } catch (error) {
            console.error('匯出資料失敗:', error);
            throw new Error(`匯出資料失敗: ${error.message}`);
        }
    }

    /**
     * 取得系統配置
     */
    async getConfig() {
        try {
            return await this.get('/api/config');
        } catch (error) {
            console.warn('無法載入系統配置');
            return this.getDefaultConfig();
        }
    }

    /**
     * 預設配置
     */
    getDefaultConfig() {
        return {
            project: {
                name: 'IS1AB CTF',
                flag_prefix: 'is1abCTF',
                year: new Date().getFullYear()
            },
            categories: ['web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc', 'general'],
            difficulties: ['baby', 'easy', 'middle', 'hard', 'impossible'],
            challenge_types: [
                'static_attachment',
                'static_container',
                'dynamic_attachment',
                'dynamic_container',
                'nc_challenge'
            ],
            points: {
                baby: 50,
                easy: 100,
                middle: 200,
                hard: 300,
                impossible: 500
            }
        };
    }

    /**
     * 執行 Git 操作
     */
    async executeGitOperation(operation, params = {}) {
        try {
            return await this.post('/api/git', { operation, ...params });
        } catch (error) {
            console.error('Git 操作失敗:', error);
            throw new Error(`Git 操作失敗: ${error.message}`);
        }
    }

    /**
     * 取得 Docker 狀態
     */
    async getDockerStatus() {
        try {
            return await this.get('/api/docker/status');
        } catch (error) {
            console.warn('無法取得 Docker 狀態');
            throw error;
        }
    }

    /**
     * 啟動 Docker 容器
     */
    async startDockerContainer(challengePath) {
        try {
            return await this.post('/api/docker/start', { path: challengePath });
        } catch (error) {
            console.error('啟動容器失敗:', error);
            throw new Error(`啟動容器失敗: ${error.message}`);
        }
    }

    /**
     * 停止 Docker 容器
     */
    async stopDockerContainer(challengePath) {
        try {
            return await this.post('/api/docker/stop', { path: challengePath });
        } catch (error) {
            console.error('停止容器失敗:', error);
            throw new Error(`停止容器失敗: ${error.message}`);
        }
    }

    /**
     * 檢查檔案是否存在
     */
    async checkFileExists(filePath) {
        try {
            return await this.get(`/api/file/exists?path=${encodeURIComponent(filePath)}`);
        } catch (error) {
            return false;
        }
    }

    /**
     * 讀取檔案內容
     */
    async readFile(filePath) {
        try {
            return await this.get(`/api/file/read?path=${encodeURIComponent(filePath)}`);
        } catch (error) {
            console.error('讀取檔案失敗:', error);
            throw new Error(`讀取檔案失敗: ${error.message}`);
        }
    }

    /**
     * 寫入檔案內容
     */
    async writeFile(filePath, content) {
        try {
            return await this.post('/api/file/write', { path: filePath, content });
        } catch (error) {
            console.error('寫入檔案失敗:', error);
            throw new Error(`寫入檔案失敗: ${error.message}`);
        }
    }

    /**
     * 取得伺服器狀態
     */
    async getServerStatus() {
        try {
            const start = Date.now();
            await this.get('/api/health');
            const latency = Date.now() - start;
            return {
                status: 'online',
                latency: latency,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            return {
                status: 'offline',
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * 搜尋題目
     */
    async searchChallenges(query) {
        try {
            return await this.get(`/api/search?q=${encodeURIComponent(query)}`);
        } catch (error) {
            console.error('搜尋失敗:', error);
            throw new Error(`搜尋失敗: ${error.message}`);
        }
    }

    /**
     * 取得系統日誌
     */
    async getLogs(limit = 100) {
        try {
            return await this.get(`/api/logs?limit=${limit}`);
        } catch (error) {
            console.error('取得日誌失敗:', error);
            throw error;
        }
    }

    // ========== 提示管理 API 方法 ==========

    /**
     * 取得題目提示
     */
    async getChallengeHints(category, name) {
        try {
            return await this.get(`/api/challenges/${category}/${name}/hints`);
        } catch (error) {
            console.error('載入題目提示失敗:', error);
            throw new Error(`載入題目提示失敗: ${error.message}`);
        }
    }

    /**
     * 新增題目提示
     */
    async addChallengeHint(category, name, hintData) {
        try {
            return await this.post(`/api/challenges/${category}/${name}/hints`, hintData);
        } catch (error) {
            console.error('新增提示失敗:', error);
            throw new Error(`新增提示失敗: ${error.message}`);
        }
    }

    /**
     * 更新題目提示
     */
    async updateChallengeHint(category, name, level, hintData) {
        try {
            return await this.put(`/api/challenges/${category}/${name}/hints/${level}`, hintData);
        } catch (error) {
            console.error('更新提示失敗:', error);
            throw new Error(`更新提示失敗: ${error.message}`);
        }
    }

    /**
     * 刪除題目提示
     */
    async deleteChallengeHint(category, name, level) {
        try {
            return await this.delete(`/api/challenges/${category}/${name}/hints/${level}`);
        } catch (error) {
            console.error('刪除提示失敗:', error);
            throw new Error(`刪除提示失敗: ${error.message}`);
        }
    }

    /**
     * 取得題目詳細資訊
     */
    async getChallengeDetails(category, name) {
        try {
            return await this.get(`/api/challenges/${category}/${name}/details`);
        } catch (error) {
            console.error('載入題目詳情失敗:', error);
            throw new Error(`載入題目詳情失敗: ${error.message}`);
        }
    }
}

// 創建全域 API 實例
const api = new CTFManagerAPI();

// 匯出供其他模組使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CTFManagerAPI, api };
}

// 瀏覽器環境下的全域變數
if (typeof window !== 'undefined') {
    window.api = api;
    window.CTFManagerAPI = CTFManagerAPI;
}

// 工具函數

/**
 * 延遲函數
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 重試函數
 */
async function retry(fn, maxRetries = 3, delayMs = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) {
                throw error;
            }
            console.warn(`重試 ${i + 1}/${maxRetries}:`, error.message);
            await delay(delayMs * Math.pow(2, i)); // 指數退避
        }
    }
}

/**
 * 格式化檔案大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 格式化時間差
 */
function formatTimeAgo(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days} 天前`;
    if (hours > 0) return `${hours} 小時前`;
    if (minutes > 0) return `${minutes} 分鐘前`;
    return `${seconds} 秒前`;
}

/**
 * 驗證表單資料
 */
function validateChallengeForm(data) {
    const errors = [];

    if (!data.name || data.name.trim() === '') {
        errors.push('題目名稱不能為空');
    } else if (!/^[a-z0-9_]+$/.test(data.name)) {
        errors.push('題目名稱只能包含小寫字母、數字和底線');
    }

    if (!data.category) {
        errors.push('請選擇題目分類');
    }

    if (!data.difficulty) {
        errors.push('請選擇題目難度');
    }

    if (!data.challenge_type) {
        errors.push('請選擇題目類型');
    }

    if (!data.description || data.description.trim() === '') {
        errors.push('題目描述不能為空');
    }

    if (!data.author || data.author.trim() === '') {
        errors.push('作者不能為空');
    }

    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

/**
 * 產生隨機 ID
 */
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

/**
 * 深拷貝物件
 */
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * 節流函數
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 防抖函數
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

// 匯出工具函數
if (typeof window !== 'undefined') {
    window.utils = {
        delay,
        retry,
        formatFileSize,
        formatTimeAgo,
        validateChallengeForm,
        generateId,
        deepClone,
        throttle,
        debounce
    };
}