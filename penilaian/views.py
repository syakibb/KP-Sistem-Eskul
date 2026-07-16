import csv
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FormPendaftaran, CustomLoginForm, FormProfilEskul, FormGaleriEskul, SiswaBiodataForm
from .models import Ekstrakurikuler, FotoEskul, Kelas, Pendaftaran, Penilaian, Profile, Semester, Siswa, TahunAjaran

# ==========================================
# AUTH & DASHBOARD ROUTING
# ==========================================
def login_view(request):
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard') 
    else:
        form = CustomLoginForm()
    return render(request, 'penilaian/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def dashboard_view(request):
    user = request.user
    if user.is_superuser:
        return redirect('/admin/') 
    elif user.groups.filter(name='Waka Kesiswaan').exists():
        return redirect('admin_dashboard')
    elif user.groups.filter(name='Operator Dapodik').exists():
        return redirect('laporan_rekap')
    elif user.groups.filter(name='Wali Kelas').exists():
        return redirect('wali_kelas_dashboard')
    elif user.groups.filter(name='Pelatih').exists():
        return redirect('pelatih_dashboard')
    else:
        messages.error(request, 'Akun Anda belum memiliki peran. Harap hubungi Admin.')
        return redirect('login')

# ==========================================
# AREA PUBLIK & PENDAFTARAN
# ==========================================
def eskul_list_view(request):
    semua_eskul = Ekstrakurikuler.objects.filter(foto_sampul__isnull=False).order_by('nama_eskul')
    
    nis_dicari = request.GET.get('cari_nis')
    hasil_cari = []     
    search_performed = False
    
    # 1. Ambil tahun ajaran yang sedang aktif
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()

    if nis_dicari:
        search_performed = True
        # 2. REVISI: Tambahkan filter tahun_ajaran=tahun_aktif
        pendaftar_web = Pendaftaran.objects.filter(
            nis=nis_dicari, 
            tahun_ajaran=tahun_aktif
        ).exclude(status__in=['KELUAR', 'NONAKTIF']).select_related('eskul_tujuan')
        
        for p in pendaftar_web:
            hasil_cari.append({
                'nama_siswa': p.nama_siswa,
                'nama_eskul': p.eskul_tujuan.nama_eskul,
                'status': p.status, 
                'tanggal': p.tanggal_daftar
            })

    context = {
        'semua_eskul': semua_eskul,
        'jumlah_eskul': semua_eskul.count(),
        'nis_dicari': nis_dicari,
        'hasil_cari': hasil_cari,
        'search_performed': search_performed,
    }
    return render(request, 'penilaian/eskul_list.html', context)

def eskul_detail_view(request, eskul_id):
    eskul = get_object_or_404(Ekstrakurikuler, id=eskul_id)
    return render(request, 'penilaian/eskul_detail.html', {'eskul': eskul})

def pendaftaran_siswa(request):
    success = False
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()

    if request.method == 'POST':
        form = FormPendaftaran(request.POST)
        if form.is_valid():
            nis = form.cleaned_data['nis']
            daftar_eskul_id = list(set(request.POST.getlist('eskul_tujuan')))
            berhasil_disimpan = 0
            
            for eskul_id in daftar_eskul_id:
                try:
                    eskul_obj = Ekstrakurikuler.objects.get(id=eskul_id)
                    pendaftaran_lama = Pendaftaran.objects.filter(nis=nis, eskul_tujuan=eskul_obj, tahun_ajaran=tahun_aktif).first()
                    if pendaftaran_lama:
                        if pendaftaran_lama.status == 'APPROVED':
                            messages.warning(request, f"Info: NIS {nis} sudah resmi bergabung di {eskul_obj.nama_eskul} tahun ini.")
                            continue
                        elif pendaftaran_lama.status == 'PENDING':
                            messages.info(request, f"Info: Pendaftaran ke {eskul_obj.nama_eskul} sedang diproses.")
                            continue

                    Pendaftaran.objects.create(
                        nama_siswa=form.cleaned_data['nama_siswa'],
                        nis=nis,
                        kelas=form.cleaned_data['kelas'],
                        eskul_tujuan=eskul_obj, 
                        tahun_ajaran=tahun_aktif,
                        nomor_wa=form.cleaned_data['nomor_wa'],
                        no_hp_ortu=form.cleaned_data['no_hp_ortu'],
                        alamat=form.cleaned_data['alamat'],
                        alasan=form.cleaned_data['alasan'],
                        status='PENDING'
                    )
                    berhasil_disimpan += 1
                except Ekstrakurikuler.DoesNotExist:
                    continue

            if berhasil_disimpan > 0:
                success = True
                form = FormPendaftaran() 
        else:
            messages.error(request, "Mohon periksa kembali isian Anda.")
    else:
        initial_data = {}
        if request.GET.get('eskul_id'):
            try:
                initial_data['eskul_tujuan'] = Ekstrakurikuler.objects.get(id=request.GET.get('eskul_id'))
            except Ekstrakurikuler.DoesNotExist:
                pass
        form = FormPendaftaran(initial=initial_data)

    return render(request, 'penilaian/pendaftaran_eskul.html', {'form': form, 'success': success, 'tahun_aktif': tahun_aktif})

# ==========================================
# AREA WAKA KESISWAAN / ADMIN
# ==========================================
@staff_member_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='Waka Kesiswaan').exists()):
        return redirect('dashboard')

    # AMBIL DATA AKTIF LANGSUNG DARI MODEL MASING-MASING
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()
    semester_ini = Semester.objects.filter(is_active=True, tahun_ajaran=tahun_aktif).first()

    semua_eskul = Ekstrakurikuler.objects.select_related('pelatih').all().order_by('nama_eskul')
    daftar_progres = []

    for eskul in semua_eskul:
        nis_aktif = Pendaftaran.objects.filter(eskul_tujuan=eskul, status='APPROVED', tahun_ajaran=tahun_aktif).values_list('nis', flat=True)
        total_anggota = nis_aktif.count()
        
        sudah_dinilai = Penilaian.objects.filter(eskul=eskul, semester=semester_ini, siswa__nis__in=nis_aktif).count()
        
        persentase_selesai = int((sudah_dinilai / total_anggota) * 100) if total_anggota > 0 else 0
        if persentase_selesai > 100: 
            persentase_selesai = 100
        
        daftar_progres.append({
            'id': eskul.id,
            'nama_eskul': eskul.nama_eskul,
            'pelatih': eskul.pelatih,
            'total_anggota': total_anggota,
            'sudah_dinilai': sudah_dinilai,
            'persentase_selesai': persentase_selesai,
        })

    total_siswa_aktif = Pendaftaran.objects.filter(status='APPROVED', tahun_ajaran=tahun_aktif).values('nis').distinct().count()

    context = {
        'daftar_progres': daftar_progres,
        'semester_ini': semester_ini,
        'total_eskul': semua_eskul.count(),
        'total_siswa': total_siswa_aktif,
        # FILTER NOTIFIKASI HANYA UNTUK TAHUN YANG AKTIF SAJA
        'jumlah_pending': Pendaftaran.objects.filter(status='PENDING', tahun_ajaran=tahun_aktif).count(),
    }
    return render(request, 'penilaian/admin_dashboard.html', context)

@staff_member_required
def admin_detail_eskul(request, eskul_id):
    if not (request.user.is_superuser or request.user.groups.filter(name='Waka Kesiswaan').exists()):
        return redirect('dashboard')
    
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()
    semester_ini = Semester.objects.filter(is_active=True, tahun_ajaran=tahun_aktif).first()
    eskul = get_object_or_404(Ekstrakurikuler, id=eskul_id)

    pendaftaran_aktif = Pendaftaran.objects.filter(eskul_tujuan=eskul, status='APPROVED', tahun_ajaran=tahun_aktif)
    nis_aktif = pendaftaran_aktif.values_list('nis', flat=True)
    
    # KINI LANGSUNG MENGAMBIL BIODATA DARI TABEL SISWA
    daftar_siswa = Siswa.objects.filter(nis__in=nis_aktif).order_by('nama_siswa')

    penilaian_dibuat = Penilaian.objects.filter(eskul=eskul, semester=semester_ini, siswa__nis__in=nis_aktif).values_list('siswa_id', flat=True)

    context = {
        'eskul': eskul,
        'daftar_siswa': daftar_siswa,
        'siswa_sudah_dinilai': set(penilaian_dibuat),
        'total_anggota': daftar_siswa.count(),
        'sudah_dinilai': len(set(penilaian_dibuat)),
        'semester_ini': semester_ini,
    }
    return render(request, 'penilaian/admin_detail_eskul.html', context)

@staff_member_required
def laporan_rekap(request):
    semua_semester = Semester.objects.all().order_by('-nama_semester')
    semua_penilaian = Penilaian.objects.select_related('siswa', 'eskul', 'siswa__kelas', 'semester').all()
    
    semester_filter_id = request.GET.get('semester_filter')
    if not request.GET:
         semester_aktif = semua_semester.filter(is_active=True).first()
         if semester_aktif:
            semua_penilaian = semua_penilaian.filter(semester=semester_aktif)
            semester_filter_id = str(semester_aktif.id) 
    elif semester_filter_id:
        semua_penilaian = semua_penilaian.filter(semester__id=semester_filter_id)
    
    if request.GET.get('kelas_filter'):
        semua_penilaian = semua_penilaian.filter(siswa__kelas__id=request.GET.get('kelas_filter'))
    if request.GET.get('eskul_filter'):
        semua_penilaian = semua_penilaian.filter(eskul__id=request.GET.get('eskul_filter'))

    semua_penilaian = semua_penilaian.order_by('siswa__kelas__nama_kelas', 'siswa__nama_siswa')

    if 'export' in request.GET and request.GET['export'] == 'csv':
        response = HttpResponse(content_type='text/csv', headers={'Content-Disposition': 'attachment; filename="laporan_eskul.csv"'})
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response)
        writer.writerow(['Kelas', 'Nama Siswa', 'NIS', 'Ekstrakurikuler', 'Semester', 'Jumlah Kehadiran', 'Keaktifan', 'Lomba', 'Catatan'])
        for nilai in semua_penilaian:
            writer.writerow([nilai.siswa.kelas.nama_kelas, nilai.siswa.nama_siswa, nilai.siswa.nis, nilai.eskul.nama_eskul, nilai.semester.nama_semester, nilai.nilai_kehadiran, nilai.get_nilai_keaktifan_display(), nilai.kepersertaan_lomba, nilai.catatan_pelatih])
        return response

    return render(request, 'penilaian/laporan_rekap.html', {
        'daftar_penilaian': semua_penilaian,
        'semua_semester_list': semua_semester,
        'semua_kelas_list': Kelas.objects.all().order_by('nama_kelas'),
        'semua_eskul_list': Ekstrakurikuler.objects.all().order_by('nama_eskul'), 
        'selected_semester_id_str': semester_filter_id, 
        'selected_kelas_id_str': request.GET.get('kelas_filter'),
        'selected_eskul_id_str': request.GET.get('eskul_filter'),
    })

# ==========================================
# AREA WALI KELAS
# ==========================================
@login_required
def wali_kelas_dashboard(request):
    semua_semester = Semester.objects.all().order_by('-nama_semester')
    semua_eskul = Ekstrakurikuler.objects.all().order_by('nama_eskul') 

    semester_filter_id = request.GET.get('semester_filter')
    eskul_filter_id = request.GET.get('eskul_filter')
    semester_terpilih = None

    if not request.GET: 
        semester_terpilih = semua_semester.filter(is_active=True).first()
        if not semester_terpilih:
            semester_terpilih = semua_semester.first()
    elif semester_filter_id: 
        semester_terpilih = get_object_or_404(Semester, id=semester_filter_id)

    try:
        kelas_perwalian = request.user.profile.kelas_perwalian
        if not kelas_perwalian: raise Profile.DoesNotExist
    except (Profile.DoesNotExist, AttributeError):
        messages.error(request, 'Akun Anda tidak terdaftar sebagai Wali Kelas yang valid.')
        return redirect('login')

    siswa_di_kelas = Siswa.objects.filter(kelas=kelas_perwalian).order_by('nama_siswa')
    
    daftar_penilaian = Penilaian.objects.filter(
        siswa__in=siswa_di_kelas
    ).select_related('siswa', 'eskul').order_by('siswa__nama_siswa', 'eskul__nama_eskul')

    if semester_terpilih:
        daftar_penilaian = daftar_penilaian.filter(semester=semester_terpilih)

    if eskul_filter_id:
        daftar_penilaian = daftar_penilaian.filter(eskul__id=eskul_filter_id)

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

    context = {
        'kelas_perwalian': kelas_perwalian,
        'semester_terpilih': semester_terpilih,
        'semua_semester_list': semua_semester,
        'daftar_penilaian': daftar_penilaian,
        'semua_eskul_list': semua_eskul, 
        'selected_eskul_id_str': eskul_filter_id, 
    }

    return render(request, 'penilaian/wali_kelas_dashboard.html', context)

# ==========================================
# AREA PELATIH ESKUL
# ==========================================
@login_required
def pelatih_dashboard(request):
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()
    semester_ini = Semester.objects.filter(is_active=True, tahun_ajaran=tahun_aktif).first()

    if not semester_ini:
        messages.error(request, 'Admin belum mendaftarkan semester aktif untuk tahun ajaran ini.')
        return render(request, 'penilaian/pelatih_dashboard.html', {'semua_siswa_coach': []})

    eskul_diampu = Ekstrakurikuler.objects.filter(pelatih=request.user)
    jumlah_pending = Pendaftaran.objects.filter(eskul_tujuan__in=eskul_diampu, status='PENDING', tahun_ajaran=tahun_aktif).count()

    pendaftaran_aktif = Pendaftaran.objects.filter(eskul_tujuan__in=eskul_diampu, status='APPROVED', tahun_ajaran=tahun_aktif)
    nis_aktif = pendaftaran_aktif.values_list('nis', flat=True)
    semua_siswa = Siswa.objects.filter(nis__in=nis_aktif).order_by('nama_siswa')

    for siswa in semua_siswa:
        pd = pendaftaran_aktif.filter(nis=siswa.nis).first()
        if pd:
            siswa.pendaftaran_id = pd.id # Cuma simpan ID untuk keperluan tombol hapus

    penilaian_dibuat = Penilaian.objects.filter(siswa__in=semua_siswa, semester=semester_ini).values_list('siswa_id', flat=True)

    context = {
        'semua_siswa_coach': semua_siswa,
        'siswa_sudah_dinilai': set(penilaian_dibuat),
        'semester_ini': semester_ini, 
        'jumlah_pending': jumlah_pending,
    }
    return render(request, 'penilaian/pelatih_dashboard.html', context)

@login_required
def input_nilai(request, siswa_id):
    eskul_diampu = Ekstrakurikuler.objects.filter(pelatih=request.user)
    if request.method == 'POST':
        try:
            siswa = Siswa.objects.get(id=siswa_id)
            eskul = Ekstrakurikuler.objects.get(id=request.POST.get('eskul'))
            semester = Semester.objects.get(id=request.POST.get('semester'))

            if eskul not in eskul_diampu:
                 messages.error(request, 'Akses ditolak.')
                 return redirect('pelatih_dashboard')

            penilaian, created = Penilaian.objects.update_or_create(
                siswa=siswa, eskul=eskul, semester=semester,
                defaults={
                    'nilai_kehadiran': request.POST.get('kehadiran'),
                    'nilai_keaktifan': request.POST.get('keaktifan'),
                    'kepersertaan_lomba': request.POST.get('kepersertaan_lomba'), 
                    'catatan_pelatih': request.POST.get('catatan')
                }
            )
            messages.success(request, f'Nilai {siswa.nama_siswa} berhasil disimpan.')
            return redirect('pelatih_dashboard')
        except Exception as e:
            messages.error(request, f'Terjadi kesalahan: {e}')
            return redirect('pelatih_dashboard')

    siswa = Siswa.objects.get(id=siswa_id)
    semua_semester = Semester.objects.all().order_by('-nama_semester')
    semester_aktif = semua_semester.filter(is_active=True).first() or semua_semester.first()

    try:
        nilai_sebelumnya = Penilaian.objects.get(siswa=siswa, semester=semester_aktif, eskul__in=eskul_diampu)
    except Penilaian.DoesNotExist:
        nilai_sebelumnya = None 

    context = {
        'siswa': siswa,
        'nilai': nilai_sebelumnya,
        'semua_semester_list': semua_semester, 
        'semester_aktif': semester_aktif, 
        'semua_eskul_coach': eskul_diampu,
    }
    return render(request, 'penilaian/input_nilai.html', context)

@login_required
def edit_biodata_siswa(request, siswa_id):
    siswa = get_object_or_404(Siswa, id=siswa_id)
    eskul_diampu = Ekstrakurikuler.objects.filter(pelatih=request.user)
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()
    
    is_authorized = Pendaftaran.objects.filter(nis=siswa.nis, eskul_tujuan__in=eskul_diampu, status='APPROVED', tahun_ajaran=tahun_aktif).exists()
    if not is_authorized:
        messages.error(request, "Akses ditolak. Siswa ini bukan anggota aktif di ekstrakurikuler Anda.")
        return redirect('pelatih_dashboard')

    if request.method == 'POST':
        form = SiswaBiodataForm(request.POST, instance=siswa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Biodata {siswa.nama_siswa} berhasil diperbarui.')
            return redirect('pelatih_dashboard')
    else:
        form = SiswaBiodataForm(instance=siswa)

    return render(request, 'penilaian/edit_biodata_siswa.html', {'form': form, 'siswa': siswa})

@login_required
def keluarkan_siswa(request, pendaftaran_id):
    pendaftaran = get_object_or_404(Pendaftaran, id=pendaftaran_id)
    if pendaftaran.eskul_tujuan.pelatih == request.user:
        pendaftaran.status = 'KELUAR'
        pendaftaran.save()
        messages.success(request, f'Siswa {pendaftaran.nama_siswa} telah dikeluarkan dari ekstrakurikuler.')
    else:
        messages.error(request, 'Anda tidak memiliki hak untuk melakukan aksi ini.')
    return redirect('pelatih_dashboard')

@login_required
def verifikasi_list(request):
    user = request.user
    is_waka = user.is_superuser or user.groups.filter(name='Waka Kesiswaan').exists()
    is_pelatih = user.groups.filter(name='Pelatih').exists()
    tahun_aktif = TahunAjaran.objects.filter(is_active=True).first()

    if not (is_waka or is_pelatih):
        return redirect('dashboard')

    if is_waka:
        pendaftaran_list = Pendaftaran.objects.filter(status='PENDING', tahun_ajaran=tahun_aktif).order_by('-id')
        judul_halaman = "Semua Pengajuan Pendaftaran Siswa"
    elif is_pelatih:
        pendaftaran_list = Pendaftaran.objects.filter(eskul_tujuan__pelatih=user, status='PENDING', tahun_ajaran=tahun_aktif).order_by('-id')
        judul_halaman = "Pengajuan Pendaftaran Ekskul Anda"

    return render(request, 'penilaian/verifikasi_pendaftaran.html', {'pendaftaran_list': pendaftaran_list, 'is_waka': is_waka, 'is_pelatih': is_pelatih, 'judul_halaman': judul_halaman})

@login_required
def verifikasi_aksi(request, pendaftaran_id, aksi):
    user = request.user
    pendaftar = get_object_or_404(Pendaftaran, id=pendaftaran_id)
    is_waka = user.is_superuser or user.groups.filter(name='Waka Kesiswaan').exists()
    is_pelatih_sah = user.groups.filter(name='Pelatih').exists() and pendaftar.eskul_tujuan.pelatih == user

    if not (is_waka or is_pelatih_sah):
        return redirect('verifikasi_list')

    if aksi == 'approve':
        try:
            siswa, created = Siswa.objects.get_or_create(
                nis=pendaftar.nis,
                defaults={'nama_siswa': pendaftar.nama_siswa, 'kelas': pendaftar.kelas}
            )
            # REVISI: Menyimpan data kontak pendaftaran ke tabel Siswa hanya jika tabel Siswa kosong
            if pendaftar.nomor_wa and not siswa.nomor_wa: siswa.nomor_wa = pendaftar.nomor_wa
            if pendaftar.no_hp_ortu and not siswa.no_hp_ortu: siswa.no_hp_ortu = pendaftar.no_hp_ortu
            if pendaftar.alamat and not siswa.alamat: siswa.alamat = pendaftar.alamat
            siswa.save()

            pendaftar.status = 'APPROVED'
            pendaftar.save()
            messages.success(request, f"Siswa {pendaftar.nama_siswa} berhasil diterima.")
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat memproses data: {e}")

    elif aksi == 'reject':
        pendaftar.status = 'REJECTED'
        pendaftar.save()
        messages.warning(request, f"Pendaftaran {pendaftar.nama_siswa} telah ditolak.")

    return redirect('verifikasi_list')

@login_required
def edit_profil_eskul(request):
    try:
        eskul = Ekstrakurikuler.objects.get(pelatih=request.user)
    except Ekstrakurikuler.DoesNotExist:
        messages.error(request, 'Anda tidak terdaftar sebagai pelatih.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = FormProfilEskul(request.POST, request.FILES, instance=eskul)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil Ekstrakurikuler berhasil diperbarui!')
            return redirect('edit_profil_eskul')
    else:
        form = FormProfilEskul(instance=eskul)

    context = {
        'eskul': eskul,
        'form': form,
        'galeri_foto': FotoEskul.objects.filter(eskul=eskul),
        'form_galeri': FormGaleriEskul(),
    }
    return render(request, 'penilaian/edit_profil_eskul.html', context)

@login_required
def tambah_foto_galeri(request):
    if request.method == 'POST':
        try:
            eskul = Ekstrakurikuler.objects.get(pelatih=request.user)
            form = FormGaleriEskul(request.POST, request.FILES)
            if form.is_valid():
                foto_baru = form.save(commit=False)
                foto_baru.eskul = eskul
                foto_baru.save()
                messages.success(request, 'Foto berhasil ditambahkan!')
            else:
                messages.error(request, 'Gagal mengunggah foto.')
        except Ekstrakurikuler.DoesNotExist:
            pass
    return redirect('edit_profil_eskul')

@login_required
def hapus_foto_galeri(request, foto_id):
    foto = get_object_or_404(FotoEskul, id=foto_id)
    if foto.eskul.pelatih == request.user:
        foto.delete() 
        messages.success(request, 'Foto berhasil dihapus.')
    return redirect('edit_profil_eskul')