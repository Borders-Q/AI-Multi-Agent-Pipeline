param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PipIndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple"
$NpmRegistry = "https://mirrors.tuna.tsinghua.edu.cn/npm/"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $ProjectRoot "frontend"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$BookManagerRequirements = Join-Path $ProjectRoot "book_manager\book_manager\requirements.txt"

$PythonPackages = @(
    "fastapi",
    "uvicorn[standard]",
    "pymysql",
    "openai",
    "requests",
    "aiohttp",
    "python-dotenv",
    "cryptography",
    "psutil",
    "pydantic",
    "playwright",
    "torch",
    "transformers",
    "flask",
    "jinja2"
)

function Write-Title {
    param([string]$Text)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor DarkCyan
}

function Invoke-InstallStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host ""
    Write-Host ">>> $Name" -ForegroundColor Yellow
    if ($DryRun) {
        Write-Host "[DryRun] skipped." -ForegroundColor DarkYellow
        return
    }

    & $Action
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $FilePath $($Arguments -join ' ')"
    }
}

function Get-RequiredCommand {
    param([string[]]$Names)

    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw "Missing command: $($Names -join ' or '). Install it and make sure it is available in PATH."
}

function Get-PreferredPython {
    if ($env:SKYT_PYTHON -and (Test-Path $env:SKYT_PYTHON)) {
        return (Resolve-Path $env:SKYT_PYTHON).Path
    }

    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    $commonPythonPaths = @(
        (Join-Path $localAppData "Programs\Python\Python312\python.exe"),
        (Join-Path $localAppData "Programs\Python\Python311\python.exe"),
        (Join-Path $localAppData "Programs\Python\Python313\python.exe"),
        (Join-Path $localAppData "Programs\Python\Python310\python.exe"),
        (Join-Path $localAppData "Programs\Python\Python39\python.exe"),
        (Join-Path $localAppData "Programs\Python\Python314\python.exe")
    )
    foreach ($candidate in $commonPythonPaths) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $preferredVersions = @("3.12", "3.11", "3.13", "3.10", "3.9", "3.14")
        foreach ($version in $preferredVersions) {
            $candidate = $null
            try {
                $candidate = & $pyLauncher.Source "-$version" -c "import sys; print(sys.executable)" 2>$null
            } catch {
                continue
            }
            if ($LASTEXITCODE -eq 0 -and $candidate -and (Test-Path $candidate)) {
                $actualVersion = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($actualVersion -ne $version) {
                    continue
                }
                return (Resolve-Path $candidate).Path
            }
        }
    }

    return Get-RequiredCommand @("python")
}

Write-Title "Ai Multi Agent dependency installer"
Write-Host "Project root: $ProjectRoot"
Write-Host "pip index: $PipIndexUrl"
Write-Host "npm registry: $NpmRegistry"

$SystemPython = Get-PreferredPython
$NodeExe = Get-RequiredCommand @("node")
$NpmExe = Get-RequiredCommand @("npm.cmd", "npm")

Write-Host "Python: $SystemPython"
Write-Host "Node.js: $NodeExe"
Write-Host "npm: $NpmExe"

$env:PIP_INDEX_URL = $PipIndexUrl
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PIP_NO_INPUT = "1"
$env:npm_config_registry = $NpmRegistry

Invoke-InstallStep "Create or reuse .venv" {
    if (Test-Path $VenvPython) {
        Write-Host "Existing virtual environment: $VenvDir" -ForegroundColor Green
    } else {
        Invoke-Native -FilePath $SystemPython -Arguments @("-m", "venv", $VenvDir)
        Write-Host "Created virtual environment: $VenvDir" -ForegroundColor Green
    }
}

if ($DryRun) {
    $EffectivePython = $VenvPython
} else {
    if (-not (Test-Path $VenvPython)) {
        throw "Virtual environment Python not found: $VenvPython"
    }
    $EffectivePython = $VenvPython
}

Invoke-InstallStep "Upgrade pip, setuptools and wheel from Tsinghua source" {
    Invoke-Native -FilePath $EffectivePython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "--index-url", $PipIndexUrl)
}

Invoke-InstallStep "Install backend Python packages from Tsinghua source" {
    $arguments = @("-m", "pip", "install") + $PythonPackages + @("--index-url", $PipIndexUrl)
    Invoke-Native -FilePath $EffectivePython -Arguments $arguments
}

Invoke-InstallStep "Install book_manager requirements from Tsinghua source" {
    if (Test-Path $BookManagerRequirements) {
        Invoke-Native -FilePath $EffectivePython -Arguments @("-m", "pip", "install", "-r", $BookManagerRequirements, "--index-url", $PipIndexUrl)
    } else {
        Write-Host "requirements.txt not found, skipped: $BookManagerRequirements" -ForegroundColor DarkYellow
    }
}

Invoke-InstallStep "Install frontend npm packages from Tsinghua source" {
    if (-not (Test-Path $FrontendDir)) {
        throw "Frontend directory not found: $FrontendDir"
    }

    $packageLock = Join-Path $FrontendDir "package-lock.json"
    $originalPackageLock = $null
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    if (Test-Path $packageLock) {
        $originalPackageLock = [System.IO.File]::ReadAllText($packageLock)
        $rewrittenPackageLock = $originalPackageLock.
            Replace("https://registry.npmjs.org/", $NpmRegistry).
            Replace("http://registry.npmjs.org/", $NpmRegistry).
            Replace("https://registry.npmmirror.com/", $NpmRegistry).
            Replace("http://registry.npmmirror.com/", $NpmRegistry)

        if ($rewrittenPackageLock -ne $originalPackageLock) {
            Write-Host "Temporarily rewriting package-lock resolved URLs to the Tsinghua npm source." -ForegroundColor DarkYellow
            [System.IO.File]::WriteAllText($packageLock, $rewrittenPackageLock, $utf8NoBom)
        } else {
            $originalPackageLock = $null
        }
    }

    Push-Location $FrontendDir
    try {
        if (Test-Path (Join-Path $FrontendDir "package-lock.json")) {
            Invoke-Native -FilePath $NpmExe -Arguments @("ci", "--registry", $NpmRegistry)
        } else {
            Invoke-Native -FilePath $NpmExe -Arguments @("install", "--registry", $NpmRegistry)
        }
    } finally {
        Pop-Location
        if ($originalPackageLock -ne $null) {
            [System.IO.File]::WriteAllText($packageLock, $originalPackageLock, $utf8NoBom)
            Write-Host "Restored original package-lock.json." -ForegroundColor DarkGray
        }
    }
}

Write-Host ""
Write-Host "Playwright Python package is installed by pip from the Tsinghua source." -ForegroundColor Yellow
Write-Host "Playwright browser binaries are not downloaded automatically." -ForegroundColor Yellow
Write-Host "Reason: no confirmed Tsinghua PLAYWRIGHT_DOWNLOAD_HOST is configured, and this script must not silently use a foreign source." -ForegroundColor Yellow

Write-Title "Dependency installation flow completed"
if ($DryRun) {
    Write-Host "DryRun completed. No dependencies were installed." -ForegroundColor Green
} else {
    Write-Host "Python virtual environment: $VenvDir" -ForegroundColor Green
    Write-Host "Frontend dependency directory: $(Join-Path $FrontendDir "node_modules")" -ForegroundColor Green
    Write-Host "You can now start the project from the repository root." -ForegroundColor Green
}
