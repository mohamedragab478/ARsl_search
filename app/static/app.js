// Application State
let currentTab = 'translator';
let allSigns = [];
let currentAnalysis = [];

// API Base URL
const API_BASE = '/api';

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI event handlers
    initEventListeners();
    
    // Eagerly fetch dictionary in background
    fetchDictionary();
});

function initEventListeners() {
    // Threshold slider change handler
    const thresholdSlider = document.getElementById('slider-threshold');
    const thresholdVal = document.getElementById('threshold-val');
    thresholdSlider.addEventListener('input', (e) => {
        thresholdVal.textContent = e.target.value;
    });

    // Analyze sentence button
    const btnAnalyze = document.getElementById('btn-analyze');
    btnAnalyze.addEventListener('click', analyzeSentence);

    // Generate GIF button
    const btnGenerate = document.getElementById('btn-generate-gif');
    btnGenerate.addEventListener('click', generateTranslationGif);

    // Dictionary search input
    const dictSearchInput = document.getElementById('dict-search-input');
    dictSearchInput.addEventListener('input', filterDictionary);

    // Trigger analysis on Enter key (Ctrl + Enter) in textarea
    const inputSentence = document.getElementById('input-sentence');
    inputSentence.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            analyzeSentence();
        }
    });
}

// Tab Switching Logic
function switchTab(tabId) {
    if (tabId === currentTab) return;
    
    currentTab = tabId;
    
    // Update navigation buttons active state
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.getElementById(`btn-tab-${tabId}`).classList.add('active');

    // Update content area active state
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active-content');
    });
    document.getElementById(`tab-${tabId}-content`).classList.add('active-content');
    
    // Refresh dictionary if entering tab
    if (tabId === 'dictionary' && allSigns.length === 0) {
        fetchDictionary();
    }
}

// ==========================================
// 1. TRANSLATOR LOGIC
// ==========================================

async function analyzeSentence() {
    const inputSentence = document.getElementById('input-sentence');
    const thresholdSlider = document.getElementById('slider-threshold');
    const btnAnalyze = document.getElementById('btn-analyze');
    
    const sentence = inputSentence.value.trim();
    if (!sentence) {
        alert('الرجاء إدخال جملة أولاً للتحليل.');
        return;
    }

    // UI Loading State
    btnAnalyze.disabled = true;
    btnAnalyze.querySelector('.btn-text').classList.add('hidden');
    btnAnalyze.querySelector('.btn-loader').classList.remove('hidden');

    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sentence: sentence,
                threshold: parseFloat(thresholdSlider.value)
            })
        });

        if (!response.ok) {
            throw new Error('فشل الاتصال بالخادم لتحليل الجملة');
        }

        const data = await response.json();
        currentAnalysis = data.words;
        
        renderWordAnalysisCards();
        
        // Show result section
        document.getElementById('analysis-result-section').classList.remove('hidden');
    } catch (error) {
        console.error('Error analyzing sentence:', error);
        alert(`حدث خطأ أثناء تحليل الجملة: ${error.message}`);
    } finally {
        // Restore button state
        btnAnalyze.disabled = false;
        btnAnalyze.querySelector('.btn-text').classList.remove('hidden');
        btnAnalyze.querySelector('.btn-loader').classList.add('hidden');
    }
}

function renderWordAnalysisCards() {
    const container = document.getElementById('words-cards-container');
    container.innerHTML = '';

    if (currentAnalysis.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">لا توجد كلمات صالحة للتحليل.</p>';
        return;
    }

    currentAnalysis.forEach((item, index) => {
        // Add use_sign field dynamically
        item.use_sign = item.is_matched;

        const card = document.createElement('div');
        card.className = 'word-card';
        
        let badgeHTML = '';
        let infoHTML = '';
        let toggleHTML = '';

        if (item.is_person) {
            card.classList.add('spelled-person');
            badgeHTML = `<span class="badge-status badge-person"><i class="fa-solid fa-signature"></i> اسم شخص</span>`;
            infoHTML = `<span class="word-mapping-desc">سيتم تهجئتها حرفاً بحرف تلقائياً.</span>`;
            toggleHTML = `
                <span class="toggle-label-text">تهجئة</span>
                <label class="toggle-container">
                    <input type="checkbox" disabled>
                    <span class="toggle-slider"></span>
                </label>
            `;
        } else if (item.is_matched) {
            card.classList.add('matched');
            badgeHTML = `<span class="badge-status badge-matched"><i class="fa-solid fa-check-double"></i> تطابق دلالي</span>`;
            infoHTML = `
                <span class="word-mapping-desc">مقترنة بـ: <strong>${item.label_ar}</strong> (${item.label_en})</span>
                <span class="word-score">نسبة التشابه: ${item.score_pct}</span>
            `;
            
            toggleHTML = `
                <span class="toggle-label-text" id="toggle-label-${index}">إشارة دلالية</span>
                <label class="toggle-container">
                    <input type="checkbox" checked onchange="toggleWordMapping(${index}, this)">
                    <span class="toggle-slider"></span>
                </label>
            `;
        } else {
            card.classList.add('spelled-unknown');
            badgeHTML = `<span class="badge-status badge-unknown"><i class="fa-solid fa-spell-check"></i> كلمة مجهولة</span>`;
            infoHTML = `<span class="word-mapping-desc">غير مسجلة بالقاموس. سيتم تهجئتها أبجدياً.</span>`;
            toggleHTML = `
                <span class="toggle-label-text">تهجئة</span>
                <label class="toggle-container">
                    <input type="checkbox" disabled>
                    <span class="toggle-slider"></span>
                </label>
            `;
        }

        card.innerHTML = `
            <div class="word-info-col">
                <div class="word-title-row">
                    <span class="word-text">${item.word}</span>
                    ${badgeHTML}
                </div>
                ${infoHTML}
            </div>
            <div class="word-action-col">
                ${toggleHTML}
            </div>
        `;
        
        container.appendChild(card);
    });
}

function toggleWordMapping(index, checkbox) {
    if (index >= 0 && index < currentAnalysis.length) {
        currentAnalysis[index].use_sign = checkbox.checked;
        const labelText = document.getElementById(`toggle-label-${index}`);
        if (labelText) {
            labelText.textContent = checkbox.checked ? 'إشارة دلالية' : 'تهجئة الكلمة';
        }
    }
}

async function generateTranslationGif() {
    const btnGenerate = document.getElementById('btn-generate-gif');
    
    // UI Panel States
    const placeholder = document.getElementById('output-placeholder');
    const loading = document.getElementById('output-loading');
    const result = document.getElementById('output-result');
    const logsContainer = document.getElementById('logs-container');
    const logsContent = document.getElementById('logs-content');

    placeholder.classList.add('hidden');
    result.classList.add('hidden');
    logsContainer.classList.add('hidden');
    loading.classList.remove('hidden');

    btnGenerate.disabled = true;
    btnGenerate.querySelector('.btn-text').classList.add('hidden');
    btnGenerate.querySelector('.btn-loader').classList.remove('hidden');

    // Build words instruction payload
    const wordsPayload = currentAnalysis.map(item => ({
        word: item.word,
        use_sign: item.use_sign,
        sign_id: item.is_matched ? item.best_id : null
    }));

    try {
        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                words: wordsPayload,
                fps: 12
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'فشل توليد الفيديو لترجمة الكلمات');
        }

        const data = await response.json();

        if (data.success && data.gif_url) {
            // Success! Load GIF with Cache-buster to force re-render
            const timestamp = new Date().getTime();
            const gifImg = document.getElementById('result-gif-img');
            gifImg.src = `${data.gif_url}?t=${timestamp}`;
            
            // Set download link
            const downloadBtn = document.getElementById('btn-download-gif');
            downloadBtn.href = data.gif_url;

            // Render detailed console log of translation
            logsContent.innerHTML = '';
            data.words_info.forEach(info => {
                const logDiv = document.createElement('div');
                logDiv.className = 'log-entry';
                
                if (info.type === 'sign' && info.status === 'success') {
                    logDiv.innerHTML = `✔️ تم دمج الكلمة دلالياً: <strong style="color:var(--accent-emerald)">"${info.word}"</strong> (معرف الإشارة: ${info.sign_id})`;
                } else if (info.type === 'spelling' && info.status === 'success') {
                    const lettersStr = info.spelled_chars.join(' - ');
                    logDiv.innerHTML = `🔤 تم تهجئة الكلمة أبجدياً: <strong style="color:var(--accent-amber)">"${info.word}"</strong> (${lettersStr})`;
                } else {
                    logDiv.innerHTML = `❌ لم يتم التعرف على الكلمة: "${info.word}" (تخطي)`;
                }
                logsContent.appendChild(logDiv);
            });

            // Show UI panels
            loading.classList.add('hidden');
            result.classList.remove('hidden');
            logsContainer.classList.remove('hidden');
        } else {
            throw new Error('لم يقم الخادم بإرجاع رابط GIF صالح.');
        }
    } catch (error) {
        console.error('Error generating GIF:', error);
        alert(`حدث خطأ أثناء دمج وتوليد لغة الإشارة: ${error.message}`);
        loading.classList.add('hidden');
        placeholder.classList.remove('hidden');
    } finally {
        // Restore button state
        btnGenerate.disabled = false;
        btnGenerate.querySelector('.btn-text').classList.remove('hidden');
        btnGenerate.querySelector('.btn-loader').classList.add('hidden');
    }
}

// ==========================================
// 2. DICTIONARY BROWSER LOGIC
// ==========================================

async function fetchDictionary() {
    const listLoading = document.getElementById('dict-list-loading');
    const signsList = document.getElementById('dict-signs-list');
    
    try {
        const response = await fetch(`${API_BASE}/signs`);
        if (!response.ok) {
            throw new Error('فشل تحميل قاموس الإشارات');
        }

        allSigns = await response.json();
        
        // Update stats
        document.getElementById('total-signs-count').textContent = allSigns.length;
        const countWithGif = allSigns.filter(s => s.has_gif).length;
        document.getElementById('gif-signs-count').textContent = countWithGif;

        renderDictionaryList(allSigns);
        listLoading.classList.add('hidden');
    } catch (error) {
        console.error('Error fetching dictionary:', error);
        listLoading.innerHTML = `<p class="text-center style="color:var(--accent-rose)">حدث خطأ أثناء تحميل القاموس: ${error.message}</p>`;
    }
}

function renderDictionaryList(signs) {
    const signsList = document.getElementById('dict-signs-list');
    signsList.innerHTML = '';

    if (signs.length === 0) {
        signsList.innerHTML = '<li class="text-center text-muted p-3">لا توجد نتائج مطابقة لبحثك.</li>';
        return;
    }

    signs.forEach(sign => {
        const li = document.createElement('li');
        li.className = 'sign-list-item';
        li.id = `dict-item-${sign.sign_id}`;
        li.onclick = () => selectDictionarySign(sign);

        const badge = sign.has_gif 
            ? `<span class="badge-has-gif"><i class="fa-solid fa-play"></i> GIF متوفر</span>`
            : `<span class="badge-no-gif">غير متوفر</span>`;

        li.innerHTML = `
            <div>
                <span class="sign-item-title">${sign.label_ar}</span>
                <div class="sign-item-sub">ID: #${sign.sign_id} | ${sign.label_en}</div>
            </div>
            ${badge}
        `;

        signsList.appendChild(li);
    });
}

function filterDictionary() {
    const query = document.getElementById('dict-search-input').value.toLowerCase().trim();
    if (!query) {
        renderDictionaryList(allSigns);
        return;
    }

    const filtered = allSigns.filter(sign => {
        const labelAr = sign.label_ar.toLowerCase();
        const labelEn = sign.label_en.toLowerCase();
        const signId = sign.sign_id.toLowerCase();
        
        return labelAr.includes(query) || labelEn.includes(query) || signId.includes(query);
    });

    renderDictionaryList(filtered);
}

function selectDictionarySign(sign) {
    // Highlight list item
    document.querySelectorAll('.sign-list-item').forEach(item => {
        item.classList.remove('selected');
    });
    const selectedItem = document.getElementById(`dict-item-${sign.sign_id}`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }

    // Toggle panels
    document.getElementById('dict-preview-empty').classList.add('hidden');
    const previewContent = document.getElementById('dict-preview-content');
    previewContent.classList.remove('hidden');

    // Populate Details
    document.getElementById('preview-ar-label').textContent = sign.label_ar;
    document.getElementById('preview-en-label').textContent = sign.label_en;
    document.getElementById('preview-id-badge').textContent = `معرف: #${sign.sign_id}`;

    // Load visual GIF
    const gifImg = document.getElementById('preview-gif-img');
    const gifLoader = document.getElementById('preview-gif-loading');
    
    gifImg.classList.add('hidden');
    gifLoader.classList.remove('hidden');

    if (sign.has_gif) {
        // In FastAPI, data_gifs is mounted under /data_gifs
        gifImg.src = `/data_gifs/${sign.sign_id}.gif`;
        gifImg.onload = () => {
            gifLoader.classList.add('hidden');
            gifImg.classList.remove('hidden');
        };
        gifImg.onerror = () => {
            gifLoader.classList.add('hidden');
            gifImg.alt = "فشل تحميل ملف الـ GIF الخاص بهذه الإشارة.";
            gifImg.classList.remove('hidden');
        };
    } else {
        gifLoader.classList.add('hidden');
        gifImg.src = '';
        gifImg.alt = "ملف الـ GIF الخاص بهذه الإشارة غير متوفر حالياً في قاعدة البيانات.";
        gifImg.classList.remove('hidden');
    }

    // Render synonyms / translations
    const synonymsList = document.getElementById('preview-synonyms-tags');
    synonymsList.innerHTML = '';
    
    // We can add standard tags
    const tags = [sign.label_ar];
    if (sign.label_en) tags.push(sign.label_en);
    
    // If the server returns synonyms (or if we can guess them, e.g. for numbers/common terms)
    if (sign.synonyms && sign.synonyms.length > 0) {
        sign.synonyms.forEach(syn => {
            if (!tags.includes(syn)) tags.push(syn);
        });
    }

    tags.forEach(tag => {
        const li = document.createElement('li');
        li.className = 'synonym-tag';
        li.textContent = tag;
        synonymsList.appendChild(li);
    });
}
