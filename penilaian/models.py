from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image


# --- MODEL BARU 1: SEMESTER ---
# Untuk mengelola periode semester secara dinamis
class Semester(models.Model):
    nama_semester = models.CharField(max_length=100, unique=True, help_text="Contoh: GANJIL 2025/2026")
    is_active = models.BooleanField(default=False, help_text="Centang ini untuk semester yang sedang berjalan")

    def __str__(self):
        return self.nama_semester

# --- MODEL BARU 2: KELAS ---
# Untuk mengelola daftar kelas secara dinamis
class Kelas(models.Model):
    nama_kelas = models.CharField(max_length=100, unique=True, help_text="Contoh: X Kuliner 1")

    def __str__(self):
        return self.nama_kelas

# --- MODEL BARU 3: PROFILE ---
# Untuk menghubungkan User (Wali Kelas) dengan Kelas yang diampunya
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Ini HANYA diisi jika peran user adalah "Wali Kelas"
    kelas_perwalian = models.ForeignKey(Kelas, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

# Fungsi ini otomatis membuat Profile setiap kali User baru dibuat
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# Fungsi ini otomatis menyimpan Profile setiap kali User disimpan
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# --- MODEL LAMA YANG DIMODIFIKASI ---

class Ekstrakurikuler(models.Model):
    nama_eskul = models.CharField(max_length=100)
    pelatih = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="eskul_diampu")

    # --- KOLOM BARU UNTUK LANDING PAGE ---
    deskripsi_singkat = models.CharField(max_length=255, blank=True, null=True, help_text="Deskripsi 1-2 kalimat untuk galeri eskul")
    deskripsi_panjang = models.TextField(blank=True, null=True, help_text="Biodata lengkap eskul (akan tampil di halaman detail)")
    jadwal_latihan = models.CharField(max_length=100, blank=True, null=True, help_text="Contoh: Setiap Jumat, 15:00 - 17:00")
    lokasi = models.CharField(max_length=100, blank=True, null=True, help_text="Contoh: Lapangan Sekolah")
    prestasi_unggulan = models.TextField(blank=True, null=True, help_text="Daftar prestasi, pisahkan dengan baris baru")
    foto_sampul = models.ImageField(upload_to='foto_eskul/', blank=True, null=True, help_text="Upload foto sampul (akan di-resize otomatis)")
    # --- AKHIR KOLOM BARU ---

    def __str__(self):
        return self.nama_eskul

    # --- LOGIKA KOMPRESI GAMBAR OTOMATIS ---
    def save(self, *args, **kwargs):
        if self.foto_sampul:
            # Buka gambar yang di-upload
            img = Image.open(self.foto_sampul)

            # Tentukan batas maksimal lebar dan kualitas
            max_width = 1920  # Lebar maksimal 1920px
            quality = 85      # Kompresi 85%

            # Jika gambar lebih lebar dari batas, resize
            if img.width > max_width:
                new_height = int((max_width / img.width) * img.height)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Siapkan buffer untuk menyimpan gambar yang sudah diproses
            output_io_stream = BytesIO()
            # Konversi gambar ke RGB (penting untuk format JPEG)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Simpan gambar ke buffer dengan format JPEG dan kualitas yang sudah ditentukan
            img.save(output_io_stream, format='JPEG', quality=quality)
            output_io_stream.seek(0)

            # Ganti file yang di-upload dengan file baru yang sudah dikompres
            self.foto_sampul = ContentFile(output_io_stream.getvalue(), name=self.foto_sampul.name)

        super(Ekstrakurikuler, self).save(*args, **kwargs)

class Siswa(models.Model):
    nama_siswa = models.CharField(max_length=255)
    nis = models.CharField(max_length=50, unique=True, help_text="Nomor Induk Siswa")

    # --- PERUBAHAN DI SINI ---
    # Mengganti CharField (teks) menjadi ForeignKey (link) ke model Kelas
    kelas = models.ForeignKey(Kelas, on_delete=models.PROTECT, related_name="siswa_di_kelas")
    # ---------------------------

    eskul_yang_diikuti = models.ManyToManyField(Ekstrakurikuler, related_name="anggota")

    def __str__(self):
        return f"{self.nama_siswa} ({self.kelas.nama_kelas})"

class Penilaian(models.Model):
    PREDIKAT_CHOICES = [
        ('A', 'A - Sangat Baik'),
        ('B', 'B - Baik'),
        ('C', 'C - Cukup'),
        ('D', 'D - Kurang'),
    ]

    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name="nilai_eskul")
    eskul = models.ForeignKey(Ekstrakurikuler, on_delete=models.CASCADE, related_name="penilaian_anggota")

    # --- PERUBAHAN 1 DI SINI ---
    # Mengganti CharField (teks) menjadi ForeignKey (link) ke model Semester
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="penilaian_di_semester")
    # ---------------------------

    nilai_kehadiran = models.IntegerField(default=0, help_text="Jumlah kehadiran", verbose_name="Jumlah Kehadiran")
    nilai_keaktifan = models.CharField(max_length=1, choices=PREDIKAT_CHOICES, default='C')

    # --- PERUBAHAN 2 DI SINI ---
    # Mengganti 'prestasi' menjadi 'kepersertaan_lomba' (sesuai hasil wawancara Pak Eko) 
    kepersertaan_lomba = models.TextField(blank=True, null=True, help_text="Catatan keikutsertaan/prestasi lomba")
    # ---------------------------

    catatan_pelatih = models.TextField(blank=True, null=True)
    tanggal_input = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nilai {self.siswa.nama_siswa} untuk {self.eskul.nama_eskul} ({self.semester.nama_semester})"
    
    # --- MODEL BARU UNTUK GALERI FOTO KEGIATAN ESKUL ---
class FotoEskul(models.Model):
    # Link ke eskul induknya
    eskul = models.ForeignKey(Ekstrakurikuler, on_delete=models.CASCADE, related_name="galeri_foto")

    # File foto itu sendiri
    foto = models.ImageField(upload_to='foto_kegiatan/', help_text="Upload foto kegiatan (akan di-resize otomatis)")

    # Keterangan/caption singkat untuk foto
    keterangan = models.CharField(max_length=255, blank=True, null=True, help_text="Keterangan singkat tentang foto ini")

    tanggal_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tanggal_upload'] # Foto terbaru akan muncul duluan
        verbose_name = "Foto Kegiatan Eskul"
        verbose_name_plural = "Galeri Foto Eskul"

    def __str__(self):
        return f"Foto untuk {self.eskul.nama_eskul} ({self.id})"

    # --- LOGIKA KOMPRESI GAMBAR OTOMATIS (Sama seperti di Tahap 14) ---
    def save(self, *args, **kwargs):
        if self.foto:
            img = Image.open(self.foto)
            max_width = 1024  # Kita buat lebih kecil dari foto sampul, 1024px sudah cukup
            quality = 80      # Kompresi 80%

            if img.width > max_width:
                new_height = int((max_width / img.width) * img.height)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            output_io_stream = BytesIO()
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.save(output_io_stream, format='JPEG', quality=quality)
            output_io_stream.seek(0)

            self.foto = ContentFile(output_io_stream.getvalue(), name=self.foto.name)

        super(FotoEskul, self).save(*args, **kwargs)

# --- MODEL BARU: PENDAFTARAN (Menampung data calon anggota) ---
class Pendaftaran(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Persetujuan'),
        ('APPROVED', 'Disetujui'),
        ('REJECTED', 'Ditolak'),
    ]

    # Data diri siswa pendaftar
    nama_siswa = models.CharField(max_length=255)
    nis = models.CharField(max_length=50, help_text="Nomor Induk Siswa")
    
    # Kita gunakan ForeignKey ke Kelas agar datanya valid
    kelas = models.ForeignKey(Kelas, on_delete=models.CASCADE, related_name="pendaftar")
    
    # Eskul yang dituju
    eskul_tujuan = models.ForeignKey(Ekstrakurikuler, on_delete=models.CASCADE, related_name="pendaftar")
    
    alasan = models.TextField(help_text="Alasan ingin bergabung", blank=True)
    no_hp_ortu = models.CharField(max_length=20, blank=True, null=True, help_text="Nomor HP Orang Tua (Opsional)")
    alamat = models.TextField(blank=True, null=True, help_text="Alamat Domisili (Opsional)")
    nomor_wa = models.CharField(max_length=20, help_text="Nomor WA yang bisa dihubungi")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    tanggal_daftar = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama_siswa} - {self.eskul_tujuan.nama_eskul} ({self.status})"