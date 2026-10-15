# Skillable lifecycle action: download this repository to the lab VM desktop.
# While the repository is private, set $token to a read-only GitHub token; leave it empty once it is public.
$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'   # progress bar makes IWR very slow on PS 5.1
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo   = 'microsoft/ignite26-PREL42'
$branch = 'main'
$token  = ''
# lifecycle_bicep_deployment.ps1, setup-lab.ps1, and the attendee instructions expect the repo here.
$dest   = 'C:\Users\LabUser\Desktop\ignite26-PREL42'
$zip    = "$env:TEMP\repo.zip"
$tmp    = "$env:TEMP\repo_extract"

if ($token) {
    $url = "https://api.github.com/repos/$repo/zipball/$branch"
    $headers = @{ Authorization = "Bearer $token"; Accept = 'application/vnd.github+json' }
} else {
    $url = "https://github.com/$repo/archive/refs/heads/$branch.zip"
    $headers = @{}
}

# Retry in case networking isn't fully up when the LCA fires
for ($i = 1; $i -le 5; $i++) {
    try {
        Invoke-WebRequest $url -Headers $headers -OutFile $zip -UseBasicParsing
        break
    } catch {
        if ($i -eq 5) { throw }
        Start-Sleep -Seconds 10
    }
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive $zip -DestinationPath $tmp -Force

# GitHub zips contain a single top-level folder (e.g. ignite26-PREL42-main); copy its contents
$inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
New-Item $dest -ItemType Directory -Force | Out-Null
Copy-Item "$($inner.FullName)\*" $dest -Recurse -Force

Remove-Item $zip, $tmp -Recurse -Force
