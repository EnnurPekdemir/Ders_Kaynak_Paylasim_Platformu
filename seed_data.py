import os
import random
from datetime import datetime, timedelta, timezone

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from app import app, db
from models import Note

# Renk paleti
COLORS = [
    ("#0f766e", "#14b8a6"), # Teal / Turkuaz (Selçuk Üniversitesi tonları)
    ("#1e3a8a", "#3b82f6"), # Royal Blue
    ("#4338ca", "#6366f1"), # Indigo
    ("#065f46", "#10b981"), # Emerald
    ("#831843", "#ec4899"), # Rose
    ("#7c2d12", "#f97316"), # Amber / Orange
]

SAMPLE_NOTES = [
    {
        "course_code": "BIL101",
        "course_name": "Programlamaya Giriş",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "Python Temel Sözdizimi, Döngüler ve Fonksiyonlar Özeti",
        "description": "Değişkenler, liste metodları, döngü mantığı ve lambda fonksiyonları içeren kapsamlı vize çalışma notu.",
        "file_type": "pdf",
        "download_count": 142,
        "upvotes": 38,
        "downvotes": 1,
        "report_count": 0
    },
    {
        "course_code": "BIL105",
        "course_name": "Matematik I",
        "class_level": 1,
        "exam_type": "Final",
        "title": "Limit, Türev Alma Kuralları ve İntegral Formül Kartı",
        "description": "Vize ve Finalde çıkabilecek tüm temel türev/integral formülleri ve örnek çözüm grafikleri.",
        "file_type": "png",
        "download_count": 215,
        "upvotes": 52,
        "downvotes": 2,
        "report_count": 0
    },
    {
        "course_code": "BIL102",
        "course_name": "Nesne Yönelimli Programlama",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "Java OOP Prensipleri (Kapsülleme, Kalıtım, Polimorfizm)",
        "description": "Sınıf yapıları, soyut sınıflar, arayüzler ve örnek UML diyagramları ile pratik kod blokları.",
        "file_type": "pdf",
        "download_count": 98,
        "upvotes": 27,
        "downvotes": 0,
        "report_count": 0
    },
    {
        "course_code": "BIL201",
        "course_name": "Veri Yapıları",
        "class_level": 2,
        "exam_type": "Final",
        "title": "Bağlı Listeler, İkili Arama Ağaçları (BST) ve AVL Ağaçları",
        "description": "Yığın, kuyruk, bağlı liste implementasyonları ve ağaç rotasyon adımları görselleştirmeli ders notu.",
        "file_type": "pdf",
        "download_count": 310,
        "upvotes": 84,
        "downvotes": 3,
        "report_count": 0
    },
    {
        "course_code": "BIL203",
        "course_name": "Sayısal Mantık Tasarımı",
        "class_level": 2,
        "exam_type": "Vize",
        "title": "Karnaugh Haritaları (K-Map), Mantık Kapıları ve Flip-Floplar",
        "description": "Boole cebri sadeleştirme kuralları, JK, D ve T flip-flop geçiş tabloları ve örnek vize soruları.",
        "file_type": "jpg",
        "download_count": 184,
        "upvotes": 45,
        "downvotes": 1,
        "report_count": 0
    },
    {
        "course_code": "BIL202",
        "course_name": "Algoritma Analizi",
        "class_level": 2,
        "exam_type": "Genel",
        "title": "Asimptotik Notasyon (Big-O) ve Dinamik Programlama",
        "description": "Böl ve Yönet yaklaşımı, Sıralama algoritmaları karmaşıklık analizi ve Sırt Çantası (Knapsack) çözümü.",
        "file_type": "pdf",
        "download_count": 167,
        "upvotes": 41,
        "downvotes": 2,
        "report_count": 0
    },
    {
        "course_code": "BIL301",
        "course_name": "İşletim Sistemleri",
        "class_level": 3,
        "exam_type": "Vize",
        "title": "Süreç Yönetimi, CPU Zamanlama ve Deadlock (Kilitlenme) Çözümü",
        "description": "Process & Thread farkı, Banker algoritması adımları, Semaphore ve Mutex mekanizmaları.",
        "file_type": "pdf",
        "download_count": 278,
        "upvotes": 73,
        "downvotes": 2,
        "report_count": 0
    },
    {
        "course_code": "BIL303",
        "course_name": "Veritabanı Sistemleri",
        "class_level": 3,
        "exam_type": "Final",
        "title": "İlişkisel Cebir, Normalizasyon (1NF, 2NF, 3NF, BCNF) ve SQL",
        "description": "E-R diyagramları dönüştürme, karmaşık SQL sorguları, indeksleme ve transaction ACID prensipleri.",
        "file_type": "pdf",
        "download_count": 340,
        "upvotes": 96,
        "downvotes": 4,
        "report_count": 1
    },
    {
        "course_code": "BIL302",
        "course_name": "Bilgisayar Ağları",
        "class_level": 3,
        "exam_type": "Vize",
        "title": "OSI & TCP/IP Katmanları, IP Subnetting (Alt Ağlara Bölme)",
        "description": "CIDR hesaplamaları, TCP 3-Way Handshake, DNS/DHCP protokolleri ve yönlendirme algoritmaları.",
        "file_type": "png",
        "download_count": 195,
        "upvotes": 49,
        "downvotes": 1,
        "report_count": 0
    },
    {
        "course_code": "BIL401",
        "course_name": "Makine Öğrenmesi",
        "class_level": 4,
        "exam_type": "Final",
        "title": "Denetimli ve Denetimsiz Öğrenme, Karar Ağaçları & Sinir Ağları",
        "description": "Lineer Regresyon, Lojistik Regresyon, SVM, K-Means kümeleme ve Yapay Sinir Ağı aktivasyon fonksiyonları.",
        "file_type": "pdf",
        "download_count": 156,
        "upvotes": 42,
        "downvotes": 1,
        "report_count": 0
    }
]


def create_sample_document(file_path, file_type, course_code, course_name, title, exam_type):
    """Pillow kütüphanesi varsa şık önizleme dosyası, yoksa standart minimal dosya oluşturur."""
    if not HAS_PIL:
        if file_type.lower() == 'pdf':
            pdf_data = (
                b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
                b"4 0 obj\n<< /Length 55 >>\nstream\nBT /F1 18 Tf 50 700 Td (Selcuk Uni Bilgisayar Muh - Ders Notu) Tj ET\nendstream\nendobj\n"
                b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \n"
                b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n310\n%%EOF\n"
            )
            with open(file_path, 'wb') as f:
                f.write(pdf_data)
        else:
            # 1x1 piksel şeffaf PNG binary
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
            with open(file_path, 'wb') as f:
                f.write(png_data)
        return

    width, height = 1200, 1600
    color_bg = (248, 250, 252)  # slate-50
    header_color = (15, 118, 110)  # Selçuk turquoise (#0f766e)

    img = Image.new('RGB', (width, height), color=color_bg)
    draw = ImageDraw.Draw(img)

    # Üst banner
    draw.rectangle([(0, 0), (width, 220)], fill=header_color)

    # Başlık ve Üst Bilgi
    draw.text((60, 40), "SELÇUK ÜNİVERSİTESİ BİLGİSAYAR MÜHENDİSLİĞİ", fill=(255, 255, 255))
    draw.text((60, 80), "Topluma Hizmet Uygulamaları - Açık Ders Notu Havuzu", fill=(204, 251, 241))
    draw.text((60, 140), f"{course_code} - {course_name} ({exam_type} Notu)", fill=(255, 255, 255))

    # Not Gövdesi Kartı
    draw.rectangle([(60, 270), (width - 60, height - 120)], fill=(255, 255, 255), outline=(226, 232, 240), width=3)

    # Başlık
    draw.text((100, 320), f"Konu: {title}", fill=(15, 23, 42))

    # İçerik maddeleri
    lines = [
        "1. TEMEL KAVRAMLAR VE TANIMLAR",
        "   - Bu ders notu Selçuk Üniversitesi öğrencileri arasındaki akademik dayanışmayı",
        "     güçlendirmek amacıyla hazırlanmış açık kaynak bir kaynak özetidir.",
        "   - Ders içeriğindeki temel teoremler, sözdizimi kuralları ve algoritmalar derlenmiştir.",
        "",
        "2. ÖNEMLİ FORMÜLLER VE İPUÇLARI",
        "   - Sınav hazırlığında dikkat edilmesi gereken anahtar yöntemler ve zaman karmaşıklıkları.",
        "   - Soru çözüm adımlarında pratik kısayollar ve kontrol basamakları.",
        "",
        "3. UYGULAMA VE ÖRNEK PROBLEM ÇÖZÜMLERİ",
        "   - Adım adım algoritma yürütme (Trace table) ve bellek yönetimi analizleri.",
        "   - Vize ve Final sorularında sıkça karşılaşılan senaryolar.",
        "",
        "----------------------------------------------------------------------------------",
        "Dayanışma Paylaştıkça Büyür! Başarılar dileriz.",
        "Selçuk Üniversitesi Bilgisayar Mühendisliği Bölümü Öğrenci İnisiyatifi"
    ]

    y_offset = 400
    for line in lines:
        draw.text((100, y_offset), line, fill=(51, 65, 85))
        y_offset += 45

    # Alt Bilgi Çubuğu
    draw.rectangle([(0, height - 70), (width, height)], fill=(15, 23, 42))
    draw.text((60, height - 45), "Ders Notu ve Kaynak Dayanışma Platformu • Lisans: Açık Not Havuzu (CC-BY)", fill=(148, 163, 184))

    if file_type.lower() == 'pdf':
        img.save(file_path, "PDF", resolution=100.0)
    elif file_type.lower() in ['jpg', 'jpeg']:
        img.save(file_path, "JPEG", quality=90)
    else:
        img.save(file_path, "PNG")


def seed():
    with app.app_context():
        # Tabloları oluştur
        db.create_all()

        # Eğer zaten notlar varsa tekrar ekleme
        existing_count = Note.query.count()
        if existing_count > 0:
            print(f"Veritabanında zaten {existing_count} adet not mevcut. Seed işlemi atlandı.")
            return

        print("Örnek ders notları ve dosyaları oluşturuluyor...")
        base_date = datetime.now(timezone.utc) - timedelta(days=20)

        for i, item in enumerate(SAMPLE_NOTES):
            filename = f"sample_{item['course_code'].lower()}_{item['exam_type'].lower()}_{i+1}.{item['file_type']}"
            file_full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Dosyayı diske oluştur
            create_sample_document(
                file_full_path, 
                item['file_type'],
                item['course_code'], 
                item['course_name'], 
                item['title'],
                item['exam_type']
            )

            file_size = os.path.getsize(file_full_path)

            note = Note(
                title=item['title'],
                course_code=item['course_code'],
                course_name=item['course_name'],
                class_level=item['class_level'],
                exam_type=item['exam_type'],
                file_path=filename,
                file_type=item['file_type'],
                file_size=file_size,
                description=item['description'],
                download_count=item['download_count'],
                upvotes=item['upvotes'],
                downvotes=item['downvotes'],
                report_count=item['report_count'],
                is_approved=True,  # Örnek notlar doğrudan onaylı yayında başlasın
                created_at=base_date + timedelta(days=i * 2, hours=random.randint(1, 10))
            )
            db.session.add(note)

        db.session.commit()
        print(f"Başarıyla {len(SAMPLE_NOTES)} adet örnek ders notu ve dosyası yüklendi (tümü onaylı)!")


if __name__ == '__main__':
    seed()
