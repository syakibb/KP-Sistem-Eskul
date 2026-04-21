import sys
import os

# --- BAGIAN PENTING: ALAMAT LENGKAP ---
# Kita beri tahu Python alamat lengkap rumahnya secara manual
# Sesuai info kamu: /home/smkneger/repo_ekskul
project_home = '/home/smkneger/repo_ekskul'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# --- BAGIAN EKSEKUSI ---
try:
    # Coba jalankan aplikasi
    from proyek_sekolah.wsgi import application
    
except Exception as e:
    # JIKA ERROR, TAMPILKAN DI LAYAR (Supaya tidak cuma layar putih)
    import traceback
    trace = traceback.format_exc()
    def application(environ, start_response):
        status = '200 OK'
        output = f"=== ERROR PYTHON ===\n\n{trace}".encode('utf-8')
        response_headers = [('Content-type', 'text/plain'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]