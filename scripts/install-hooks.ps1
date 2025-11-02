# Install git hooks for WomCast (Windows PowerShell)

$ErrorActionPreference = "Stop"

$HookDir = ".git\hooks"

Write-Host "Installing git hooks..." -ForegroundColor Cyan

# Copy PowerShell hook as the main pre-commit
Copy-Item "$HookDir\pre-commit.ps1" "$HookDir\pre-commit" -Force

Write-Host "✓ Git hooks installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "The following hooks are now active:"
Write-Host "  - pre-commit: Runs linting and type checks before commit"
Write-Host ""
Write-Host "To bypass hooks (not recommended), use: git commit --no-verify" -ForegroundColor Yellow
