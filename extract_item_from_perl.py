import re
import csv
import os
import sys
import glob
from pathlib import Path
import time  # パフォーマンス計測用

def extract_field(text, field_name, debug=True):
    """
    テキストから特定のフィールドを抽出する補助関数
    複数行にわたるフィールドにも対応
    # ****** パターンがあればそこで終了
    
    Args:
        text (str): 検索対象のテキスト
        field_name (str): 抽出するフィールド名（例: "Test no"）
        debug (bool): デバッグ出力を表示するかどうか
    
    Returns:
        str: 抽出された値（整形済み）
    """
    # 事前コンパイルされた正規表現パターン（グローバル定数）を使用
    global FIELD_PATTERNS_COMPILED
    global DELIMITER_PATTERN_COMPILED
    
    # 指定されたフィールドのパターンを作成 (より柔軟なマッチングのため)
    field_pattern = re.compile(rf"#\s*{field_name}\s*:", re.IGNORECASE)
    
    # まず通常のケースでマッチを試みる
    start_match = field_pattern.search(text)
    
    if not start_match:
        if debug:
            print(f"フィールド '{field_name}' が見つかりませんでした")
        return ""
    
    start_pos = start_match.end()
    
    # 次のフィールドの開始位置または区切りパターンの開始位置を検索
    end_pos = len(text)
    
    # 全てのフィールドパターンに対して次の出現位置を探す
    for pattern in FIELD_PATTERNS_COMPILED:
        # より柔軟な検索パターン
        next_field_match = pattern.search(text[start_pos:])
        if next_field_match:
            next_field_pos = start_pos + next_field_match.start()
            if next_field_pos < end_pos:
                end_pos = next_field_pos
    
    # 区切りパターンを検索
    delimiter_match = DELIMITER_PATTERN_COMPILED.search(text[start_pos:])
    if delimiter_match:
        delimiter_pos = start_pos + delimiter_match.start()
        if delimiter_pos < end_pos:
            end_pos = delimiter_pos
            if debug:
                print(f"フィールド '{field_name}' の終了を区切りパターン '# ******' で検出しました")
    
    # フィールドの内容を取得
    field_content = text[start_pos:end_pos].strip()
    
    # 複数行の場合、各行から先頭の '#' と余分な空白を除去
    lines = field_content.split('\n')
    processed_lines = []
    
    for line in lines:
        # 行頭の '#' と空白を除去 (より柔軟に)
        line = re.sub(r'^\s*#\s*(:)?\s*', '', line.strip())
        if line:  # 空行でなければ追加
            processed_lines.append(line)
    
    result = ' '.join(processed_lines)
    if debug:
        if result:
            print(f"フィールド '{field_name}' の抽出結果: '{result[:50]}...'")
        else:
            print(f"フィールド '{field_name}' の内容が空です")
        
    # 処理した行を結合
    return result

def extract_test_info_from_file(file_path, debug=True):
    """
    単一のファイルからテスト情報を抽出する関数
    
    Args:
        file_path (str): 入力ファイルのパス
        debug (bool): デバッグ出力を表示するかどうか
    
    Returns:
        list: 抽出されたテスト情報のリスト
    """
    # 結果を格納するリスト
    test_info_list = []
    
    # ファイルを読み込む
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        try:
            # UTF-8でデコードできない場合は他のエンコーディングを試す
            with open(file_path, 'r', encoding='shift-jis') as file:
                content = file.read()
        except UnicodeDecodeError:
            print(f"ファイル '{file_path}' のエンコーディングを特定できませんでした")
            return []
    
    if debug:
        # ファイルの内容を確認（デバッグ用）
        print(f"ファイルサイズ: {len(content)} バイト")
        print(f"ファイルの先頭500文字: {content[:500].replace('\n', '\\n')}")
    
    # # ******** パターンで囲まれた部分を抽出
    # 事前コンパイルされたパターンを使用
    
    # デリミタ（区切り）パターンの位置を見つける
    delimiter_positions = [m.start() for m in SECTION_DELIMITER_PATTERN_COMPILED.finditer(content)]
    if debug:
        print(f"見つかった区切りパターンの数: {len(delimiter_positions)}")
    
    if len(delimiter_positions) < 2:
        print(f"ファイル '{file_path}' に十分な区切りパターンがありません。")
        return []
    
    # 区切りパターンのペアで囲まれた部分を抽出
    test_blocks = []
    for i in range(0, len(delimiter_positions) - 1, 2):
        start_pos = delimiter_positions[i]
        end_pos = delimiter_positions[i + 1]
        
        # 開始区切りパターンの行末までスキップ
        line_end = content.find('\n', start_pos)
        if line_end > 0:
            start_pos = line_end + 1
        
        # 終了区切りパターンの行頭まで
        block = content[start_pos:end_pos].strip()
        test_blocks.append(block)
    
    if debug:
        print(f"抽出されたブロック数: {len(test_blocks)}")
        if test_blocks:
            print(f"最初のブロックのサンプル（先頭100文字）: {test_blocks[0][:100].replace('\n', '\\n')}")
    
    # 各ブロックからテスト情報を抽出
    for block in test_blocks:
        # 各項目を抽出
        test_info = {}
        
        # 必要なフィールドのリスト
        fields = [
            ("Test no", "Test No"),
            ("Item1", "Item1"),
            ("Item2", "Item2"),
            ("Item3", "Item3"),
            ("Test Sequence", "Test Sequence"),
            ("Input Parameter", "Input Parameter"),
            ("Test Purpose", "Test Purpose")
        ]
        
        # 各フィールドを抽出
        for field_name, csv_column in fields:
            value = extract_field(block, field_name, debug=debug)
            test_info[csv_column] = value
        
        # 少なくとも1つのフィールドが存在する場合のみ追加
        if any(test_info.values()):
            test_info_list.append(test_info)
    
    print(f"ファイル '{file_path}' から {len(test_info_list)} 件のテスト情報を抽出しました。")
    return test_info_list

def process_directory(directory_path, output_csv_path):
    """
    指定されたディレクトリ内のすべての .vec ファイルを処理し、
    抽出した情報を1つのCSVファイルにまとめる
    
    Args:
        directory_path (str): 処理するディレクトリのパス
        output_csv_path (str): 出力するCSVファイルのパス
    """
    start_time = time.time()  # 処理開始時間
    
    # 結果を格納するリスト
    all_test_info = []
    
    # 失敗したファイルのリスト
    failed_files = []
    
    # .vec ファイルの一覧を取得
    vec_files = list(Path(directory_path).glob('**/*.vec'))
    
    if not vec_files:
        print(f"ディレクトリ '{directory_path}' 内に .vec ファイルが見つかりませんでした。")
        return
    
    print(f"合計 {len(vec_files)} 個の .vec ファイルが見つかりました。")
    
    # 処理成功・失敗のカウンター
    success_count = 0
    failed_count = 0
    total_records = 0
    
    # バッチサイズ（何ファイルごとに進捗を表示するか）
    batch_size = max(1, len(vec_files) // 20)  # 全体の5%ごとに表示
    
    # 各ファイルを処理
    for i, file_path in enumerate(vec_files):
        # 進捗表示（バッチごと）
        if i % batch_size == 0 or i == len(vec_files) - 1:
            progress = (i + 1) / len(vec_files) * 100
            elapsed = time.time() - start_time
            estimated_total = elapsed / (i + 1) * len(vec_files)
            remaining = estimated_total - elapsed
            print(f"進捗: {progress:.1f}% ({i+1}/{len(vec_files)}) 経過時間: {elapsed:.1f}秒 残り時間: {remaining:.1f}秒")
        
        try:
            # ファイルからテスト情報を抽出 (詳細なデバッグ出力をオフに)
            test_info_list = extract_test_info_from_file(str(file_path), debug=False)
            
            # ファイル名情報を追加
            if test_info_list:
                for info in test_info_list:
                    info['File Name'] = file_path.name
                
                # 全体のリストに追加
                all_test_info.extend(test_info_list)
                total_records += len(test_info_list)
                success_count += 1
            else:
                # 情報が抽出されなかった場合は失敗としてカウント
                failed_count += 1
                failed_files.append({
                    'File Path': str(file_path),
                    'Error': '抽出可能なテスト情報が見つかりませんでした',
                    'Timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            error_msg = str(e)
            print(f"エラー: ファイル '{file_path}' の処理中に例外が発生しました: {error_msg}")
            failed_count += 1
            failed_files.append({
                'File Path': str(file_path),
                'Error': error_msg,
                'Timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # メモリ最適化のために大きなリストを直接CSVに書き出す
    if all_test_info:
        fieldnames = ['File Name', 'Test No', 'Item1', 'Item2', 'Item3', 'Test Sequence', 'Input Parameter', 'Test Purpose']
        
        try:
            with open(output_csv_path, 'w', newline='', encoding='shift_jis', errors='replace') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # メモリ効率のために一度に書き込まずにバッチ処理
                batch_size = 1000  # 一度に書き込むレコード数
                for i in range(0, len(all_test_info), batch_size):
                    writer.writerows(all_test_info[i:i+batch_size])
            
            print(f"\n抽出完了: 合計 {len(all_test_info)} 件のテスト情報を '{output_csv_path}' に保存しました。")
        except Exception as e:
            print(f"\nエラー: CSVファイルの書き込み中に例外が発生しました: {str(e)}")
    else:
        print("\nテスト情報が見つかりませんでした。")
    
    # 失敗したファイル一覧をCSVに出力
    if failed_files:
        # 失敗リスト用のCSVファイル名を生成
        failed_csv_path = os.path.splitext(output_csv_path)[0] + "_failed.csv"
        
        try:
            with open(failed_csv_path, 'w', newline='', encoding='shift_jis', errors='replace') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['File Path', 'Error', 'Timestamp'])
                writer.writeheader()
                writer.writerows(failed_files)
            
            print(f"失敗したファイル一覧: 合計 {len(failed_files)} 件を '{failed_csv_path}' に保存しました。")
        except Exception as e:
            print(f"エラー: 失敗リストのCSV出力中に例外が発生しました: {str(e)}")
            # 最低限の情報だけでも表示
            print("\n=== 失敗したファイル一覧 ===")
            for i, failed in enumerate(failed_files[:10]):  # 最初の10件だけ表示
                print(f"{i+1}. {failed['File Path']} - {failed['Error']}")
            if len(failed_files) > 10:
                print(f"... 他 {len(failed_files) - 10} 件")
    
    # 処理サマリーを表示
    total_time = time.time() - start_time
    print(f"\n処理サマリー:")
    print(f"  - 処理ファイル数: {len(vec_files)} ファイル")
    print(f"  - 成功: {success_count} ファイル")
    print(f"  - 失敗/スキップ: {failed_count} ファイル")
    print(f"  - 抽出レコード数: {total_records} レコード")
    print(f"  - 処理時間: {total_time:.1f}秒 (平均: {total_time/len(vec_files):.3f}秒/ファイル)")

def scan_for_fields(file_path):
    """
    ファイル内のすべてのフィールドをスキャンして表示する（デバッグ用）
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='shift-jis') as file:
                content = file.read()
        except UnicodeDecodeError:
            print("ファイルのエンコーディングを特定できませんでした")
            return
    
    # 区切りパターンを探す
    delimiter_matches = list(SECTION_DELIMITER_PATTERN_COMPILED.finditer(content))
    print(f"\n=== 区切りパターン '# ********' の検出結果 ===")
    print(f"合計: {len(delimiter_matches)}個見つかりました")
    if delimiter_matches:
        for i, m in enumerate(delimiter_matches[:3]):  # 最初の3つのみ表示
            line_start = content.rfind('\n', 0, m.start()) + 1
            line_end = content.find('\n', m.start())
            if line_end == -1:
                line_end = len(content)
            print(f"  サンプル{i+1}: '{content[line_start:line_end]}'")
    
    # 一般的なフィールドパターンを探す
    field_patterns = [
        r'#\s*Test no\s*:',
        r'#\s*Item1\s*:',
        r'#\s*Item2\s*:',
        r'#\s*Item3\s*:',
        r'#\s*Test Sequence\s*:',
        r'#\s*Input Parameter\s*:',
        r'#\s*Test Purpose\s*:'
    ]
    
    print("\n=== ファイル内のフィールド検出結果 ===")
    for pattern in field_patterns:
        matches = list(re.finditer(pattern, content))
        print(f"{pattern}: {len(matches)}個見つかりました")
        if matches and len(matches) <= 3:  # サンプル表示は3つまで
            for i, m in enumerate(matches):
                context_start = max(0, m.start() - 20)
                context_end = min(len(content), m.end() + 40)
                context = content[context_start:context_end].replace('\n', '\\n')
                print(f"  サンプル{i+1}: ...{context}...")

# グローバル変数として正規表現パターンを事前コンパイル
# フィールドパターン
FIELD_PATTERNS = [
    r"#\s*Test no\s*:", r"#\s*Item1\s*:", r"#\s*Item2\s*:", r"#\s*Item3\s*:",
    r"#\s*Test Sequence\s*:", r"#\s*Input Parameter\s*:", r"#\s*Test Purpose\s*:"
]
FIELD_PATTERNS_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in FIELD_PATTERNS]

# 区切りパターン
DELIMITER_PATTERN = r"#\s*\*{6,}"  # 終了検出用（6個以上のアスタリスク）
DELIMITER_PATTERN_COMPILED = re.compile(DELIMITER_PATTERN)

# セクション区切りパターン
SECTION_DELIMITER_PATTERN = r'#\s*\*{8,}'  # ブロック抽出用（8個以上のアスタリスク）
SECTION_DELIMITER_PATTERN_COMPILED = re.compile(SECTION_DELIMITER_PATTERN)

if __name__ == "__main__":
    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        print("使用方法: python script.py <入力パス> [出力CSVファイル]")
        print("  <入力パス> : 単一の.vecファイルまたはディレクトリのパス")
        print("  [出力CSVファイル] : 省略可。出力CSVファイルのパス")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # 出力ファイル名の設定
    if len(sys.argv) > 2:
        output_csv_path = sys.argv[2]
    else:
        if os.path.isdir(input_path):
            # ディレクトリの場合、ディレクトリ名をベースに出力ファイル名を設定
            dir_name = os.path.basename(os.path.normpath(input_path))
            output_csv_path = f"{dir_name}_test_info.csv"
        else:
            # ファイルの場合、ファイル名をベースに出力ファイル名を設定
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_csv_path = f"{base_name}_test_info.csv"
    
    # 入力パスがディレクトリかファイルかによって処理を分岐
    if os.path.isdir(input_path):
        print(f"ディレクトリ '{input_path}' を処理中...")
        process_directory(input_path, output_csv_path)
    else:
        if not input_path.lower().endswith('.vec'):
            print(f"警告: 入力ファイル '{input_path}' は .vec 拡張子ではありません。")
        
        print(f"ファイル '{input_path}' を処理中...")
        # デバッグ情報を表示
        scan_for_fields(input_path)
        
        # ファイルを処理
        test_info_list = extract_test_info_from_file(input_path)
        
        # CSVファイルに書き出し
        if test_info_list:
            fieldnames = ['Test No', 'Item1', 'Item2', 'Item3', 'Test Sequence', 'Input Parameter', 'Test Purpose']
            
            with open(output_csv_path, 'w', newline='', encoding='shift_jis', errors='replace') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(test_info_list)
            
            print(f"抽出完了: {len(test_info_list)}件のテスト情報を'{output_csv_path}'に保存しました。")
        else:
            print("テスト情報が見つかりませんでした。")
