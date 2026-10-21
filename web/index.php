<?php
/**
 * PES 2027 Asset Server - Web Portal & Dashboard
 * Style: eFootball 2027 Official Game Design
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
    "sha256" => "",
    "title" => "PES 2027 Legends Mod - Zidane, R9, Özil",
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

// Thống kê save files trên máy chủ
$saveFiles = glob($root . '/saves/*.zip');
$saveCount = is_array($saveFiles) ? count($saveFiles) : 0;

// Làm sạch triệt để mọi ký tự ngoặc đơn trong tiêu đề và thông báo nếu có
$cleanTitle = str_replace(['(', ')'], ['', ''], $versionData['title']);
$cleanNotice = str_replace(['(', ')'], ['', ''], $versionData['notice']);
?>
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>eFootball 2027 Asset Server • pes.minhgame.com</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;0,900;1,700;1,800;1,900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --ef-bg: #040711;
            --ef-bg-card: rgba(8, 14, 28, 0.82);
            --ef-bg-card-hover: rgba(12, 20, 38, 0.9);
            --ef-cyan: #00f0ff;
            --ef-cyan-glow: rgba(0, 240, 255, 0.45);
            --ef-blue: #0055ff;
            --ef-volt: #d8ff00;
            --ef-volt-glow: rgba(216, 255, 0, 0.45);
            --ef-pitch-green: rgba(16, 185, 129, 0.08);
            --ef-border: rgba(0, 240, 255, 0.18);
            --ef-border-highlight: rgba(0, 240, 255, 0.45);
            --ef-text-main: #f8fafc;
            --ef-text-muted: #8b9bb4;
            --ef-font-sports: 'Barlow Condensed', sans-serif;
            --ef-font-body: 'Plus Jakarta Sans', sans-serif;
            --ef-font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--ef-bg);
            /* Sân bóng bóng đá eFootball & Ánh sáng sân vận động */
            background-image:
                /* Đèn pha sân vận động góc trái */
                radial-gradient(ellipse at 15% -5%, rgba(0, 240, 255, 0.22) 0%, transparent 55%),
                /* Đèn pha sân vận động góc phải */
                radial-gradient(ellipse at 85% -5%, rgba(216, 255, 0, 0.16) 0%, transparent 50%),
                /* Ánh sáng cỏ sân vận động ở đáy */
                radial-gradient(ellipse at 50% 100%, rgba(0, 85, 255, 0.15) 0%, transparent 60%),
                /* Sọc cắt cỏ sân bóng */
                repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.012) 0px, rgba(255, 255, 255, 0.012) 60px, transparent 60px, transparent 120px),
                /* Lưới mắt cáo bóng đá / áo thi đấu */
                linear-gradient(45deg, rgba(0, 240, 255, 0.015) 25%, transparent 25%),
                linear-gradient(-45deg, rgba(0, 240, 255, 0.015) 25%, transparent 25%);
            background-size: 100% 100%, 100% 100%, 100% 100%, 120px 100%, 30px 30px, 30px 30px;
            color: var(--ef-text-main);
            font-family: var(--ef-font-body);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            position: relative;
        }

        /* Lớp đồ họa nền sân bóng chiến thuật eFootball */
        .football-pitch-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
            opacity: 0.18;
        }

        /* Top Bar Header */
        header {
            padding: 16px 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--ef-border);
            backdrop-filter: blur(16px);
            background: rgba(4, 7, 17, 0.88);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        /* eFootball Monogram Vector Shield */
        .ef-logo-mark {
            width: 46px;
            height: 46px;
            background: linear-gradient(135deg, #090e1f 0%, #0c1633 100%);
            border: 1.5px solid var(--ef-cyan);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 18px var(--ef-cyan-glow);
            position: relative;
            transform: skewX(-8deg);
        }

        .ef-logo-mark svg {
            transform: skewX(8deg);
        }

        .brand-info {
            display: flex;
            flex-direction: column;
        }

        .brand-name {
            font-family: var(--ef-font-sports);
            font-size: 26px;
            font-weight: 900;
            font-style: italic;
            letter-spacing: 0.5px;
            line-height: 1;
            text-transform: uppercase;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .brand-name span.ef-title {
            color: #ffffff;
        }

        .brand-name span.ef-sub {
            background: linear-gradient(90deg, var(--ef-cyan), var(--ef-volt));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-meta {
            font-family: var(--ef-font-mono);
            font-size: 11px;
            letter-spacing: 1px;
            color: var(--ef-text-muted);
            text-transform: uppercase;
            margin-top: 3px;
        }

        .header-telemetry {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .telemetry-chip {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 6px;
            background: rgba(0, 240, 255, 0.06);
            border: 1px solid rgba(0, 240, 255, 0.25);
            font-family: var(--ef-font-mono);
            font-size: 11px;
            color: var(--ef-cyan);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            transform: skewX(-6deg);
        }

        .telemetry-chip-content {
            transform: skewX(6deg);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--ef-volt);
            box-shadow: 0 0 10px var(--ef-volt);
            animation: pulse-dot 1.8s infinite;
        }

        @keyframes pulse-dot {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }

        /* Container */
        .main-wrapper {
            max-width: 1180px;
            width: 100%;
            margin: 32px auto;
            padding: 0 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 28px;
            position: relative;
            z-index: 2;
        }

        /* Live Ticker Bar */
        .ticker-bar {
            display: flex;
            align-items: center;
            background: rgba(10, 16, 32, 0.65);
            border: 1px solid var(--ef-border);
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 12.5px;
            color: var(--ef-text-muted);
            overflow: hidden;
            position: relative;
            backdrop-filter: blur(12px);
        }

        .ticker-badge {
            font-family: var(--ef-font-sports);
            font-weight: 800;
            font-style: italic;
            font-size: 14px;
            background: var(--ef-volt);
            color: #000;
            padding: 2px 10px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-right: 14px;
            flex-shrink: 0;
            transform: skewX(-10deg);
        }

        .ticker-text {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-family: var(--ef-font-body);
            font-weight: 500;
            color: #d1d9e6;
        }

        /* Hero eFootball Epic Card */
        .ef-hero-card {
            background: var(--ef-bg-card);
            border: 1px solid var(--ef-border);
            border-radius: 16px;
            padding: 38px 40px;
            backdrop-filter: blur(24px);
            position: relative;
            overflow: hidden;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.75), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        /* Quả bóng đá eFootball 3D Vector chìm trong Hero Card */
        .hero-ball-watermark {
            position: absolute;
            top: -40px;
            right: -30px;
            width: 420px;
            height: 420px;
            pointer-events: none;
            opacity: 0.16;
            z-index: 1;
            transition: all 0.5s ease;
        }

        .ef-hero-card:hover .hero-ball-watermark {
            opacity: 0.22;
            transform: scale(1.03) rotate(8deg);
        }

        .ef-hero-card::after {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--ef-cyan) 0%, var(--ef-blue) 50%, var(--ef-volt) 100%);
        }

        .hero-top-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 24px;
            position: relative;
            z-index: 2;
        }

        .hero-title-area {
            max-width: 680px;
        }

        .category-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            background: rgba(0, 240, 255, 0.12);
            border-left: 3px solid var(--ef-cyan);
            font-family: var(--ef-font-sports);
            font-size: 14px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--ef-cyan);
            margin-bottom: 12px;
        }

        .hero-title-area h2 {
            font-family: var(--ef-font-sports);
            font-size: 44px;
            font-weight: 900;
            font-style: italic;
            line-height: 1.05;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #ffffff;
            text-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }

        .hero-title-area p {
            color: var(--ef-text-muted);
            font-size: 15px;
            line-height: 1.5;
            margin-top: 10px;
            font-weight: 500;
        }

        /* Action Buttons */
        .hero-actions {
            display: flex;
            flex-direction: column;
            gap: 12px;
            align-items: flex-start;
        }

        .ef-btn {
            font-family: var(--ef-font-sports);
            font-size: 20px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 14px 28px;
            border: none;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            position: relative;
            transform: skewX(-10deg);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .ef-btn > * {
            transform: skewX(10deg);
        }

        .ef-btn-primary {
            background: linear-gradient(135deg, var(--ef-volt) 0%, #a4e600 100%);
            color: #050811;
            box-shadow: 0 6px 25px var(--ef-volt-glow);
            clip-path: polygon(10px 0%, 100% 0%, calc(100% - 10px) 100%, 0% 100%);
        }

        .ef-btn-primary:hover {
            transform: skewX(-10deg) translateY(-3px);
            box-shadow: 0 10px 35px var(--ef-volt-glow);
            background: linear-gradient(135deg, #efff44 0%, var(--ef-volt) 100%);
        }

        .ef-btn-disabled {
            background: #2a3348;
            color: #72819c;
            cursor: not-allowed;
            box-shadow: none;
            clip-path: polygon(10px 0%, 100% 0%, calc(100% - 10px) 100%, 0% 100%);
        }

        .ef-btn-secondary {
            background: rgba(14, 22, 42, 0.85);
            border: 1px solid var(--ef-border-highlight);
            color: #ffffff;
            clip-path: polygon(10px 0%, 100% 0%, calc(100% - 10px) 100%, 0% 100%);
        }

        .ef-btn-secondary:hover {
            background: rgba(22, 34, 62, 0.95);
            border-color: var(--ef-cyan);
            color: var(--ef-cyan);
            transform: skewX(-10deg) translateY(-2px);
        }

        /* Stats Grid (eFootball Player Attributes Card Style) */
        .ef-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-top: 32px;
            position: relative;
            z-index: 2;
        }

        .stat-card {
            background: rgba(6, 10, 20, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-left: 3px solid var(--ef-border-highlight);
            border-radius: 8px;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            transition: all 0.25s ease;
        }

        .stat-card:hover {
            border-left-color: var(--ef-cyan);
            background: rgba(10, 16, 32, 0.85);
            transform: translateY(-2px);
        }

        .stat-card.active-volt {
            border-left-color: var(--ef-volt);
        }

        .stat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .stat-label {
            font-family: var(--ef-font-sports);
            font-size: 14px;
            font-weight: 700;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--ef-text-muted);
        }

        .stat-sub-badge {
            font-family: var(--ef-font-mono);
            font-size: 9.5px;
            padding: 2px 6px;
            border-radius: 3px;
            background: rgba(0, 240, 255, 0.1);
            color: var(--ef-cyan);
            text-transform: uppercase;
        }

        .stat-value {
            font-family: var(--ef-font-sports);
            font-size: 32px;
            font-weight: 900;
            font-style: italic;
            color: #ffffff;
            letter-spacing: 0.5px;
            line-height: 1;
        }

        .stat-value.cyan {
            color: var(--ef-cyan);
            text-shadow: 0 0 16px rgba(0, 240, 255, 0.3);
        }

        .stat-value.volt {
            color: var(--ef-volt);
            text-shadow: 0 0 16px rgba(216, 255, 0, 0.3);
        }

        .stat-meta {
            font-family: var(--ef-font-body);
            font-size: 11.5px;
            color: var(--ef-text-muted);
        }

        /* SHA-256 Box */
        .hash-card {
            margin-top: 20px;
            background: rgba(5, 8, 17, 0.8);
            border: 1px solid rgba(0, 240, 255, 0.18);
            border-radius: 8px;
            padding: 12px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            position: relative;
            z-index: 2;
        }

        .hash-content {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
            min-width: 260px;
        }

        .hash-label {
            font-family: var(--ef-font-sports);
            font-size: 14px;
            font-weight: 800;
            font-style: italic;
            color: var(--ef-cyan);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .hash-code {
            font-family: var(--ef-font-mono);
            font-size: 11.5px;
            color: #cbd5e1;
            word-break: break-all;
        }

        .copy-btn {
            background: rgba(0, 240, 255, 0.1);
            border: 1px solid rgba(0, 240, 255, 0.3);
            color: var(--ef-cyan);
            font-family: var(--ef-font-sports);
            font-size: 13px;
            font-weight: 700;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 6px 14px;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }

        .copy-btn:hover {
            background: var(--ef-cyan);
            color: #000;
            box-shadow: 0 0 14px var(--ef-cyan-glow);
        }

        /* Panel */
        .ef-panel {
            background: var(--ef-bg-card);
            border: 1px solid var(--ef-border);
            border-radius: 14px;
            padding: 28px;
            backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            gap: 20px;
            position: relative;
            overflow: hidden;
        }

        .panel-ball-watermark {
            position: absolute;
            bottom: -50px;
            right: -30px;
            width: 260px;
            height: 260px;
            pointer-events: none;
            opacity: 0.08;
            z-index: 0;
        }

        .ef-panel::before {
            content: "";
            position: absolute;
            top: 0;
            left: 20px;
            right: 20px;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--ef-border-highlight), transparent);
        }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            padding-bottom: 16px;
            position: relative;
            z-index: 1;
        }

        .panel-title {
            font-family: var(--ef-font-sports);
            font-size: 22px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .panel-title svg {
            color: var(--ef-cyan);
        }

        .panel-pill {
            font-family: var(--ef-font-mono);
            font-size: 10.5px;
            padding: 3px 8px;
            border-radius: 4px;
            background: rgba(216, 255, 0, 0.1);
            border: 1px solid rgba(216, 255, 0, 0.3);
            color: var(--ef-volt);
            text-transform: uppercase;
        }

        /* Tactical Steps Grid */
        .step-list {
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            position: relative;
            z-index: 1;
        }

        .tactical-step {
            display: flex;
            gap: 16px;
            align-items: flex-start;
            background: rgba(6, 10, 20, 0.55);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            padding: 18px;
            transition: all 0.2s ease;
        }

        .tactical-step:hover {
            border-color: rgba(0, 240, 255, 0.3);
            background: rgba(10, 16, 32, 0.8);
            transform: translateY(-2px);
        }

        .step-badge {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.15) 0%, rgba(0, 85, 255, 0.2) 100%);
            border: 1px solid var(--ef-cyan);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--ef-font-sports);
            font-size: 19px;
            font-weight: 900;
            font-style: italic;
            color: var(--ef-cyan);
            flex-shrink: 0;
            transform: skewX(-6deg);
        }

        .step-badge span {
            transform: skewX(6deg);
        }

        .step-body {
            flex: 1;
        }

        .step-body h4 {
            font-family: var(--ef-font-sports);
            font-size: 17px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #ffffff;
            margin-bottom: 6px;
        }

        .step-body p {
            font-size: 13.5px;
            color: var(--ef-text-muted);
            line-height: 1.5;
        }

        .step-body code {
            font-family: var(--ef-font-mono);
            font-size: 12px;
            background: rgba(0, 240, 255, 0.1);
            color: var(--ef-cyan);
            padding: 2px 6px;
            border-radius: 4px;
        }

        /* Server Specs Feature Bar */
        .specs-bar {
            background: rgba(10, 16, 30, 0.65);
            border: 1px solid var(--ef-border);
            border-radius: 12px;
            padding: 18px 24px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            backdrop-filter: blur(12px);
        }

        .spec-item {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .spec-icon {
            width: 34px;
            height: 34px;
            border-radius: 6px;
            background: rgba(0, 240, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.2);
            color: var(--ef-cyan);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .spec-text h5 {
            font-family: var(--ef-font-sports);
            font-size: 15px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #ffffff;
        }

        .spec-text p {
            font-size: 11.5px;
            color: var(--ef-text-muted);
        }

        /* Toast Alert HUD Style */
        #toast {
            position: fixed;
            bottom: 28px;
            right: 28px;
            background: #090e1c;
            border: 1.5px solid var(--ef-cyan);
            border-radius: 8px;
            padding: 14px 22px;
            color: #ffffff;
            font-family: var(--ef-font-body);
            font-size: 13.5px;
            font-weight: 600;
            transform: translateY(120px);
            opacity: 0;
            transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 1000;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), 0 0 20px var(--ef-cyan-glow);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        #toast.show {
            transform: translateY(0);
            opacity: 1;
        }

        #toast.toast-error {
            border-color: #ef4444;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), 0 0 20px rgba(239, 68, 68, 0.4);
        }

        /* Footer */
        footer {
            padding: 28px 20px;
            text-align: center;
            font-size: 12.5px;
            color: var(--ef-text-muted);
            border-top: 1px solid var(--ef-border);
            margin-top: auto;
            background: rgba(4, 7, 17, 0.92);
            display: flex;
            flex-direction: column;
            gap: 6px;
            align-items: center;
            position: relative;
            z-index: 2;
        }

        .footer-brand {
            font-family: var(--ef-font-sports);
            font-size: 16px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #cbd5e1;
        }

        .footer-brand span {
            color: var(--ef-cyan);
        }

        /* Cloud Save Sync Deck Styles */
        .cloud-sync-panel {
            background: linear-gradient(135deg, rgba(8, 14, 28, 0.92) 0%, rgba(14, 24, 46, 0.88) 100%);
            border: 1px solid var(--ef-border-highlight);
            border-radius: 16px;
            padding: 26px 28px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(0, 240, 255, 0.25);
            position: relative;
            overflow: hidden;
        }

        .cloud-sync-panel::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, var(--ef-cyan), var(--ef-volt), var(--ef-cyan));
        }

        .cloud-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }

        .cloud-box {
            background: rgba(6, 10, 20, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 22px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            transition: all 0.25s ease;
        }

        .cloud-box:hover {
            border-color: rgba(0, 240, 255, 0.4);
            box-shadow: 0 8px 24px rgba(0, 240, 255, 0.1);
        }

        .cloud-box-title {
            font-family: var(--ef-font-sports);
            font-size: 19px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .cloud-box-desc {
            font-size: 13px;
            color: var(--ef-text-muted);
            line-height: 1.5;
        }

        .cloud-input-group {
            display: flex;
            gap: 10px;
        }

        .cloud-code-input {
            flex: 1;
            background: rgba(4, 7, 16, 0.85);
            border: 1.5px solid rgba(0, 240, 255, 0.4);
            border-radius: 8px;
            padding: 12px 16px;
            font-family: var(--ef-font-mono);
            font-size: 18px;
            font-weight: 700;
            color: var(--ef-cyan);
            text-align: center;
            letter-spacing: 4px;
            outline: none;
            transition: all 0.2s ease;
        }

        .cloud-code-input:focus {
            border-color: var(--ef-cyan);
            box-shadow: 0 0 15px var(--ef-cyan-glow);
        }

        .cloud-action-btn {
            background: linear-gradient(135deg, var(--ef-cyan) 0%, #0088ff 100%);
            color: #040711;
            font-family: var(--ef-font-sports);
            font-size: 16px;
            font-weight: 800;
            font-style: italic;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 0 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }

        .cloud-action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px var(--ef-cyan-glow);
        }

        .cloud-action-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        .cloud-upload-dropzone {
            border: 2px dashed rgba(216, 255, 0, 0.35);
            border-radius: 10px;
            padding: 22px 16px;
            text-align: center;
            cursor: pointer;
            background: rgba(216, 255, 0, 0.03);
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }

        .cloud-upload-dropzone:hover {
            border-color: var(--ef-volt);
            background: rgba(216, 255, 0, 0.08);
        }

        .cloud-code-display {
            display: none;
            background: rgba(216, 255, 0, 0.08);
            border: 1px solid var(--ef-volt);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }

        .cloud-code-number {
            font-family: var(--ef-font-mono);
            font-size: 32px;
            font-weight: 800;
            color: var(--ef-volt);
            letter-spacing: 6px;
            text-shadow: 0 0 16px var(--ef-volt-glow);
        }
    </style>
</head>
<body>

    <!-- Đồ họa sân bóng đá eFootball nền (Tactical Football Pitch Lines) -->
    <div class="football-pitch-bg">
        <svg width="100%" height="100%" viewBox="0 0 1920 1080" fill="none" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
            <!-- Vạch biên sân bóng -->
            <rect x="160" y="80" width="1600" height="920" stroke="#00f0ff" stroke-width="2.5" stroke-dasharray="16 8"/>
            <!-- Đường giữa sân -->
            <line x1="960" y1="80" x2="960" y2="1000" stroke="#00f0ff" stroke-width="2.5"/>
            <!-- Vòng tròn trung tâm & Điểm phát bóng -->
            <circle cx="960" cy="540" r="160" stroke="#d8ff00" stroke-width="2.5"/>
            <circle cx="960" cy="540" r="6" fill="#d8ff00"/>
            <!-- Vòng cấm địa cánh trái -->
            <rect x="160" y="270" width="280" height="540" stroke="#00f0ff" stroke-width="2"/>
            <rect x="160" y="390" width="110" height="300" stroke="#00f0ff" stroke-width="1.5"/>
            <path d="M 440 450 A 90 90 0 0 1 440 630" stroke="#d8ff00" stroke-width="2"/>
            <circle cx="360" cy="540" r="5" fill="#00f0ff"/>
            <!-- Vòng cấm địa cánh phải -->
            <rect x="1480" y="270" width="280" height="540" stroke="#00f0ff" stroke-width="2"/>
            <rect x="1650" y="390" width="110" height="300" stroke="#00f0ff" stroke-width="1.5"/>
            <path d="M 1480 450 A 90 90 0 0 0 1480 630" stroke="#d8ff00" stroke-width="2"/>
            <circle cx="1560" cy="540" r="5" fill="#00f0ff"/>
            <!-- Vòng cung 4 góc sân -->
            <path d="M 160 140 A 60 60 0 0 0 220 80" stroke="#d8ff00" stroke-width="2"/>
            <path d="M 1700 80 A 60 60 0 0 0 1760 140" stroke="#d8ff00" stroke-width="2"/>
            <path d="M 160 940 A 60 60 0 0 1 220 1000" stroke="#d8ff00" stroke-width="2"/>
            <path d="M 1700 1000 A 60 60 0 0 1 1760 940" stroke="#d8ff00" stroke-width="2"/>
        </svg>
    </div>

    <!-- Header Navigation -->
    <header>
        <div class="brand-container">
            <div class="ef-logo-mark">
                <!-- Stylized eFootball Monogram Vector -->
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M5 4h14l-4 8h-6l3 8H4z" fill="url(#brandGrad)" stroke="none"/>
                    <defs>
                        <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#00f0ff" />
                            <stop offset="100%" stop-color="#d8ff00" />
                        </linearGradient>
                    </defs>
                </svg>
            </div>
            <div class="brand-info">
                <div class="brand-name">
                    <span class="ef-title">eFootball</span>
                    <span class="ef-sub">2027</span>
                </div>
                <div class="brand-meta">pes.minhgame.com • OTA Asset Distribution</div>
            </div>
        </div>

        <div class="header-telemetry">
            <div class="telemetry-chip">
                <div class="telemetry-chip-content">
                    <div class="live-dot"></div>
                    <span>Server Active // VN-CDN</span>
                </div>
            </div>
        </div>
    </header>

    <div class="main-wrapper">

        <!-- Live Status Ticker -->
        <div class="ticker-bar">
            <div class="ticker-badge">Live Broadcast</div>
            <div class="ticker-text">
                Máy chủ cập nhật OTA eFootball 2027 sẵn sàng • Băng thông tốc độ cao không giới hạn • Tương thích iOS 14.0+ TrollStore / Scarlet / Sideloadly
            </div>
        </div>

        <!-- Main Hero Card (eFootball Big Time Event Aesthetic) -->
        <div class="ef-hero-card">

            <!-- Quả bóng đá eFootball 3D Vector Art làm Watermark nền -->
            <div class="hero-ball-watermark">
                <svg viewBox="0 0 400 400" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <radialGradient id="ballShade" cx="35%" cy="30%" r="65%">
                            <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.35"/>
                            <stop offset="45%" stop-color="#0a1836" stop-opacity="0.8"/>
                            <stop offset="100%" stop-color="#030712" stop-opacity="0.95"/>
                        </radialGradient>
                        <linearGradient id="ballStripe1" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#00f0ff"/>
                            <stop offset="100%" stop-color="#0055ff"/>
                        </linearGradient>
                        <linearGradient id="ballStripe2" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#d8ff00"/>
                            <stop offset="100%" stop-color="#10b981"/>
                        </linearGradient>
                    </defs>
                    <!-- Khối cầu bóng đá -->
                    <circle cx="200" cy="200" r="175" fill="url(#ballShade)" stroke="#00f0ff" stroke-width="3"/>
                    <!-- Các múi ngũ giác và lục giác bóng đá eFootball -->
                    <!-- Múi trung tâm -->
                    <polygon points="200,140 248,175 230,230 170,230 152,175" fill="#040918" stroke="#d8ff00" stroke-width="2.5"/>
                    <circle cx="200" cy="189" r="14" fill="url(#ballStripe2)" opacity="0.8"/>
                    <!-- Múi đỉnh -->
                    <line x1="200" y1="140" x2="200" y2="70" stroke="#00f0ff" stroke-width="2.5"/>
                    <polygon points="170,35 230,35 250,70 200,70 150,70" stroke="#00f0ff" stroke-width="2" fill="#06122c"/>
                    <!-- Múi phải trên -->
                    <line x1="248" y1="175" x2="310" y2="145" stroke="#00f0ff" stroke-width="2.5"/>
                    <polygon points="310,145 350,175 330,225 275,205 248,175" stroke="#d8ff00" stroke-width="2" fill="url(#ballStripe1)" fill-opacity="0.25"/>
                    <!-- Múi phải dưới -->
                    <line x1="230" y1="230" x2="275" y2="295" stroke="#00f0ff" stroke-width="2.5"/>
                    <polygon points="275,295 335,305 355,255 300,240 275,205" stroke="#00f0ff" stroke-width="2" fill="#06122c"/>
                    <!-- Múi đáy -->
                    <line x1="170" y1="230" x2="155" y2="305" stroke="#00f0ff" stroke-width="2.5"/>
                    <polygon points="155,305 210,345 260,330 275,295 215,280" stroke="#d8ff00" stroke-width="2" fill="url(#ballStripe2)" fill-opacity="0.2"/>
                    <!-- Múi trái dưới -->
                    <line x1="170" y1="230" x2="105" y2="245" stroke="#00f0ff" stroke-width="2.5"/>
                    <polygon points="105,245 70,295 110,335 155,305 135,260" stroke="#00f0ff" stroke-width="2" fill="#06122c"/>
                    <!-- Múi trái trên -->
                    <line x1="152" y1="175" x2="90" y2="145" stroke="#00f0ff" stroke-width="2.5"/>
                    <polygon points="90,145 50,185 70,240 120,215 105,175" stroke="#d8ff00" stroke-width="2" fill="url(#ballStripe1)" fill-opacity="0.25"/>
                    <!-- Dải lượn eFootball Kinetic Speed Trails -->
                    <path d="M 60 70 Q 200 120 340 70" stroke="#00f0ff" stroke-width="2" stroke-dasharray="8 6" opacity="0.6"/>
                    <path d="M 40 320 Q 200 270 360 320" stroke="#d8ff00" stroke-width="2" stroke-dasharray="8 6" opacity="0.6"/>
                </svg>
            </div>

            <div class="hero-top-row">
                <div class="hero-title-area">
                    <div class="category-tag">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                        </svg>
                        <span>Official Mod Release</span>
                    </div>
                    <h2><?php echo htmlspecialchars($cleanTitle); ?></h2>
                    <p><?php echo htmlspecialchars($cleanNotice); ?>. Tối ưu hoá toàn diện đồ hoạ cầu thủ, khuôn mặt huyền thoại, bộ áo đấu mùa giải 2026/2027 cùng cơ chế chuyển nhượng mới nhất.</p>
                </div>

                <div class="hero-actions">
                    <?php if ($zipExists): ?>
                        <a href="download.php" class="ef-btn ef-btn-primary">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            <span>Tải Gói Data <?php echo $versionData['size_mb']; ?> MB</span>
                        </a>
                    <?php else: ?>
                        <button class="ef-btn ef-btn-disabled" disabled>
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                            <span>Chưa Có File Trên Server</span>
                        </button>
                    <?php endif; ?>
                </div>
            </div>

            <!-- Stats Grid -->
            <div class="ef-stats-grid">
                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-label">Phiên Bản Game</span>
                        <span class="stat-sub-badge">LIVE OTA</span>
                    </div>
                    <div class="stat-value cyan"><?php echo htmlspecialchars($versionData['version']); ?></div>
                    <div class="stat-meta">Mod Build 2027.1 • All Rosters</div>
                </div>

                <div class="stat-card active-volt">
                    <div class="stat-header">
                        <span class="stat-label">Dung Lượng Gói Tải</span>
                        <span class="stat-sub-badge">CDN FAST</span>
                    </div>
                    <div class="stat-value volt">
                        <?php echo $zipExists ? ($versionData['size_mb'] . " MB") : "0 MB"; ?>
                    </div>
                    <div class="stat-meta">Nén định dạng ZIP chuẩn iOS</div>
                </div>

                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-label">Cập Nhật Lần Cuối</span>
                        <span class="stat-sub-badge">TIMESTAMP</span>
                    </div>
                    <div class="stat-value" style="font-size: 22px; margin-top: 4px;">
                        <?php echo date('d/m/Y H:i', $versionData['updated_at']); ?>
                    </div>
                    <div class="stat-meta">Giờ máy chủ Đông Dương UTC+7</div>
                </div>

                <div class="stat-card">
                    <div class="stat-header">
                        <span class="stat-label">Trạng Thái File ZIP</span>
                        <span class="stat-sub-badge">INTEGRITY</span>
                    </div>
                    <div class="stat-value <?php echo $zipExists ? 'cyan' : ''; ?>" style="font-size: 20px; margin-top: 5px;">
                        <?php echo $zipExists ? 'Sẵn Sàng Tải Về' : 'Đang Chờ File'; ?>
                    </div>
                    <div class="stat-meta">Hỗ trợ tải ngắt quãng và tiếp tục tải</div>
                </div>
            </div>

            <!-- Checksum SHA256 Box -->
            <?php if (!empty($versionData['sha256'])): ?>
                <div class="hash-card">
                    <div class="hash-content">
                        <span class="hash-label">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            </svg>
                            SHA-256:
                        </span>
                        <span class="hash-code" id="shaCode"><?php echo htmlspecialchars($versionData['sha256']); ?></span>
                    </div>
                    <button class="copy-btn" id="btnCopyHash" onclick="copyHash()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <span>Sao chép</span>
                    </button>
                </div>
            <?php endif; ?>
        </div>

        <!-- Specs Feature Bar -->
        <div class="specs-bar">
            <div class="spec-item">
                <div class="spec-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
                        <line x1="12" y1="18" x2="12.01" y2="18"></line>
                    </svg>
                </div>
                <div class="spec-text">
                    <h5>Nền Tảng Hỗ Trợ</h5>
                    <p>iOS 14.0 đến iOS 18+</p>
                </div>
            </div>

            <div class="spec-item">
                <div class="spec-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </div>
                <div class="spec-text">
                    <h5>Tốc Độ Mượt Mà</h5>
                    <p>Mở khoá 60 FPS / 120 FPS</p>
                </div>
            </div>

            <div class="spec-item">
                <div class="spec-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
                <div class="spec-text">
                    <h5>Đồng Bộ OTA Trực Tiếp</h5>
                    <p>Tải 1-chạm không cần máy tính</p>
                </div>
            </div>

            <div class="spec-item">
                <div class="spec-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                    </svg>
                </div>
                <div class="spec-text">
                    <h5>HTTP Range Resume</h5>
                    <p>Tiếp tục tải nếu mạng ngắt</p>
                </div>
            </div>
        </div>

        <!-- Cloud Save Database Sync Panel (6-Digit Ingame & Web Sync) -->
        <div class="cloud-sync-panel">
            <div class="panel-header">
                <div class="panel-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
                    </svg>
                    <span>Lưu Trữ & Khôi Phục Save Cloud (Mã 6 Chữ Số)</span>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span class="panel-pill" style="background: rgba(0, 240, 255, 0.1); border-color: rgba(0, 240, 255, 0.3); color: var(--ef-cyan);">
                        Đang Lưu: <?php echo $saveCount; ?> Save
                    </span>
                    <span class="panel-pill">Sync Ingame & Web</span>
                </div>
            </div>

            <div class="cloud-grid">
                <!-- Box 1: Khôi phục bằng mã 6 số -->
                <div class="cloud-box">
                    <div class="cloud-box-title">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color: var(--ef-cyan);">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>1. Tra Cứu & Tải Save Từ Mã 6 Số</span>
                    </div>
                    <div class="cloud-box-desc">
                        Nhập mã 6 chữ số đã được cấp từ điện thoại (hoặc từ web) để tải file save <code>.zip</code> hoặc kiểm tra thông tin:
                    </div>
                    <div class="cloud-input-group">
                        <input type="text" id="webCloudCode" class="cloud-code-input" placeholder="839102" maxlength="6" pattern="[0-9]*" inputmode="numeric">
                        <button class="cloud-action-btn" id="btnWebCloudDownload" onclick="webDownloadSave()">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            <span>Tải Save</span>
                        </button>
                    </div>
                    <div id="webCloudInfo" style="font-size: 12.5px; color: var(--ef-cyan); font-family: var(--ef-font-mono); min-height: 18px;"></div>
                </div>

                <!-- Box 2: Tải Save từ máy tính lên Web để lấy mã 6 số -->
                <div class="cloud-box">
                    <div class="cloud-box-title">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" style="color: var(--ef-volt);">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="17 8 12 3 7 8"></polyline>
                            <line x1="12" y1="3" x2="12" y2="15"></line>
                        </svg>
                        <span>2. Tải File Save Lên Web Để Nhận Mã 6 Số</span>
                    </div>
                    <div class="cloud-box-desc">
                        Chọn file <code>ziru_save.db</code> hoặc file <code>.zip</code> từ máy tính để tải lên máy chủ và nhận mã 6 số nạp vào game:
                    </div>
                    <input type="file" id="webSaveFileInput" accept=".db,.zip" style="display: none;" onchange="webHandleFileSelect(this)">
                    <div class="cloud-upload-dropzone" id="webDropZone" onclick="document.getElementById('webSaveFileInput').click()">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--ef-volt);">
                            <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>
                            <path d="M12 12v9"/>
                            <path d="m16 16-4-4-4 4"/>
                        </svg>
                        <span style="font-size: 13.5px; font-weight: 700; color: #ffffff;" id="webDropText">Nhấn để chọn file ziru_save.db hoặc .zip</span>
                        <span style="font-size: 11.5px; color: var(--ef-text-muted);">Tối đa 50MB • Tự động mã hoá an toàn</span>
                    </div>

                    <!-- Khu vực hiển thị mã 6 số khi tải lên thành công -->
                    <div class="cloud-code-display" id="webCodeDisplay">
                        <span style="font-size: 12px; font-weight: 700; color: #ffffff; text-transform: uppercase;">MÃ KHÔI PHỤC INGAME CỦA BẠN:</span>
                        <div class="cloud-code-number" id="webAssignedCode">------</div>
                        <div style="font-size: 12.5px; color: var(--ef-text-muted);">
                            Vào game trên iPhone > Bấm nút nổi <strong style="color: var(--ef-lime, #d8ff00);">DATA</strong> ở góc trên > Nhập 6 số này để khôi phục!
                        </div>
                        <button class="copy-btn" onclick="copyWebCloudCode()" style="margin-top: 4px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            <span>Sao chép mã 6 số</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Instructions For Players (Full Width Tactical Deck) -->
        <div class="ef-panel">
            <!-- Quả bóng phụ làm watermark cho phần hướng dẫn -->
            <div class="panel-ball-watermark">
                <svg viewBox="0 0 200 200" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="100" cy="100" r="90" stroke="#00f0ff" stroke-width="2" stroke-dasharray="6 6"/>
                    <polygon points="100,65 125,85 115,115 85,115 75,85" stroke="#d8ff00" stroke-width="2"/>
                    <line x1="100" y1="65" x2="100" y2="20" stroke="#00f0ff" stroke-width="1.5"/>
                    <line x1="125" y1="85" x2="170" y2="70" stroke="#00f0ff" stroke-width="1.5"/>
                    <line x1="115" y1="115" x2="150" y2="160" stroke="#00f0ff" stroke-width="1.5"/>
                    <line x1="85" y1="115" x2="50" y2="160" stroke="#00f0ff" stroke-width="1.5"/>
                    <line x1="75" y1="85" x2="30" y2="70" stroke="#00f0ff" stroke-width="1.5"/>
                </svg>
            </div>

            <div class="panel-header">
                <div class="panel-title">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                        <line x1="8" y1="21" x2="16" y2="21"></line>
                        <line x1="12" y1="17" x2="12" y2="21"></line>
                    </svg>
                    <span>Hướng Dẫn Cài Đặt Cho Người Chơi</span>
                </div>
                <span class="panel-pill">iOS Sideload Protocol</span>
            </div>

            <ul class="step-list">
                <li class="tactical-step">
                    <div class="step-badge"><span>01</span></div>
                    <div class="step-body">
                        <h4>Cài Đặt File IPA Client</h4>
                        <p>Sử dụng <strong>TrollStore</strong>, <strong>Scarlet</strong>, <strong>Esign</strong> hoặc <strong>Sideloadly</strong> để cài đặt tệp IPA game nhẹ khoảng 200MB vào thiết bị iPhone hoặc iPad.</p>
                    </div>
                </li>

                <li class="tactical-step">
                    <div class="step-badge"><span>02</span></div>
                    <div class="step-body">
                        <h4>Khởi Động & Kết Nối Máy Chủ</h4>
                        <p>Mở ứng dụng lần đầu. Client game sẽ tự động kết nối cổng OTA <code>pes.minhgame.com</code> để kiểm tra danh mục tài nguyên dữ liệu mới nhất.</p>
                    </div>
                </li>

                <li class="tactical-step">
                    <div class="step-badge"><span>03</span></div>
                    <div class="step-body">
                        <h4>Tự Động Nạp Data & Thi Đấu</h4>
                        <p>Chọn nút <strong>"Tải data từ Server"</strong> trong game. Hệ thống sẽ tự động tải gói ZIP về máy, tự giải nén và vào ngay sân cỏ với đầy đủ huyền thoại.</p>
                    </div>
                </li>
            </ul>
        </div>

    </div>

    <!-- Official Style Footer -->
    <footer>
        <div class="footer-brand">
            eFootball™ <span>2027</span> Mod Project • Powered by iOSVN & MinhGame
        </div>
        <div>
            Máy chủ phân phối tài nguyên game di động • pes.minhgame.com • Tất cả quyền được bảo lưu
        </div>
    </footer>

    <!-- HUD Notification Toast -->
    <div id="toast">
        <svg id="toastIcon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span id="toastMsg">Thông báo</span>
    </div>

    <script>
        function showToast(msg, isErr = false) {
            const t = document.getElementById('toast');
            const msgEl = document.getElementById('toastMsg');
            const iconEl = document.getElementById('toastIcon');

            msgEl.textContent = msg;
            if (isErr) {
                t.className = 'toast-error show';
                iconEl.innerHTML = '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>';
            } else {
                t.className = 'show';
                iconEl.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
            }

            clearTimeout(window.__toastTimer);
            window.__toastTimer = setTimeout(() => {
                t.className = '';
            }, 3500);
        }

        function copyHash() {
            const code = document.getElementById('shaCode');
            const btn = document.getElementById('btnCopyHash');
            if (!code) return;
            
            navigator.clipboard.writeText(code.innerText.trim()).then(() => {
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Đã chép</span>';
                showToast('Đã sao chép mã SHA-256 vào bộ nhớ tạm');
                setTimeout(() => {
                    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg><span>Sao chép</span>';
                }, 2000);
            }).catch(() => {
                showToast('Không thể sao chép tự động', true);
            });
        }

        // =========================================================================
        // Cloud Save Sync Web Handlers
        // =========================================================================
        async function webDownloadSave() {
            const input = document.getElementById('webCloudCode');
            const info = document.getElementById('webCloudInfo');
            const btn = document.getElementById('btnWebCloudDownload');
            const code = (input.value || '').trim().replace(/[^0-9]/g, '');

            if (code.length !== 6) {
                showToast('Vui lòng nhập đúng 6 chữ số!', true);
                input.focus();
                return;
            }

            btn.disabled = true;
            info.textContent = 'Đang kiểm tra mã ' + code + ' trên máy chủ...';

            try {
                const res = await fetch('/api/save.php?action=info&code=' + code);
                const data = await res.json();
                if (!res.ok || !data.success) {
                    throw new Error(data.message || 'Không tìm thấy file save với mã này.');
                }

                info.textContent = `Tìm thấy save (${data.size_kb} KB, lưu lúc ${data.created_at}). Đang tải về...`;
                showToast('Đang tải file save ' + code + '...');
                window.location.href = '/api/save.php?action=download&code=' + code;
            } catch (err) {
                info.textContent = 'Lỗi: ' + err.message;
                showToast(err.message, true);
            } finally {
                btn.disabled = false;
            }
        }

        async function webHandleFileSelect(input) {
            const file = input.files && input.files[0];
            if (!file) return;

            const dropText = document.getElementById('webDropText');
            const display = document.getElementById('webCodeDisplay');
            const assignedCode = document.getElementById('webAssignedCode');

            dropText.textContent = `Đang tải lên: ${file.name} (${(file.size / 1024).toFixed(1)} KB)...`;
            showToast('Đang gửi file save lên máy chủ...');

            const formData = new FormData();
            formData.append('file', file);
            formData.append('action', 'upload');

            try {
                const res = await fetch('/api/save.php?action=upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();

                if (!res.ok || !data.success) {
                    throw new Error(data.message || 'Lỗi tải lên file save.');
                }

                assignedCode.textContent = data.code;
                display.style.display = 'flex';
                dropText.textContent = `Đã lưu ${file.name}! Nhận mã thành công.`;
                showToast(`Thành công! Mã của bạn là: ${data.code}`);

                // Tự động điền sang ô tải save
                const codeInput = document.getElementById('webCloudCode');
                if (codeInput) codeInput.value = data.code;
            } catch (err) {
                dropText.textContent = 'Lỗi: ' + err.message;
                showToast(err.message, true);
            } finally {
                input.value = '';
            }
        }

        function copyWebCloudCode() {
            const el = document.getElementById('webAssignedCode');
            if (!el) return;
            const code = el.textContent.trim();
            navigator.clipboard.writeText(code).then(() => {
                showToast(`Đã sao chép mã ${code} vào bộ nhớ tạm!`);
            }).catch(() => {
                showToast('Không thể sao chép', true);
            });
        }
    </script>
</body>
</html>
