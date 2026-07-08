import csv

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import models  # noqa: F401
from django.db.models import Count, F  # noqa: F401
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from itertools import chain

from .forms import FormPendaftaran, CustomLoginForm
from .models import (
    Ekstrakurikuler,
    Kelas,
    Pendaftaran,
    Penilaian,
    Profile,
    Semester,
    Siswa,
)


# Decorator ini akan otomatis melindungi halaman
# Hanya user yang sudah login yang bisa mengaksesnya
# Ubah definisi fungsi untuk menerima siswa_id dari URL
@login_required
def input_nilai(request, siswa_id):
    # Logika cari eskul_diampu (tetap sama)
    try:
        eskul_diampu = Ekstrakurikuler.objects.filter(pelatih=request.user)
    except Ekstrakurikuler.DoesNotExist:
        return render(request, 'penilaian/error_page.html', {'message': 'Anda tidak terdaftar sebagai pelatih.'})

    if request.method == 'POST':
        try:
            # Ambil data dari formulir
            eskul_id = request.POST.get('eskul')
            semester_id = request.POST.get('semester') # <-- Ini sekarang ID, bukan teks
            kehadiran = request.POST.get('kehadiran')
            keaktifan = request.POST.get('keaktifan')
            kepersertaan_lomba = request.POST.get('kepersertaan_lomba') # <-- KPI BARU 
            catatan = request.POST.get('catatan')

            # Ambil objek Siswa, Eskul, dan Semester
            siswa = Siswa.objects.get(id=siswa_id)
            eskul = Ekstrakurikuler.objects.get(id=eskul_id)
            semester = Semester.objects.get(id=semester_id) # <-- Ambil objek Semester

            # Cek hak akses pelatih (tetap sama)
            if eskul not in eskul_diampu:
                 messages.error(request, 'Error: Anda tidak berhak menginput nilai untuk eskul ini.')
                 return redirect('pelatih_dashboard')

            # Logika update_or_create (diperbarui)
            penilaian, created = Penilaian.objects.update_or_create(
                siswa=siswa,
                eskul=eskul,
                semester=semester, # <-- Gunakan objek semester
                defaults={
                    'nilai_kehadiran': kehadiran,
                    'nilai_keaktifan': keaktifan,
                    'kepersertaan_lomba': kepersertaan_lomba, # <-- Simpan KPI baru 
                    'catatan_pelatih': catatan
                }
            )

            if created:
                messages.success(request, f'Sukses! Nilai untuk {siswa.nama_siswa} ({semester.nama_semester}) telah disimpan.')
            else:
                messages.info(request, f'Sukses! Nilai untuk {siswa.nama_siswa} ({semester.nama_semester}) telah diperbarui.')

            return redirect('pelatih_dashboard')

        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {e}')
            return redirect('pelatih_dashboard')

    # 3. Jika halaman baru dibuka (method GET)

    # Ambil data siswa yang akan di-edit
    siswa = Siswa.objects.get(id=siswa_id)

    # Ambil SEMUA semester untuk dropdown 
    semua_semester = Semester.objects.all().order_by('-nama_semester')
    if not semua_semester.exists():
        messages.error(request, 'Error: Admin belum mendaftarkan semester.')
        return redirect('pelatih_dashboard')

    # Tentukan semester yang aktif sebagai default
    semester_aktif = semua_semester.filter(is_active=True).first()
    if not semester_aktif:
        semester_aktif = semua_semester.first() # Ambil yg terbaru jika tidak ada yg aktif

    # Coba cari apakah nilai untuk siswa ini sudah ada DI SEMESTER AKTIF
    try:
        nilai_sebelumnya = Penilaian.objects.get(
            siswa=siswa,
            semester=semester_aktif,
            eskul__in=eskul_diampu
        )
    except Penilaian.DoesNotExist:
        nilai_sebelumnya = None # Data belum ada

    context = {
        'siswa': siswa,
        'nilai': nilai_sebelumnya,
        'semua_semester_list': semua_semester, # <-- Kirim daftar semester
        'semester_aktif': semester_aktif, # <-- Kirim semester aktif (untuk default)
        'semua_eskul_coach': eskul_diampu,
    }

    return render(request, 'penilaian/input_nilai.html', context)

@staff_member_required
def laporan_rekap(request):
    # Ambil semua data master untuk filter dropdown
    semua_semester = Semester.objects.all().order_by('-nama_semester')
    semua_kelas = Kelas.objects.all().order_by('nama_kelas')
    semua_eskul = Ekstrakurikuler.objects.all().order_by('nama_eskul')

# --- Logika Filter Baru (REVISI) ---
    semua_penilaian = Penilaian.objects.select_related('siswa', 'eskul', 'siswa__kelas', 'semester').all()
    
    semester_filter_id = request.GET.get('semester_filter')
    kelas_filter_id = request.GET.get('kelas_filter')
    eskul_filter_id = request.GET.get('eskul_filter')
    
    # Logika Default: Hanya set semester aktif jika INI KUNJUNGAN PERTAMA (tanpa parameter sama sekali)
    if not request.GET:
         semester_aktif = semua_semester.filter(is_active=True).first()
         if semester_aktif:
            semua_penilaian = semua_penilaian.filter(semester=semester_aktif)
            semester_filter_id = str(semester_aktif.id) 
    else:
        # Jika user sudah klik filter (parameter ada)
        if semester_filter_id: # Jika user pilih semester spesifik
            semua_penilaian = semua_penilaian.filter(semester__id=semester_filter_id)
        # Jika semester_filter_id kosong ("Semua Semester"), KITA TIDAK FILTER (Tampilkan semua)
    
    if kelas_filter_id:
        semua_penilaian = semua_penilaian.filter(siswa__kelas__id=kelas_filter_id)
    
    if eskul_filter_id:
        semua_penilaian = semua_penilaian.filter(eskul__id=eskul_filter_id)
    # --- Akhir Logika Filter ---

    # Urutkan hasil akhir berdasarkan permintaan Pak Eko (Rekap per Kelas) 
    semua_penilaian = semua_penilaian.order_by('siswa__kelas__nama_kelas', 'siswa__nama_siswa')

    # --- Logika Ekspor CSV (Diperbarui) ---
    if 'export' in request.GET and request.GET['export'] == 'csv':
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="laporan_eskul_rekap.csv"'},
        )
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response)

        # Header baru (sesuai permintaan )
        writer.writerow([
            'Kelas', 'Nama Siswa', 'NIS', 'Ekstrakurikuler', 'Semester',
            'Jumlah Kehadiran', 'Keaktifan (Predikat)', 'Kepersertaan Lomba', 'Catatan Pelatih'
        ])

        for nilai in semua_penilaian:
            writer.writerow([
                nilai.siswa.kelas.nama_kelas,
                nilai.siswa.nama_siswa,
                nilai.siswa.nis,
                nilai.eskul.nama_eskul,
                nilai.semester.nama_semester,
                nilai.nilai_kehadiran,
                nilai.get_nilai_keaktifan_display(),
                nilai.kepersertaan_lomba,
                nilai.catatan_pelatih
            ])
        return response
    # --- Akhir Logika Ekspor CSV ---

    context = {
        'daftar_penilaian': semua_penilaian,
        'semua_semester_list': semua_semester,
        'semua_kelas_list': semua_kelas,
        'semua_eskul_list': semua_eskul, # <-- Kirim data eskul
        'selected_semester_id_str': semester_filter_id, 
        'selected_kelas_id_str': kelas_filter_id,
        'selected_eskul_id_str': eskul_filter_id,
    }

    return render(request, 'penilaian/laporan_rekap.html', context)

def login_view(request):
    if request.method == 'POST':
        # Gunakan CustomLoginForm di sini
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard') 
    else:
        # Gunakan CustomLoginForm di sini juga
        form = CustomLoginForm()
    
    return render(request, 'penilaian/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def pelatih_dashboard(request):
    # Tentukan semester aktif (dinamis)
    try:
        # Ambil semester yang dicentang "is_active" di Halaman Admin
        semester_ini = Semester.objects.get(is_active=True)
    except Semester.DoesNotExist:
        # Jika admin lupa set, ambil semester terbaru
        semester_ini = Semester.objects.order_by('-nama_semester').first()

    # Jika database semester benar-benar kosong
    if not semester_ini:
        messages.error(request, 'Error: Admin belum mendaftarkan semester. Harap hubungi admin.')
        return render(request, 'penilaian/pelatih_dashboard.html', {'semua_siswa_coach': []})

    try:
        # Ambil eskul yang diampu oleh pelatih ini
        eskul_diampu = Ekstrakurikuler.objects.filter(pelatih=request.user)
        # Ambil semua siswa yang terdaftar di eskul tersebut
        semua_siswa = Siswa.objects.filter(eskul_yang_diikuti__in=eskul_diampu).distinct().order_by('nama_siswa')

        for siswa in semua_siswa:
            pendaftaran = Pendaftaran.objects.filter(nis=siswa.nis).order_by('-tanggal_daftar').first()
            if pendaftaran:
                siswa.nomor_wa_temp = pendaftaran.nomor_wa
                siswa.no_hp_ortu_temp = pendaftaran.no_hp_ortu # Baru
                siswa.alamat_temp = pendaftaran.alamat         # Baru
            else:
                siswa.nomor_wa_temp = "-"
                siswa.no_hp_ortu_temp = "-"
                siswa.alamat_temp = "-"


        # Cari siswa yang sudah punya data penilaian di semester ini (semester_ini.id)
        penilaian_dibuat = Penilaian.objects.filter(
            siswa__in=semua_siswa,
            semester=semester_ini # Gunakan objek semester_ini
        ).values_list('siswa_id', flat=True) # Hanya ambil ID siswanya

        siswa_sudah_dinilai = set(penilaian_dibuat)

    except Exception as e:
        messages.error(request, f"Terjadi kesalahan: {e}")
        semua_siswa = []
        siswa_sudah_dinilai = set()

    context = {
        'semua_siswa_coach': semua_siswa,
        'siswa_sudah_dinilai': siswa_sudah_dinilai,
        'semester_ini': semester_ini, # Kirim objek semester, bukan string
    }
    return render(request, 'penilaian/pelatih_dashboard.html', context)

@login_required
def dashboard_view(request):
    user = request.user

    # 1. Cek Superuser (Admin Utama - Anda) -> Arahkan ke ruang mesin Django
    if user.is_superuser:
        return redirect('/admin/') 

    # 2. Cek Waka Kesiswaan (Pak Eko) -> Arahkan ke dashboard penilaian
    elif user.groups.filter(name='Waka Kesiswaan').exists():
        return redirect('admin_dashboard')

    # 3. Cek Operator Dapodik -> Arahkan ke halaman rekap laporan
    elif user.groups.filter(name='Operator Dapodik').exists():
        return redirect('laporan_rekap')

    # 4. Cek Wali Kelas -> Arahkan ke dashboard wali kelas
    elif user.groups.filter(name='Wali Kelas').exists():
        return redirect('wali_kelas_dashboard')

    # 5. Cek Pelatih -> Arahkan ke dashboard pelatih
    elif user.groups.filter(name='Pelatih').exists():
        return redirect('pelatih_dashboard')

    # 6. Jika user login tapi tidak punya grup (default)
    else:
        messages.error(request, 'Akun Anda belum memiliki peran. Harap hubungi Admin.')
        return redirect('login')

@staff_member_required
def admin_dashboard(request):
    # Hanya Superuser atau Waka Kesiswaan yang boleh masuk sini
    if not (request.user.is_superuser or request.user.groups.filter(name='Waka Kesiswaan').exists()):
        messages.error(request, "Akses ditolak. Halaman ini khusus Waka Kesiswaan.")
        return redirect('dashboard')

    # Tentukan semester aktif
    try:
        semester_ini = Semester.objects.get(is_active=True)
    except Semester.DoesNotExist:
        semester_ini = Semester.objects.order_by('-nama_semester').first()
    
    if not semester_ini:
        messages.error(request, 'Error: Admin belum mendaftarkan data semester.')
        return redirect('admin:index')

    # 1. Ambil data Master untuk Statistik Atas
    total_eskul = Ekstrakurikuler.objects.count()
    total_siswa = Siswa.objects.count()
    # Hitung berapa pendaftaran yang masih PENDING
    jumlah_pending = Pendaftaran.objects.filter(status='PENDING').count()

    # 2. Logika Progres (Sama seperti sebelumnya)
    semua_eskul = Ekstrakurikuler.objects.select_related('pelatih').all().order_by('nama_eskul')
    daftar_progres = []

    for eskul in semua_eskul:
        total_anggota = Siswa.objects.filter(eskul_yang_diikuti=eskul).count()
        
        sudah_dinilai = Penilaian.objects.filter(
            eskul=eskul,
            semester=semester_ini 
        ).count()
        
        if total_anggota > 0:
            persentase_selesai = int((sudah_dinilai / total_anggota) * 100)
        else:
            persentase_selesai = 0 # 0% jika tidak ada anggota
        
        daftar_progres.append({
            'id': eskul.id,
            'nama_eskul': eskul.nama_eskul,
            'pelatih': eskul.pelatih,
            'total_anggota': total_anggota,
            'sudah_dinilai': sudah_dinilai,
            'persentase_selesai': persentase_selesai,
        })

    context = {
        'daftar_progres': daftar_progres,
        'semester_ini': semester_ini,
        # Data Statistik Baru
        'total_eskul': total_eskul,
        'total_siswa': total_siswa,
        'jumlah_pending': jumlah_pending,
    }
    return render(request, 'penilaian/admin_dashboard.html', context)

@staff_member_required
def admin_detail_eskul(request, eskul_id):
    # --- PENGAMAN TAMBAHAN ---
    if not (request.user.is_superuser or request.user.groups.filter(name='Waka Kesiswaan').exists()):
        messages.error(request, "Akses ditolak.")
        return redirect('dashboard')
    
    # Tentukan semester aktif (dinamis)
    try:
        semester_ini = Semester.objects.get(is_active=True)
    except Semester.DoesNotExist:
        semester_ini = Semester.objects.order_by('-nama_semester').first()

    if not semester_ini:
        messages.error(request, 'Error: Admin belum mendaftarkan data semester.')
        return redirect('admin_dashboard')
    # --- AKHIR PERBAIKAN LOGIKA SEMESTER ---

    # Ambil data eskul yang spesifik
    eskul = get_object_or_404(Ekstrakurikuler, id=eskul_id)

    # Ambil semua siswa yang terdaftar di eskul ini
    daftar_siswa = Siswa.objects.filter(eskul_yang_diikuti=eskul).order_by('nama_siswa')
    total_anggota = daftar_siswa.count()

    # Cari siswa yang sudah punya data penilaian di semester ini
    penilaian_dibuat = Penilaian.objects.filter(
        eskul=eskul,
        semester=semester_ini # <-- Sekarang ini menggunakan objek Semester, bukan string
    ).values_list('siswa_id', flat=True)

    siswa_sudah_dinilai = set(penilaian_dibuat)
    sudah_dinilai_count = len(siswa_sudah_dinilai)

    # --- TAMBAHAN BARU: Ambil Nomor WA untuk setiap siswa ---
    for siswa in daftar_siswa:
        pendaftaran = Pendaftaran.objects.filter(nis=siswa.nis).order_by('-tanggal_daftar').first()
        if pendaftaran:
            siswa.nomor_wa_temp = pendaftaran.nomor_wa
            siswa.no_hp_ortu_temp = pendaftaran.no_hp_ortu # Baru
            siswa.alamat_temp = pendaftaran.alamat         # Baru
        else:
            siswa.nomor_wa_temp = "-"
            siswa.no_hp_ortu_temp = "-"
            siswa.alamat_temp = "-"

    context = {
        'eskul': eskul,
        'daftar_siswa': daftar_siswa,
        'siswa_sudah_dinilai': siswa_sudah_dinilai,
        'total_anggota': total_anggota,
        'sudah_dinilai': sudah_dinilai_count,
        'semester_ini': semester_ini,
    }
    return render(request, 'penilaian/admin_detail_eskul.html', context)

@login_required
def wali_kelas_dashboard(request):
    # --- PERSIAPAN ---
    # Tentukan semester aktif
    semester_ini = Semester.objects.filter(is_active=True).first()
    if not semester_ini:
        # Jika admin lupa set semester aktif, ambil yang terbaru
        semester_ini = Semester.objects.latest('id')

    try:
        # Ambil kelas perwalian dari wali kelas yang sedang login
        kelas_perwalian = request.user.profile.kelas_perwalian
    except Profile.DoesNotExist or AttributeError:
        # Jika user ini tidak punya profil atau bukan wali kelas
        messages.error(request, 'Anda tidak terdaftar sebagai Wali Kelas.')
        return redirect('login')

    # Ambil semua siswa di kelas tersebut
    siswa_di_kelas = Siswa.objects.filter(kelas=kelas_perwalian).order_by('nama_siswa')

    # Ambil semua data penilaian untuk siswa-siswa tersebut di semester ini
    daftar_penilaian = Penilaian.objects.filter(
        siswa__in=siswa_di_kelas,
        semester=semester_ini
    ).select_related('siswa', 'eskul').order_by('siswa__nama_siswa', 'eskul__nama_eskul')

    context = {
        'kelas_perwalian': kelas_perwalian,
        'semester_ini': semester_ini,
        'daftar_penilaian': daftar_penilaian,
    }

    return render(request, 'penilaian/wali_kelas_dashboard.html', context)

@login_required
def wali_kelas_dashboard(request):  # noqa: F811
    # 1. Ambil data master
    semua_semester = Semester.objects.all().order_by('-nama_semester')
    semua_eskul = Ekstrakurikuler.objects.all().order_by('nama_eskul') # <-- TAMBAHAN BARU

# 2. Tentukan semester yang difilter
    semester_filter_id = request.GET.get('semester_filter')
    eskul_filter_id = request.GET.get('eskul_filter')
    semester_terpilih = None

    # Logika Semester Baru:
    if not request.GET: # Kunjungan pertama kali
        semester_terpilih = semua_semester.filter(is_active=True).first()
        if not semester_terpilih:
            semester_terpilih = semua_semester.first()
    elif semester_filter_id: # User memilih semester tertentu
        semester_terpilih = get_object_or_404(Semester, id=semester_filter_id)
    # Jika request.GET ada TAPI semester_filter_id kosong ("Semua Semester") -> semester_terpilih tetap None

    # 3. Ambil data Wali Kelas
    try:
        kelas_perwalian = request.user.profile.kelas_perwalian
        if not kelas_perwalian: raise Profile.DoesNotExist
    except (Profile.DoesNotExist, AttributeError):
        messages.error(request, 'Akun Anda tidak terdaftar sebagai Wali Kelas yang valid.')
        return redirect('login')

    # 4. Ambil data siswa dan nilai
    siswa_di_kelas = Siswa.objects.filter(kelas=kelas_perwalian).order_by('nama_siswa')
    
    # Query Dasar
    daftar_penilaian = Penilaian.objects.filter(
        siswa__in=siswa_di_kelas
    ).select_related('siswa', 'eskul').order_by('siswa__nama_siswa', 'eskul__nama_eskul')

    # Terapkan Filter Semester (Hanya jika tidak None)
    if semester_terpilih:
        daftar_penilaian = daftar_penilaian.filter(semester=semester_terpilih)

    # --- TERAPKAN FILTER ESKUL BARU ---
    if eskul_filter_id:
        daftar_penilaian = daftar_penilaian.filter(eskul__id=eskul_filter_id)
    # --- AKHIR FILTER BARU ---

    # 5. Logika Ekspor CSV (Tetap sama, tapi datanya sudah terfilter)
    if 'export' in request.GET and request.GET['export'] == 'csv':
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="laporan_kelas_{kelas_perwalian.nama_kelas}_{semester_terpilih.nama_semester}.csv"'},
        )
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response)
        writer.writerow(['NIS', 'Nama Siswa', 'Ekstrakurikuler', 'Jumlah Kehadiran', 'Keaktifan (Predikat)', 'Kepersertaan Lomba', 'Catatan Pelatih'])

        for nilai in daftar_penilaian:
            writer.writerow([
                nilai.siswa.nis,
                nilai.siswa.nama_siswa,
                nilai.eskul.nama_eskul,
                nilai.nilai_kehadiran,
                nilai.get_nilai_keaktifan_display(),
                nilai.kepersertaan_lomba,
                nilai.catatan_pelatih
            ])
        return response
    # --- Akhir Logika Ekspor CSV ---

    for nilai in daftar_penilaian:
        pendaftaran = Pendaftaran.objects.filter(nis=nilai.siswa.nis).order_by('-tanggal_daftar').first()
        if pendaftaran:
            nilai.siswa.nomor_wa_temp = pendaftaran.nomor_wa
            nilai.siswa.no_hp_ortu_temp = pendaftaran.no_hp_ortu # Baru
            nilai.siswa.alamat_temp = pendaftaran.alamat         # Baru
        else:
            nilai.siswa.nomor_wa_temp = "-"
            nilai.siswa.no_hp_ortu_temp = "-"
            nilai.siswa.alamat_temp = "-"

    context = {
        'kelas_perwalian': kelas_perwalian,
        'semester_terpilih': semester_terpilih,
        'semua_semester_list': semua_semester,
        'daftar_penilaian': daftar_penilaian,
        'semua_eskul_list': semua_eskul, # <-- KIRIM DATA ESKUL
        'selected_eskul_id_str': eskul_filter_id, # <-- KIRIM FILTER TERPILIH
    }

    return render(request, 'penilaian/wali_kelas_dashboard.html', context)

# --- Views untuk Landing Page Publik (Tanpa Login) ---

def eskul_list_view(request):
    # 1. Ambil data untuk galeri eskul (Logika Lama)
    semua_eskul = Ekstrakurikuler.objects.filter(foto_sampul__isnull=False).order_by('nama_eskul')
    jumlah_eskul = semua_eskul.count()
    
    # 2. --- LOGIKA BARU: PENCARIAN GABUNGAN (PENDAFTARAN & SISWA RESMI) ---
    nis_dicari = request.GET.get('cari_nis')
    hasil_cari = []     # Kita gunakan list kosong default
    search_performed = False

    if nis_dicari:
        search_performed = True
        
        # A. Cari di tabel Pendaftaran (Yang daftar via Web)
        # Ambil semua status (PENDING, REJECTED, APPROVED)
        pendaftar_web = Pendaftaran.objects.filter(nis=nis_dicari).select_related('eskul_tujuan')

        # B. Cari di tabel Siswa (Anggota Resmi / Input Manual)
        # Karena satu siswa bisa ikut banyak eskul (Many-to-Many), kita ambil relasinya
        siswa_resmi = Siswa.objects.filter(nis=nis_dicari).prefetch_related('eskul_yang_diikuti').first()
        
        # C. Gabungkan Hasilnya
        
        # 1. Masukkan data dari tabel Pendaftaran dulu
        for p in pendaftar_web:
            hasil_cari.append({
                'nama_siswa': p.nama_siswa,
                'nama_eskul': p.eskul_tujuan.nama_eskul,
                'status': p.status, # BISA: APPROVED, PENDING, REJECTED
                'tanggal': p.tanggal_daftar
            })
            
        # 2. Masukkan data dari tabel Siswa (yang input manual)
        if siswa_resmi:
            for eskul in siswa_resmi.eskul_yang_diikuti.all():
                # Cek agar tidak duplikat (misal sudah ada di list pendaftaran sebagai APPROVED)
                # Kita hanya masukkan jika belum tercatat di list hasil_cari
                sudah_ada = False
                for item in hasil_cari:
                    if item['nama_eskul'] == eskul.nama_eskul and item['status'] == 'APPROVED':
                        sudah_ada = True
                        break
                
                if not sudah_ada:
                    hasil_cari.append({
                        'nama_siswa': siswa_resmi.nama_siswa,
                        'nama_eskul': eskul.nama_eskul,
                        'status': 'APPROVED', # Anggota resmi pasti APPROVED
                        'tanggal': None       # Data manual mungkin tidak punya tanggal daftar
                    })

    context = {
        'semua_eskul': semua_eskul,
        'jumlah_eskul': jumlah_eskul,
        'nis_dicari': nis_dicari,
        'hasil_cari': hasil_cari,
        'search_performed': search_performed,
    }
    
    return render(request, 'penilaian/eskul_list.html', context)

def eskul_detail_view(request, eskul_id):
    # Ambil satu eskul berdasarkan ID-nya, atau tampilkan 404
    eskul = get_object_or_404(Ekstrakurikuler, id=eskul_id)

    context = {
        'eskul': eskul,
    }
    return render(request, 'penilaian/eskul_detail.html', context)

# penilaian/views.py

def pendaftaran_siswa(request):
    success = False
    
    if request.method == 'POST':
        form = FormPendaftaran(request.POST)
        
        # Kita cek validitas dasar dulu (Nama, NIS, Kelas, dll)
        if form.is_valid():
            # 1. Ambil data siswa (yang cuma diisi sekali)
            nama_siswa = form.cleaned_data['nama_siswa']
            nis = form.cleaned_data['nis']
            kelas = form.cleaned_data['kelas']
            nomor_wa = form.cleaned_data['nomor_wa']
            no_hp_ortu = form.cleaned_data['no_hp_ortu']
            alamat = form.cleaned_data['alamat']
            alasan = form.cleaned_data['alasan']
            
            # 2. Ambil LIST eskul yang dipilih (karena bisa lebih dari satu)
            # 'eskul_tujuan' adalah nama field di HTML
            daftar_eskul_id = request.POST.getlist('eskul_tujuan')
            
            # Cek duplikasi input (misal siswa pilih Basket 2 kali di form)
            daftar_eskul_id = list(set(daftar_eskul_id)) 

            berhasil_disimpan = 0
            
            # 3. Looping untuk menyimpan setiap eskul
            for eskul_id in daftar_eskul_id:
                try:
                    eskul_obj = Ekstrakurikuler.objects.get(id=eskul_id)
                    
                    # --- VALIDASI DUPLIKASI DATABASE ---
                    # Cek apakah sudah jadi anggota resmi?
                    if Siswa.objects.filter(nis=nis, eskul_yang_diikuti=eskul_obj).exists():
                        messages.warning(request, f"Info: NIS {nis} sudah menjadi anggota resmi {eskul_obj.nama_eskul}.")
                        continue # Lanjut ke eskul berikutnya
                        
                    # Cek apakah sedang pending?
                    if Pendaftaran.objects.filter(nis=nis, eskul_tujuan=eskul_obj, status='PENDING').exists():
                        messages.info(request, f"Info: Pendaftaran untuk ekskul {eskul_obj.nama_eskul} sedang diproses (Pending).")
                        continue

                    # --- SIMPAN DATA BARU ---
                    Pendaftaran.objects.create(
                        nama_siswa=nama_siswa,
                        nis=nis,
                        kelas=kelas,
                        eskul_tujuan=eskul_obj, # Simpan eskul saat ini
                        nomor_wa=nomor_wa,
                        no_hp_ortu=no_hp_ortu,
                        alamat=alamat,
                        alasan=alasan,
                        status='PENDING'
                    )
                    berhasil_disimpan += 1
                    
                except Ekstrakurikuler.DoesNotExist:
                    continue

            # Jika ada minimal 1 data yang berhasil disimpan, anggap Sukses
            if berhasil_disimpan > 0:
                success = True
                form = FormPendaftaran() # Reset form
                return render(request, 'penilaian/pendaftaran_eskul.html', {'form': form, 'success': success})
            else:
                # Jika semua gagal (misal karena duplikat semua)
                return render(request, 'penilaian/pendaftaran_eskul.html', {'form': form, 'success': False})

        else:
            messages.error(request, "Mohon periksa kembali isian Anda.")
    else:
        # (Bagian GET biarkan seperti semula)
        initial_data = {}
        eskul_id = request.GET.get('eskul_id')
        if eskul_id:
            try:
                initial_data['eskul_tujuan'] = Ekstrakurikuler.objects.get(id=eskul_id)
            except Ekstrakurikuler.DoesNotExist:
                pass
        form = FormPendaftaran(initial=initial_data)

    return render(request, 'penilaian/pendaftaran_eskul.html', {'form': form, 'success': success})

# --- View untuk Menampilkan Daftar Pendaftar (Admin Only) ---
@staff_member_required
def verifikasi_list(request):
    # --- PENGAMAN TAMBAHAN ---
    if not (request.user.is_superuser or request.user.groups.filter(name='Waka Kesiswaan').exists()):
        messages.error(request, "Hanya Waka Kesiswaan yang bisa melakukan verifikasi.")
        return redirect('dashboard')
    
    # Ambil semua pendaftaran yang statusnya masih PENDING
    pendaftar_pending = Pendaftaran.objects.filter(status='PENDING').order_by('-tanggal_daftar')

    context = {
        'pendaftar_pending': pendaftar_pending
    }
    return render(request, 'penilaian/verifikasi_pendaftaran.html', context)

# --- View untuk Memproses Approve/Reject (Admin Only) ---
@staff_member_required
def verifikasi_aksi(request, pendaftaran_id, aksi):
    # --- PENGAMAN TAMBAHAN ---
    if not (request.user.is_superuser or request.user.groups.filter(name='Waka Kesiswaan').exists()):
        return redirect('dashboard')

    # Ambil data pendaftaran
    pendaftar = get_object_or_404(Pendaftaran, id=pendaftaran_id)

    if aksi == 'approve':
        try:
            # 1. Cek apakah siswa dengan NIS ini sudah ada di database?
            siswa, created = Siswa.objects.get_or_create(
                nis=pendaftar.nis,
                defaults={
                    'nama_siswa': pendaftar.nama_siswa,
                    'kelas': pendaftar.kelas
                }
            )

            # 2. Masukkan siswa ke eskul yang dituju
            siswa.eskul_yang_diikuti.add(pendaftar.eskul_tujuan)

            # 3. Ubah status pendaftaran jadi APPROVED
            pendaftar.status = 'APPROVED'
            pendaftar.save()

            messages.success(request, f"Siswa {pendaftar.nama_siswa} berhasil diterima di {pendaftar.eskul_tujuan.nama_eskul}.")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat memproses data: {e}")

    elif aksi == 'reject':
        # Ubah status jadi REJECTED
        pendaftar.status = 'REJECTED'
        pendaftar.save()
        messages.info(request, f"Pendaftaran {pendaftar.nama_siswa} telah ditolak.")

    return redirect('verifikasi_list')