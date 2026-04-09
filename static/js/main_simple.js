// 简化版图书馆管理系统 JavaScript
// 避免复杂的依赖，确保与Python 3.13兼容

document.addEventListener('DOMContentLoaded', function() {
    console.log('🏛️ 图书馆管理系统加载完成');
    
    // 自动隐藏警告消息
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.classList.contains('alert-danger')) {
            setTimeout(() => {
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }, 5000);
        }
    });
    
    // 表格行点击效果
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', function(e) {
            if (!e.target.closest('button')) {
                // 移除其他行的选中状态
                tableRows.forEach(r => r.classList.remove('table-active'));
                // 添加当前行选中状态
                this.classList.add('table-active');
            }
        });
    });
    
    // 搜索功能增强
    const searchInputs = document.querySelectorAll('input[name="search"]');
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const bookCards = document.querySelectorAll('.book-card');
            
            bookCards.forEach(card => {
                const title = card.querySelector('.card-title').textContent.toLowerCase();
                const author = card.querySelector('.card-subtitle').textContent.toLowerCase();
                const description = card.querySelector('.card-text').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || author.includes(searchTerm) || description.includes(searchTerm)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
    
    // 确认对话框增强
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && submitBtn.textContent.includes('归还')) {
                if (!confirm('确认归还这本图书吗？')) {
                    e.preventDefault();
                }
            }
        });
    });
    
    // 卡片悬停效果
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // 统计数据动画效果
    const statsNumbers = document.querySelectorAll('.stats-number');
    statsNumbers.forEach(element => {
        const finalValue = parseInt(element.textContent);
        if (!isNaN(finalValue)) {
            animateValue(element, 0, finalValue, 2000);
        }
    });
    
    // 数字动画函数
    function animateValue(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            element.textContent = Math.floor(current);
            
            if (current >= end) {
                element.textContent = end;
                clearInterval(timer);
            }
        }, 16);
    }
    
    // 平滑滚动到锚点
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // 键盘快捷键
    document.addEventListener('keydown', function(e) {
        // Ctrl + / 聚焦到搜索框
        if (e.ctrlKey && e.key === '/') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // ESC 关闭模态框
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            });
        }
    });
    
    // 表单验证增强
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
        });
    });
    
    function validateField(field) {
        const value = field.value.trim();
        const fieldType = field.type;
        let isValid = true;
        let message = '';
        
        if (field.required && !value) {
            isValid = false;
            message = '此字段为必填项';
        } else if (fieldType === 'email' && value && !isValidEmail(value)) {
            isValid = false;
            message = '请输入有效的邮箱地址';
        } else if (fieldType === 'password' && value && value.length < 6) {
            isValid = false;
            message = '密码长度至少6位';
        }
        
        // 显示验证结果
        showFieldValidation(field, isValid, message);
        return isValid;
    }
    
    function showFieldValidation(field, isValid, message) {
        // 移除之前的验证状态
        field.classList.remove('is-valid', 'is-invalid');
        
        // 添加新的验证状态
        if (field.value.trim()) {
            field.classList.add(isValid ? 'is-valid' : 'is-invalid');
        }
        
        // 更新提示信息
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!isValid && !feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            field.parentNode.appendChild(feedback);
        }
        
        if (feedback) {
            feedback.textContent = message;
        }
    }
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // 加载状态管理
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading';
        loadingDiv.className = 'text-center p-4';
        loadingDiv.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">加载中...</span>
            </div>
            <div class="mt-2">处理中，请稍候...</div>
        `;
        document.body.appendChild(loadingDiv);
    }
    
    function hideLoading() {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
    
    // 提交按钮加载状态
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (!this.disabled) {
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> 处理中...';
                this.disabled = true;
                
                // 如果是表单提交，3秒后恢复按钮状态
                const form = this.closest('form');
                if (form) {
                    setTimeout(() => {
                        this.innerHTML = this.getAttribute('data-original-text') || '提交';
                        this.disabled = false;
                    }, 3000);
                }
            }
        });
        
        // 保存原始文本
        button.setAttribute('data-original-text', button.innerHTML);
    });
    
    // 错误处理
    window.addEventListener('error', function(e) {
        console.error('JavaScript错误:', e.error);
        // 在生产环境中，这里可以发送错误报告到服务器
    });
    
    // 网络状态监控
    window.addEventListener('online', function() {
        showNotification('网络连接已恢复', 'success');
    });
    
    window.addEventListener('offline', function() {
        showNotification('网络连接已断开', 'warning');
    });
    
    function showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // 5秒后自动移除
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    console.log('✅ 所有功能初始化完成');
});