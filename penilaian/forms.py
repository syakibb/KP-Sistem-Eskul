from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Pendaftaran, Ekstrakurikuler, FotoEskul, Siswa

# --- FORM PENDAFTARAN ---
class FormPendaftaran(forms.ModelForm):
    class Meta:
        model = Pendaftaran
        fields = ['nama_siswa', 'nis', 'kelas', 'eskul_tujuan', 'nomor_wa', 'no_hp_ortu', 'alamat', 'alasan']        
        BASE_CLASS = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-[#F57C00] focus:ring-2 focus:ring-[#F57C00] focus:ring-opacity-20 outline-none transition duration-200 bg-gray-50 focus:bg-white'
        
        widgets = {
            'nama_siswa': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Masukkan Nama Lengkap'}),
            # Menambahkan type="number" agar keyboard HP otomatis memunculkan angka
            'nis': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: 1120...', 'type': 'number'}),
            'kelas': forms.Select(attrs={'class': BASE_CLASS + ' cursor-pointer bg-white'}),
            'eskul_tujuan': forms.Select(attrs={'class': BASE_CLASS + ' cursor-pointer bg-white font-semibold'}),
            'nomor_wa': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: 0812xxxxx', 'type': 'number'}),
            'no_hp_ortu': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: 0812xxxxx', 'type': 'number'}),
            'alamat': forms.Textarea(attrs={'class': BASE_CLASS, 'rows': 3, 'placeholder': 'Alamat lengkap ...'}),
            'alasan': forms.Textarea(attrs={'class': BASE_CLASS, 'rows': 4, 'placeholder': 'Alasan bergabung...'}),
        }
        labels = {
            'eskul_tujuan': 'Pilih Ekstrakurikuler',
            'nama_siswa': 'Nama Lengkap Siswa',
            'nomor_wa': 'Nomor WhatsApp',
            'no_hp_ortu': 'No. HP Orang Tua',
            'alamat': 'Alamat Rumah',
        }

    # Proteksi keamanan ganda: Menolak input jika ada huruf walau html sudah diedit paksa
    def clean_nis(self):
        nis = self.cleaned_data.get('nis')
        if not nis.isdigit():
            raise forms.ValidationError("NIS tidak valid! Hanya boleh berisi angka.")
        return nis

# --- FORM LOGIN ---
class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        INPUT_STYLE = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-[#1B4D3E] focus:ring-2 focus:ring-[#1B4D3E] focus:ring-opacity-20 outline-none transition duration-200 bg-gray-50 focus:bg-white pl-10'
        
        self.fields['username'].widget.attrs.update({'class': INPUT_STYLE, 'placeholder': 'Username'})
        self.fields['password'].widget.attrs.update({'class': INPUT_STYLE, 'placeholder': 'Password'})

# --- FORM PROFIL ESKUL ---
class FormProfilEskul(forms.ModelForm):
    class Meta:
        model = Ekstrakurikuler
        fields = ['foto_sampul', 'deskripsi_singkat', 'deskripsi_panjang', 'jadwal_latihan', 'lokasi', 'prestasi_unggulan']
        BASE_CLASS = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-[#1B4D3E] focus:ring-2 focus:ring-[#1B4D3E] focus:ring-opacity-20 outline-none transition duration-200 bg-gray-50 focus:bg-white'
        
        widgets = {
            'deskripsi_singkat': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Singkat, padat, jelas (Max 255 karakter)'}),
            'deskripsi_panjang': forms.Textarea(attrs={'class': BASE_CLASS, 'rows': 4, 'placeholder': 'Ceritakan selengkapnya tentang ekskul ini...'}),
            'jadwal_latihan': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: Setiap Jumat, 15:00 - 17:00 WIB'}),
            'lokasi': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: Lapangan Utama SMKN 30'}),
            'prestasi_unggulan': forms.Textarea(attrs={'class': BASE_CLASS, 'rows': 3, 'placeholder': '1. Juara 1 ... \n2. Juara 2...'}),
            'foto_sampul': forms.FileInput(attrs={'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-[#E8F5E9] file:text-[#1B4D3E] hover:file:bg-green-200 cursor-pointer transition'}),
        }
        labels = {
            'foto_sampul': 'Upload Foto Sampul',
            'deskripsi_singkat': 'Motto / Slogan Singkat',
        }

# --- FORM GALERI ESKUL ---
class FormGaleriEskul(forms.ModelForm):
    class Meta:
        model = FotoEskul
        fields = ['foto', 'keterangan']
        BASE_CLASS = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-[#F57C00] focus:ring-2 focus:ring-[#F57C00] focus:ring-opacity-20 outline-none transition duration-200 bg-gray-50 focus:bg-white'
        
        widgets = {
            'foto': forms.ClearableFileInput(attrs={'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-[#E8F5E9] file:text-[#1B4D3E] hover:file:bg-green-200 cursor-pointer transition', 'required': True}),
            'keterangan': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: Lomba Futsal Tingkat Provinsi 2025'}),
        }

# --- FORM BIODATA SISWA (UNTUK PELATIH) ---
class SiswaBiodataForm(forms.ModelForm):
    class Meta:
        model = Siswa
        # Hapus field sensitif
        fields = ['alamat', 'nomor_wa', 'no_hp_ortu']
        BASE_CLASS = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-green-600 focus:ring-2 focus:ring-green-600 focus:ring-opacity-20 outline-none transition duration-200'
        
        widgets = {
            'alamat': forms.Textarea(attrs={'class': BASE_CLASS, 'rows': 3}),
            'nomor_wa': forms.TextInput(attrs={'class': BASE_CLASS, 'type': 'number'}),
            'no_hp_ortu': forms.TextInput(attrs={'class': BASE_CLASS, 'type': 'number'}),
        }