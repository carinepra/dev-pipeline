# Ativa o ambiente dev-pipeline no Windows (PowerShell)
# Uso: . .\activate.ps1

$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$VenvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv nao encontrado. Execute primeiro: python -m venv venv"
    return
}

# Ativar venv
& $VenvActivate

# Variaveis do projeto
$env:PYTHONPATH = $ProjectRoot
$env:PYTHONIOENCODING = "utf-8"
$env:DEV_PIPELINE_ROOT = $ProjectRoot

# Python global no PATH da sessao (se instalado em AppData)
$PythonRoot = "$env:LOCALAPPDATA\Programs\Python\Python313"
if (Test-Path $PythonRoot) {
    $pathsToAdd = @(
        $PythonRoot
        (Join-Path $PythonRoot "Scripts")
        (Join-Path $ProjectRoot "venv\Scripts")
    )
    foreach ($p in $pathsToAdd) {
        if ($env:PATH -notlike "*$p*") {
            $env:PATH = "$p;$env:PATH"
        }
    }
}

# UTF-8 no console (evita erro de emoji no Rich)
try {
    chcp 65001 | Out-Null
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Ignora se o terminal nao suportar
}

Write-Host "Ambiente dev-pipeline ativado!" -ForegroundColor Green
Write-Host ""
Write-Host "Comandos rapidos:"
Write-Host "  .\dev-pipeline.ps1 list"
Write-Host "  .\dev-pipeline.ps1 start -Story PROJ-123"
Write-Host "  .\dev-pipeline.ps1 start -Task PROJ-456"
Write-Host "  .\dev-pipeline.ps1 help"
Write-Host ""
