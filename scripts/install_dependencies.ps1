param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PipIndexUrl = "https://pypi.tuna.tsinghua.edu.cn/simple"
$NpmRegistry = "https://mirrors.tuna.tsinghua.edu.cn/npm/"
$PythonBootstrapVersion = "3.12.10"
$PythonBootstrapUrl = "https://mirrors.tuna.tsinghua.edu.cn/python/$PythonBootstrapVersion/python-$PythonBootstrapVersion-amd64.exe"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $ProjectRoot "frontend"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$LocalPythonDir = Join-Path $ProjectRoot ".python"
$LocalPython = Join-Path $LocalPythonDir "python.exe"
$InstallerCacheDir = Join-Path $ProjectRoot ".installer-cache"
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

function Test-IsWindowsAppsAlias {
    param([string]$Path)

    if (-not $Path) {
        return $false
    }

    return $Path -like "*\Microsoft\WindowsApps\*"
}

function Test-RealPython {
    param([string]$Path)

    if (-not $Path -or -not (Test-Path $Path) -or (Test-IsWindowsAppsAlias $Path)) {
        return $false
    }

    try {
        $resolved = (Resolve-Path $Path).Path
        $probe = & $resolved -c "import sys, venv, ensurepip; print(sys.executable); print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $probe -or $probe.Count -lt 2) {
            return $false
        }

        $versionText = [string]$probe[1]
        $version = [Version]$versionText
        if ($version.Major -ne 3 -or $version.Minor -lt 9 -or $version.Minor -gt 13) {
            return $false
        }

        return $true
    } catch {
        return $false
    }
}

function Resolve-RealPythonPath {
    param([string]$Path)

    if (Test-RealPython $Path) {
        return (Resolve-Path $Path).Path
    }

    return $null
}

function Install-LocalPythonFromTsinghua {
    if (Test-RealPython $LocalPython) {
        return (Resolve-Path $LocalPython).Path
    }

    Write-Host "No usable Python 3.9-3.13 was found. Installing local Python $PythonBootstrapVersion from Tsinghua mirror." -ForegroundColor Yellow
    Write-Host "Python source: $PythonBootstrapUrl" -ForegroundColor DarkYellow

    New-Item -ItemType Directory -Path $InstallerCacheDir -Force | Out-Null
    New-Item -ItemType Directory -Path $LocalPythonDir -Force | Out-Null

    $installer = Join-Path $InstallerCacheDir "python-$PythonBootstrapVersion-amd64.exe"
    if (-not (Test-Path $installer)) {
        Invoke-WebRequest -Uri $PythonBootstrapUrl -OutFile $installer
    } else {
        Write-Host "Reusing cached Python installer: $installer" -ForegroundColor DarkGray
    }

    $arguments = @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$LocalPythonDir",
        "Include_launcher=0",
        "Include_test=0",
        "Include_pip=1",
        "Include_tcltk=0",
        "PrependPath=0",
        "Shortcuts=0"
    )

    Invoke-Native -FilePath $installer -Arguments $arguments
    if (-not (Test-RealPython $LocalPython)) {
        throw "Local Python installation failed or is not usable: $LocalPython"
    }

    return (Resolve-Path $LocalPython).Path
}

function Get-PreferredPython {
    param([bool]$AllowBootstrap = $true)

    if ($env:SKYT_PYTHON) {
        $envPython = Resolve-RealPythonPath $env:SKYT_PYTHON
        if ($envPython) {
            return $envPython
        }
        Write-Host "SKYT_PYTHON is set but is not a usable Python 3.9-3.13 executable: $env:SKYT_PYTHON" -ForegroundColor DarkYellow
    }

    $projectPython = Resolve-RealPythonPath $LocalPython
    if ($projectPython) {
        return $projectPython
    }

    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    $candidatePaths = New-Object System.Collections.Generic.List[string]
    $searchRoots = @(
        (Join-Path $localAppData "Programs\Python"),
        "C:\Program Files\Python",
        "C:\Program Files (x86)\Python",
        "C:\",
        "D:\"
    )

    foreach ($root in $searchRoots) {
        if (Test-Path $root) {
            Get-ChildItem -Path $root -Directory -Filter "Python*" -ErrorAction SilentlyContinue |
                ForEach-Object {
                    $candidatePaths.Add((Join-Path $_.FullName "python.exe"))
                }
        }
    }

    foreach ($name in @("python", "python3")) {
        $commands = Get-Command $name -All -ErrorAction SilentlyContinue
        foreach ($command in $commands) {
            $candidatePaths.Add($command.Source)
        }
    }

    $preferredOrder = @("Python312", "Python311", "Python310", "Python313", "Python39")
    $orderedCandidates = $candidatePaths |
        Where-Object { $_ } |
        Select-Object -Unique |
        Sort-Object {
            $path = $_
            $rank = 99
            for ($i = 0; $i -lt $preferredOrder.Count; $i++) {
                if ($path -like "*$($preferredOrder[$i])*") {
                    $rank = $i
                    break
                }
            }
            $rank
        }, { $_ }

    foreach ($candidate in $orderedCandidates) {
        $realPython = Resolve-RealPythonPath $candidate
        if ($realPython) {
            return $realPython
        }
    }

    $pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyLauncher -and -not (Test-IsWindowsAppsAlias $pyLauncher.Source)) {
        $preferredVersions = @("3.12", "3.11", "3.10", "3.13", "3.9")
        foreach ($version in $preferredVersions) {
            $candidate = $null
            try {
                $candidate = & $pyLauncher.Source "-$version" -c "import sys; print(sys.executable)" 2>$null
            } catch {
                continue
            }
            $realPython = Resolve-RealPythonPath $candidate
            if ($LASTEXITCODE -eq 0 -and $realPython) {
                return $realPython
            }
        }
    }

    if ($AllowBootstrap) {
        return Install-LocalPythonFromTsinghua
    }

    throw "No usable Python 3.9-3.13 was found. Run without -DryRun to bootstrap local Python from the Tsinghua mirror."
}

Write-Title "天韬（SkyT） dependency installer"
Write-Host "Project root: $ProjectRoot"
Write-Host "pip index: $PipIndexUrl"
Write-Host "npm registry: $NpmRegistry"
Write-Host "Python bootstrap source: $PythonBootstrapUrl"

$SystemPython = Get-PreferredPython -AllowBootstrap (-not $DryRun)
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
