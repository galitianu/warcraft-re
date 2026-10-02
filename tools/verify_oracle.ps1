# Read-only installation verification. Run with rdpipe --target vm ps -.
$ErrorActionPreference = 'Stop'
$gameDirectory = 'C:\Program Files (x86)\Warcraft III'
$names = @('Warcraft III.exe', 'World Editor.exe', 'War3.mpq', 'War3Local.mpq', 'War3x.mpq', 'War3xLocal.mpq', 'Deprecated.mpq')
$files = @()
foreach ($name in $names) {
    $path = Join-Path $gameDirectory $name
    $file = Get-Item -LiteralPath $path
    $row = [ordered]@{ name=$name; bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
    if ($name.EndsWith('.exe')) {
        $row.file_version_text = $file.VersionInfo.FileVersion
        $row.version = '{0}.{1}.{2}.{3}' -f $file.VersionInfo.FileMajorPart, $file.VersionInfo.FileMinorPart, $file.VersionInfo.FileBuildPart, $file.VersionInfo.FilePrivatePart
        $data = [IO.File]::ReadAllBytes($path)
        $offset = [BitConverter]::ToInt32($data, 60)
        if ([Text.Encoding]::ASCII.GetString($data, $offset, 4) -ne "PE`0`0") { throw 'invalid PE signature' }
        $row.pe_machine = [BitConverter]::ToUInt16($data, $offset + 4)
    }
    $files += $row
}
$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
[ordered]@{
    reference_build='wc3-1.29.2-9231-x86'; target='vm'; machine=$env:COMPUTERNAME;
    verified_utc=[DateTime]::UtcNow.ToString('o'); os=$os.Caption; os_version=$os.Version;
    os_architecture=$env:PROCESSOR_ARCHITECTURE; logical_processors=$computer.NumberOfLogicalProcessors;
    ram_bytes=$computer.TotalPhysicalMemory; game_directory=$gameDirectory; files=$files;
    procedure='rdpipe --target vm ps -; read hashes/versions/PE machine and CIM host identity before capture'
} | ConvertTo-Json -Depth 5
