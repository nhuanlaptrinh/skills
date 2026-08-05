param (
    [string]$Mode = "Daily", # "Daily" hoặc "5Mins"
    [string]$Time = "09:00AM"
)

$ErrorActionPreference = "Stop"

# Chuẩn ALT: Đảm bảo lấy đúng thư mục hiện tại của dự án thay vì hardcode
$projectDir = (Get-Item -Path ".\").FullName
$pythonExe  = "$projectDir\venv\Scripts\python.exe"
$scriptFile = ".agents\skills\fb-auto-poster\scripts\OpenFBV2POST.py"

Write-Host "=========================================="
Write-Host " SETTING UP FACEBOOK AUTO POSTER SCHEDULE "
Write-Host "=========================================="
Write-Host "Project Directory: $projectDir"
Write-Host "Python Executable: $pythonExe"
Write-Host ""

if (!(Test-Path $pythonExe)) {
    Write-Host "LỖI: Không tìm thấy môi trường ảo (venv) tại $pythonExe!" -ForegroundColor Red
    Write-Host "Vui lòng chạy lệnh 'python -m venv venv' trước khi cài đặt lịch." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Exit
}

if ($Mode -eq "5Mins") {
    $taskName = "Auto Post Facebook Every 5 Mins"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    
    $action = New-ScheduledTaskAction -Execute $pythonExe -Argument $scriptFile -WorkingDirectory $projectDir
    
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -MultipleInstances IgnoreNew -StartWhenAvailable
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Tu dong dang bai Facebook tu Google Sheet moi 5 phut" -Force
    
    Write-Host "✅ Đã tạo lịch thành công: Chạy mỗi 5 phút!" -ForegroundColor Green
    Start-Sleep -Seconds 3
}
elseif ($Mode -eq "Daily") {
    $taskName = "Auto Post Facebook Daily $Time"
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    
    $action = New-ScheduledTaskAction -Execute $pythonExe -Argument $scriptFile -WorkingDirectory $projectDir
    $trigger = New-ScheduledTaskTrigger -Daily -At $Time
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -StartWhenAvailable -WakeToRun
    
    # Chế độ Daily có WakeToRun nên yêu cầu RunLevel Highest (Admin)
    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Tu dong dang bai Facebook vao $Time hang ngay" -RunLevel Highest -Force
        Write-Host "✅ Đã tạo lịch thành công: Chạy hàng ngày lúc $Time!" -ForegroundColor Green
        Start-Sleep -Seconds 3
    }
    catch {
        Write-Host "⚠️ LỖI: Tạo lịch Daily yêu cầu quyền Administrator!" -ForegroundColor Red
        Write-Host "Vui lòng chạy lại file này bằng PowerShell (Run as Administrator)." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}
else {
    Write-Host "Mode '$Mode' không hợp lệ. Vui lòng chọn 'Daily' hoặc '5Mins'." -ForegroundColor Red
    Start-Sleep -Seconds 3
}
