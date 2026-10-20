<?php
/**
 * PES 2027 Asset Server - Web Portal & Dashboard
 * Domain: pes.minhgame.com
 */

$root = __DIR__;
$versionFile = $root . '/version.json';
$zipFile = $root . '/PES2027-data.zip';

$versionData = [
    "version" => "2027.1.0",
    "data_id" => "pes2027-11.1.101-c7d098606d0e",
    "data_url" => "https://pes.minhgame.com/PES2027-data.zip",
    "size_bytes" => 0,
    "size_mb" => 0,
    "sha256" => "Chưa có mã băm",
    "title" => "PES 2027 Legends Mod (Zidane, R9, Özil)",
    "notice" => "Gói tài nguyên hoàn chỉnh eFootball 2027",
    "updated_at" => time()
];

if (file_exists($versionFile)) {
    $loaded = json_decode(file_get_contents($versionFile), true);
    if (is_array($loaded)) {
        $versionData = array_merge($versionData, $loaded);
    }
}

$zipExists = file_exists($zipFile);
if ($zipExists) {
    $bytes = filesize($zipFile);
    $versionData['size_bytes'] = $bytes;
    $versionData['size_mb'] = round($bytes / (1024 * 1024), 1);
    $versionData['updated_at'] = filemtime($zipFile);
}
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PES 2027 Asset Server • pes.minhgame.com</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #080a10;
            --card-bg: rgba(18, 24, 38, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #00e5ff;
            --primary-glow: rgba(0, 229, 255, 0.35);
            --accent-lime: #10b981;
            --accent-gold: #ffb800;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background: var(--bg-dark);
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 229, 255, 0.07) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(16, 185, 129, 0.07) 0%, transparent 45%),
                radial-gradient(circle at 50% 50%, rgba(255, 184, 0, 0.04) 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            padding: 20px 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--card-border);
            backdrop-filter: blur(12px);
            background: rgba(10, 14, 24, 0.75);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-logo {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, #10b981, #00e5ff);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            font-weight: 900;
            color: #000;
            box-shadow: 0 4px 15px rgba(0, 229, 255, 0.4);
        }

        .brand-text h1 {
            font-size: 19px;
            font-weight: 800;
            background: linear-gradient(90deg, #fff, #10b981, #00e5ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-text p {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 20px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #10b981;
            font-size: 13px;
            font-weight: 600;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }

        .container {
            max-width: 1100px;
            margin: 40px auto;
            padding: 0 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 30px;
        }

        .hero-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 36px;
            backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            gap: 24px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            position: relative;
            overflow: hidden;
        }

        .hero-card::after {
            content: "";
            position: absolute;
            top: 0; right: 0;
            width: 300px; height: 300px;
            background: radial-gradient(circle, rgba(0,229,255,0.08) 0%, transparent 70%);
            pointer-events: none;
        }

        .hero-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 16px;
        }

        .hero-title h2 {
            font-size: 28px;
            font-weight: 800;
            color: #fff;
        }

        .hero-title p {
            color: var(--text-muted);
            margin-top: 6px;
            font-size: 14px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }

        .stat-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 800;
            color: #fff;
            font-family: 'JetBrains Mono', monospace;
        }

        .stat-value.lime { color: var(--accent-lime); }
        .stat-value.cyan { color: var(--primary); }

        .btn-group {
            display: flex;
            gap: 14px;
            flex-wrap: wrap;
        }

        .btn {
            padding: 13px 26px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 14px;
            text-decoration: none;
            cursor: pointer;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .btn-primary {
            background: linear-gradient(135deg, #10b981 0%, #00e5ff 100%);
            color: #000;
            box-shadow: 0 4px 20px rgba(0, 229, 255, 0.35);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 229, 255, 0.5);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.06);
            color: #fff;
            border: 1px solid var(--card-border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        /* Tabs / Sections */
        .section-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        @media (max-width: 800px) {
            .section-grid { grid-template-columns: 1fr; }
        }

        .sub-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 24px;
            backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        .sub-card h3 {
            font-size: 17px;
            font-weight: 800;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .step-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .step-item {
            display: flex;
            gap: 14px;
            align-items: flex-start;
            font-size: 13.5px;
            color: #d1d5db;
            line-height: 1.5;
        }

        .step-num {
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: rgba(0, 229, 255, 0.12);
            color: var(--primary);
            font-weight: 800;
            font-size: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-top: 2px;
        }

        /* Upload Form */
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .form-label {
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .form-control {
            background: rgba(10, 14, 24, 0.85);
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 11px 14px;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: all 0.2s;
        }

        .form-control:focus {
            border-color: var(--primary);
            box-shadow: 0 0 12px var(--primary-glow);
        }

        .dropzone {
            border: 2px dashed var(--card-border);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.02);
            transition: all 0.2s;
        }

        .dropzone:hover {
            border-color: var(--primary);
            background: rgba(0, 229, 255, 0.04);
        }

        .dropzone p {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 4px;
        }

        /* Toast */
        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #111827;
            border: 1px solid var(--primary);
            border-radius: 10px;
            padding: 14px 20px;
            color: #fff;
            font-weight: 600;
            font-size: 13px;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 1000;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
        }

        #toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        footer {
            padding: 24px;
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            border-top: 1px solid var(--card-border);
            margin-top: auto;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <div class="brand-logo">27</div>
            <div class="brand-text">
                <h1>eFootball 2027 OTA Asset Server</h1>
                <p>pes.minhgame.com • Live Update & Content Delivery</p>
            </div>
        </div>

        <div class="status-badge">
            <span class="status-dot"></span>
            <span>Server Online</span>
        </div>
    </header>

    <div class="container">
        
        <!-- Main Hero Card -->
        <div class="hero-card">
            <div class="hero-header">
                <div class="hero-title">
                    <h2><?php echo htmlspecialchars($versionData['title']); ?></h2>
                    <p><?php echo htmlspecialchars($versionData['notice']); ?></p>
                </div>

                <div class="btn-group">
                    <?php if ($zipExists): ?>
                        <a href="download.php" class="btn btn-primary">
                            <span>⚡</span> Tải PES2027-data.zip (<?php echo $versionData['size_mb']; ?> MB)
                        </a>
                    <?php else: ?>
                        <button class="btn btn-primary" style="opacity: 0.6; cursor: not-allowed;">
                            <span>⚠️</span> Chưa có file trên server
                        </button>
                    <?php endif; ?>
                    <a href="version.json" target="_blank" class="btn btn-secondary">
                        <span>📄</span> Xem version.json
                    </a>
                </div>
            </div>

            <!-- Stats -->
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Phiên bản (Version)</span>
                    <span class="stat-value cyan"><?php echo htmlspecialchars($versionData['version']); ?></span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Dung lượng gói Data</span>
                    <span class="stat-value lime">
                        <?php echo $zipExists ? ($versionData['size_mb'] . " MB") : "Chưa upload"; ?>
                    </span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Cập nhật lần cuối</span>
                    <span class="stat-value" style="font-size: 14px;">
                        <?php echo date('d/m/Y H:i:s', $versionData['updated_at']); ?>
                    </span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Trạng thái file ZIP</span>
                    <span class="stat-value <?php echo $zipExists ? 'lime' : ''; ?>" style="font-size: 14px;">
                        <?php echo $zipExists ? '✓ Đã sẵn sàng tải OTA' : 'Chưa có file'; ?>
                    </span>
                </div>
            </div>

            <?php if (!empty($versionData['sha256'])): ?>
                <div style="background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-muted); word-break: break-all;">
                    <strong style="color: #fff;">SHA-256:</strong> <?php echo htmlspecialchars($versionData['sha256']); ?>
                </div>
            <?php endif; ?>
        </div>

        <!-- Two Columns: Instructions & Web Upload -->
        <div class="section-grid">
            
            <!-- Instructions for Users -->
            <div class="sub-card">
                <h3>📱 Hướng Dẫn Dành Cho Người Chơi</h3>
                <ul class="step-list">
                    <li class="step-item">
                        <span class="step-num">1</span>
                        <div><strong>Cài đặt file IPA Client:</strong> Dùng TrollStore, Scarlet, Esigned hoặc Sideloadly cài đặt file IPA nhẹ (~200MB) vào iPhone.</div>
                    </li>
                    <li class="step-item">
                        <span class="step-num">2</span>
                        <div><strong>Mở game lần đầu:</strong> Game sẽ tự động kết nối tới <code>pes.minhgame.com</code> để kiểm tra tài nguyên.</div>
                    </li>
                    <li class="step-item">
                        <span class="step-num">3</span>
                        <div><strong>Tự động tải & cài đặt:</strong> Nhấn nút <em>"⚡ Tải data từ Server"</em> trên iPhone. Game sẽ tự động tải, tự động giải nén và vào trận đấu ngay!</div>
                    </li>
                </ul>
            </div>

            <!-- Web Admin Uploader -->
            <div class="sub-card">
                <h3>⚙️ Quản Trị Viên (Upload Cập Nhật)</h3>
                <form id="uploadForm">
                    <div class="form-group">
                        <label class="form-label">Khóa Admin (Admin Secret Key)</label>
                        <input type="password" id="adminKey" class="form-control" placeholder="Mặc định: minhgame2027" value="minhgame2027">
                    </div>

                    <div class="form-group" style="margin-top: 10px;">
                        <label class="form-label">Chọn File PES2027-data.zip</label>
                        <div class="dropzone" id="dropzone">
                            <input type="file" id="fileInput" accept=".zip" style="display: none;">
                            <div style="font-size: 24px;">📦</div>
                            <div style="font-weight: 700; font-size: 13px; margin-top: 4px;" id="dropzoneText">Kéo thả file ZIP vào đây</div>
                            <p>Hoặc nhấp để chọn file từ máy tính</p>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary" id="btnSubmitUpload" style="width: 100%; justify-content: center; margin-top: 14px;">
                        <span>🚀</span> Bắt Đầu Tải Lên Server
                    </button>
                    <div id="uploadProgress" style="display: none; margin-top: 10px; font-size: 12px; color: var(--primary);">
                        Đang tải lên server: <span id="progressText">0%</span>
                    </div>
                </form>
            </div>

        </div>

    </div>

    <footer>
        eFootball 2027 Mod by iOSVN & MinhGame • Server pes.minhgame.com
    </footer>

    <div id="toast">Thông báo</div>

    <script>
        function showToast(msg, isErr = false) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.borderColor = isErr ? '#ef4444' : 'var(--primary)';
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3500);
        }

        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const dropzoneText = document.getElementById('dropzoneText');

        dropzone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                dropzoneText.innerText = e.target.files[0].name + " (" + (e.target.files[0].size / (1024*1024)).toFixed(1) + " MB)";
            }
        });

        document.getElementById('uploadForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const key = document.getElementById('adminKey').value.trim();
            if (!key) return showToast('Vui lòng nhập Admin Key!', true);
            if (!fileInput.files.length) return showToast('Chưa chọn file PES2027-data.zip!', true);

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('admin_key', key);
            formData.append('file', file);

            const xhr = new XMLHttpRequest();
            const btn = document.getElementById('btnSubmitUpload');
            const prog = document.getElementById('uploadProgress');
            const progText = document.getElementById('progressText');

            btn.disabled = true;
            btn.innerText = 'Đang tải lên...';
            prog.style.display = 'block';

            xhr.upload.addEventListener('progress', (ev) => {
                if (ev.lengthComputable) {
                    const pct = Math.round((ev.loaded / ev.total) * 100);
                    progText.innerText = pct + '% (' + (ev.loaded / (1024*1024)).toFixed(1) + ' / ' + (ev.total / (1024*1024)).toFixed(1) + ' MB)';
                }
            });

            xhr.onload = () => {
                btn.disabled = false;
                btn.innerText = 'Bắt Đầu Tải Lên Server';
                try {
                    const res = JSON.parse(xhr.responseText);
                    if (res.success) {
                        showToast('✓ ' + res.message);
                        setTimeout(() => location.reload(), 1500);
                    } else {
                        showToast(res.error || 'Lỗi upload', true);
                    }
                } catch(e) {
                    showToast('Lỗi server: ' + xhr.responseText, true);
                }
            };

            xhr.onerror = () => {
                btn.disabled = false;
                btn.innerText = 'Bắt Đầu Tải Lên Server';
                showToast('Lỗi kết nối upload', true);
            };

            xhr.open('POST', 'api/upload.php');
            xhr.send(formData);
        });
    </script>
</body>
</html>
