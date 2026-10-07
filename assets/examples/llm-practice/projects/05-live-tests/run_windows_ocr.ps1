param([Parameter(Mandatory=$true)][string]$ImagePath,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
# WinRT 异步方法在 Windows PowerShell 5.1 中通过泛型 AsTask 等待。
$asyncBridge = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
    $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
function Wait-WinRT($Operation, [Type]$ResultType) {
    $bridge = $asyncBridge.MakeGenericMethod($ResultType)
    $task = $bridge.Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}
$resolvedImage = (Resolve-Path -LiteralPath $ImagePath).Path
$file = Wait-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($resolvedImage)) ([Windows.Storage.StorageFile])
$stream = Wait-WinRT ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
try {
    $decoder = Wait-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Wait-WinRT ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,[Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied)) ([Windows.Graphics.Imaging.SoftwareBitmap])
    try {
        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        if ($null -eq $engine) { throw 'No OCR engine available for user profile languages' }
        $result = Wait-WinRT ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        # 保存原始文字及词边界，不在此步修正数字、破折号或单位。
        $lines = @($result.Lines | ForEach-Object {
            @{ text=$_.Text; words=@($_.Words | ForEach-Object {
                @{text=$_.Text; x=$_.BoundingRect.X; y=$_.BoundingRect.Y; width=$_.BoundingRect.Width; height=$_.BoundingRect.Height}
            }) }
        })
        $record = @{engine='Windows.Media.Ocr';language=$engine.RecognizerLanguage.LanguageTag;width=$bitmap.PixelWidth;height=$bitmap.PixelHeight;text=$result.Text;lines=$lines}
        $json = $record | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($OutputPath,$json,(New-Object System.Text.UTF8Encoding($false)))
        Write-Output ('OCR completed: '+$record.language+'; lines='+$lines.Count+'; chars='+$result.Text.Length)
    } finally { if ($null -ne $bitmap) { $bitmap.Dispose() } }
} finally { $stream.Dispose() }
