import os
import uuid
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    jsonify, send_from_directory, flash, abort, session
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import or_, desc, func

from config import Config
from models import db, Note

app = Flask(__name__)
app.config.from_object(Config)

# Veritabanını ve yükleme dizinini başlat
db.init_app(app)

# Uploads dizininin var olduğundan emin ol
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def admin_required(f):
    """Yönetici oturumu gerektiren rotalar için decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bu sayfaya erişmek için yönetici girişi yapmalısınız.', 'warning')
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_admin_status():
    """Tüm şablonlara yönetici oturum durumunu aktarır."""
    return {
        'is_admin': session.get('is_admin', False)
    }


def allowed_file(filename):
    """Dosya uzantısının izin verilen listede olup olmadığını kontrol eder."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_file_extension(filename):
    """Dosya uzantısını küçük harfle döndürür."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


# ==========================================
# SAYFA ROTALARI (PAGE ROUTES)
# ==========================================

@app.route('/')
def index():
    """Ana sayfa: Yalnızca onaylanmış notları listeleme, arama ve filtreleme."""
    query = Note.query.filter_by(is_approved=True)

    # Filtre parametreleri
    search_q = request.args.get('q', '').strip()
    class_level = request.args.get('class_level', '').strip()
    exam_type = request.args.get('exam_type', '').strip()
    file_type = request.args.get('file_type', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    # Arama filtresi (Ders Kodu, Ders Adı, Not Başlığı)
    if search_q:
        search_filter = or_(
            Note.title.ilike(f'%{search_q}%'),
            Note.course_code.ilike(f'%{search_q}%'),
            Note.course_name.ilike(f'%{search_q}%'),
            Note.description.ilike(f'%{search_q}%')
        )
        query = query.filter(search_filter)

    # Sınıf filtresi
    if class_level and class_level.isdigit():
        query = query.filter(Note.class_level == int(class_level))

    # Sınav türü filtresi
    if exam_type and exam_type in ['Vize', 'Final', 'Genel']:
        query = query.filter(Note.exam_type == exam_type)

    # Dosya türü filtresi
    if file_type:
        if file_type.lower() == 'pdf':
            query = query.filter(Note.file_type == 'pdf')
        elif file_type.lower() == 'image':
            query = query.filter(Note.file_type.in_(['jpg', 'jpeg', 'png']))

    # Sıralama
    if sort_by == 'popular':
        query = query.order_by(desc(Note.download_count))
    elif sort_by == 'top_rated':
        query = query.order_by(desc(Note.upvotes - Note.downvotes))
    elif sort_by == 'oldest':
        query = query.order_by(Note.created_at.asc())
    else:  # newest
        query = query.order_by(desc(Note.created_at))

    notes = query.all()

    # Genel İstatistikler (Sadece onaylı notlar)
    total_notes = Note.query.filter_by(is_approved=True).count()
    total_downloads = db.session.query(func.coalesce(func.sum(Note.download_count), 0)).filter(Note.is_approved == True).scalar() or 0
    total_courses = db.session.query(func.count(func.distinct(Note.course_code))).filter(Note.is_approved == True).scalar() or 0
    total_upvotes = db.session.query(func.coalesce(func.sum(Note.upvotes), 0)).filter(Note.is_approved == True).scalar() or 0

    return render_template(
        'index.html',
        notes=notes,
        total_notes=total_notes,
        total_downloads=total_downloads,
        total_courses=total_courses,
        total_upvotes=total_upvotes,
        current_search=search_q,
        current_class=class_level,
        current_exam=exam_type,
        current_file_type=file_type,
        current_sort=sort_by
    )


@app.route('/not-yukle')
def upload_page():
    """Not yükleme formu sayfası."""
    return render_template('upload.html')


@app.route('/istatistikler')
def stats_page():
    """Detaylı dayanışma ve platform istatistikleri sayfası (Onaylı notlar)."""
    approved_filter = (Note.is_approved == True)
    total_notes = Note.query.filter(approved_filter).count()
    total_downloads = db.session.query(func.coalesce(func.sum(Note.download_count), 0)).filter(approved_filter).scalar() or 0
    total_upvotes = db.session.query(func.coalesce(func.sum(Note.upvotes), 0)).filter(approved_filter).scalar() or 0
    total_reports = db.session.query(func.coalesce(func.sum(Note.report_count), 0)).scalar() or 0
    total_courses = db.session.query(func.count(func.distinct(Note.course_code))).filter(approved_filter).scalar() or 0

    # Sınıf düzeyine göre dağılım
    class_stats = {1: 0, 2: 0, 3: 0, 4: 0}
    class_counts = db.session.query(Note.class_level, func.count(Note.id)).filter(approved_filter).group_by(Note.class_level).all()
    for level, count in class_counts:
        if level in class_stats:
            class_stats[level] = count

    # Sınav türüne göre dağılım
    exam_stats = {'Vize': 0, 'Final': 0, 'Genel': 0}
    exam_counts = db.session.query(Note.exam_type, func.count(Note.id)).filter(approved_filter).group_by(Note.exam_type).all()
    for etype, count in exam_counts:
        if etype in exam_stats:
            exam_stats[etype] = count

    # Dosya türüne göre dağılım
    file_type_stats = {'pdf': 0, 'görsel': 0}
    ftype_counts = db.session.query(Note.file_type, func.count(Note.id)).filter(approved_filter).group_by(Note.file_type).all()
    for ftype, count in ftype_counts:
        if ftype == 'pdf':
            file_type_stats['pdf'] += count
        else:
            file_type_stats['görsel'] += count

    # En çok indirilen 5 not
    top_downloaded = Note.query.filter(approved_filter).order_by(desc(Note.download_count)).limit(5).all()

    # En yüksek puan alan 5 not (upvotes - downvotes)
    top_rated = Note.query.filter(approved_filter).order_by(desc(Note.upvotes - Note.downvotes)).limit(5).all()

    # En çok not paylaşılan 5 ders
    top_courses = db.session.query(
        Note.course_code, Note.course_name, func.count(Note.id).label('note_count')
    ).filter(approved_filter).group_by(Note.course_code, Note.course_name).order_by(desc('note_count')).limit(5).all()

    return render_template(
        'stats.html',
        total_notes=total_notes,
        total_downloads=total_downloads,
        total_upvotes=total_upvotes,
        total_reports=total_reports,
        total_courses=total_courses,
        class_stats=class_stats,
        exam_stats=exam_stats,
        file_type_stats=file_type_stats,
        top_downloaded=top_downloaded,
        top_rated=top_rated,
        top_courses=top_courses
    )


# ==========================================
# DOSYA İNDİRME VE ÖNİZLEME ROTALARI
# ==========================================

@app.route('/download/<int:id>')
def download_note(id):
    """Dosyayı güvenli bir şekilde indirir ve indirme sayısını 1 artırır."""
    note = db.session.get(Note, id)
    if not note:
        abort(404, description="Not bulunamadı.")

    # İndirme sayacını artır
    note.download_count += 1
    db.session.commit()

    # Kullanıcı dostu temiz dosya adı oluştur
    clean_course = secure_filename(note.course_code) or "DERS"
    clean_title = secure_filename(note.title.replace(' ', '_')) or "Not"
    download_filename = f"{clean_course}_{clean_title}.{note.file_type}"

    as_attachment = request.args.get('preview') != '1'

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        note.file_path,
        as_attachment=as_attachment,
        download_name=download_filename
    )


@app.route('/preview/<int:id>')
def preview_note(id):
    """Tarayıcıda önizleme (modal veya yeni sekme) için dosyayı sunar."""
    note = db.session.get(Note, id)
    if not note:
        abort(404, description="Not bulunamadı.")

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        note.file_path,
        as_attachment=False
    )


# ==========================================
# REST API ROTALARI
# ==========================================

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Dosya yükleme rotası:
    - secure_filename kontrolü
    - Max 25MB sınırı
    - Sadece .pdf, .jpg, .jpeg, .png formatları
    - SQLite veritabanına kayıt
    """
    # Dosya varlığı kontrolü
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Lütfen bir dosya seçiniz.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Seçilen dosya adı geçersiz veya boş.'}), 400

    # Form alanlarını al ve doğrula
    title = request.form.get('title', '').strip()
    course_code = request.form.get('course_code', '').strip().upper()
    course_name = request.form.get('course_name', '').strip()
    class_level_raw = request.form.get('class_level', '').strip()
    exam_type = request.form.get('exam_type', '').strip()
    description = request.form.get('description', '').strip()

    if not title or not course_code or not course_name or not class_level_raw or not exam_type:
        return jsonify({'success': False, 'message': 'Lütfen zorunlu tüm alanları eksiksiz doldurunuz.'}), 400

    try:
        class_level = int(class_level_raw)
        if class_level not in [1, 2, 3, 4]:
            raise ValueError()
    except ValueError:
        return jsonify({'success': False, 'message': 'Geçerli bir sınıf düzeyi seçiniz (1, 2, 3 veya 4).' }), 400

    if exam_type not in ['Vize', 'Final', 'Genel']:
        return jsonify({'success': False, 'message': 'Geçerli bir sınav türü seçiniz (Vize, Final veya Genel).' }), 400

    # Dosya uzantısı kontrolü
    if not allowed_file(file.filename):
        return jsonify({
            'success': False, 
            'message': 'İzin verilmeyen dosya formatı! Sadece PDF, JPG, JPEG ve PNG formatları desteklenmektedir.'
        }), 400

    # Benzersiz ve güvenli dosya adı üretimi
    ext = get_file_extension(file.filename)
    safe_base = secure_filename(file.filename.rsplit('.', 1)[0]) or 'belge'
    unique_filename = f"{uuid.uuid4().hex[:10]}_{safe_base}.{ext}"
    saved_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

    # Dosyayı diske kaydet
    file.save(saved_path)

    # Dosya boyutunu ölç
    file_size = os.path.getsize(saved_path)

    # Veritabanına kaydet (Varsayılan olarak onay bekliyor: is_approved=False)
    note = Note(
        title=title,
        course_code=course_code,
        course_name=course_name,
        class_level=class_level,
        exam_type=exam_type,
        file_path=unique_filename,
        file_type=ext,
        file_size=file_size,
        description=description,
        download_count=0,
        upvotes=0,
        downvotes=0,
        report_count=0,
        is_approved=False
    )

    db.session.add(note)
    db.session.commit()

    # Standart tarayıcı form navigasyonu ise (AJAX veya API istemcisi değilse) ana sayfaya yönlendir
    if request.headers.get('Accept') == 'text/html' and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        flash('Ders notunuz başarıyla yüklendi! Yönetici onayından sonra platformda yayınlanacaktır.', 'success')
        return redirect(url_for('index'))

    return jsonify({
        'success': True,
        'message': 'Ders notunuz başarıyla yüklendi! Yönetici onayından sonra platformda yayınlanacaktır.',
        'note_id': note.id
    }), 201


@app.route('/api/vote/<int:id>', methods=['POST'])
def api_vote(id):
    """
    Faydalı / Yetersiz oyu verme API'si (AJAX/Fetch ile asenkron tetiklenir).
    JSON: { "vote_type": "up" | "down" }
    """
    note = db.session.get(Note, id)
    if not note:
        return jsonify({'success': False, 'message': 'Not bulunamadı.'}), 404

    data = request.get_json(silent=True) or request.form
    vote_type = data.get('vote_type')

    if vote_type == 'up':
        note.upvotes += 1
    elif vote_type == 'down':
        note.downvotes += 1
    else:
        return jsonify({'success': False, 'message': 'Geçersiz oy türü. "up" veya "down" olmalıdır.'}), 400

    db.session.commit()

    return jsonify({
        'success': True,
        'upvotes': note.upvotes,
        'downvotes': note.downvotes,
        'score': note.score,
        'message': 'Oyunuz başarıyla kaydedildi!'
    })


@app.route('/api/report/<int:id>', methods=['POST'])
def api_report(id):
    """
    Hatalı içerik bildirimi API'si.
    JSON: { "reason": "İçerik okunamıyor / Telif / Yanlış ders" }
    """
    note = db.session.get(Note, id)
    if not note:
        return jsonify({'success': False, 'message': 'Not bulunamadı.'}), 404

    data = request.get_json(silent=True) or request.form
    reason = data.get('reason', 'Belirtilmedi')

    note.report_count += 1
    db.session.commit()

    return jsonify({
        'success': True,
        'report_count': note.report_count,
        'message': 'Geri bildiriminiz incelenmek üzere kaydedildi. Dayanışma kalitesini koruduğunuz için teşekkür ederiz!'
    })


@app.route('/api/notes', methods=['GET'])
def api_notes():
    """Anlık arama ve filtreleme için onaylı notların JSON listesini döndürür."""
    query = Note.query.filter_by(is_approved=True)

    search_q = request.args.get('q', '').strip()
    class_level = request.args.get('class_level', '').strip()
    exam_type = request.args.get('exam_type', '').strip()
    file_type = request.args.get('file_type', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    if search_q:
        search_filter = or_(
            Note.title.ilike(f'%{search_q}%'),
            Note.course_code.ilike(f'%{search_q}%'),
            Note.course_name.ilike(f'%{search_q}%')
        )
        query = query.filter(search_filter)

    if class_level and class_level.isdigit():
        query = query.filter(Note.class_level == int(class_level))

    if exam_type and exam_type in ['Vize', 'Final', 'Genel']:
        query = query.filter(Note.exam_type == exam_type)

    if file_type:
        if file_type.lower() == 'pdf':
            query = query.filter(Note.file_type == 'pdf')
        elif file_type.lower() == 'image':
            query = query.filter(Note.file_type.in_(['jpg', 'jpeg', 'png']))

    if sort_by == 'popular':
        query = query.order_by(desc(Note.download_count))
    elif sort_by == 'top_rated':
        query = query.order_by(desc(Note.upvotes - Note.downvotes))
    elif sort_by == 'oldest':
        query = query.order_by(Note.created_at.asc())
    else:
        query = query.order_by(desc(Note.created_at))

    notes = query.all()
    return jsonify({
        'success': True,
        'count': len(notes),
        'notes': [n.to_dict() for n in notes]
    })


# ==========================================
# YÖNETİCİ (ADMIN) ROTALARI
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Yönetici giriş sayfası ve doğrulama."""
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        admin_pass = app.config.get('ADMIN_PASSWORD', 'admin123')

        if password == admin_pass:
            session['is_admin'] = True
            flash('Yönetici girişi başarılı. Hoş geldiniz!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin_dashboard'))
        else:
            flash('Geçersiz yönetici şifresi! Lütfen tekrar deneyiniz.', 'danger')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Yönetici oturumunu sonlandırır."""
    session.pop('is_admin', None)
    flash('Yönetici oturumu güvenle kapatıldı.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Yönetici Kontrol Paneli: Onay bekleyen, yayındaki ve şikayet edilen notlar."""
    pending_notes = Note.query.filter_by(is_approved=False).order_by(desc(Note.created_at)).all()
    approved_notes = Note.query.filter_by(is_approved=True).order_by(desc(Note.created_at)).all()
    reported_notes = Note.query.filter(Note.report_count > 0).order_by(desc(Note.report_count)).all()

    return render_template(
        'admin_dashboard.html',
        pending_notes=pending_notes,
        approved_notes=approved_notes,
        reported_notes=reported_notes,
        pending_count=len(pending_notes),
        approved_count=len(approved_notes),
        reported_count=len(reported_notes)
    )


@app.route('/admin/notes/<int:id>/approve', methods=['POST'])
@admin_required
def admin_approve_note(id):
    """Notu onaylar ve sitede yayınlar."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    note.is_approved = True
    db.session.commit()
    flash(f'"{note.title}" ({note.course_code}) onaylandı ve yayına alındı.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notes/<int:id>/unapprove', methods=['POST'])
@admin_required
def admin_unapprove_note(id):
    """Onaylanmış notu yayından çekip tekrar beklemeye alır."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    note.is_approved = False
    db.session.commit()
    flash(f'"{note.title}" yayından kaldırıldı ve onay bekleyenlere taşındı.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notes/<int:id>/reject', methods=['POST'])
@app.route('/admin/notes/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_note(id):
    """Notu ve dosyasını sistemden kalıcı olarak siler."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Fiziksel dosyayı da sil
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        app.logger.warning(f"Dosya silinirken hata: {e}")

    note_title = note.title
    db.session.delete(note)
    db.session.commit()

    flash(f'"{note_title}" başarıyla sistemden silindi.', 'info')
    return redirect(url_for('admin_dashboard'))


# ==========================================
# HATA YAKALAYICILAR (ERROR HANDLERS)
# ==========================================

@app.errorhandler(RequestEntityTooLarge)
def handle_file_size_error(e):
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': 'Yüklenen dosya çok büyük! Maksimum izin verilen dosya boyutu 25 MB\'dir.'
        }), 413
    flash('Yüklenen dosya çok büyük! Maksimum izin verilen dosya boyutu 25 MB\'dir.', 'danger')
    return redirect(url_for('upload_page'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', not_found=True), 404


# CLI Komutu veya ilk çalıştırmada tabloları oluştur
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
