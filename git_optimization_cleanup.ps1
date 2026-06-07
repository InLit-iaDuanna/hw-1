# Git 优化清理脚本
# 移除不应被跟踪的 ABAQUS 文件
# 执行时间: 2026-06-05

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git 优化清理脚本 - hw-1 项目" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 检查工作目录
$expectedPath = "D:\Dunna\Documents\hw-1"
$currentPath = Get-Location

if ($currentPath.Path -ne $expectedPath) {
    Write-Host "错误: 请在项目根目录运行此脚本" -ForegroundColor Red
    Write-Host "当前目录: $currentPath" -ForegroundColor Yellow
    Write-Host "期望目录: $expectedPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ 工作目录正确" -ForegroundColor Green
Write-Host ""

# 2. 检查是否有未提交的更改
Write-Host "检查 Git 状态..." -ForegroundColor Cyan
$gitStatus = git status --short
if ($gitStatus) {
    Write-Host "警告: 发现未提交的更改" -ForegroundColor Yellow
    Write-Host $gitStatus
    $continue = Read-Host "是否继续? (y/N)"
    if ($continue -ne 'y') {
        Write-Host "已取消操作" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""

# 3. 移除 ABAQUS 敏感环境文件
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "移除 ABAQUS 敏感文件" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$filesToRemove = @(
    "fea_heel_strike/out/Job_HeelStrike.env"
)

foreach ($file in $filesToRemove) {
    if (Test-Path $file) {
        Write-Host "移除跟踪: $file" -ForegroundColor Yellow
        git rm --cached $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ 已从 Git 移除（本地文件保留）" -ForegroundColor Green
        } else {
            Write-Host "  ℹ 文件未被跟踪或已移除" -ForegroundColor Gray
        }
    } else {
        Write-Host "跳过: $file (文件不存在)" -ForegroundColor Gray
    }
}

Write-Host ""

# 4. 可选: 移除 ABAQUS 输出文件（.odb, .prt）
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ABAQUS 输出文件处理" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$abaqusFiles = @(
    "fea_heel_strike/out/Job_HeelStrike.odb",
    "fea_heel_strike/out/Job_HeelStrike.prt",
    "fea_heel_strike/out/Job_HeelStrike_TPU.odb",
    "fea_heel_strike/out/Job_HeelStrike_TPU.prt"
)

Write-Host "发现 $($abaqusFiles.Count) 个 ABAQUS 输出文件已被跟踪" -ForegroundColor Yellow
Write-Host ""
Write-Host "这些文件是 ABAQUS 仿真结果，通常较大且可重现生成。" -ForegroundColor Yellow
Write-Host "建议: 从 Git 移除，保留本地文件，需要时可重新生成。" -ForegroundColor Yellow
Write-Host ""

$removeAbaqus = Read-Host "是否移除这些文件的 Git 跟踪? (y/N)"

if ($removeAbaqus -eq 'y') {
    foreach ($file in $abaqusFiles) {
        Write-Host "移除跟踪: $file" -ForegroundColor Yellow
        git rm --cached $file 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ 已从 Git 移除（本地文件保留）" -ForegroundColor Green
        }
    }
    Write-Host ""
    Write-Host "✓ ABAQUS 文件已移除跟踪" -ForegroundColor Green
} else {
    Write-Host "已跳过 ABAQUS 文件移除" -ForegroundColor Gray
}

Write-Host ""

# 5. 暂存新配置文件
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "暂存新配置文件" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$newFiles = @(
    ".gitignore",
    ".gitattributes",
    "GIT_WORKFLOW.md",
    "GIT_OPTIMIZATION_REPORT.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/version_request.md",
    ".github/PULL_REQUEST_TEMPLATE.md"
)

foreach ($file in $newFiles) {
    if (Test-Path $file) {
        git add $file
        Write-Host "✓ 已暂存: $file" -ForegroundColor Green
    } else {
        Write-Host "⚠ 文件不存在: $file" -ForegroundColor Yellow
    }
}

Write-Host ""

# 6. 显示即将提交的更改
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "即将提交的更改" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

git status --short

Write-Host ""

# 7. 提示提交
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "下一步操作" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "建议的提交命令:" -ForegroundColor Yellow
Write-Host ""
Write-Host @"
git commit -m "chore: optimize Git configuration and workflow

- Update .gitignore to exclude ABAQUS output and data files
- Add .gitattributes for line endings and Git LFS configuration
- Add comprehensive Git workflow documentation (GIT_WORKFLOW.md)
- Add optimization report (GIT_OPTIMIZATION_REPORT.md)
- Add Issue and PR templates for better collaboration
- Remove sensitive ABAQUS env file from tracking
- Remove ABAQUS output files (.odb, .prt) from tracking

This optimization improves repository hygiene and establishes
clear collaboration guidelines for the team.
"
"@ -ForegroundColor Cyan

Write-Host ""
Write-Host "执行提交? (y/N)" -ForegroundColor Yellow
$doCommit = Read-Host

if ($doCommit -eq 'y') {
    git commit -m @"
chore: optimize Git configuration and workflow

- Update .gitignore to exclude ABAQUS output and data files
- Add .gitattributes for line endings and Git LFS configuration
- Add comprehensive Git workflow documentation (GIT_WORKFLOW.md)
- Add optimization report (GIT_OPTIMIZATION_REPORT.md)
- Add Issue and PR templates for better collaboration
- Remove sensitive ABAQUS env file from tracking
- Remove ABAQUS output files (.odb, .prt) from tracking

This optimization improves repository hygiene and establishes
clear collaboration guidelines for the team.
"@

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ 提交成功!" -ForegroundColor Green
        Write-Host ""
        Write-Host "下一步建议:" -ForegroundColor Cyan
        Write-Host "1. 审查提交: git show HEAD" -ForegroundColor White
        Write-Host "2. 推送到远程: git push origin <branch-name>" -ForegroundColor White
        Write-Host "3. 安装 pre-commit hooks: pre-commit install" -ForegroundColor White
        Write-Host "4. 考虑初始化 Git LFS (参见 GIT_OPTIMIZATION_REPORT.md)" -ForegroundColor White
    } else {
        Write-Host ""
        Write-Host "✗ 提交失败，请检查错误信息" -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "已跳过提交，你可以稍后手动提交" -ForegroundColor Gray
    Write-Host "使用以上提供的提交信息，或根据需要修改" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "清理脚本执行完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "详细优化报告: GIT_OPTIMIZATION_REPORT.md" -ForegroundColor Yellow
Write-Host "工作流文档: GIT_WORKFLOW.md" -ForegroundColor Yellow
Write-Host ""
