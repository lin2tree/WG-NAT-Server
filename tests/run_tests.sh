#!/bin/bash
#
# FCloud 自动化测试运行脚本
#
# 使用方式:
#   ./run_tests.sh              # 运行所有测试
#   ./run_tests.sh api          # 仅运行 API 测试
#   ./run_tests.sh ui           # 仅运行 UI 测试
#   ./run_tests.sh consistency  # 仅运行数据一致性测试
#   ./run_tests.sh smoke        # 运行冒烟测试
#   ./run_tests.sh regression   # 运行完整回归测试
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$PROJECT_DIR/test-reports"

mkdir -p "$REPORTS_DIR"

run_api_tests() {
    echo "=========================================="
    echo "运行 API 测试..."
    echo "=========================================="
    
    pytest "$SCRIPT_DIR/test_api.py" \
        -v \
        --html="$REPORTS_DIR/api-report.html" \
        --self-contained-html \
        --alluredir="$REPORTS_DIR/allure-results" \
        -m api
}

run_ui_tests() {
    echo "=========================================="
    echo "运行 UI 测试..."
    echo "=========================================="
    
    pytest "$SCRIPT_DIR/test_ui.py" \
        -v \
        --html="$REPORTS_DIR/ui-report.html" \
        --self-contained-html \
        --alluredir="$REPORTS_DIR/allure-results" \
        -m ui
}

run_consistency_tests() {
    echo "=========================================="
    echo "运行数据一致性测试..."
    echo "=========================================="
    
    pytest "$SCRIPT_DIR/test_consistency.py" \
        -v \
        --html="$REPORTS_DIR/consistency-report.html" \
        --self-contained-html \
        --alluredir="$REPORTS_DIR/allure-results" \
        -m consistency
}

run_smoke_tests() {
    echo "=========================================="
    echo "运行冒烟测试..."
    echo "=========================================="
    
    pytest "$SCRIPT_DIR" \
        -v \
        --html="$REPORTS_DIR/smoke-report.html" \
        --self-contained-html \
        --alluredir="$REPORTS_DIR/allure-results" \
        -m smoke
}

run_regression_tests() {
    echo "=========================================="
    echo "运行完整回归测试..."
    echo "=========================================="
    
    pytest "$SCRIPT_DIR" \
        -v \
        --html="$REPORTS_DIR/regression-report.html" \
        --self-contained-html \
        --alluredir="$REPORTS_DIR/allure-results"
}

run_all_tests() {
    echo "=========================================="
    echo "运行所有测试..."
    echo "=========================================="
    
    pytest "$SCRIPT_DIR" \
        -v \
        --html="$REPORTS_DIR/full-report.html" \
        --self-contained-html \
        --alluredir="$REPORTS_DIR/allure-results"
}

generate_allure_report() {
    echo "=========================================="
    echo "生成 Allure 报告..."
    echo "=========================================="
    
    if command -v allure &> /dev/null; then
        allure generate "$REPORTS_DIR/allure-results" \
            -o "$REPORTS_DIR/allure-report" \
            --clean
        echo "Allure 报告已生成: $REPORTS_DIR/allure-report"
    else
        echo "Allure 未安装，跳过报告生成"
        echo "安装: npm install -g allure-commandline"
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "测试完成!"
    echo "=========================================="
    echo "HTML 报告: $REPORTS_DIR/*.html"
    echo "Allure 报告: $REPORTS_DIR/allure-report"
    echo ""
}

cd "$PROJECT_DIR"

case "${1:-all}" in
    api)
        run_api_tests
        ;;
    ui)
        run_ui_tests
        ;;
    consistency)
        run_consistency_tests
        ;;
    smoke)
        run_smoke_tests
        ;;
    regression)
        run_regression_tests
        ;;
    all)
        run_all_tests
        ;;
    *)
        echo "未知参数: $1"
        echo "用法: $0 [api|ui|consistency|smoke|regression|all]"
        exit 1
        ;;
esac

generate_allure_report
print_summary
