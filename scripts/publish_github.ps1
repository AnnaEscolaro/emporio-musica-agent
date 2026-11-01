# Cria repositório público no GitHub e faz push (requer: gh auth login)
$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    Write-Error "Instale o GitHub CLI: winget install GitHub.cli"
}
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

& $gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Faça login: gh auth login -h github.com -p https -w"
    Write-Host "Ou abra https://github.com/login/device e use o código exibido pelo gh."
    exit 1
}

$remote = git remote get-url origin 2>$null
if (-not $remote) {
    & $gh repo create emporio-musica-agent --public --source=. --remote=origin --push
} else {
    git push -u origin master
}

Write-Host "Pronto. URL:" (& $gh repo view --json url -q .url)
