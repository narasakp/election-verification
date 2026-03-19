# Deploy OCR Worker Cloud Function
# Usage: .\cloud\deploy.ps1
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. GEMINI_API_KEY in .env file
#   3. Bucket gs://election69-ocr-results-th created

# Read GEMINI_API_KEY from .env
$envFile = Get-Content "$PSScriptRoot\..\.env" -ErrorAction SilentlyContinue
$geminiKey = ""
foreach ($line in $envFile) {
    if ($line -match "^GEMINI_API_KEY=(.+)$") {
        $geminiKey = $matches[1].Trim('"').Trim("'")
    }
}

if (-not $geminiKey) {
    Write-Error "GEMINI_API_KEY not found in .env"
    exit 1
}

Write-Host "Deploying ocr-worker Cloud Function..." -ForegroundColor Cyan
Write-Host "  GEMINI_API_KEY: $($geminiKey.Substring(0,12))..."
Write-Host "  Bucket: election69-ocr-results-th"
Write-Host ""

gcloud functions deploy ocr-worker `
    --gen2 `
    --runtime python311 `
    --region asia-southeast1 `
    --source "$PSScriptRoot\function" `
    --entry-point handle_request `
    --trigger-http `
    --allow-unauthenticated `
    --memory 512MB `
    --timeout 540s `
    --set-env-vars "GEMINI_API_KEY=$geminiKey,GCS_BUCKET=election69-ocr-results-th" `
    --project election-ocr

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Deploy SUCCESS!" -ForegroundColor Green
    Write-Host "Get the function URL from the output above."
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Copy the function URL"
    Write-Host "  2. Test:  curl -X POST <URL> -H 'Content-Type: application/json' -d '{""file_id"":""test""}'"
    Write-Host "  3. Run:   python cloud/dispatch.py --province tak --function-url <URL> --workers 20"
} else {
    Write-Host ""
    Write-Host "Deploy FAILED. Check errors above." -ForegroundColor Red
}
