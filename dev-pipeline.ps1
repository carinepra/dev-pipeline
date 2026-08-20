# Wrapper Windows para comandos do dev-pipeline (equivalente ao make)
# Uso: .\dev-pipeline.ps1 list
#      .\dev-pipeline.ps1 start -Story PROJ-542
#      .\dev-pipeline.ps1 start -Task NEW -Story PROJ-542

param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "help", "list", "list-stories", "list-tasks", "start", "resume",
        "status", "next", "previous", "goto", "cancel", "finalize",
        "validate", "unlock", "sync-skills"
    )]
    [string]$Command = "help",

    [string]$Story,
    [string]$Task,
    [string]$State,
    [string]$Stage,
    [switch]$DryRun
)

$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Cli = Join-Path $ProjectRoot "cli\main.py"

if (-not (Test-Path $Python)) {
    Write-Error "venv nao encontrado. Execute: python -m venv venv && .\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt"
    exit 1
}

$env:PYTHONPATH = $ProjectRoot
$env:PYTHONIOENCODING = "utf-8"

function Invoke-PipelineCli {
    param([string[]]$CliArgs)
    & $Python $Cli @CliArgs
    exit $LASTEXITCODE
}

switch ($Command) {
    "help" {
        Write-Host @"
dev-pipeline.ps1 — comandos disponiveis

  .\dev-pipeline.ps1 list [-Story KEY] [-State STATE]
  .\dev-pipeline.ps1 start -Story PROJ-542
  .\dev-pipeline.ps1 start -Task PROJ-645
  .\dev-pipeline.ps1 start -Task NEW
  .\dev-pipeline.ps1 start -Task NEW -Story PROJ-542
  .\dev-pipeline.ps1 resume -Story PROJ-542
  .\dev-pipeline.ps1 resume -Task PROJ-645
  .\dev-pipeline.ps1 status [-Story KEY] [-Task KEY]
  .\dev-pipeline.ps1 next [-Story KEY] [-Task KEY]
  .\dev-pipeline.ps1 previous [-Story KEY] [-Task KEY]
  .\dev-pipeline.ps1 goto -Story PROJ-542 -Stage story_analysis
  .\dev-pipeline.ps1 cancel -Story PROJ-542
  .\dev-pipeline.ps1 finalize -Story PROJ-542
  .\dev-pipeline.ps1 validate -Story PROJ-542
  .\dev-pipeline.ps1 unlock -Task PROJ-645
  .\dev-pipeline.ps1 sync-skills
"@
        exit 0
    }

    "list" {
        $args = @("list")
        if ($Story) { $args += @("--story", $Story) }
        if ($State) { $args += @("--state", $State) }
        Invoke-PipelineCli $args
    }

    "list-stories" { Invoke-PipelineCli @("list-stories") }
    "list-tasks" {
        $args = @("list-tasks")
        if ($Story) { $args += @("--story", $Story) }
        if ($State) { $args += @("--state", $State) }
        Invoke-PipelineCli $args
    }

    "start" {
        $args = @("start")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        if (-not $Story -and -not $Task) {
            Write-Error "Informe -Story ou -Task. Ex: .\dev-pipeline.ps1 start -Story PROJ-542"
            exit 1
        }
        Invoke-PipelineCli $args
    }

    "resume" {
        $args = @("resume")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "status" {
        $args = @("status")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "next" {
        $args = @("next")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "previous" {
        $args = @("previous")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "goto" {
        if (-not $Stage) {
            Write-Error "Informe -Stage. Ex: .\dev-pipeline.ps1 goto -Story PROJ-542 -Stage story_analysis"
            exit 1
        }
        $args = @("goto", "--stage", $Stage)
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "cancel" {
        $args = @("cancel")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "finalize" {
        $args = @("finalize")
        if ($Story) { $args += @("--story", $Story) }
        Invoke-PipelineCli $args
    }

    "validate" {
        $args = @("validate")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "unlock" {
        $args = @("unlock")
        if ($Story) { $args += @("--story", $Story) }
        if ($Task) { $args += @("--task", $Task) }
        Invoke-PipelineCli $args
    }

    "sync-skills" {
        $skillsDir = Join-Path $env:USERPROFILE ".cursor\skills"
        New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
        Get-ChildItem (Join-Path $ProjectRoot "skills\pipeline-*") -Directory | ForEach-Object {
            $target = Join-Path $skillsDir $_.Name
            New-Item -ItemType Directory -Force -Path $target | Out-Null
            Copy-Item (Join-Path $_.FullName "SKILL.md") (Join-Path $target "SKILL.md") -Force
            Write-Host "Sincronizado: $($_.Name)"
        }
        exit 0
    }
}
