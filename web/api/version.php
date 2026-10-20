<?php
/**
 * Dynamic Version & Asset Manifest API
 * Accessible via /version.json or /api/version.php
 */

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json; charset=utf-8");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$root = dirname(__DIR__);
$versionFile = $root . '/version.json';
$zipFile = $root . '/PES2027-data.zip';

$data = [
    "version" => "2027.1.0",
    "data_id" => "pes2027-11.1.101-c7d098606d0e",
    "data_url" => "",
    "size_bytes" => 0,
    "size_mb" => 0,
    "sha256" => "",
    "title" => "PES 2027 Legends Mod (Zidane, R9, Özil)",
    "notice" => "Gói tài nguyên hoàn chỉnh eFootball 2027",
    "updated_at" => time()
];

if (file_exists($versionFile)) {
    $loaded = json_decode(file_get_contents($versionFile), true);
    if (is_array($loaded)) {
        $data = array_merge($data, $loaded);
    }
}

// Auto-detect host & protocol
$protocol = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (isset($_SERVER['SERVER_PORT']) && $_SERVER['SERVER_PORT'] == 443) ? "https://" : "http://";
$host = $_SERVER['HTTP_HOST'] ?? 'pes.minhgame.com';
$baseUrl = $protocol . $host;

// If zip exists, ensure accurate size and url
if (file_exists($zipFile)) {
    $bytes = filesize($zipFile);
    $data["size_bytes"] = $bytes;
    $data["size_mb"] = round($bytes / (1024 * 1024), 1);
    $data["updated_at"] = filemtime($zipFile);
    if (empty($data["data_url"]) || strpos($data["data_url"], "http") !== 0) {
        $data["data_url"] = $baseUrl . "/PES2027-data.zip";
    }
} else {
    if (empty($data["data_url"])) {
        $data["data_url"] = $baseUrl . "/PES2027-data.zip";
    }
}

echo json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
exit;
