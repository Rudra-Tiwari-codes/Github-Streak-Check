#!/bin/bash
# Bash script to package Lambda function for deployment
# Run this script before uploading to AWS Lambda

echo "Packaging Lambda function..."

# Create package directory
rm -rf package
mkdir package

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t package/

# Copy Lambda function
cp lambda_function.py package/

# Create zip file
echo "Creating deployment.zip..."
cd package
zip -r ../deployment.zip .
cd ..

echo ""
echo "Package created: deployment.zip"
echo "Upload this file to AWS Lambda console"

