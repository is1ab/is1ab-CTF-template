// IS1AB CTF Template - 主要 JavaScript 檔案

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有組件
    initializeComponents();
    
    // 載入統計資料
    if (window.location.pathname === '/') {
        loadDashboardStats();
    }
    
    // 為頁面添加淡入動畫
    document.body.classList.add('fade-in');
});

/**
 * 初始化所有組件
 */
function initializeComponents() {
    // 導航欄 burger 選單
    initializeNavbar();
    
    // 通知自動隱藏
    initializeNotifications();
    
    // 表單驗證
    initializeFormValidation();
    
    // 工具提示
    initializeTooltips();
}

/**
 * 初始化導航欄
 */
function initializeNavbar() {
    const $navbarBurgers = Array.prototype.slice.call(
        document.querySelectorAll('.navbar-burger'), 0
    );

    if ($navbarBurgers.length > 0) {
        $navbarBurgers.forEach(el => {
            el.addEventListener('click', () => {
                const target = el.dataset.target;
                const $target = document.getElementById(target);

                el.classList.toggle('is-active');
                $target.classList.toggle('is-active');
            });
        });
    }
    
    // 高亮當前頁面的導航項目
    highlightCurrentPage();
}

/**
 * 高亮當前頁面的導航項目
 */
function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.navbar-item');
    
    navItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('is-active');
        }
    });
}

/**
 * 初始化通知
 */
function initializeNotifications() {
    // 自動隱藏成功通知
    const notifications = document.querySelectorAll('.notification.is-success');
    notifications.forEach(notification => {
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 5000);
    });
}

/**
 * 初始化表單驗證
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
        
        // 即時驗證
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
        });
    });
}

/**
 * 驗證表單
 */
function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    
    inputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

/**
 * 驗證單個欄位
 */
function validateField(field) {
    const value = field.value.trim();
    const fieldContainer = field.closest('.field');
    let errorMessage = '';
    
    // 移除現有錯誤訊息
    const existingError = fieldContainer.querySelector('.help.is-danger');
    if (existingError) {
        existingError.remove();
    }
    
    // 必填驗證
    if (field.hasAttribute('required') && !value) {
        errorMessage = '此欄位為必填';
    }
    
    // 電子郵件驗證
    if (field.type === 'email' && value && !isValidEmail(value)) {
        errorMessage = '請輸入有效的電子郵件地址';
    }
    
    // 數字驗證
    if (field.type === 'number' && value) {
        const min = field.getAttribute('min');
        const max = field.getAttribute('max');
        const num = parseFloat(value);
        
        if (min && num < parseFloat(min)) {
            errorMessage = `值不能小於 ${min}`;
        } else if (max && num > parseFloat(max)) {
            errorMessage = `值不能大於 ${max}`;
        }
    }
    
    // Pattern 驗證
    if (field.hasAttribute('pattern') && value) {
        const pattern = new RegExp(field.getAttribute('pattern'));
        if (!pattern.test(value)) {
            errorMessage = field.getAttribute('title') || '格式不正確';
        }
    }
    
    // 顯示錯誤訊息
    if (errorMessage) {
        field.classList.add('is-danger');
        const helpElement = document.createElement('p');
        helpElement.className = 'help is-danger';
        helpElement.textContent = errorMessage;
        fieldContainer.appendChild(helpElement);
        return false;
    } else {
        field.classList.remove('is-danger');
        field.classList.add('is-success');
        return true;
    }
}

/**
 * 驗證電子郵件格式
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * 初始化工具提示
 */
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

/**
 * 顯示工具提示
 */
function showTooltip(event) {
    const element = event.target;
    const tooltipText = element.getAttribute('data-tooltip');
    
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    tooltip.style.position = 'absolute';
    tooltip.style.backgroundColor = '#363636';
    tooltip.style.color = 'white';
    tooltip.style.padding = '0.5rem';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '0.875rem';
    tooltip.style.zIndex = '1000';
    tooltip.style.pointerEvents = 'none';
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    element.tooltipElement = tooltip;
}

/**
 * 隱藏工具提示
 */
function hideTooltip(event) {
    const element = event.target;
    if (element.tooltipElement) {
        element.tooltipElement.remove();
        delete element.tooltipElement;
    }
}

/**
 * 載入儀表板統計資料
 */
function loadDashboardStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStatsDisplay(data.data);
            }
        })
        .catch(error => {
            console.error('載入統計資料失敗:', error);
        });
}

/**
 * 更新統計資料顯示
 */
function updateStatsDisplay(stats) {
    // 更新統計卡片
    const totalChallenges = document.querySelector('[data-stat="total-challenges"]');
    const totalPoints = document.querySelector('[data-stat="total-points"]');
    
    if (totalChallenges) {
        animateNumber(totalChallenges, stats.total_challenges);
    }
    
    if (totalPoints) {
        animateNumber(totalPoints, stats.total_points);
    }
}

/**
 * 數字動畫效果
 */
function animateNumber(element, targetValue) {
    const startValue = 0;
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const currentValue = Math.floor(startValue + (targetValue - startValue) * progress);
        element.textContent = currentValue;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

/**
 * 顯示載入狀態
 */
function showLoading(element, text = '載入中...') {
    const originalContent = element.innerHTML;
    element.innerHTML = `<span class="icon"><i class="fas fa-spinner fa-pulse"></i></span><span>${text}</span>`;
    element.disabled = true;
    element.originalContent = originalContent;
}

/**
 * 隱藏載入狀態
 */
function hideLoading(element) {
    if (element.originalContent) {
        element.innerHTML = element.originalContent;
        element.disabled = false;
        delete element.originalContent;
    }
}

/**
 * 顯示通知訊息
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification is-${type}`;
    notification.innerHTML = `
        <button class="delete"></button>
        ${message}
    `;
    
    // 添加到頁面
    const container = document.querySelector('.main-content .container');
    if (container) {
        container.insertBefore(notification, container.firstChild);
    }
    
    // 關閉按鈕事件
    const deleteButton = notification.querySelector('.delete');
    deleteButton.addEventListener('click', () => {
        notification.remove();
    });
    
    // 自動關閉
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    }
}

/**
 * API 請求輔助函數
 */
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || '請求失敗');
        }
        
        return data;
    } catch (error) {
        console.error('API 請求錯誤:', error);
        showNotification(`錯誤: ${error.message}`, 'danger');
        throw error;
    }
}

/**
 * 格式化日期
 */
function formatDate(date) {
    return new Intl.DateTimeFormat('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

/**
 * 格式化檔案大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 防抖函數
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
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

// 全域可用的工具函數
window.CTF = {
    showLoading,
    hideLoading,
    showNotification,
    apiRequest,
    formatDate,
    formatFileSize,
    debounce,
    throttle
};
