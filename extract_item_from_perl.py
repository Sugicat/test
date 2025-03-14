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
    
    # 正規表現パターンを定義（複数のテスト情報を抽出するため）
    pattern = r'# Test no\s*:(.*?)(?=# Test no|$)'
    
    # フラグsを使用して.が改行にもマッチするようにする
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        test_block = match.group(0)
        
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
    # 各フィールドの開始パターン
    field_patterns = [
        "# Test no", "# Item1", "# Item2", "# Test Sequence", 
        "# Input Parameter", "# Test Purpose"
    ]
    
    # 指定されたフィールドの開始位置を検索
    field_pattern = f"# {field_name}"
    start_match = re.search(f"{field_pattern}\\s*:", text)
    
    if not start_match:
        return ""
    
    start_pos = start_match.end()
    
    # 次のフィールドの開始位置を検索
    end_pos = len(text)
    for pattern in field_patterns:
        # 指定されたフィールド以降で次のフィールドを検索
        next_field_match = re.search(f"(?m)^{pattern}\\s*:", text[start_pos:])
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
        # 行頭の '#' と空白を除去
        line = re.sub(r'^#\s*', '', line.strip())
        if line:  # 空行でなければ追加
            processed_lines.append(line)
    
    # 処理した行を結合
    return ' '.join(processed_lines)

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
        
        extract_test_info(perl_file_path, output_csv_path)
    else:
        print("使用方法: python script.py <入力Perlファイル> [出力CSVファイル]")
