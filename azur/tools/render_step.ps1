# One round of the PC's watch mode. render_on_windows.ps1 watch pulls the branch and runs this file every 2 minutes;
# it is read fresh each time, so changes pushed to the branch apply without restarting the window.
#
# azur/render_request.json (written by the cloud session):
#   { "id": "r3-a", "note": "...", "set": "scene3", "rebuild": true, "jobs": ["preview", "queue", "moves"] }
#   jobs: preview (quick look, azur/previews), queue (plates, passes, masks, times of day), moves (camera flights),
#         export (jersey models for the product view); "queue:room,bed" passes arguments.
#   rebuild: build the scene again and drop that set's earlier outputs (they belong to the old scene).
#   redo: outputs to delete first so they render again, as patterns in the set's folder ("views/*/masks*.png").
# A request runs once (its id is remembered in azur/.cache/render_request_done.txt). A newer request stops a running
# one between two renders. What the PC is doing goes to azur/render_status.json (pushed), so the cloud can see it.
param([switch]$Hello)
$ErrorActionPreference = "Continue"
$env:AZUR_NO_HANDOVER = "1"
$Branch = "claude/shopify-notification-signup-o5avym"
$Trailer = "`n`nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`nClaude-Session: https://claude.ai/code/session_01R3wWJYBEPWenzksQTM89FE"
$Cache = "azur\.cache"
$DoneFile = "$Cache\render_request_done.txt"
$JobLog = "$Cache\job.log"
$Version = 2
New-Item -ItemType Directory -Force -Path $Cache | Out-Null

function Write-Status($State, $ReqId, $Job, $Note) {
  $tail = @()
  if (Test-Path $JobLog) {
    $tail = @(Get-Content $JobLog -Tail 400 | Where-Object { $_ -notmatch "Blender create|glTF import|DeprecationWarning|use_nodes|^\s*$|Fra:|Sample \d" } | Select-Object -Last 30)
  }
  $dev = ""
  if (Test-Path "$Cache\queue.log") {
    $m = Select-String -Path "$Cache\queue.log" -Pattern "render device" | Select-Object -Last 1
    if ($m) { $dev = $m.Line }
  }
  $s = [ordered]@{ state = $State; request = $ReqId; job = $Job; note = $Note; watch = $Version
                   time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"); device = $dev; log = $tail }
  $path = Join-Path (Get-Location) "azur\render_status.json"
  [System.IO.File]::WriteAllText($path, ($s | ConvertTo-Json -Depth 4))
}

function Push-All($Msg) {
  foreach ($p in @("azur/prototype/assets", "azur/previews", "azur/render_status.json")) {
    if (Test-Path $p) { git add -A -- $p 2>$null }
  }
  git commit -q -m ($Msg + $Trailer) 2>$null | Out-Null
  for ($i = 0; $i -lt 4; $i++) {
    git pull -q --rebase --autostash origin $Branch 2>$null
    git push -q origin "HEAD:$Branch" 2>$null
    if ($LASTEXITCODE -eq 0) { return $true }
    Start-Sleep -Seconds ([int](2 * [math]::Pow(2, $i)))
  }
  Write-Host "Hochladen hat nicht geklappt (Internet oder GitHub-Login?). Es wird beim naechsten Mal erneut versucht."
  return $false
}

function Run-Job($Job) {
  $parts = $Job -split ":", 2
  $file = @{ preview = "render_preview.py"; queue = "render_queue.py"; moves = "render_moves.py"; export = "export_models.py" }[$parts[0]]
  if (-not $file) { Write-Host "Unbekannter Auftrag: $Job"; return 2 }
  $argv = @("azur\scene\$file")
  if ($parts.Count -gt 1 -and $parts[1]) { $argv += ($parts[1] -split ",") }
  $env:PYTHONUNBUFFERED = "1"
  # show the output live and keep it for the status file
  & python @argv 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $JobLog | Out-Host
  return $LASTEXITCODE
}

if ($Hello) {
  if (Test-Path $JobLog) { Remove-Item $JobLog }
  Write-Status "bereit" "" "" "Warte-Modus laeuft (Version $Version)"
  Push-All "AZUR PC: watch mode ready" | Out-Null
  return
}

if (-not (Test-Path "azur\render_request.json")) { return }
$last = if (Test-Path $DoneFile) { (Get-Content $DoneFile -Raw).Trim() } else { "" }
$req = Get-Content "azur\render_request.json" -Raw | ConvertFrom-Json
if (-not $req.id -or $req.id -eq $last) { return }

Write-Host ("[{0}] Neuer Auftrag {1}: {2}" -f (Get-Date -Format "HH:mm"), $req.id, $req.note)
$env:AZUR_REQUEST_ID = $req.id
if ($req.set) { $env:AZUR_SET = $req.set } else { $env:AZUR_SET = "scene3" }
if ($req.rebuild) {
  Remove-Item ("$Cache\azur_room_" + $env:AZUR_SET + ".blend") -ErrorAction SilentlyContinue
  if ($env:AZUR_SET -notin @("scene1", "scene2")) {
    # outputs of the old scene would be skipped as "done": remove them (they come back from the new scene)
    Remove-Item -Recurse -Force ("azur\prototype\assets\" + $env:AZUR_SET) -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force ("$Cache\exr\" + $env:AZUR_SET) -ErrorAction SilentlyContinue
  }
}
if ($req.redo) {
  # outputs to render again (patterns inside this set's folder, e.g. "views/*/masks*.png")
  $setDir = "azur\prototype\assets\" + $env:AZUR_SET + "\"
  foreach ($pat in $req.redo) {
    if ($pat -match '\.\.' -or [System.IO.Path]::IsPathRooted($pat)) { continue }
    Get-ChildItem -Path ($setDir + ($pat -replace '/', '\')) -File -ErrorAction SilentlyContinue | Remove-Item -Force
  }
}
uv pip install -q bpy==5.0.1 numpy pillow scikit-image scipy imageio-ffmpeg

$final = "fertig"; $note = $req.note; $failed = @()
foreach ($job in $req.jobs) {
  Write-Status "arbeitet" $req.id $job $req.note
  Push-All "AZUR PC: $($req.id) $job started" | Out-Null
  $t0 = Get-Date
  $code = Run-Job $job
  $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
  if ($code -eq 3) { $final = "abgeloest"; $note = "neuer Auftrag auf dem Branch, dieser wurde bei $job beendet"; break }
  if ($code -ne 0) {
    # report it (the commit keeps this job's log), then go on: the next jobs do not depend on it
    $failed += "$job (Exit $code nach $mins min)"
    Write-Status "fehler" $req.id $job ("$job ist fehlgeschlagen (Exit $code nach $mins min), es geht mit dem naechsten Auftragsteil weiter")
    Push-All "AZUR PC: $($req.id) $job failed" | Out-Null
    continue
  }
  Write-Status "arbeitet" $req.id $job "$job fertig nach $mins min"
  Push-All "AZUR renders from the PC: $($req.id) $job" | Out-Null
}
Set-Content -Path $DoneFile -Value $req.id
if ($failed.Count -and $final -eq "fertig") { $final = "fehler"; $note = "fehlgeschlagen: " + ($failed -join ", ") }
Write-Status $final $req.id "" $note
Push-All "AZUR PC: $($req.id) $final" | Out-Null
Write-Host ("[{0}] Auftrag {1}: {2}" -f (Get-Date -Format "HH:mm"), $req.id, $final)
