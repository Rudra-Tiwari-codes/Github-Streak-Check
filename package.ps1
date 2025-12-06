# PowerShell script to package Lambda function for deployment
# Run this script before uploading to AWS Lambda

Write-Host "Packaging Lambda function..." -ForegroundColor Cyan

# Create package directory
if (Test-Path "package") {
    Remove-Item -Recurse -Force package
}
New-Item -ItemType Directory -Path package | Out-Null

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -t package/

# Copy Lambda function
Copy-Item lambda_function.py package/

# Create zip file
Write-Host "Creating deployment.zip..." -ForegroundColor Yellow
if (Test-Path "deployment.zip") {
    Remove-Item -Force deployment.zip
}
Compress-Archive -Path package\* -DestinationPath deployment.zip -Force

Write-Host "`nPackage created: deployment.zip" -ForegroundColor Green
Write-Host "Upload this file to AWS Lambda console" -ForegroundColor Green

