$env:PYTHONIOENCODING = 'utf-8'
$ErrorActionPreference = 'Continue'
$startTime = Get-Date

Write-Host "============================================================"
Write-Host "  PRODUCTION RUN - $startTime"
Write-Host "  3 provinces: chaiyaphum (263), tak (1080), phetchabun (1106)"
Write-Host "============================================================"

# 1. Chaiyaphum (smallest - validation run)
Write-Host "`n>>> STARTING: chaiyaphum (263 files) <<<"
python scripts/ocr_multimodel.py --province chaiyaphum --all --resume --models gemini --max-pages 3
Write-Host ">>> chaiyaphum DONE (exit=$LASTEXITCODE) <<<"

# 2. Tak
Write-Host "`n>>> STARTING: tak (1080 files) <<<"
python scripts/ocr_multimodel.py --province tak --all --resume --models gemini --max-pages 3
Write-Host ">>> tak DONE (exit=$LASTEXITCODE) <<<"

# 3. Phetchabun
Write-Host "`n>>> STARTING: phetchabun (1106 files) <<<"
python scripts/ocr_multimodel.py --province phetchabun --all --resume --models gemini --max-pages 3
Write-Host ">>> phetchabun DONE (exit=$LASTEXITCODE) <<<"

$endTime = Get-Date
$elapsed = $endTime - $startTime
Write-Host "`n============================================================"
Write-Host "  PRODUCTION RUN COMPLETE"
Write-Host "  Duration: $($elapsed.TotalHours.ToString('F1')) hours"
Write-Host "  Started: $startTime"
Write-Host "  Ended: $endTime"
Write-Host "============================================================"

# Show final progress
python scripts/_check_progress.py
