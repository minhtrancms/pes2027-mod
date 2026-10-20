<?php
/**
 * PES 2027 Asset Streaming & Resumable Download Handler
 * Supports HTTP Range Requests (206 Partial Content) for iOS & browser clients.
 */

// Allow cross-origin requests
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, HEAD, OPTIONS");
header("Access-Control-Allow-Headers: Range, Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$file = __DIR__ . '/PES2027-data.zip';
if (!file_exists($file)) {
    // Check if there is any other .zip in this directory
    $zips = glob(__DIR__ . '/*.zip');
    if (!empty($zips)) {
        $file = $zips[0];
    } else {
        http_response_code(404);
        header("Content-Type: application/json; charset=utf-8");
        echo json_encode([
            "error" => "File not found",
            "message" => "Chưa có file PES2027-data.zip trong thư mục web/. Vui lòng upload file trước."
        ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
        exit;
    }
}

$filesize = filesize($file);
$filename = basename($file);

// Prevent script timeout
@set_time_limit(0);
if (function_exists('apache_setenv')) {
    @apache_setenv('no-gzip', '1');
}
@ini_set('zlib.output_compression', 'Off');

$fp = @fopen($file, 'rb');
if (!$fp) {
    http_response_code(500);
    echo "Could not open file.";
    exit;
}

$start = 0;
$end = $filesize - 1;

header("Accept-Ranges: bytes");
header("Content-Type: application/zip");
header("Content-Disposition: attachment; filename=\"{$filename}\"");

if (isset($_SERVER['HTTP_RANGE'])) {
    $c_start = $start;
    $c_end = $end;

    list(, $range) = explode('=', $_SERVER['HTTP_RANGE'], 2);
    if (strpos($range, ',') !== false) {
        header('HTTP/1.1 416 Requested Range Not Satisfiable');
        header("Content-Range: bytes $start-$end/$filesize");
        exit;
    }

    if ($range === '-') {
        $c_start = $filesize - substr($range, 1);
    } else {
        $range = explode('-', $range);
        $c_start = $range[0];
        $c_end = (isset($range[1]) && is_numeric($range[1])) ? $range[1] : $filesize - 1;
    }

    $c_end = ($c_end > $end) ? $end : $c_end;
    if ($c_start > $c_end || $c_start > $filesize - 1 || $c_end >= $filesize) {
        header('HTTP/1.1 416 Requested Range Not Satisfiable');
        header("Content-Range: bytes $start-$end/$filesize");
        exit;
    }

    $start = $c_start;
    $end = $c_end;
    $length = $end - $start + 1;

    fseek($fp, $start);
    header('HTTP/1.1 206 Partial Content');
    header("Content-Range: bytes $start-$end/$filesize");
    header("Content-Length: " . $length);
} else {
    header("Content-Length: " . $filesize);
}

// Stream in chunks of 64KB
$bufferSize = 64 * 1024;
while (!feof($fp) && ($pos = ftell($fp)) <= $end) {
    if ($pos + $bufferSize > $end) {
        $bufferSize = $end - $pos + 1;
    }
    echo fread($fp, $bufferSize);
    @ob_flush();
    flush();
    if (connection_status() != 0) {
        @fclose($fp);
        exit;
    }
}
@fclose($fp);
exit;
