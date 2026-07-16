import os
from io import BytesIO
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from PIL import Image

class TahunAjaran(models.Model):
    nama_tahun = models.CharField(max_length=50, unique=True, help_text="Contoh: 2025/2026")
    is_active = models.BooleanField(default=False, help_text="Centang untuk tahun ajaran yang sedang berjalan")

    def save(self, *args, **kwargs):
        if self.is_active:
            # Otomatis MATIKAN SEMUA tahun ajaran lain jika ini diaktifkan
            TahunAjaran.objects.exclude(pk=self.pk).update(is_active=False)
        super(TahunAjaran, self).save(*args, **kwargs)

    def __str__(self):
        return self.nama_tahun

class Semester(models.Model):
    nama_semester = models.CharField(max_length=50, help_text="Contoh: Ganjil atau Genap")
    tahun_ajaran = models.ForeignKey(TahunAjaran, on_delete=models.CASCADE, related_name="semester_list", null=True, blank=True)
    is_active = models.BooleanField(default=False, help_text="Centang ini untuk semester yang sedang berjalan")

    def clean(self):
        # MENCEGAH MENGAKTIFKAN SEMESTER JIKA TAHUN AJARANNYA TIDAK AKTIF
        if self.is_active and self.tahun_ajaran:
            if not self.tahun_ajaran.is_active:
                raise ValidationError({
                    'is_active': f"GAGAL: Anda tidak bisa mengaktifkan semester ini karena Tahun Ajaran '{self.tahun_ajaran.nama_tahun}' sedang TIDAK AKTIF."
                })

    def save(self, *args, **kwargs):
        if self.is_active:
            # Otomatis MATIKAN SEMUA semester lain jika ini diaktifkan
            Semester.objects.exclude(pk=self.pk).update(is_active=False)
        super(Semester, self).save(*args, **kwargs)

    def __str__(self):
        if self.tahun_ajaran:
            return f"{self.nama_semester} - {self.tahun_ajaran.nama_tahun}"
        return self.nama_semester

class Kelas(models.Model):
    nama_kelas = models.CharField(max_length=100, unique=True, help_text="Contoh: 10 Kuliner 1")

    def __str__(self):
        return self.nama_kelas

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    kelas_perwalian = models.ForeignKey(Kelas, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Ekstrakurikuler(models.Model):
    nama_eskul = models.CharField(max_length=100)
    pelatih = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="eskul_diampu")

    deskripsi_singkat = models.CharField(max_length=255, blank=True, null=True, help_text="Deskripsi 1-2 kalimat untuk galeri eskul")
    deskripsi_panjang = models.TextField(blank=True, null=True, help_text="Biodata lengkap eskul (akan tampil di halaman detail)")
    jadwal_latihan = models.CharField(max_length=100, blank=True, null=True, help_text="Contoh: Setiap Jumat, 15:00 - 17:00")
    lokasi = models.CharField(max_length=100, blank=True, null=True, help_text="Contoh: Lapangan Sekolah")
    prestasi_unggulan = models.TextField(blank=True, null=True, help_text="Daftar prestasi, pisahkan dengan baris baru")
    foto_sampul = models.ImageField(upload_to='foto_eskul/', blank=True, null=True, help_text="Upload foto sampul (akan di-resize otomatis)")

    def __str__(self):
        return self.nama_eskul

    def save(self, *args, **kwargs):
        if self.foto_sampul:
            img = Image.open(self.foto_sampul)
            max_width = 1920  
            quality = 85      

            if img.width > max_width:
                new_height = int((max_width / img.width) * img.height)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            output_io_stream = BytesIO()
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img.save(output_io_stream, format='JPEG', quality=quality)
            output_io_stream.seek(0)
            self.foto_sampul = ContentFile(output_io_stream.getvalue(), name=self.foto_sampul.name)

        super(Ekstrakurikuler, self).save(*args, **kwargs)

class Siswa(models.Model):
    nama_siswa = models.CharField(max_length=255)
    nis = models.CharField(max_length=50, unique=True, help_text="Nomor Induk Siswa")
    kelas = models.ForeignKey(Kelas, on_delete=models.PROTECT, related_name="siswa_di_kelas")
    
    #Link WA
    @property
    def wa_link(self):
        if self.nomor_wa:
            # Bersihkan spasi atau strip jika pengguna iseng mengetiknya
            no = self.nomor_wa.replace(" ", "").replace("-", "")
            # Jika dimulai dengan 0, ganti dengan 62
            if no.startswith('0'):
                return '62' + no[1:]
            return no
        return ""
    
    # BIODATA UNTUK DIEDIT OLEH PELATIH (Hanya kontak & alamat)
    alamat = models.TextField(blank=True, null=True)
    nomor_wa = models.CharField(max_length=20, blank=True, null=True)
    no_hp_ortu = models.CharField(max_length=20, blank=True, null=True, verbose_name="No HP Orang Tua")

    def __str__(self):
        return f"{self.nama_siswa} ({self.kelas.nama_kelas})"

class Pendaftaran(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Persetujuan'),
        ('APPROVED', 'Aktif'), 
        ('REJECTED', 'Ditolak'),
        ('NONAKTIF', 'Nonaktif / Lulus'), 
        ('KELUAR', 'Dikeluarkan / Mengundurkan Diri'), 
    ]

    nama_siswa = models.CharField(max_length=255)
    nis = models.CharField(max_length=50, help_text="Nomor Induk Siswa")
    kelas = models.ForeignKey(Kelas, on_delete=models.CASCADE, related_name="pendaftar")
    eskul_tujuan = models.ForeignKey(Ekstrakurikuler, on_delete=models.CASCADE, related_name="pendaftar")
    tahun_ajaran = models.ForeignKey(TahunAjaran, on_delete=models.CASCADE, related_name="pendaftar_tahun_ini", null=True)

    alasan = models.TextField(help_text="Alasan ingin bergabung", blank=True)
    no_hp_ortu = models.CharField(max_length=20, blank=True, null=True, help_text="Nomor HP Orang Tua (Opsional)")
    alamat = models.TextField(blank=True, null=True, help_text="Alamat Domisili (Opsional)")
    nomor_wa = models.CharField(max_length=20, help_text="Nomor WA yang bisa dihubungi")
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    tanggal_daftar = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama_siswa} - {self.eskul_tujuan.nama_eskul} ({self.get_status_display()})"

class Penilaian(models.Model):
    PREDIKAT_CHOICES = [
        ('A', 'A - Sangat Baik'),
        ('B', 'B - Baik'),
        ('C', 'C - Cukup'),
        ('D', 'D - Kurang'),
    ]

    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name="nilai_eskul")
    eskul = models.ForeignKey(Ekstrakurikuler, on_delete=models.CASCADE, related_name="penilaian_anggota")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="penilaian_di_semester")

    nilai_kehadiran = models.IntegerField(default=0, help_text="Jumlah kehadiran", verbose_name="Jumlah Kehadiran")
    nilai_keaktifan = models.CharField(max_length=1, choices=PREDIKAT_CHOICES, default='C')
    kepersertaan_lomba = models.TextField(blank=True, null=True, help_text="Catatan keikutsertaan/prestasi lomba")
    catatan_pelatih = models.TextField(blank=True, null=True)
    tanggal_input = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Nilai {self.siswa.nama_siswa} - {self.eskul.nama_eskul} ({self.semester.nama_semester})"

class FotoEskul(models.Model):
    eskul = models.ForeignKey(Ekstrakurikuler, on_delete=models.CASCADE, related_name="galeri_foto")
    foto = models.ImageField(upload_to='foto_kegiatan/', help_text="Upload foto kegiatan (akan di-resize otomatis)")
    keterangan = models.CharField(max_length=255, blank=True, null=True, help_text="Keterangan singkat tentang foto ini")
    tanggal_upload = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tanggal_upload'] 
        verbose_name = "Foto Kegiatan Eskul"
        verbose_name_plural = "Galeri Foto Eskul"

    def __str__(self):
        return f"Foto untuk {self.eskul.nama_eskul} ({self.id})"

    def save(self, *args, **kwargs):
        if self.foto:
            img = Image.open(self.foto)
            max_width = 1024  
            quality = 80      

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

@receiver(pre_save, sender=Ekstrakurikuler)
def hapus_foto_sampul_lama(sender, instance, **kwargs):
    if not instance.pk:
        return False
    try:
        eskul_lama = Ekstrakurikuler.objects.get(pk=instance.pk)
        foto_lama = eskul_lama.foto_sampul
    except Ekstrakurikuler.DoesNotExist:
        return False

    foto_baru = instance.foto_sampul
    if foto_lama and foto_lama != foto_baru:
        if os.path.isfile(foto_lama.path):
            os.remove(foto_lama.path)

@receiver(post_delete, sender=FotoEskul)
def hapus_file_galeri_terhapus(sender, instance, **kwargs):
    if instance.foto:
        if os.path.isfile(instance.foto.path):
            os.remove(instance.foto.path)

@receiver(pre_save, sender=FotoEskul)
def hapus_file_galeri_lama(sender, instance, **kwargs):
    if not instance.pk:
        return False
    try:
        galeri_lama = FotoEskul.objects.get(pk=instance.pk)
        foto_lama = galeri_lama.foto
    except FotoEskul.DoesNotExist:
        return False

    foto_baru = instance.foto
    if foto_lama and foto_lama != foto_baru:
        if os.path.isfile(foto_lama.path):
            os.remove(foto_lama.path)