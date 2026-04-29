# voiceMemo

Macの標準「ボイスメモ」を効率化するCLIツール。録音ファイルの自動結合（Merge）と、データベースを含めたクリーンな削除（Delete/Reset）を実現します。

## 1. 基本コマンドと動作

| コマンド | 動作内容 |
| :--- | :--- |
| `voiceMemo --merge` | 既存の最新マージファイルと新規録音を結合し、Recordings内に保存してFinderでハイライト表示する。 |
| `voiceMemo --transcribe` | 新規録音ファイルを文字起こしし、テキストファイルを統合する。 |
| `voiceMemo --list` | 現在の録音ファイルと文字起こし済みテキストの一覧を表示する。 |
| `voiceMemo --open <voice\|v\|text\|t>` | 録音データまたは文字起こしフォルダをFinderで開く。 |
| `voiceMemo --del` | マージ済みファイル以外（元の録音や波形データ）を削除し、DBをリセットする。 |
| `voiceMemo --delall` | 全ての録音ファイル（マージ済みを含む）およびDBを完全に削除しリセットする。 |

## 2. 機能詳細

### A. Merge機能 (`--merge`)
- **対象**: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings` 内の `.m4a`。
- **結合ロジック**: 
  - 既に `merge_` ファイルが存在する場合、**最新の1つのみ**を対象に含めます。
  - それに加えて、まだマージされていない新規の録音ファイルを結合します。
  - これにより、前回の成果物を引き継ぎつつ新しい録音を末尾に追加していくことが可能です。
- **出力**:
  - ファイル名: `merge_YYYYMMDD_HHMMSS.m4a`
  - 出力先: `Recordings` フォルダ内（ボイスメモのデータディレクトリ）
  - 完了後: `open -R` でFinder上でハイライト。
- **技術要件**: `ffmpeg` を使用した無劣化結合（`-c copy`）。

### B. Transcribe機能 (`--transcribe`)
- **対象**: `merge_` を含まない新規の `.m4a` ファイル。
- **動作**: 
  - `mlx-whisper` を使用して各ファイルを文字起こしし、個別のテキストファイルとして保存。
  - 全てのテキストファイルを結合した `merged_transcript_YYYYMMDD_HHMMSS.txt` を作成。
- **出力先**: `/Volumes/ExDrive/Data/env/script/python/merge_voicememo/transcript`

### C. Open機能 (`--open`)
- **`--open voice` / `--open v`**: ボイスメモの録音データが保存されている `Recordings` フォルダをFinderで開きます。
- **`--open text` / `--open t`**: 文字起こし結果が保存されている `transcript` フォルダをFinderで開きます。

### D. List機能 (`--list`)
- 現在保存されている録音ファイル（`.m4a`）と、文字起こし済みテキスト（`.txt`）の一覧、およびそれぞれの合計サイズを表示します。

### E. Delete機能 (`--del`)
- **対象**: `merge_` プレフィックスが付いていない `.m4a` および `.waveform`。
- **DBリセット**: アプリを終了させた後、`CloudRecordings.db*` を削除して履歴をクリア。
- **目的**: 作業済みの中間ファイルを消し、ボイスメモアプリ内の表示をスッキリさせつつ、マージ後の成果物（`merge_...`）だけを次回の結合用に残す。

### F. Reset機能 (`--delall`)
- **対象**: `Recordings` フォルダ内の全ファイル（`merge_` ファイルを含む）、および管理用データベース。
- **実行フロー**:
  1. `VoiceMemos` アプリを終了。
  2. 全ての録音ファイルを物理削除。
  3. デスクトップ等に残っている古い結合済みファイルがあれば削除。
  4. DB関連ファイルを削除し、完全な初期状態に戻す。
  5. `transcript` フォルダ内の全てのテキストファイルを削除。

## 3. 環境・設定

- **OS**: macOS (macOS Tahoe 16.3.1 対応確認済み)
- **言語**: Python 3.x
- **依存ツール**: `ffmpeg` (Homebrew等でインストール済みであること)
- **ディレクトリ構成**:
  - スクリプト: `/Volumes/ExDrive/Data/env/script/python/merge_voicememo/voice_memo.py`
  - コマンドリンク: `/Volumes/ExDrive/Data/env/script/systools/voiceMemo` (パスが通っているディレクトリ)

## 4. インストール/設定

以下のコマンドで実行権限を付与し、シンボリックリンクを作成して利用します。

```bash
chmod +x voice_memo.py
ln -sf $(pwd)/voice_memo.py /Volumes/ExDrive/Data/env/script/systools/voiceMemo
```
