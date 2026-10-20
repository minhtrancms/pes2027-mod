<?php
/**
 * PES 2027 Asset Upload & Maintenance API
 * Allows uploading updated PES2027-data.zip or updating version.json
 */

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, X-Admin-Key");
header("Content-Type: application/json; charset=utf-8");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$ADMIN_SECRET = getenv('PES_ADMIN_KEY') ?: 'minhgame2027';
$providedKey = $_POST['admin_key'] ?? $_SERVER['HTTP_X_ADMIN_KEY'] ?? '';

if ($providedKey !== $ADMIN_SECRET) {
    http_response_code(403);
    echo json_encode(["error" => "Unauthorized", "message" => "Khóa bảo mật admin_key không chính xác."], JSON_UNESCAPED_UNICODE);
    exit;
}

$root = dirname(__DIR__);
$zipTarget = $root . '/PES2027-data.zip';
$versionTarget = $root . '/version.json';

// Action 1: Uploading a zip file
if (isset($_FILES['file'])) {
    $file = $_FILES['file'];
    if ($file['error'] !== UPLOAD_ERR_OK) {
        http_response_code(400);
        echo json_encode(["error" => "Upload error code: " . $file['error']], JSON_UNESCAPED_UNICODE);
        exit;
    }

    if (!move_uploaded_file($file['tmp_name'], $zipTarget)) {
        http_response_code(500);
        echo json_encode(["error" => "Failed to move uploaded file."], JSON_UNESCAPED_UNICODE);
        exit;
    }

    // Auto-update version.json
    $sha256 = hash_file('sha256', $zipTarget);
    $bytes = filesize($zipTarget);

    $versionData = [];
    if (file_exists($versionTarget)) {
        $versionData = json_decode(file_get_contents($versionTarget), true) ?: [];
    }
    $versionData['size_bytes'] = $bytes;
    $versionData['size_mb'] = round($bytes / (1024 * 1024), 1);
    $versionData['sha256'] = $sha256;
    $versionData['updated_at'] = time();

    file_put_contents($versionTarget, json_encode($versionData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));

    echo json_encode([
        "success" => true,
        "message" => "Upload thành công file PES2027-data.zip!",
        "size_mb" => $versionData['size_mb'],
        "sha256" => $sha256
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// Action 2: Update version manifest directly
if (isset($_POST['version_json'])) {
    $raw = $_POST['version_json'];
    $decoded = json_decode($raw, true);
    if (!is_array($decoded)) {
        http_response_code(400);
        echo json_encode(["error" => "JSON không hợp lệ."], JSON_UNESCAPED_UNICODE);
        exit;
    }
    file_put_contents($versionTarget, json_encode($decoded, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    echo json_encode(["success" => true, "message" => "Đã cập nhật version.json thành công!"], JSON_UNESCAPED_UNICODE);
    exit;
}

echo json_encode(["error" => "No action provided. Send 'file' or 'version_json'."], JSON_UNESCAPED_UNICODE);
exit;
