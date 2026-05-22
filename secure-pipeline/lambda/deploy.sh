#!/bin/bash

# Deployment Script for Secure Pipeline Lambda Functions
# This script packages the Lambda functions and prepares them for deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDA_DIR="${SCRIPT_DIR}"
PROJECT_NAME="secure-pipeline"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${GREEN}=== $1 ===${NC}"
}

print_error() {
    echo -e "${RED}❌ Error: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check for Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"

    # Check for pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed"
        exit 1
    fi
    print_success "pip3 found: $(pip3 --version)"

    # Check for zip
    if ! command -v zip &> /dev/null; then
        print_error "zip is not installed"
        exit 1
    fi
    print_success "zip found"

    # Check for AWS CLI
    if ! command -v aws &> /dev/null; then
        print_warning "AWS CLI is not installed. You'll need it for deployment."
    else
        print_success "AWS CLI found: $(aws --version)"
    fi

    # Check for Terraform
    if ! command -v terraform &> /dev/null; then
        print_warning "Terraform is not installed. You'll need it for infrastructure deployment."
    else
        print_success "Terraform found: $(terraform --version | head -1)"
    fi
}

# Install dependencies
install_dependencies() {
    print_header "Installing Python Dependencies"

    if [ ! -f "${LAMBDA_DIR}/requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi

    pip3 install -r "${LAMBDA_DIR}/requirements.txt"
    print_success "Dependencies installed"
}

# Run tests
run_tests() {
    print_header "Running Unit Tests"

    if [ ! -f "${LAMBDA_DIR}/test_upload_handler.py" ] || [ ! -f "${LAMBDA_DIR}/test_process_handler.py" ]; then
        print_warning "Test files not found, skipping tests"
        return
    fi

    python3 -m unittest discover -s "${LAMBDA_DIR}" -p "test_*.py" -v
    print_success "All tests passed"
}

# Package upload handler
package_upload_handler() {
    print_header "Packaging Upload Handler"

    local OUTPUT_FILE="${LAMBDA_DIR}/upload_handler.zip"

    # Remove old zip if exists
    if [ -f "${OUTPUT_FILE}" ]; then
        rm "${OUTPUT_FILE}"
    fi

    # Create zip with Lambda function
    cd "${LAMBDA_DIR}"
    zip -q -j "${OUTPUT_FILE}" upload_handler.py
    
    # Add dependencies if they exist in site-packages
    if [ -d "python" ]; then
        zip -r -q "${OUTPUT_FILE}" python/
    fi

    cd - > /dev/null

    local SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    print_success "Upload Handler packaged: ${OUTPUT_FILE} (${SIZE})"
}

# Package process handler
package_process_handler() {
    print_header "Packaging Process Handler"

    local OUTPUT_FILE="${LAMBDA_DIR}/process_handler.zip"

    # Remove old zip if exists
    if [ -f "${OUTPUT_FILE}" ]; then
        rm "${OUTPUT_FILE}"
    fi

    # Create zip with Lambda function
    cd "${LAMBDA_DIR}"
    zip -q -j "${OUTPUT_FILE}" process_handler.py
    
    # Add dependencies if they exist in site-packages
    if [ -d "python" ]; then
        zip -r -q "${OUTPUT_FILE}" python/
    fi

    cd - > /dev/null

    local SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
    print_success "Process Handler packaged: ${OUTPUT_FILE} (${SIZE})"
}

# Validate packages
validate_packages() {
    print_header "Validating Packages"

    local UPLOAD_ZIP="${LAMBDA_DIR}/upload_handler.zip"
    local PROCESS_ZIP="${LAMBDA_DIR}/process_handler.zip"

    if [ ! -f "${UPLOAD_ZIP}" ]; then
        print_error "Upload handler ZIP not found"
        exit 1
    fi

    if [ ! -f "${PROCESS_ZIP}" ]; then
        print_error "Process handler ZIP not found"
        exit 1
    fi

    # List contents
    echo -e "\n${YELLOW}Upload Handler contents:${NC}"
    unzip -l "${UPLOAD_ZIP}" | head -10

    echo -e "\n${YELLOW}Process Handler contents:${NC}"
    unzip -l "${PROCESS_ZIP}" | head -10

    print_success "Packages validated"
}

# Summary
print_summary() {
    print_header "Deployment Summary"

    echo -e "${GREEN}Lambda Functions:${NC}"
    echo "  - Upload Handler:   ${LAMBDA_DIR}/upload_handler.zip"
    echo "  - Process Handler:  ${LAMBDA_DIR}/process_handler.zip"
    echo ""
    echo -e "${GREEN}Next Steps:${NC}"
    echo "  1. Review terraform_example.tf and integrate with your Terraform code"
    echo "  2. Update environment variables as needed"
    echo "  3. Run: terraform plan"
    echo "  4. Run: terraform apply"
    echo ""
    echo -e "${GREEN}For manual deployment:${NC}"
    echo "  aws lambda update-function-code --function-name ${PROJECT_NAME}-upload-handler --zip-file fileb://${LAMBDA_DIR}/upload_handler.zip"
    echo "  aws lambda update-function-code --function-name ${PROJECT_NAME}-process-handler --zip-file fileb://${LAMBDA_DIR}/process_handler.zip"
    echo ""
    echo -e "${GREEN}Testing:${NC}"
    echo "  Run test_upload_handler.py and test_process_handler.py with unit test runner"
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  ${PROJECT_NAME} - Lambda Deployment Script        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_prerequisites
    install_dependencies
    run_tests
    package_upload_handler
    package_process_handler
    validate_packages
    print_summary

    echo -e "\n${GREEN}✅ Deployment preparation complete!${NC}\n"
}

# Run main
main "$@"
