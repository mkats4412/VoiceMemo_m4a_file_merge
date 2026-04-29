# VoiceMemo & Transcribe CLI Tool

Macの標準「ボイスメモ」を効率化するCLIツール。録音ファイルの自動結合（Merge）、ローカルAIによる高精度な文字起こし（Transcribe）、およびデータベースを含めたクリーンな環境リセット（Delete/Reset）を実現します。

## 1. 基本コマンドと動作

| コマンド | 動作内容 |
| :--- | :--- |
| `voiceMemo --merge` | 既存の最新マージファイルと新規録音を結合し、Recordings内に保存してFinderでハイライト表示する。 |
| `voiceMemo --transcribe`| 録音ファイルをローカルAIで文字起こしし、個別テキストと結合済みテキストを生成する。 |
| `voiceMemo --list` | 現在保存されている音声ファイルと文字起こしテキストの一覧、および合計サイズを表示する。 |
| `voiceMemo --del` | マージ済みファイル以外（元の録音や波形データ）を削除し、DBをリセットする。 |
| `voiceMemo --delall` | 全ての録音ファイル、文字起こしテキスト、およびDBを完全に削除しリセットする。 |

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
- **対象**: `Recordings` フォルダ内の未マージの `.m4a` ファイル。
- **文字起こしロジック**:
  - `uv run` と `mlx-whisper` (モデル: `large-v3-turbo`) を利用し、Macのローカル環境で高速に文字起こしを実行します。
  - システム環境(`pip list`)を汚染しないよう、一時的な仮想環境とキャッシュ（`UV_CACHE_DIR`, `HF_HOME`）はすべて外部ドライブに指定しています。
- **出力**:
  - **個別テキスト**: `TRANSCRIPT_DIR` 内に `[元のファイル名].txt` として保存（先頭に元の録音日時を見出しとして自動挿入）。
  - **結合テキスト**: 生成された全ての個別テキストを1つのファイル（`merged_transcript_YYYYMMDD_HHMMSS.txt`）に結合し、Finder上でハイライト表示。NotebookLM等のナレッジベースへの一括取り込みに最適です。

### C. List機能 (`--list`)
- **機能**: 現在のディレクトリ状況の可視化。
- **表示内容**:
  - 音声データとテキストデータを時系列順にリスト表示（マージ済みファイルには `(Merged Audio)` などのラベルを付与）。
  - 各ディレクトリ内の対象ファイルの合計サイズ(MB)を表示し、ストレージ容量の管理を容易にします。

### D. Delete機能 (`--del`)
- **対象**: `merge_` プレフィックスが付いていない `.m4a` および `.waveform`。
- **DBリセット**: アプリを終了させた後、`CloudRecordings.db*` を削除して履歴をクリア。
- **目的**: 作業済みの中間ファイルを消し、ボイスメモアプリ内の表示をスッキリさせつつ、マージ後の成果物（`merge_...`）だけを次回の結合用に残す。

### E. Reset機能 (`--delall`)
- **対象**: `Recordings` フォルダ内の全ファイル、`transcript` フォルダ内の全テキストファイル、および管理用データベース。
- **実行フロー**:
  1. `VoiceMemos` アプリを終了。
  2. 全ての録音ファイルを物理削除。
  3. 全ての文字起こしテキストファイル(.txt)を物理削除。
  4. デスクトップ等に残っている古い結合済みファイルがあれば削除。
  5. DB関連ファイルを削除し、完全な初期状態に戻す。

## 3. 環境・設定

- **OS**: macOS (macOS Tahoe 16.3.1 対応確認済み / Apple Silicon 推奨)
- **言語**: Python 3.x
- **依存ツール**:
  - `ffmpeg` (音声結合用。Homebrew等でインストール済みであること)
  - `uv` (文字起こし環境の動的構築用)
- **ディレクトリ構成**:
  - スクリプト: `/Volumes/ExDrive/Data/env/script/python/merge_voicememo/voice_memo.py`
  - トランスクリプト出力先: `/Volumes/ExDrive/Data/env/script/python/merge_voicememo/transcript`
  - コマンドリンク: `/Volumes/ExDrive/Data/env/script/systools/voiceMemo` (パスが通っているディレクトリ)

## 4. インストール/設定

以下のコマンドで実行権限を付与し、パスの通ったディレクトリへシンボリックリンクを作成して利用します。

```bash
chmod +x /Volumes/ExDrive/Data/env/script/python/merge_voicememo/voice_memo.py
ln -sf /Volumes/ExDrive/Data/env/script/python/merge_voicememo/voice_memo.py /Volumes/ExDrive/Data/env/script/systools/voiceMemo
