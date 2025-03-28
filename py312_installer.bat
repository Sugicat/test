@echo off
setlocal enabledelayedexpansion

:: ログファイルの設定
set LOG_FILE=%~dp0install_log.txt
echo Installation started at %date% %time% > %LOG_FILE%

:: SVNコマンドが存在するか確認
where svn >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo SVNコマンドが見つかりません。Subversionクライアントをインストールしてください。 >> %LOG_FILE%
    echo SVNコマンドが見つかりません。Subversionクライアントをインストールしてください。
    exit /b 1
)

:: SVNリポジトリの存在確認
echo SVNリポジトリの確認中... >> %LOG_FILE%
svn list https://hoge/svn/python_svn >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo SVNリポジトリ「https://hoge/svn/python_svn」にアクセスできません。 >> %LOG_FILE%
    echo SVNリポジトリ「https://hoge/svn/python_svn」にアクセスできません。
    exit /b 1
)
echo SVNリポジトリにアクセス成功しました。 >> %LOG_FILE%

:: C:/UFS/ディレクトリの確認と作成
echo C:/UFS/ディレクトリを確認中... >> %LOG_FILE%
if not exist "C:\UFS" (
    echo C:/UFS/ディレクトリが存在しません。作成します... >> %LOG_FILE%
    mkdir "C:\UFS" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo C:/UFS/ディレクトリの作成に失敗しました。 >> %LOG_FILE%
        echo C:/UFS/ディレクトリの作成に失敗しました。
        exit /b 1
    )
)

:: C:/UFS/ufs_python_svnディレクトリの確認
echo C:/UFS/ufs_python_svnディレクトリを確認中... >> %LOG_FILE%
if exist "C:\UFS\ufs_python_svn" (
    echo C:/UFS/ufs_python_svnディレクトリはすでに存在します。 >> %LOG_FILE%
    echo 既存のチェックアウトを更新するか確認します... >> %LOG_FILE%
    
    :: SVNワーキングコピーかチェック
    if exist "C:\UFS\ufs_python_svn\.svn" (
        echo 既存のSVNワーキングコピーを更新します... >> %LOG_FILE%
        cd /d "C:\UFS\ufs_python_svn"
        svn update >> %LOG_FILE% 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo SVNアップデートに失敗しました。 >> %LOG_FILE%
            echo SVNアップデートに失敗しました。
            :: 更新に失敗しても続行
        ) else (
            echo SVNアップデートに成功しました。 >> %LOG_FILE%
        )
    ) else (
        echo C:/UFS/ufs_python_svnフォルダはSVNワーキングコピーではありません。 >> %LOG_FILE%
        echo 既存のフォルダを削除し、再チェックアウトします... >> %LOG_FILE%
        rmdir /s /q "C:\UFS\ufs_python_svn" >nul 2>&1
        goto checkout_svn
    )
) else (
    :checkout_svn
    echo C:/UFS/ufs_python_svnディレクトリを作成し、SVNリポジトリをチェックアウトします... >> %LOG_FILE%
    echo C:/UFS/ufs_python_svnディレクトリを作成し、SVNリポジトリをチェックアウトします...
    
    mkdir "C:\UFS\ufs_python_svn" >nul 2>&1
    svn checkout https://hoge/svn/python_svn/trunk/ "C:\UFS\ufs_python_svn" >> %LOG_FILE% 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo SVNチェックアウトに失敗しました。 >> %LOG_FILE%
        echo SVNチェックアウトに失敗しました。
        exit /b 1
    )
    echo SVNチェックアウトに成功しました。 >> %LOG_FILE%
    echo SVNチェックアウトに成功しました。
)

:: Pythonインストーラーのパスを設定 - チェックアウトしたリポジトリから
set PYTHON_INSTALLER=Python-3.12.7-amd64.exe
set INSTALLER_PATH=C:\UFS\ufs_python_svn\setup\%PYTHON_INSTALLER%

:: インストーラーが存在するか確認
if not exist "%INSTALLER_PATH%" (
    echo Pythonインストーラー「%INSTALLER_PATH%」が見つかりません。 >> %LOG_FILE%
    echo Pythonインストーラー「%INSTALLER_PATH%」が見つかりません。
    exit /b 1
)

:: Pythonのインストール
echo Pythonをインストールしています... >> %LOG_FILE%
echo Pythonをインストールしています...
"%INSTALLER_PATH%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Pythonのインストールに失敗しました。 >> %LOG_FILE%
    echo [FAIL] Pythonのインストールに失敗しました。
    exit /b 1
)
echo [PASS] Pythonのインストールに成功しました。 >> %LOG_FILE%
echo [PASS] Pythonのインストールに成功しました。

:: PATH更新を反映させる
set PATH=%PATH%;C:\Program Files\Python312;C:\Program Files\Python312\Scripts

:: Pythonが正しくインストールされたか確認
python --version >> %LOG_FILE% 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] Pythonがインストールされましたが、コマンドが見つかりません。 >> %LOG_FILE%
    echo [FAIL] Pythonがインストールされましたが、コマンドが見つかりません。
    exit /b 1
)

:: pipのアップグレード
echo pipをアップグレードしています... >> %LOG_FILE%
python -m pip install --upgrade pip >> %LOG_FILE% 2>&1

:: パッケージのインストール
echo パッケージのインストールを開始します... >> %LOG_FILE%
echo パッケージのインストールを開始します...

:: パッケージディレクトリの設定
set PACKAGES_DIR=C:\UFS\ufs_python_svn\pypi_packages\312_win64

:: パッケージディレクトリが存在するか確認
if not exist "%PACKAGES_DIR%" (
    echo パッケージディレクトリ「%PACKAGES_DIR%」が見つかりません。 >> %LOG_FILE%
    echo パッケージディレクトリ「%PACKAGES_DIR%」が見つかりません。
    exit /b 1
)

:: 各パッケージをインストール
for %%a in ("%PACKAGES_DIR%\*.whl") do (
    echo "%%a"のインストールを試みています... >> %LOG_FILE%
    echo "%%~nxa"のインストールを試みています...
    
    python -m pip install "%%a" >> %LOG_FILE% 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo [WARNING] "%%~nxa"のインストールに失敗しました。 >> %LOG_FILE%
        echo [WARNING] "%%~nxa"のインストールに失敗しました。
    ) else (
        echo [SUCCESS] "%%~nxa"のインストールに成功しました。 >> %LOG_FILE%
        echo [SUCCESS] "%%~nxa"のインストールに成功しました。
    )
)

echo インストール処理が完了しました。詳細は %LOG_FILE% を確認してください。
echo インストール処理が完了しました。

endlocal
