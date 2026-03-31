@echo off
REM Deploy OCR Worker — reads GEMINI_API_KEY from .env
REM Usage: cloud\_deploy.cmd
for /f "tokens=1,2 delims==" %%a in ('findstr "GEMINI_API_KEY" .env') do set GEMINI_KEY=%%b
if "%GEMINI_KEY%"=="" (echo ERROR: GEMINI_API_KEY not found in .env & exit /b 1)
gcloud functions deploy ocr-worker --gen2 --runtime python311 --region asia-southeast1 --source cloud/function --entry-point handle_request --trigger-http --allow-unauthenticated --memory 512MB --timeout 540s --set-env-vars GEMINI_API_KEY=%GEMINI_KEY% --update-env-vars GCS_BUCKET=election69-ocr-results-th --project election-ocr
