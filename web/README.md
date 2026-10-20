# eFootball 2027 OTA Asset Server (PHP)

Thư mục này là mã nguồn Web Server dùng để phân phối dữ liệu OTA cho game eFootball 2027 trên iPhone qua tên miền **`pes.minhgame.com`**.

---

## 📁 Cấu Trúc Thư Mục

```
web/
├── index.php             # Giao diện Portal thông tin & trang Upload Admin
├── version.json          # File manifest bản cập nhật (cho iPhone đọc)
├── download.php          # Trình stream file nén hỗ trợ tiếp tục tải (HTTP Range 206)
├── api/
│   ├── version.php       # API tự động tính dung lượng và cập nhật version
│   └── upload.php        # API upload dữ liệu qua Web / cURL
├── .htaccess             # Cấu hình Apache / LiteSpeed (CORS, Range, upload 5GB)
├── nginx_pes.conf        # Mẫu cấu hình Nginx tối ưu cho pes.minhgame.com
└── start_local.sh        # Script chạy thử server nội bộ (php -S)
```

---

## 🚀 Hướng Dẫn Deploy Lên Hosting / VPS

### Cách 1: Nginx trên VPS (Ubuntu/Debian) - Khuyên Dùng
1. Copy toàn bộ thư mục `web/` vào `/var/www/pes.minhgame.com/web`.
2. Tạo file cấu hình Nginx từ mẫu `nginx_pes.conf`:
   ```bash
   sudo cp nginx_pes.conf /etc/nginx/sites-available/pes.minhgame.com
   sudo ln -s /etc/nginx/sites-available/pes.minhgame.com /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
3. Cài SSL miễn phí bằng Certbot:
   ```bash
   sudo certbot --nginx -d pes.minhgame.com
   ```

### Cách 2: cPanel / DirectAdmin / Apache Hosting
1. Nén toàn bộ nội dung trong thư mục `web/` thành file zip.
2. Upload và giải nén vào thư mục `public_html` (hoặc thư mục subdomain `pes.minhgame.com`).
3. File `.htaccess` đã được cấu hình sẵn CORS và HTTP Range cho iPhone.

---

## 📦 Cách Đưa File Dữ Liệu `PES2027-data.zip` Lên Server

Bạn có thể chọn 1 trong 3 cách:

1. **Upload qua giao diện Web:**
   - Mở trình duyệt vào `https://pes.minhgame.com`.
   - Nhập khóa admin: `minhgame2027` (hoặc đổi trong `api/upload.php`).
   - Kéo thả file `PES2027-data.zip` vào ô uploader và nhấn Tải Lên.

2. **Copy trực tiếp qua SSH / SCP / FTP:**
   - Chạy lệnh đóng gói dữ liệu trên máy tính:
     ```bash
     ./tools/prepare_server_assets.py
     ```
   - Dùng FileZilla / WinSCP / rsync copy file `PES2027-data.zip` và `version.json` vào thư mục `web/`.

3. **Chạy thử nghiệm nội bộ trên máy Mac:**
   ```bash
   ./web/start_local.sh
   # Truy cập http://localhost:8080 trên trình duyệt
   ```
