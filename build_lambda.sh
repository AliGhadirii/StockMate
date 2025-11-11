#!/bin/bash
# ============================================================================
# AWS Lambda Build Script for Unix/Linux/Mac
# Creates lambda_deployment.zip ready to upload to AWS Lambda Console
# ============================================================================

set -e  # Exit on error

echo ""
echo "========================================================================"
echo "Building AWS Lambda Deployment Package"
echo "========================================================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    exit 1
fi

echo "[1/6] Cleaning old build artifacts..."
rm -rf lambda_build
rm -f lambda_deployment.zip
echo "      Done."
echo ""

echo "[2/6] Creating build directory..."
mkdir lambda_build
echo "      Done."
echo ""

echo "[3/6] Installing dependencies to build directory..."
echo "      This may take a few minutes..."
echo "      Downloading packages compatible with AWS Lambda..."
echo "      (includes all transitive dependencies)"
echo ""
python3 -m pip install -r lambda_requirements.txt -t lambda_build --upgrade --platform manylinux2014_x86_64 --only-binary=:all: --python-version 311 --implementation cp --quiet 2>/dev/null || \
python3 -m pip install -r lambda_requirements.txt -t lambda_build --upgrade --quiet
echo "      Done."
echo ""

echo "[4/6] Copying Lambda function..."
cp lambda_function.py lambda_build/
echo "      Done."
echo ""

echo "[4.5/6] Cleaning up unnecessary files to reduce size..."
# Remove test files, examples, and cache
find lambda_build -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find lambda_build -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lambda_build -type f -name "*.pyc" -delete 2>/dev/null || true
find lambda_build -type f -name "*.pyo" -delete 2>/dev/null || true
find lambda_build -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
echo "      Done."
echo ""

echo "[5/6] Creating deployment package (fast compression)..."
cd lambda_build
zip -r6 -q ../lambda_deployment.zip .
cd ..
echo "      Done."
echo ""

echo "[6/6] Cleaning up build directory..."
rm -rf lambda_build
echo "      Done."
echo ""

# Get file size
size=$(du -h lambda_deployment.zip | cut -f1)

echo "========================================================================"
echo "BUILD SUCCESSFUL!"
echo "========================================================================"
echo ""
echo "Package created: lambda_deployment.zip"
echo "Size: $size"
echo ""
echo "Ready to upload to AWS Lambda Console!"
echo ""
echo "Next steps:"
echo "1. Go to: https://console.aws.amazon.com/lambda"
echo "2. Create/select your Lambda function"
echo "3. Upload lambda_deployment.zip"
echo "4. Set handler to: lambda_function.lambda_handler"
echo "5. Add environment variables from lambda_env_template.txt"
echo ""
echo "========================================================================"
echo ""
