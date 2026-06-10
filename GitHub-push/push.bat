@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ======== 把你的仓库绝对路径写在这里（一行一个） ========
set REPOS[0]=C:\Users\24130\Desktop\central warehouse\薇花
set REPOS[1]=C:\Users\24130\Desktop\central warehouse\Python
set REPOS[2]=C:\Users\24130\Desktop\central warehouse\note
set REPOS[3]=C:\Users\24130\Desktop\central warehouse\C-C++
:: ========================================================

set COMMIT_MSG=%1
if "%COMMIT_MSG%"=="" set COMMIT_MSG=auto backup %date% %time%

echo 准备推送 %REPO_COUNT% 个仓库...
echo.

for /l %%i in (0,1,10) do (
    if defined REPOS[%%i] (
        set REPO=!REPOS[%%i]!
        echo === 正在处理: !REPO! ===
        cd /d "!REPO!"
        if errorlevel 1 (
            echo [失败] 目录不存在或无法访问
        ) else (
            git add .
            git commit -m "!COMMIT_MSG!"
            git push
            if errorlevel 1 (
                echo [失败] 推送出错，请检查
            ) else (
                echo [成功] 推送完毕
            )
        )
        echo.
    )
)

echo 全部操作完成
pause