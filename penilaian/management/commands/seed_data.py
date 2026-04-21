# File: penilaian/management/commands/seed_data.py

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User, Group
# Impor semua model kita
from penilaian.models import Semester, Kelas, Siswa, Ekstrakurikuler, Profile, Penilaian

# --- FUNGSI HELPER BARU UNTUK FORMAT KUSTOM WALI KELAS ---
def create_wali_slug(nama_kelas):
    slug = nama_kelas.lower()
    slug = slug.replace(' ', '').replace('.', '')
    slug = slug.replace('perhotelan', 'hotel')
    slug = slug.replace('dpbusana', 'busana')
    return slug
# --------------------------------------------------------

DAFTAR_KELAS = [
    "X Kuliner 1", "X Kuliner 2", "X Kuliner 3",
    "X Perhotelan 1", "X Perhotelan 2",
    "X D.P. Busana",
    "XI Kuliner 1", "XI Kuliner 2", "XI Kuliner 3",
    "XI D.P. Busana 1", "XI D.P. Busana 2",
    "XI Perhotelan",
    "XII Kuliner 1", "XII Kuliner 2", "XII Kuliner 3",
    "XII D.P. Busana 1", "XII D.P. Busana 2",
    "XII Perhotelan"
]

DAFTAR_SEMESTER = [
    ("GANJIL 2025/2026", True),
    ("GENAP 2025/2026", False),
    ("GANJIL 2026/2027", False),
    ("GENAP 2026/2027", False),
]

DAFTAR_ESKUL_PELATIH = {
    "Futsal": "Budi Santoso",
    "Paskibra": "Siti Aminah",
    "PMR": "Agus Wijaya",
    "Pramuka": "Dewi Lestari",
    "Basket": "Rian Hidayat",
    "Tari Tradisional": "Eka Putri",
}

NAMA_SISWA_CONTOH = [
    "Ahmad Budi", "Citra Lestari", "Dedi Prasetyo", "Eka Putri", "Fajar Nugroho",
    "Gita Permata", "Hasanudin", "Indah Cahyani", "Joko Susilo", "Lia Marlina",
    "Mega Wati", "Nina Kirana", "Oscar Pranata", "Putra Pratama", "Qori Ramadhan",
    "Rina Amelia", "Sari Dewi", "Tito Gunawan", "Vina Astuti", "Wahyu Hidayat",
    "Yulia Puspita", "Zainal Abidin", "Aldi Saputra", "Bella Ananda", "Candra Wijaya"
]


class Command(BaseCommand):
    help = 'Mengisi database dengan data dummy untuk E-Eskul'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Memulai proses seeding data...'))

        # --- 1. HAPUS DATA LAMA (Urutan Benar) ---
        self.stdout.write('Menghapus data lama (anak-anak dulu)...')
        Penilaian.objects.all().delete()
        Siswa.objects.all().delete()
        Ekstrakurikuler.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write('Menghapus data master (orang tua)...')
        Kelas.objects.all().delete()
        Semester.objects.all().delete()
        Group.objects.all().delete()

        # --- 2. BUAT DATA MASTER (Semester, Kelas, Grup) ---
        self.stdout.write('Membuat data master (Semester, Kelas, Grup)...')
        
        dict_semester = {}
        for nama, aktif in DAFTAR_SEMESTER:
            sem = Semester.objects.create(nama_semester=nama, is_active=aktif)
            dict_semester[nama] = sem

        dict_kelas = {}
        for nama in DAFTAR_KELAS:
            kelas_obj = Kelas.objects.create(nama_kelas=nama)
            dict_kelas[nama] = kelas_obj

        grup_waka = Group.objects.create(name='Waka Kesiswaan')
        grup_operator = Group.objects.create(name='Operator Dapodik')
        grup_wali = Group.objects.create(name='Wali Kelas')
        grup_pelatih = Group.objects.create(name='Pelatih')

        # --- 3. BUAT PENGGUNA (Users & Profiles) ---
        
        # Buat Pengguna Admin (Pak Eko)
        self.stdout.write('Membuat pengguna Waka Kesiswaan (Pak Eko)...')
        pak_eko = User.objects.create_user(username='pak_eko', password='eko123456', first_name='Bapak Eko', is_staff=True)
        pak_eko.groups.add(grup_waka)

        # Buat Pengguna Operator Dapodik
        self.stdout.write('Membuat pengguna Operator Dapodik...')
        operator = User.objects.create_user(username='operator_dapodik', password='operator_123', first_name='Operator', is_staff=True)
        operator.groups.add(grup_operator)

        # Buat Pengguna Wali Kelas
        self.stdout.write('Membuat pengguna Wali Kelas...')
        for nama_kelas, kelas_obj in dict_kelas.items():
            slug_kelas = create_wali_slug(nama_kelas)
            username = f"walikelas_{slug_kelas}"
            password = f"{slug_kelas}_123"
            wali = User.objects.create_user(username=username, password=password, first_name=f"Wali {nama_kelas}")
            wali.groups.add(grup_wali)
            wali.profile.kelas_perwalian = kelas_obj
            wali.profile.save()

        # Buat Pengguna Pelatih
        self.stdout.write('Membuat pengguna Pelatih dan Ekstrakurikuler...')
        dict_eskul = {}
        for nama_eskul, nama_pelatih in DAFTAR_ESKUL_PELATIH.items():
            username = f"pelatih_{nama_eskul.lower().replace(' ', '_')}"
            pw_slug = nama_eskul.lower().split()[0]
            password = f"{pw_slug}123"
            pelatih = User.objects.create_user(username=username, password=password, first_name=nama_pelatih)
            pelatih.groups.add(grup_pelatih)
            eskul_obj = Ekstrakurikuler.objects.create(nama_eskul=nama_eskul, pelatih=pelatih, deskripsi=f"Ekstrakurikuler {nama_eskul}")
            dict_eskul[nama_eskul] = eskul_obj

        # --- 4. BUAT DATA SISWA ---
        self.stdout.write('Membuat data Siswa...')
        daftar_eskul_obj = list(dict_eskul.values())
        daftar_kelas_obj = list(dict_kelas.values())

        for i, nama_siswa in enumerate(NAMA_SISWA_CONTOH):
            kelas_siswa = random.choice(daftar_kelas_obj)
            eskul_siswa = random.choice(daftar_eskul_obj)
            siswa = Siswa.objects.create(nama_siswa=nama_siswa, nis=f"221011{200 + i}", kelas=kelas_siswa)
            siswa.eskul_yang_diikuti.add(eskul_siswa)
            
            # Tambah 1 eskul lagi untuk beberapa siswa (agar data lebih variatif)
            if i % 4 == 0:
                eskul_tambahan = random.choice(daftar_eskul_obj)
                if eskul_tambahan != eskul_siswa:
                    siswa.eskul_yang_diikuti.add(eskul_tambahan)

        # --- 5. BUAT DATA PENILAIAN DUMMY (BAGIAN BARU) ---
        self.stdout.write('Membuat data Penilaian dummy (nilai eskul)...')
        
        PREDIKAT_CHOICES = ['A', 'B', 'C', 'D']
        LOMBA_EXAMPLES = ["Juara 1 Lomba Kota", "Peserta Lomba Nasional", None, None, None, None]
        
        # Ambil semester aktif yang sudah kita buat
        semester_aktif = dict_semester["GANJIL 2025/2026"]
        
        # Ambil eskul yang ingin kita buat 100% selesai
        eskul_futsal = dict_eskul["Futsal"]
        eskul_paskibra = dict_eskul["Paskibra"]
        eskul_selesai = [eskul_futsal, eskul_paskibra]
        
        # Ambil semua eskul
        semua_eskul_obj = list(dict_eskul.values())
        
        for eskul in semua_eskul_obj:
            # Dapatkan semua siswa di eskul ini
            anggota_eskul = Siswa.objects.filter(eskul_yang_diikuti=eskul)

            for siswa in anggota_eskul:
                # Tentukan apakah siswa ini akan dinilai
                if eskul in eskul_selesai:
                    # Eskul ini WAJIB dinilai semua (100% selesai)
                    harus_dinilai = True
                else:
                    # Eskul lain, dinilai secara acak (60% kemungkinan dinilai)
                    harus_dinilai = random.random() < 0.6 

                if harus_dinilai:
                    Penilaian.objects.create(
                        siswa=siswa,
                        eskul=eskul,
                        semester=semester_aktif,
                        nilai_kehadiran=random.randint(10, 20),
                        nilai_keaktifan=random.choice(PREDIKAT_CHOICES),
                        kepersertaan_lomba=random.choice(LOMBA_EXAMPLES),
                        catatan_pelatih="Catatan dummy oleh pelatih."
                    )
        # --- AKHIR BAGIAN BARU ---


        self.stdout.write(self.style.SUCCESS('=========================================='))
        self.stdout.write(self.style.SUCCESS('Proses Seeding Data Selesai!'))
        self.stdout.write(self.style.WARNING('Data dummy telah dibuat, termasuk data penilaian.'))
        self.stdout.write('Anda bisa login ke /admin/ dengan akun superuser Anda.')
        self.stdout.write('Akun Waka: pak_eko / eko123456')
        self.stdout.write('Contoh Pelatih: pelatih_futsal / futsal123')
        self.stdout.write('Contoh Wali Kelas: walikelas_xhotel1 / xhotel1_123')
        self.stdout.write('==========================================')