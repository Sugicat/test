import re
import csv
import os
import sys

def extract_test_info(perl_file_path, output_csv_path):
    """
    Perlファイルから特定のテスト情報を抽出してCSVファイルに出力する関数
    
    Args:
        perl_file_path (str): 入力するPerlファイルのパス
        output_csv_path (str): 出力するCSVファイルのパス
    """
    # 結果を格納するリスト
    test_info_list = []
    
    # ファイルを読み込む
    try:
        with open(perl_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        # UTF-8でデコードできない場合は他のエンコーディングを試す
        with open(perl_file_path, 'r', encoding='shift-jis') as file:
            content = file.read()
    
    # ファイルの内容を確認（デバッグ用）
    print(f"ファイルサイズ: {len(content)} バイト")
    print(f"ファイルの先頭500文字: {content[:500]}")
    
    # より柔軟な正規表現パターンを定義
    # ファイル全体を1つのブロックとして扱い、各フィールドを個別に抽出するアプローチに変更
    test_blocks = []
    
    # Test no が存在する行を検索
    test_no_positions = [m.start() for m in re.finditer(r'(?m)^#\s*Test no\s*:', content)]
    print(f"見つかった 'Test no' マーカーの数: {len(test_no_positions)}")
    
    if not test_no_positions:
        # Test no が見つからない場合、ファイル全体を1つのブロックとして処理
        test_blocks = [content]
        print("'Test no' マーカーが見つからないため、ファイル全体を1ブロックとして処理します")
    else:
        # 各 Test no の位置から次の Test no の位置までをブロックとして切り出す
        for i in range(len(test_no_positions)):
            start_pos = test_no_positions[i]
            end_pos = test_no_positions[i+1] if i < len(test_no_positions) - 1 else len(content)
            test_blocks.append(content[start_pos:end_pos])
    
    print(f"処理するブロック数: {len(test_blocks)}")
    
    for test_block in test_blocks:
        
        # 各項目を抽出（フィールド名を指定）
        test_no = extract_field(test_block, "Test no")
        item1 = extract_field(test_block, "Item1")
        item2 = extract_field(test_block, "Item2")
        test_sequence = extract_field(test_block, "Test Sequence")
        input_parameter = extract_field(test_block, "Input Parameter")
        test_purpose = extract_field(test_block, "Test Purpose")
        
        # 抽出した情報を辞書としてリストに追加
        test_info = {
            'Test No': test_no,
            'Item1': item1,
            'Item2': item2,
            'Test Sequence': test_sequence,
            'Input Parameter': input_parameter,
            'Test Purpose': test_purpose
        }
        
        test_info_list.append(test_info)
    
    # CSVファイルに書き出し
    if test_info_list:
        fieldnames = ['Test No', 'Item1', 'Item2', 'Test Sequence', 'Input Parameter', 'Test Purpose']
        
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(test_info_list)
        
        print(f"抽出完了: {len(test_info_list)}件のテスト情報を'{output_csv_path}'に保存しました。")
    else:
        print("テスト情報が見つかりませんでした。")

def extract_field(text, field_name):
    """
    テキストから特定のフィールドを抽出する補助関数
    複数行にわたるフィールドにも対応
    
    Args:
        text (str): 検索対象のテキスト
        field_name (str): 抽出するフィールド名（例: "Test no"）
    
    Returns:
        str: 抽出された値（整形済み）
    """
    # 各フィールドの開始パターン (より柔軟なパターンに)
    field_patterns = [
        r"#\s*Test no\s*:", r"#\s*Item1\s*:", r"#\s*Item2\s*:", 
        r"#\s*Test Sequence\s*:", r"#\s*Input Parameter\s*:", r"#\s*Test Purpose\s*:"
    ]
    
    # 指定されたフィールドのパターンを作成 (より柔軟なマッチングのため)
    field_pattern = rf"#\s*{field_name}\s*:"
    
    # まず通常のケースでマッチを試みる
    start_match = re.search(field_pattern, text, re.IGNORECASE)
    
    if not start_match:
        print(f"フィールド '{field_name}' が見つかりませんでした")
        return ""
    
    start_pos = start_match.end()
    
    # 次のフィールドの開始位置を検索
    end_pos = len(text)
    
    # 全てのフィールドパターンに対して次の出現位置を探す
    for pattern in field_patterns:
        # より柔軟な検索パターン (行頭にこだわらない)
        next_field_match = re.search(pattern, text[start_pos:], re.IGNORECASE)
        if next_field_match:
            next_field_pos = start_pos + next_field_match.start()
            if next_field_pos < end_pos:
                end_pos = next_field_pos
    
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
    if result:
        print(f"フィールド '{field_name}' の抽出結果: '{result[:50]}...'")
    else:
        print(f"フィールド '{field_name}' の内容が空です")
        
    # 処理した行を結合
    return result

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
    delimiter_pattern = r'#\s*\*{8,}'
    delimiter_matches = list(re.finditer(delimiter_pattern, content))
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

if __name__ == "__main__":
    # コマンドライン引数からファイルパスを取得
    if len(sys.argv) > 1:
        perl_file_path = sys.argv[1]
        # 出力ファイル名が指定されていない場合は、入力ファイル名をベースにする
        if len(sys.argv) > 2:
            output_csv_path = sys.argv[2]
        else:
            base_name = os.path.splitext(os.path.basename(perl_file_path))[0]
            output_csv_path = f"{base_name}_test_info.csv"
        
        # デバッグ情報を表示
        print(f"ファイル '{perl_file_path}' を処理します")
        scan_for_fields(perl_file_path)
        
        # 本処理を実行
        extract_test_info(perl_file_path, output_csv_path)
    else:
        print("使用方法: python script.py <入力Perlファイル> [出力CSVファイル]")
