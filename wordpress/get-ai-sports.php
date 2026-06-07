<?php
// Shared hosting may print PHP warnings before headers; keep JSON clean.
if (!ob_get_level()) {
    ob_start();
}

/**
 * PRIZOLOV Sports AI — same-origin proxy for prizolov.ru
 *
 * Deploy: upload this file to the WordPress site root as get-ai-sports.php
 * URL:    https://prizolov.ru/get-ai-sports.php
 *
 * The Elementor widget sends POST JSON (get_all, analytics_summary, event_index).
 * This script forwards the body unchanged to Amvera POST /get-ai-sports.php.
 *
 * Optional override in wp-config.php:
 *   define('PRIZOLOV_API_BASE', 'https://prizolov-sports-dmandreyanov.amvera.io');
 */

if (!defined('PRIZOLOV_API_BASE')) {
    define('PRIZOLOV_API_BASE', 'https://prizolov-sports-dmandreyanov.amvera.io');
}

if (!defined('PRIZOLOV_PROXY_TIMEOUT')) {
    define('PRIZOLOV_PROXY_TIMEOUT', 90);
}

if (!defined('PRIZOLOV_PROXY_CONNECT_TIMEOUT')) {
    define('PRIZOLOV_PROXY_CONNECT_TIMEOUT', 15);
}

function prizolov_proxy_cors_headers(): void
{
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Accept');
}

function prizolov_proxy_no_cache_headers(): void
{
    header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    header('Pragma: no-cache');
}

function prizolov_proxy_flush_output_buffers(): void
{
    while (ob_get_level() > 0) {
        ob_end_clean();
    }
}

function prizolov_proxy_json_response(int $status, array $payload): void
{
    prizolov_proxy_flush_output_buffers();
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    prizolov_proxy_cors_headers();
    prizolov_proxy_no_cache_headers();
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function prizolov_proxy_bool($value)
{
    if (is_bool($value)) {
        return $value;
    }
    if (is_int($value) || is_float($value)) {
        return (bool) $value;
    }
    if (!is_string($value)) {
        return $value;
    }

    $normalized = strtolower(trim($value));
    if ($normalized === 'true' || $normalized === '1' || $normalized === 'yes') {
        return true;
    }
    if ($normalized === 'false' || $normalized === '0' || $normalized === 'no') {
        return false;
    }

    return $value;
}

function prizolov_proxy_read_payload(): array
{
    $rawBody = file_get_contents('php://input');
    if (!is_string($rawBody)) {
        $rawBody = '';
    }

    $payload = [];
    if ($rawBody !== '') {
        $decoded = json_decode($rawBody, true);
        if (is_array($decoded)) {
            $payload = $decoded;
        } else {
            prizolov_proxy_json_response(400, [
                'error' => 'invalid_json',
                'message' => 'Request body must be valid JSON',
            ]);
        }
    }

    $boolKeys = [
        'get_all',
        'analytics_summary',
        'include_live',
        'include_upcoming',
        'include_consensus',
        'include_watch',
        'refresh',
        'recommendations_only',
        'premium_only',
        'passable_only',
        'adaptive_policy',
    ];

    foreach ($boolKeys as $key) {
        if (array_key_exists($key, $payload)) {
            $payload[$key] = prizolov_proxy_bool($payload[$key]);
        }
    }

    return $payload;
}

function prizolov_proxy_upstream_url(): string
{
    return rtrim((string) PRIZOLOV_API_BASE, '/') . '/get-ai-sports.php';
}

function prizolov_proxy_forward(array $payload): void
{
    if (!function_exists('curl_init')) {
        prizolov_proxy_json_response(500, [
            'error' => 'curl_missing',
            'message' => 'PHP cURL extension is required',
        ]);
    }

    $upstreamUrl = prizolov_proxy_upstream_url();
    $jsonBody = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

    $ch = curl_init($upstreamUrl);
    if ($ch === false) {
        prizolov_proxy_json_response(500, [
            'error' => 'curl_init_failed',
            'message' => 'Failed to initialize upstream request',
        ]);
    }

    $headers = [
        'Content-Type: application/json',
        'Accept: application/json',
    ];

    if (!empty($_SERVER['HTTP_ACCEPT_LANGUAGE'])) {
        $headers[] = 'Accept-Language: ' . $_SERVER['HTTP_ACCEPT_LANGUAGE'];
    }

    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $jsonBody,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => (int) PRIZOLOV_PROXY_CONNECT_TIMEOUT,
        CURLOPT_TIMEOUT => (int) PRIZOLOV_PROXY_TIMEOUT,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_MAXREDIRS => 3,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);

    $responseBody = curl_exec($ch);
    $curlError = curl_error($ch);
    $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    // curl_close() is deprecated in PHP 8.5+ and can emit HTML warnings on shared hosting.
    unset($ch);

    if ($responseBody === false) {
        prizolov_proxy_json_response(503, [
            'error' => 'upstream_unavailable',
            'message' => $curlError !== '' ? $curlError : 'Failed to reach PRIZOLOV API',
            'upstream' => $upstreamUrl,
        ]);
    }

    $decoded = json_decode($responseBody, true);
    if (!is_array($decoded)) {
        if ($httpCode >= 500 || $httpCode === 0) {
            prizolov_proxy_json_response(200, [
                'events' => [],
                'total' => 0,
                'window_hours' => 24,
                'sports' => [],
                'sports_line' => [],
                'meta' => [
                    'upstream_error' => 'upstream_unavailable',
                    'upstream_status' => $httpCode,
                    'message' => 'PRIZOLOV API временно недоступен. Повторите через 1–2 минуты.',
                    'retry_after_seconds' => 60,
                ],
            ]);
        }

        prizolov_proxy_json_response(502, [
            'error' => 'invalid_upstream_json',
            'message' => 'Upstream returned non-JSON response',
            'upstream_status' => $httpCode,
            'upstream_preview' => substr((string) $responseBody, 0, 300),
        ]);
    }

    $status = $httpCode >= 200 && $httpCode < 600 ? $httpCode : 502;
    if ($status < 200 || $status >= 300) {
        prizolov_proxy_json_response($status, $decoded);
    }

    prizolov_proxy_flush_output_buffers();
    http_response_code(200);
    header('Content-Type: application/json; charset=utf-8');
    prizolov_proxy_cors_headers();
    prizolov_proxy_no_cache_headers();
    echo json_encode($decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$method = isset($_SERVER['REQUEST_METHOD']) ? strtoupper((string) $_SERVER['REQUEST_METHOD']) : 'GET';

if ($method === 'OPTIONS') {
    prizolov_proxy_flush_output_buffers();
    http_response_code(204);
    prizolov_proxy_cors_headers();
    prizolov_proxy_no_cache_headers();
    exit;
}

if ($method !== 'POST') {
    prizolov_proxy_json_response(405, [
        'error' => 'method_not_allowed',
        'message' => 'Use POST with JSON body',
        'allowed' => ['POST', 'OPTIONS'],
    ]);
}

$payload = prizolov_proxy_read_payload();
prizolov_proxy_forward($payload);
