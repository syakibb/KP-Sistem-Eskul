from django import forms
from django.contrib.auth.forms import AuthenticationForm # <-- Import ini
from .models import Pendaftaran

# --- FORM PENDAFTARAN (YANG SUDAH ADA) ---
class FormPendaftaran(forms.ModelForm):
    class Meta:
        model = Pendaftaran
        fields = ['nama_siswa', 'nis', 'kelas', 'eskul_tujuan', 'nomor_wa', 'no_hp_ortu', 'alamat', 'alasan']        
        BASE_CLASS = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-[#F57C00] focus:ring-2 focus:ring-[#F57C00] focus:ring-opacity-20 outline-none transition duration-200 bg-gray-50 focus:bg-white'
        
        widgets = {
            'nama_siswa': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Masukkan Nama Lengkap'}),
            'nis': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: 2210...'}),
            'kelas': forms.Select(attrs={'class': BASE_CLASS + ' cursor-pointer bg-white'}),
            'eskul_tujuan': forms.Select(attrs={'class': BASE_CLASS + ' cursor-pointer bg-white font-semibold'}),
            'nomor_wa': forms.TextInput(attrs={'class': BASE_CLASS, 'placeholder': 'Contoh: 0812xxxxx'}),
            'no_hp_ortu': forms.TextInput(attrs={
                'class': BASE_CLASS, 
                'placeholder': 'Contoh: 0812xxxxx'
            }),
            'alamat': forms.Textarea(attrs={
                'class': BASE_CLASS, 
                'rows': 3, 
                'placeholder': 'Alamat lengkap ...'
            }),
            'alasan': forms.Textarea(attrs={'class': BASE_CLASS, 'rows': 4, 'placeholder': 'Alasan bergabung...'}),
        }
        labels = {
            'eskul_tujuan': 'Pilih Ekstrakurikuler',
            'nama_siswa': 'Nama Lengkap Siswa',
            'nomor_wa': 'Nomor WhatsApp',
            'no_hp_ortu': 'No. HP Orang Tua',
            'alamat': 'Alamat Rumah',
        }

# --- FORM LOGIN BARU (TAMBAHKAN INI) ---
class CustomLoginForm(AuthenticationForm):
    # Kita hapus styling di sini dan akan atur di HTML saja
    def __init__(self, *args, **kwargs):
        super(CustomLoginForm, self).__init__(*args, **kwargs)
        
        # Styling Tailwind untuk Username & Password
        INPUT_STYLE = 'w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-[#1B4D3E] focus:ring-2 focus:ring-[#1B4D3E] focus:ring-opacity-20 outline-none transition duration-200 bg-gray-50 focus:bg-white pl-10'
        
        self.fields['username'].widget.attrs.update({
            'class': INPUT_STYLE,
            'placeholder': 'Username'
        })
        self.fields['password'].widget.attrs.update({
            'class': INPUT_STYLE,
            'placeholder': 'Password'
        })