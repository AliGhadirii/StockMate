@echo off
REM ============================================================================
REM AWS Lambda Build Script for Windows
REM Creates lambda_deployment.zip ready to upload to AWS Lambda Console
REM ============================================================================

echo.
echo ========================================================================
echo Building AWS Lambda Deployment Package
echo ========================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ and try again
    echo.
    pause
    exit /b 1
)

echo [1/6] Cleaning old build artifacts...
if exist lambda_build rmdir /s /q lambda_build
if exist lambda_deployment.zip del /q lambda_deployment.zip
echo       Done.
echo.

echo [2/6] Creating build directory...
mkdir lambda_build
echo       Done.
echo.

echo [3/6] Installing dependencies to build directory...
echo       This may take a few minutes...
echo       Downloading packages compatible with AWS Lambda...
echo.

REM Install with Linux-compatible wheels for AWS Lambda
REM This includes all dependencies automatically
python -m pip install -r lambda_requirements.txt -t lambda_build --upgrade --platform manylinux2014_x86_64 --only-binary=:all: --python-version 311 --implementation cp --quiet

if errorlevel 1 (
    echo [ERROR] Failed to download packages
    echo.
    pause
    exit /b 1
)

echo       Done.
echo.

echo [4/6] Copying Lambda function and modules...
copy lambda_function.py lambda_build\ >nul
copy google_drive_client.py lambda_build\ >nul
copy telegram_client.py lambda_build\ >nul
copy etf_analysis.py lambda_build\ >nul
echo       Done.
echo.

echo [4.5/6] Cleaning up unnecessary files to reduce size...
REM Remove test files, examples, and cache to reduce package size
for /d /r lambda_build %%d in (tests __pycache__ *.dist-info) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
del /s /q lambda_build\*.pyc 2>nul
del /s /q lambda_build\*.pyo 2>nul
echo       Done.
echo.

echo [5/6] Creating deployment package (using Python zipfile - much faster)...
python -c "import zipfile,os;z=zipfile.ZipFile('lambda_deployment.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6);[z.write(os.path.join(r,f),os.path.join(r,f).replace('lambda_build\\','')) for r,_,fs in os.walk('lambda_build') for f in fs];z.close()"
echo       Done.
echo.

echo [6/6] Cleaning up build directory...
rmdir /s /q lambda_build
echo       Done.
echo.

REM Get file size
for %%A in (lambda_deployment.zip) do set size=%%~zA
set /a sizeMB=%size% / 1048576

echo ========================================================================
echo BUILD SUCCESSFUL!
echo ========================================================================
echo.
echo Package created: lambda_deployment.zip
echo Size: %sizeMB% MB
echo.

if %sizeMB% GTR 50 (
    echo WARNING: Package is larger than 50 MB
    echo Lambda Console upload limit is 50 MB
    echo Consider using S3 or Lambda Layers
    echo.
)

echo Ready to upload to AWS Lambda Console!
echo.
echo Next steps:
echo 1. Go to: https://console.aws.amazon.com/lambda
echo 2. Create/select your Lambda function
echo 3. Upload lambda_deployment.zip
echo 4. Set handler to: lambda_function.lambda_handler
echo 5. Add environment variables from lambda_env_template.txt
echo.
echo ========================================================================
echo.
pause
