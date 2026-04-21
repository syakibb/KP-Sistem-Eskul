from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Impor semua model kita, termasuk yang baru
from .models import (
    Ekstrakurikuler,
    FotoEskul,
    Kelas,
    Penilaian,
    Profile,
    Semester,
    Siswa,
)

# --- Pengaturan untuk Model Baru ---

# Daftarkan Model Semester
@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('nama_semester', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('nama_semester',)
    ordering = ('-nama_semester',)

# Daftarkan Model Kelas
@admin.register(Kelas)
class KelasAdmin(admin.ModelAdmin):
    search_fields = ('nama_kelas',)
    ordering = ('nama_kelas',)

# --- Pengaturan untuk Model yang Dimodifikasi ---

@admin.register(Siswa)
class SiswaAdmin(admin.ModelAdmin):
    # Sekarang kita bisa filter & cari berdasarkan 'kelas' sebagai objek
    list_display = ('nama_siswa', 'nis', 'kelas')
    search_fields = ('nama_siswa', 'nis', 'kelas__nama_kelas')
    list_filter = ('kelas', 'eskul_yang_diikuti')
    ordering = ('kelas__nama_kelas', 'nama_siswa')

@admin.register(Penilaian)
class PenilaianAdmin(admin.ModelAdmin):
    # Sekarang kita bisa filter & cari berdasarkan 'semester' sebagai objek
    list_display = ('siswa', 'eskul', 'semester', 'nilai_keaktifan')
    list_filter = ('semester', 'eskul', 'nilai_keaktifan')
    search_fields = ('siswa__nama_siswa', 'eskul__nama_eskul', 'semester__nama_semester')
    ordering = ('-semester__nama_semester', 'siswa__nama_siswa')

class FotoEskulInline(admin.TabularInline):
    model = FotoEskul
    extra = 1 # Menampilkan 1 slot upload kosong secara default
    fields = ('foto', 'keterangan')
    verbose_name = "Foto Kegiatan"
    verbose_name_plural = "Galeri Foto Kegiatan"

@admin.register(Ekstrakurikuler)
class EkstrakurikulerAdmin(admin.ModelAdmin):
    # Tampilkan kolom baru di daftar
    list_display = ('nama_eskul', 'pelatih', 'jadwal_latihan', 'lokasi')
    search_fields = ('nama_eskul', 'pelatih__username')
    autocomplete_fields = ['pelatih']

    # Atur formulir edit agar lebih rapi
    fieldsets = (
        ('Informasi Dasar (Wajib)', {
            'fields': ('nama_eskul', 'pelatih')
        }),
        ('Informasi Landing Page Publik', {
            'fields': ('deskripsi_singkat', 'deskripsi_panjang', 'jadwal_latihan', 'lokasi', 'prestasi_unggulan', 'foto_sampul')
        }),
    )

    inlines = [FotoEskulInline]

# --- Pengaturan untuk Wali Kelas (Profile) ---

# Ini adalah cara untuk "menempelkan" form Profile ke dalam form User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil Tambahan (Wali Kelas)'
    fk_name = 'user'

    # Kita hanya ingin menampilkan ini jika user adalah anggota grup "Wali Kelas"
    # (Ini adalah logika kustom yang canggih)
    def get_fields(self, request, obj=None):
        if obj and obj.groups.filter(name='Wali Kelas').exists():
            return ('kelas_perwalian',)
        return ()

# Definisikan tampilan User Admin baru yang menyertakan ProfileInline
class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'groups')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# Daftarkan ulang User dengan pengaturan kustom kita
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# PENTING: Kita TIDAK lagi unregister 'Group'.
# admin.site.unregister(Group) <-- (Baris ini sudah kita hapus)
# Ini akan membuat menu "Grup" muncul kembali di admin,
# yang kita butuhkan untuk membuat peran baru.