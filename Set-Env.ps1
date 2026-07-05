# Function to load .env file
function Import-EnvFile {
    if (-not (Test-Path '.env')) {
        Write-Host "Error: .env file not found."
        Write-Host "Please create a .env file with VAR_NAME=value pairs."
        return $false
    }

    Get-Content '.env' | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) {
            return
        }

        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) {
            return
        }

        $name = $parts[0].Trim()
        if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            return
        }

        $value = $parts[1].Trim()
        if ($value -match '\s#') {
            $value = ($value -split '\s#', 2)[0].Trim()
        }
        if (($value.StartsWith("'") -and $value.EndsWith("'")) -or ($value.StartsWith('"') -and $value.EndsWith('"'))) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        [System.Environment]::SetEnvironmentVariable($name, $value)
    }

    Write-Host "Environment variables from .env have been set."
    return $true
}
# Function to activate the virtual environment if it exists
function Enable-VirtualEnvironment {
    if (Test-Path '.venv\Scripts\Activate.ps1') {
        Write-Host "Activated virtual environment found at .venv\Scripts\Activate.ps1"
        . '.venv\Scripts\Activate.ps1'
    }
}

# Main execution
Enable-VirtualEnvironment
Import-EnvFile
