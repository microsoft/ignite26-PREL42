# Skillable lifecycle action: download this repository to the lab VM desktop.
# Skillable replaces SECRET with a GitHub token while the repository is private.
$token = "SECRET"
$targetPath = "C:\Users\LabUser\Desktop\ignite26-PREL42"
$tempZip = "$env:TEMP\repo.zip"

$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
}

$zipUrl = "https://api.github.com/repos/microsoft/ignite26-PREL42/zipball/main"

Invoke-WebRequest -Uri $zipUrl -Headers $headers -OutFile $tempZip -UseBasicParsing

$tempExtract = "$env:TEMP\extracted"
if (Test-Path $tempExtract) {
    Remove-Item $tempExtract -Recurse -Force
}
Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

$extractedFolder = Get-ChildItem $tempExtract -Directory | Select-Object -First 1

if (Test-Path $targetPath) {
    Remove-Item $targetPath -Recurse -Force
}
Move-Item $extractedFolder.FullName $targetPath -Force
