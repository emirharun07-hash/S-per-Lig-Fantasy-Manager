# Render the AZUR scene on a Windows PC with a graphics card: Cycles via HIP (AMD Radeon RX 6000 and newer),
# OptiX/CUDA (NVIDIA). Falls back to the CPU if no supported card is found (the queue log says which device it used).
#
# In PowerShell, inside the cloned repo:
#   powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1          everything still missing
#   powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1 moves    only the camera moves
#   powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1 queue    only view plates and passes
#   powershell -ExecutionPolicy Bypass -File azur\tools\render_on_windows.ps1 test     set up + one timed test render
#
# Needs: Git for Windows (git-scm.com; its credential manager opens a browser for the GitHub login on the first push)
# and a current AMD Adrenalin driver. First run installs uv, Python 3.11 and Blender's Python module into azur\.venv
# (about 1 GB) and downloads the CC0 textures (about 300 MB). Finished outputs are skipped; every new output is
# committed and pushed like the cloud renders. Do not let the cloud render the same job at the same time.
param([string]$Mode = "all")
$ErrorActionPreference = "Stop"
Set-Location (git rev-parse --show-toplevel)
$Branch = "claude/shopify-notification-signup-o5avym"
git fetch -q origin $Branch
git checkout -q $Branch
git pull -q --rebase origin $Branch
if (-not (git config user.email)) {
  Write-Host "git kennt dich noch nicht. Einmal ausfuehren (deine private GitHub-E-Mail):"
  Write-Host '  git config --global user.name "Dein Name"; git config --global user.email "deine@mail.de"'
  exit 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
if (-not (Test-Path "azur\.venv")) { uv venv -q -p 3.11 azur\.venv }
. "azur\.venv\Scripts\Activate.ps1"
uv pip install -q bpy==5.0.1 numpy pillow scikit-image scipy imageio-ffmpeg

$env:AZUR_GPU = "1"
$ErrorActionPreference = "Continue"
if ($Mode -eq "test") {
  python azur\scene\bench.py
  Select-String -Path "azur\.cache\queue.log" -Pattern "render device|bench:" | Select-Object -Last 2
  exit 0
}
switch ($Mode) {
  "queue" { python azur\scene\render_queue.py }
  "moves" { python azur\scene\render_moves.py }
  default { python azur\scene\render_queue.py; if ($LASTEXITCODE -eq 0) { python azur\scene\render_moves.py } }
}
Select-String -Path "azur\.cache\queue.log" -Pattern "render device" | Select-Object -Last 1

# anything a failed push left behind (e.g. before the GitHub login was set up)
git add azur/prototype/assets
git commit -q -m "AZUR renders from the PC"
git pull -q --rebase origin $Branch
git push -q origin "HEAD:$Branch"
if ($LASTEXITCODE -eq 0) { Write-Host "Alles hochgeladen." }
