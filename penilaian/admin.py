from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Ekstrakurikuler,
    FotoEskul,
    Kelas,
    Penilaian,
    Profile,
    Semester,
    Siswa,
    TahunAjaran,
    Pendaftaran,
)

@admin.register(TahunAjaran)
class TahunAjaranAdmin(admin.ModelAdmin):
    list_display = ('nama_tahun', 'is_active')
    list_filter = ('is_active',)
    actions = ['set_active_tahun']

    @admin.action(description='Aktifkan Tahun Ajaran Ini (Matikan yang lain)')
    def set_active_tahun(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "Error: Pilih SATU tahun ajaran saja untuk diaktifkan!", level='error')
            return
        
        # Matikan semua tahun ajaran, lalu aktifkan yang dipilih
        TahunAjaran.objects.update(is_active=False)
        selected = queryset.first()
        selected.is_active = True
        selected.save()
        self.message_user(request, f"Tahun Ajaran {selected.nama_tahun} berhasil diaktifkan.")

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('nama_semester', 'tahun_ajaran', 'is_active')
    list_filter = ('is_active', 'tahun_ajaran')
    actions = ['set_active_semester']

    @admin.action(description='Aktifkan Semester Ini (Matikan yang lain)')
    def set_active_semester(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "Error: Pilih SATU semester saja untuk diaktifkan!", level='error')
            return
        
        # Matikan semua semester, lalu aktifkan yang dipilih
        Semester.objects.update(is_active=False)
        selected = queryset.first()
        selected.is_active = True
        selected.save()
        self.message_user(request, f"Semester {selected.nama_semester} berhasil diaktifkan.")

@admin.register(Pendaftaran)
class PendaftaranAdmin(admin.ModelAdmin):
    list_display = ('nama_siswa', 'nis', 'eskul_tujuan', 'tahun_ajaran', 'status')
    list_filter = ('status', 'eskul_tujuan', 'tahun_ajaran')
    search_fields = ('nama_siswa', 'nis')
    actions = ['nonaktifkan_anggota']

    @admin.action(description='Luluskan / Nonaktifkan Anggota Terpilih (Ganti Tahun Ajaran)')
    def nonaktifkan_anggota(self, request, queryset):
        # Ubah status pendaftaran yang di-ceklis menjadi NONAKTIF
        updated = queryset.update(status='NONAKTIF')
        self.message_user(request, f"{updated} siswa berhasil dinonaktifkan (Lulus/Ganti Tahun Ajaran).")

@admin.register(Kelas)
class KelasAdmin(admin.ModelAdmin):
    search_fields = ('nama_kelas',)
    ordering = ('nama_kelas',)

@admin.register(Siswa)
class SiswaAdmin(admin.ModelAdmin):
    list_display = ('nama_siswa', 'nis', 'kelas', 'nomor_wa')
    search_fields = ('nama_siswa', 'nis', 'kelas__nama_kelas')
    list_filter = ('kelas',)
    ordering = ('kelas__nama_kelas', 'nama_siswa')

@admin.register(Penilaian)
class PenilaianAdmin(admin.ModelAdmin):
    list_display = ('siswa', 'eskul', 'semester', 'nilai_keaktifan')
    list_filter = ('semester', 'eskul', 'nilai_keaktifan')
    search_fields = ('siswa__nama_siswa', 'eskul__nama_eskul', 'semester__nama_semester')
    ordering = ('-semester__nama_semester', 'siswa__nama_siswa')

class FotoEskulInline(admin.TabularInline):
    model = FotoEskul
    extra = 1
    fields = ('foto', 'keterangan')

@admin.register(Ekstrakurikuler)
class EkstrakurikulerAdmin(admin.ModelAdmin):
    list_display = ('nama_eskul', 'pelatih', 'jadwal_latihan', 'lokasi')
    search_fields = ('nama_eskul', 'pelatih__username')
    autocomplete_fields = ['pelatih']
    fieldsets = (
        ('Informasi Dasar (Wajib)', {
            'fields': ('nama_eskul', 'pelatih')
        }),
        ('Informasi Landing Page Publik', {
            'fields': ('deskripsi_singkat', 'deskripsi_panjang', 'jadwal_latihan', 'lokasi', 'prestasi_unggulan', 'foto_sampul')
        }),
    )
    inlines = [FotoEskulInline]

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil Tambahan (Wali Kelas)'
    fk_name = 'user'

    def get_fields(self, request, obj=None):
        if obj and obj.groups.filter(name='Wali Kelas').exists():
            return ('kelas_perwalian',)
        return ()

class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'groups')

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)