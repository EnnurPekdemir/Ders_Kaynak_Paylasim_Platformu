/**
 * SELÇUK ÜNİVERSİTESİ BİLGİSAYAR MÜHENDİSLİĞİ
 * Ders Notu ve Kaynak Dayanışma Platformu - JavaScript Modülü
 */

document.addEventListener('DOMContentLoaded', () => {
    initVoteButtons();
    initReportModal();
    initPreviewModal();
    initUploadDropzone();
    initFilterLiveSync();
});

/* ==========================================================================
   TOAST BİLDİRİM YARDIMCISI
   ========================================================================== */
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'custom-toast';

    let icon = 'fa-circle-info';
    let iconColor = '#38bdf8';
    if (type === 'success') {
        icon = 'fa-circle-check';
        iconColor = '#34d399';
    } else if (type === 'error' || type === 'danger') {
        icon = 'fa-circle-exclamation';
        iconColor = '#f87171';
    }

    toast.innerHTML = `
        <i class="fa-solid ${icon}" style="color: ${iconColor}; font-size: 1.15rem;"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 3800);
}

/* ==========================================================================
   OY VERME (FAYDALI / YETERSİZ) - AJAX
   ========================================================================== */
function initVoteButtons() {
    const voteButtons = document.querySelectorAll('.btn-vote');
    
    // Daha önce oy verilmiş notları localStorage'dan al
    const votedNotes = JSON.parse(localStorage.getItem('suk_voted_notes') || '{}');

    // Sayfa yüklendiğinde aktif oyları işaretle
    voteButtons.forEach(btn => {
        const noteId = btn.dataset.noteId;
        const voteType = btn.dataset.voteType;
        if (votedNotes[noteId] === voteType) {
            btn.classList.add(voteType === 'up' ? 'voted-up' : 'voted-down');
        }
    });

    voteButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const noteId = btn.dataset.noteId;
            const voteType = btn.dataset.voteType;

            // Zaten aynı oyu vermişse uyar
            if (votedNotes[noteId] === voteType) {
                showToast('Bu not için zaten oyunuzu kullandınız.', 'info');
                return;
            }

            btn.disabled = true;

            try {
                const response = await fetch(`/api/vote/${noteId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ vote_type: voteType })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    // Sayacı güncelle
                    const card = btn.closest('.note-card');
                    if (card) {
                        const upSpan = card.querySelector(`.btn-vote[data-vote-type="up"] .vote-count`);
                        const downSpan = card.querySelector(`.btn-vote[data-vote-type="down"] .vote-count`);
                        if (upSpan) upSpan.textContent = result.upvotes;
                        if (downSpan) downSpan.textContent = result.downvotes;

                        // Buton stillerini güncelle
                        card.querySelectorAll('.btn-vote').forEach(b => {
                            b.classList.remove('voted-up', 'voted-down');
                        });
                        btn.classList.add(voteType === 'up' ? 'voted-up' : 'voted-down');
                    }

                    // LocalStorage kaydet
                    votedNotes[noteId] = voteType;
                    localStorage.setItem('suk_voted_notes', JSON.stringify(votedNotes));

                    showToast(
                        voteType === 'up' 
                            ? 'Faydalı oyu kaydedildi! Dayanışmaya katkınız için teşekkürler.' 
                            : 'Geri bildiriminiz kaydedildi.', 
                        'success'
                    );
                } else {
                    showToast(result.message || 'Oy kaydedilemedi.', 'error');
                }
            } catch (err) {
                console.error('Vote error:', err);
                showToast('Bir bağlantı hatası oluştu.', 'error');
            } finally {
                btn.disabled = false;
            }
        });
    });
}

/* ==========================================================================
   HATALI İÇERİK BİLDİRİMİ (REPORT MODAL)
   ========================================================================== */
let activeReportNoteId = null;

function initReportModal() {
    const reportButtons = document.querySelectorAll('.btn-report');
    const modalEl = document.getElementById('reportModal');
    const submitBtn = document.getElementById('btnSubmitReport');
    const noteTitleSpan = document.getElementById('reportNoteTitle');
    const reasonSelect = document.getElementById('reportReason');
    const otherDetails = document.getElementById('reportOtherDetails');

    if (!modalEl || !submitBtn) return;

    const bsModal = new bootstrap.Modal(modalEl);

    reportButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            activeReportNoteId = btn.dataset.noteId;
            const title = btn.dataset.noteTitle || 'Bu Not';
            if (noteTitleSpan) noteTitleSpan.textContent = title;
            if (otherDetails) otherDetails.value = '';
            bsModal.show();
        });
    });

    submitBtn.addEventListener('click', async () => {
        if (!activeReportNoteId) return;

        const reason = reasonSelect ? reasonSelect.value : 'Belirtilmedi';
        const details = otherDetails ? otherDetails.value.trim() : '';
        const fullReason = details ? `${reason} - Açıklama: ${details}` : reason;

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>İletiliyor...';

        try {
            const response = await fetch(`/api/report/${activeReportNoteId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ reason: fullReason })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                bsModal.hide();
                showToast(result.message, 'success');
            } else {
                showToast(result.message || 'Bildirim iletilemedi.', 'error');
            }
        } catch (err) {
            console.error('Report error:', err);
            showToast('Bağlantı hatası oluştu.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane me-1"></i> Bildirimi Gönder';
        }
    });
}

/* ==========================================================================
   BELGE ÖNİZLEME MODALI (PREVIEW MODAL)
   ========================================================================== */
function initPreviewModal() {
    const previewButtons = document.querySelectorAll('.btn-preview');
    const modalEl = document.getElementById('previewModal');
    const titleEl = document.getElementById('previewModalTitle');
    const downloadDirectLink = document.getElementById('previewModalDownloadBtn');
    const bodyEl = document.getElementById('previewModalContent');

    if (!modalEl || !bodyEl) return;

    const bsModal = new bootstrap.Modal(modalEl);

    previewButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const noteId = btn.dataset.noteId;
            const title = btn.dataset.noteTitle || 'Belge Önizleme';
            const fileType = (btn.dataset.fileType || '').toLowerCase();
            const previewUrl = `/preview/${noteId}`;
            const downloadUrl = `/download/${noteId}`;

            if (titleEl) titleEl.textContent = title;
            if (downloadDirectLink) downloadDirectLink.href = downloadUrl;

            // İçeriği oluştur (PDF ise iframe/embed, Resim ise img)
            if (fileType === 'pdf') {
                bodyEl.innerHTML = `
                    <iframe src="${previewUrl}#toolbar=0" class="preview-iframe" title="PDF Önizleme"></iframe>
                `;
            } else {
                bodyEl.innerHTML = `
                    <div class="p-3 text-center w-100">
                        <img src="${previewUrl}" class="preview-img rounded" alt="${title}" />
                    </div>
                `;
            }

            bsModal.show();
        });
    });

    // Modal kapandığında iframe belleğini temizle
    modalEl.addEventListener('hidden.bs.modal', () => {
        bodyEl.innerHTML = '';
    });
}

/* ==========================================================================
   SÜRÜKLE-BIRAK (DRAG & DROP) DOSYA YÜKLEME
   ========================================================================== */
function initUploadDropzone() {
    const dropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('noteFileInput');
    const filePreview = document.getElementById('filePreview');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const fileSizeDisplay = document.getElementById('fileSizeDisplay');
    const removeFileBtn = document.getElementById('btnRemoveFile');
    const uploadForm = document.getElementById('noteUploadForm');
    const courseCodeInput = document.getElementById('course_code');
    const courseNameInput = document.getElementById('course_name');

    if (!dropzone || !fileInput) return;

    // Selçuk Bilgisayar Mühendisliği dersleri otomatik tamamlama eşleştirmesi
    const courseDirectory = {
        'BIL101': 'Programlamaya Giriş',
        'BIL103': 'Bilgisayar Mühendisliğine Giriş',
        'BIL105': 'Matematik I',
        'BIL107': 'Fizik I',
        'BIL102': 'Nesne Yönelimli Programlama',
        'BIL104': 'Matematik II',
        'BIL106': 'Fizik II',
        'BIL201': 'Veri Yapıları',
        'BIL203': 'Sayısal Mantık Tasarımı',
        'BIL205': 'Diferansiyel Denklemler',
        'BIL202': 'Algoritma Analizi',
        'BIL204': 'Elektrik ve Elektronik Devreler',
        'BIL301': 'İşletim Sistemleri',
        'BIL303': 'Veritabanı Sistemleri',
        'BIL305': 'Bilgisayar Mimarisi',
        'BIL302': 'Bilgisayar Ağları',
        'BIL304': 'Yazılım Mühendisliği',
        'BIL306': 'Web Teknolojileri',
        'BIL401': 'Makine Öğrenmesi',
        'BIL403': 'Derleyici Tasarımı',
        'BIL405': 'Dağıtık Sistemler',
        'BIL407': 'Yapay Zeka',
        'BIL402': 'Bilgi Güvenliği ve Kriptoloji'
    };

    if (courseCodeInput && courseNameInput) {
        courseCodeInput.addEventListener('input', () => {
            const val = courseCodeInput.value.trim().toUpperCase();
            if (courseDirectory[val] && (!courseNameInput.value || courseNameInput.value === '')) {
                courseNameInput.value = courseDirectory[val];
            }
        });
    }

    // Tıklayınca dosya seçiciyi aç
    dropzone.addEventListener('click', (e) => {
        if (e.target !== removeFileBtn && !removeFileBtn?.contains(e.target)) {
            fileInput.click();
        }
    });

    // Drag-over ve Drop olayları
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleSelectedFile(files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleSelectedFile(fileInput.files[0]);
        }
    });

    function handleSelectedFile(file) {
        const validExtensions = ['pdf', 'jpg', 'jpeg', 'png'];
        const ext = file.name.split('.').pop().toLowerCase();

        if (!validExtensions.includes(ext)) {
            showToast('Sadece PDF, JPG, JPEG veya PNG dosyaları kabul edilir!', 'error');
            fileInput.value = '';
            return;
        }

        const maxSize = 25 * 1024 * 1024; // 25 MB
        if (file.size > maxSize) {
            showToast('Dosya boyutu 25 MB sınırını aşıyor!', 'error');
            fileInput.value = '';
            return;
        }

        // Seçilen dosyayı DataTransfer ile input'a ata
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;

        if (fileNameDisplay) fileNameDisplay.textContent = file.name;
        if (fileSizeDisplay) {
            const mbSize = (file.size / (1024 * 1024)).toFixed(2);
            fileSizeDisplay.textContent = `${mbSize} MB`;
        }

        if (filePreview) filePreview.style.display = 'flex';
        dropzone.querySelector('.dropzone-prompt')?.classList.add('d-none');
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            if (filePreview) filePreview.style.display = 'none';
            dropzone.querySelector('.dropzone-prompt')?.classList.remove('d-none');
        });
    }

    // Form gönderimini ele al (AJAX ile güzel geri bildirim)
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Lütfen yüklenecek bir not dosyası seçiniz.', 'error');
                return;
            }

            const submitBtn = document.getElementById('btnSubmitUpload');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Yükleniyor ve Doğrulanıyor...';
            }

            const formData = new FormData(uploadForm);

            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(result.message, 'success');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1200);
                } else {
                    showToast(result.message || 'Yükleme sırasında bir hata oluştu.', 'error');
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalBtnHtml;
                    }
                }
            } catch (err) {
                console.error('Upload error:', err);
                showToast('Yükleme sırasında sunucu veya ağ hatası oluştu.', 'error');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                }
            }
        });
    }
}

/* ==========================================================================
   FİLTRE DEĞİŞİKLİĞİNDE OTOMATİK FORM GÖNDERİMİ
   ========================================================================== */
function initFilterLiveSync() {
    const filterForm = document.getElementById('filterForm');
    if (!filterForm) return;

    const autoSubmits = filterForm.querySelectorAll('select');
    autoSubmits.forEach(select => {
        select.addEventListener('change', () => {
            filterForm.submit();
        });
    });
}
