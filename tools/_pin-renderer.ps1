param([int]$Seconds = 900, [int64]$Mask = 0xFFF)
# Keeps Playwright-launched Chrome renderer processes on P-cores (CPU 0-11).
# Workaround for Windows 11 hybrid-CPU scheduler demoting long-lived renderers
# to E-cores ~3s after launch (halves JS/rendering throughput; measured 2.1x).
$deadline = (Get-Date).AddSeconds($Seconds)
while((Get-Date) -lt $deadline){
  $procs = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match '--type=renderer' -and $_.CommandLine -match 'playwright|chromiumdev' }
  foreach($pr in $procs){
    try{
      $p = Get-Process -Id $pr.ProcessId -ErrorAction Stop
      if([int64]$p.ProcessorAffinity -ne $Mask){
        $p.ProcessorAffinity = [IntPtr]$Mask
        Write-Output ("{0} pinned pid={1}" -f (Get-Date -Format 'HH:mm:ss'), $pr.ProcessId)
      }
    }catch{}
  }
  Start-Sleep -Milliseconds 400
}
Write-Output "pin-renderer done"
