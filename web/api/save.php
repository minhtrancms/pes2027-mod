<?php
/**
 * PES 2027 Cloud Save Database Sync API
 * Server: pes.minhgame.com
 * Handles in-game and web export/import of user save files via 6-digit codes.
 */

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, X-Admin-Key, Accept");

$requestMethod = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($requestMethod === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$saveDir = dirname(__DIR__) . '/saves';
if (!is_dir($saveDir)) {
    @mkdir($saveDir, 0755, true);
}

$action = $_GET['action'] ?? $_POST['action'] ?? '';
$code = $_GET['code'] ?? $_POST['code'] ?? '';

// Sanitize 6-digit code
$code = preg_replace('/[^0-9]/', '', (string)$code);

// -------------------------------------------------------------------------
// Action 1: Upload Save (Export from in-game or web)
// -------------------------------------------------------------------------
if ($action === 'upload' || ($_SERVER['REQUEST_METHOD'] === 'POST' && (isset($_FILES['file']) || isset($_FILES['save']) || !empty($_POST['data_base64'])))) {
    $tempFile = null;
    $origName = 'ziru_save.db';

    if (isset($_FILES['file']) && $_FILES['file']['error'] === UPLOAD_ERR_OK) {
        $tempFile = $_FILES['file']['tmp_name'];
        $origName = $_FILES['file']['name'];
    } elseif (isset($_FILES['save']) && $_FILES['save']['error'] === UPLOAD_ERR_OK) {
        $tempFile = $_FILES['save']['tmp_name'];
        $origName = $_FILES['save']['name'];
    } elseif (!empty($_POST['data_base64'])) {
        $decoded = base64_decode($_POST['data_base64']);
        if ($decoded !== false && strlen($decoded) > 0) {
            $tempFile = tempnam(sys_get_temp_dir(), 'pes_save_');
            file_put_contents($tempFile, $decoded);
            $origName = 'ziru_save.zip';
        }
    } else {
        // Try reading raw php://input
        $raw = file_get_contents('php://input');
        if (strlen($raw) > 32) {
            $tempFile = tempnam(sys_get_temp_dir(), 'pes_save_');
            file_put_contents($tempFile, $raw);
            $origName = 'ziru_save.zip';
        }
    }

    if (!$tempFile || !file_exists($tempFile) || filesize($tempFile) < 16) {
        header("Content-Type: application/json; charset=utf-8");
        http_response_code(400);
        echo json_encode([
            "success" => false,
            "error" => "No file provided",
            "message" => "Vui lòng chọn hoặc gửi file save (ziru_save.db hoặc .zip) để tải lên."
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $fileSize = filesize($tempFile);
    if ($fileSize > 50 * 1024 * 1024) { // 50MB limit
        @unlink($tempFile);
        header("Content-Type: application/json; charset=utf-8");
        http_response_code(400);
        echo json_encode([
            "success" => false,
            "error" => "File too large",
            "message" => "File save quá lớn (tối đa 50MB)."
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // Check magic bytes: Zip (PK\x03\x04) or SQLite ("SQLite format 3\0")
    $fh = fopen($tempFile, 'rb');
    $magic = fread($fh, 16);
    fclose($fh);

    $isZip = (substr($magic, 0, 4) === "PK\x03\x04" || substr($magic, 0, 4) === "PK\x05\x06");
    $isSqlite = (substr($magic, 0, 15) === "SQLite format 3");

    // Generate unique 6-digit numeric code
    $assignedCode = '';
    $attempts = 0;
    do {
        $assignedCode = sprintf('%06d', mt_rand(100000, 999999));
        $targetZip = $saveDir . '/' . $assignedCode . '.zip';
        $attempts++;
    } while (file_exists($targetZip) && $attempts < 100);

    $targetZip = $saveDir . '/' . $assignedCode . '.zip';

    if ($isZip) {
        // Already a zip archive, move or copy directly
        if (is_uploaded_file($tempFile)) {
            move_uploaded_file($tempFile, $targetZip);
        } else {
            rename($tempFile, $targetZip);
        }
    } else {
        // Raw sqlite or single file, pack into a zip archive with ziru_save.db inside
        $zip = new ZipArchive();
        if ($zip->open($targetZip, ZipArchive::CREATE | ZipArchive::OVERWRITE) === true) {
            $entryName = ($isSqlite || stripos($origName, 'ziru_save') !== false) ? 'ziru_save.db' : basename($origName);
            $zip->addFile($tempFile, $entryName);
            $zip->setArchiveComment("PES2027 Save Archive • Code: " . $assignedCode);
            $zip->close();
        } else {
            // Fallback: copy file directly
            copy($tempFile, $targetZip);
        }
        @unlink($tempFile);
    }

    $finalSize = filesize($targetZip);
    $meta = [
        "code" => $assignedCode,
        "created_at" => time(),
        "date" => date('Y-m-d H:i:s'),
        "size_bytes" => $finalSize,
        "size_kb" => round($finalSize / 1024, 1),
        "ip" => $_SERVER['REMOTE_ADDR'] ?? '',
        "user_agent" => $_SERVER['HTTP_USER_AGENT'] ?? 'PES2027 Client',
        "downloads" => 0,
        "is_sqlite" => $isSqlite
    ];

    $metaFile = $saveDir . '/' . $assignedCode . '.json';
    file_put_contents($metaFile, json_encode($meta, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    header("Content-Type: application/json; charset=utf-8");
    echo json_encode([
        "success" => true,
        "code" => $assignedCode,
        "message" => "Lưu file save lên máy chủ thành công!",
        "size_kb" => $meta['size_kb'],
        "created_at" => $meta['date']
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// -------------------------------------------------------------------------
// Action 2: Check Info of a 6-digit code
// -------------------------------------------------------------------------
if ($action === 'info' || $action === 'check') {
    header("Content-Type: application/json; charset=utf-8");
    if (strlen($code) !== 6) {
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Mã khôi phục phải đủ 6 chữ số."], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $targetZip = $saveDir . '/' . $code . '.zip';
    $metaFile = $saveDir . '/' . $code . '.json';

    if (!file_exists($targetZip)) {
        http_response_code(404);
        echo json_encode(["success" => false, "message" => "Không tìm thấy file save với mã " . $code . "."], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $meta = [];
    if (file_exists($metaFile)) {
        $meta = json_decode(file_get_contents($metaFile), true) ?: [];
    }

    $sizeKb = round(filesize($targetZip) / 1024, 1);
    $createdAt = isset($meta['created_at']) ? date('Y-m-d H:i:s', $meta['created_at']) : date('Y-m-d H:i:s', filemtime($targetZip));

    echo json_encode([
        "success" => true,
        "code" => $code,
        "size_kb" => $sizeKb,
        "created_at" => $createdAt,
        "downloads" => $meta['downloads'] ?? 0
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// -------------------------------------------------------------------------
// Action 3: Download Save Archive by 6-digit code
// -------------------------------------------------------------------------
if ($action === 'download' || (!empty($code) && strlen($code) === 6 && $_SERVER['REQUEST_METHOD'] === 'GET')) {
    if (strlen($code) !== 6) {
        header("Content-Type: application/json; charset=utf-8");
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Mã khôi phục phải đúng 6 chữ số."], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $targetZip = $saveDir . '/' . $code . '.zip';
    if (!file_exists($targetZip)) {
        header("Content-Type: application/json; charset=utf-8");
        http_response_code(404);
        echo json_encode(["success" => false, "message" => "Không tìm thấy dữ liệu cho mã " . $code . ". Hãy kiểm tra lại."], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // Update download counter
    $metaFile = $saveDir . '/' . $code . '.json';
    if (file_exists($metaFile)) {
        $meta = json_decode(file_get_contents($metaFile), true) ?: [];
        $meta['downloads'] = ($meta['downloads'] ?? 0) + 1;
        $meta['last_download_at'] = time();
        file_put_contents($metaFile, json_encode($meta, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    }

    // Stream download file
    header("Content-Description: File Transfer");
    header("Content-Type: application/zip");
    header('Content-Disposition: attachment; filename="pes2027_save_' . $code . '.zip"');
    header("Content-Transfer-Encoding: binary");
    header("Expires: 0");
    header("Cache-Control: must-revalidate");
    header("Pragma: public");
    header("Content-Length: " . filesize($targetZip));

    readfile($targetZip);
    exit;
}

// -------------------------------------------------------------------------
// Default / Stats overview
// -------------------------------------------------------------------------
header("Content-Type: application/json; charset=utf-8");
$count = 0;
if (is_dir($saveDir)) {
    $files = glob($saveDir . '/*.zip');
    $count = is_array($files) ? count($files) : 0;
}

echo json_encode([
    "service" => "PES 2027 Cloud Save Sync API",
    "status" => "active",
    "total_saves_stored" => $count,
    "actions" => [
        "upload" => "POST /api/save.php (multipart 'file')",
        "download" => "GET /api/save.php?code=XXXXXX (or ?action=download&code=XXXXXX)",
        "info" => "GET /api/save.php?action=info&code=XXXXXX"
    ]
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
exit;
