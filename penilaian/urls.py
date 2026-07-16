from django.urls import path
from . import views

urlpatterns = [
    path('laporan/', views.laporan_rekap, name='laporan_rekap'),
    path('input-nilai/<int:siswa_id>/', views.input_nilai, name='input_nilai_edit'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # UBAH BARIS INI: 'profil-eskul/' diubah menjadi ''
    path('', views.eskul_list_view, name='eskul_list'),
    
    path('profil-eskul/<int:eskul_id>/', views.eskul_detail_view, name='eskul_detail'),
    path('daftar-eskul/', views.pendaftaran_siswa, name='pendaftaran_siswa'),
    path('verifikasi/', views.verifikasi_list, name='verifikasi_list'),
    path('verifikasi/<int:pendaftaran_id>/<str:aksi>/', views.verifikasi_aksi, name='verifikasi_aksi'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('detail-eskul/<int:eskul_id>/', views.admin_detail_eskul, name='admin_detail_eskul'),
    path('wali-kelas/', views.wali_kelas_dashboard, name='wali_kelas_dashboard'),
    path('pelatih-dashboard/', views.pelatih_dashboard, name='pelatih_dashboard'),

    # --- Rute Fitur Pengaturan Pelatih ---
    path('pengaturan-eskul/', views.edit_profil_eskul, name='edit_profil_eskul'),
    path('pengaturan-eskul/galeri/tambah/', views.tambah_foto_galeri, name='tambah_foto_galeri'),
    path('pengaturan-eskul/galeri/hapus/<int:foto_id>/', views.hapus_foto_galeri, name='hapus_foto_galeri'),

    # --- RUTE BARU: Edit Biodata & Keluarkan Siswa ---
    path('edit-biodata/<int:siswa_id>/', views.edit_biodata_siswa, name='edit_biodata_siswa'),
    path('keluarkan-siswa/<int:pendaftaran_id>/', views.keluarkan_siswa, name='keluarkan_siswa'),
]