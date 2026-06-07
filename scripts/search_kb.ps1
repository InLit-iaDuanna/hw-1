# Knowledge Base Search Script
# 在知识库中搜索关键词

param(
    [Parameter(Mandatory=$true)]
    [string]$keyword,

    [Parameter(Mandatory=$false)]
    [int]$context = 1,

    [Parameter(Mandatory=$false)]
    [switch]$caseSensitive
)

$kb_path = "D:\Dunna\Documents\hw-1\knowledge_base"

Write-Host "`n=== Searching for '$keyword' in Knowledge Base ===" -ForegroundColor Green
Write-Host "Path: $kb_path" -ForegroundColor Gray
Write-Host "Context lines: $context`n" -ForegroundColor Gray

# 搜索参数
$searchParams = @{
    Path = $kb_path
    Recurse = $true
    Include = "*.md"
    Pattern = $keyword
    Context = $context
}

if (-not $caseSensitive) {
    $searchParams.Add('CaseSensitive', $false)
}

# 执行搜索
$results = Get-ChildItem -Path $kb_path -Recurse -Include "*.md" |
    Select-String -Pattern $keyword -Context $context

if ($results.Count -eq 0) {
    Write-Host "No results found for '$keyword'" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($results.Count) match(es):`n" -ForegroundColor Cyan

# 按文件分组显示
$groupedResults = $results | Group-Object -Property Path

foreach ($group in $groupedResults) {
    $relativePath = $group.Name -replace [regex]::Escape($kb_path), "knowledge_base"
    Write-Host "--- $relativePath ---" -ForegroundColor Yellow

    foreach ($match in $group.Group) {
        Write-Host "  Line $($match.LineNumber):" -ForegroundColor Cyan

        # 显示上下文
        if ($context -gt 0 -and $match.Context) {
            foreach ($line in $match.Context.PreContext) {
                Write-Host "    $line" -ForegroundColor DarkGray
            }
        }

        # 高亮匹配行
        $highlightedLine = $match.Line -replace "($keyword)", "`e[93m`$1`e[0m"
        Write-Host "  > $highlightedLine" -ForegroundColor White

        if ($context -gt 0 -and $match.Context) {
            foreach ($line in $match.Context.PostContext) {
                Write-Host "    $line" -ForegroundColor DarkGray
            }
        }

        Write-Host ""
    }
    Write-Host ""
}

Write-Host "=== Search completed ===" -ForegroundColor Green
Write-Host "Total matches: $($results.Count)" -ForegroundColor Cyan
