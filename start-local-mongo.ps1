$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime'
$mongo = Get-ChildItem -LiteralPath $runtime -Filter 'mongod.exe' -Recurse | Select-Object -First 1
if (-not $mongo) { throw 'MongoDB executable not found under backend/.runtime. Install MongoDB or provide its executable.' }
$data = Join-Path $runtime 'db'
New-Item -ItemType Directory -Path $data -Force | Out-Null
# Run in this terminal so Ctrl+C shuts down MongoDB normally.
& $mongo.FullName --dbpath $data --bind_ip 127.0.0.1 --port 27017 --logpath (Join-Path $runtime 'mongod.log') --logappend
