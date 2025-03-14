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
        
        # 各項目を抽出
        test_no = extract_field(test_block, r'# Test no\s*:(.*?)(?=#|\n|$)')
        item1 = extract_field(test_block, r'# Item1\s*:(.*?)(?=#|\n|$)')
        item2 = extract_field(test_block, r'# Item2\s*:(.*?)(?=#|\n|$)')
        test_sequence = extract_field(test_block, r'# Test Sequence\s*:(.*?)(?=#|\n|$)')
        input_parameter = extract_field(test_block, r'# Input Parameter\s*:(.*?)(?=#|\n|$)')
        test_purpose = extract_field(test_block, r'# Test Purpose\s*:(.*?)(?=#|\n|$)')
        
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

def extract_field(text, pattern):
    """
    テキストから特定のフィールドを抽出する補助関数
    
    Args:
        text (str): 検索対象のテキスト
        pattern (str): 抽出するための正規表現パターン
    
    Returns:
        str: 抽出された値（空白除去済み）
    """
    match = re.search(pattern, text)
    if match:
        # 空白を除去して返す
        return match.group(1).strip()
    return ""

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
