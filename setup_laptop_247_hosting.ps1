# ==============================================================================
# NIFTY 50 Pro Terminal - Laptop 24/7 Hosting Setup & Optimization Script
# ==============================================================================
Write-Host "Configuring Windows Power Settings for uninterrupted 24/7 server execution..." -ForegroundColor Cyan

# 1. Disable Standby / Sleep on AC Power
powercfg -change -standby-timeout-ac 0
Write-Host "[OK] Laptop Sleep on AC Power disabled (Never sleep)." -ForegroundColor Green

# 2. Disable Hibernation on AC Power
powercfg -change -hibernate-timeout-ac 0
Write-Host "[OK] Hibernation disabled." -ForegroundColor Green

# 3. Turn off Monitor after 10 minutes to save power & protect screen (CPU stays 100% awake)
powercfg -change -monitor-timeout-ac 10
Write-Host "[OK] Screen turns off after 10 mins (Laptop CPU & Server stay active 24/7)." -ForegroundColor Green

# 4. Optional: Close Lid Action reminder
Write-Host "`nIMPORTANT MANUAL STEP (Lid Close Action):" -ForegroundColor Yellow
Write-Host "To run the server with your laptop lid closed:" -ForegroundColor White
Write-Host "1. Press Windows Key + R, type 'control powercfg.cpl', press Enter." -ForegroundColor White
Write-Host "2. Click 'Choose what closing the lid does' on the left." -ForegroundColor White
Write-Host "3. Under 'When I close the lid' -> 'Plugged in', select: 'Do nothing'." -ForegroundColor White
Write-Host "`nYour laptop is now fully optimized for 24/7 hosting!" -ForegroundColor Cyan
