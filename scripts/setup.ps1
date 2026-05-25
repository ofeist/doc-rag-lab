param(
    [switch]$Rag
)

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvDir = Join-Path $RootDir ".venv"

function Get-PythonCommand {
    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @("py", "-3")
    }

    $python = Get-Command "python" -ErrorAction SilentlyContinue
    if ($python) {
        return @("python")
    }

    $python3 = Get-Command "python3" -ErrorAction SilentlyContinue
    if ($python3) {
        return @("python3")
    }

    throw "Python 3 was not found on PATH."
}

$PythonCommand = Get-PythonCommand
$PythonExe = $PythonCommand[0]
$PythonArgs = @()
if ($PythonCommand.Length -gt 1) {
    $PythonArgs = $PythonCommand[1..($PythonCommand.Length - 1)]
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment: $VenvDir"
    & $PythonExe @PythonArgs -m venv $VenvDir
}
else {
    Write-Host "Virtual environment already exists: $VenvDir"
}

$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    throw "Could not find activation script: $ActivateScript"
}

. $ActivateScript

python -m pip install --upgrade pip
python -m pip install -r (Join-Path $RootDir "requirements.txt")

if ($Rag) {
    python -m pip install -r (Join-Path $RootDir "requirements-rag.txt")
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Activate with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
if (-not $Rag) {
    Write-Host ""
    Write-Host "RAG dependencies were not installed."
    Write-Host "Install them later with:"
    Write-Host "  .\scripts\setup.ps1 -Rag"
}
Write-Host ""
Write-Host "Example:"
Write-Host "  python scripts\extract_pages.py docs\infineon-aurix-tc3xx-part1-usermanual-en.pdf --max-pages 20"
