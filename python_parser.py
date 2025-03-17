#!/usr/bin/env python3
import json
import sys
import os

def load_perl_vars(json_file):
    """
    Perlから出力されたJSON形式の変数データを読み込む
    
    Args:
        json_file: JSONファイルのパス
        
    Returns:
        読み込まれたデータ
    """
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    return data

def display_file_info(data):
    """ファイル情報を表示"""
    print("===== ファイル情報 =====")
    print(f"パス: {data['file']['path']}")
    print(f"パッケージ: {data['file']['package']}")
    print()

def display_variables(data):
    """変数情報を表示"""
    print("===== 変数 =====")
    for name, info in data['variables'].items():
        print(f"{name}: {info['type']}")
        if info['type'] == 'SCALAR':
            print(f"  値: {info['value']}")
        elif info['type'] == 'ARRAY':
            print(f"  要素数: {info['size']}")
            if info['size'] > 0 and info['size'] < 10:  # 小さい配列のみ表示
                print(f"  値: {info['value']}")
        elif info['type'] == 'HASH':
            print(f"  キー: {', '.join(info['keys'])}")
            if len(info['keys']) > 0 and len(info['keys']) < 10:  # 小さいハッシュのみ表示
                print(f"  値: {info['value']}")
    print()

def display_subroutines(data):
    """サブルーチン情報を表示"""
    print("===== サブルーチン =====")
    for name, info in data['subroutines'].items():
        print(f"{name}:")
        # ソースコードは長いので最初の数行だけ表示
        code_lines = info['source'].split('\n')
        preview = '\n'.join(code_lines[:5])
        if len(code_lines) > 5:
            preview += "\n..."
        print(f"  {preview}")
    print()

def display_dependencies(data):
    """依存関係を表示"""
    print("===== 依存モジュール =====")
    for dep in data['dependencies']:
        print(f"{dep['name']} ({dep['file']})")
    print()

def extract_specific_vars(data, var_names=None):
    """
    指定された変数のみを抽出する
    
    Args:
        data: 変数データ
        var_names: 抽出する変数名のリスト (Noneの場合はすべて)
        
    Returns:
        抽出された変数のみを含む辞書
    """
    if var_names is None:
        return data['variables']
    
    result = {}
    for name, info in data['variables'].items():
        base_name = name.split()[0]  # "(scalar)" などの接尾辞を削除
        if base_name in var_names:
            result[name] = info
    
    return result

def export_as_perl(data, output_file=None):
    """
    変数データをPerlスクリプトとして出力する
    
    Args:
        data: 変数データ
        output_file: 出力ファイル名（Noneの場合は標準出力）
    """
    out = sys.stdout
    if output_file:
        out = open(output_file, 'w')
    
    try:
        out.write("#!/usr/bin/env perl\n")
        out.write("# 自動生成されたPerlスクリプト\n\n")
        
        # スカラー変数
        for name, info in data['variables'].items():
            if ' (scalar)' in name:
                var_name = name.split()[0]
                value = info['value']
                if value == 'undef':
                    out.write(f"our ${var_name}; # undef\n")
                elif value.startswith('ARRAY') or value.startswith('HASH') or value.startswith('OBJECT'):
                    out.write(f"# ${var_name} = {value} # 複合型\n")
                else:
                    out.write(f"our ${var_name} = '{value}';\n")
        
        # 配列変数
        for name, info in data['variables'].items():
            if ' (array)' in name:
                var_name = name.split()[0]
                size = info['size']
                if size > 0 and size < 20:  # 小さな配列のみ再現
                    out.write(f"our @{var_name} = (\n")
                    for item in info['value']:
                        out.write(f"    '{item}',\n")
                    out.write(");\n")
                else:
                    out.write(f"# @{var_name} - {size} 要素の配列\n")
        
        # ハッシュ変数
        for name, info in data['variables'].items():
            if ' (hash)' in name:
                var_name = name.split()[0]
                keys = info['keys']
                if len(keys) > 0 and len(keys) < 20:  # 小さなハッシュのみ再現
                    out.write(f"our %{var_name} = (\n")
                    for k, v in info['value'].items():
                        out.write(f"    '{k}' => '{v}',\n")
                    out.write(");\n")
                else:
                    out.write(f"# %{var_name} - {len(keys)} キーのハッシュ\n")
    
    finally:
        if output_file and out != sys.stdout:
            out.close()

def export_as_python(data, output_file=None):
    """
    変数データをPythonスクリプトとして出力する
    
    Args:
        data: 変数データ
        output_file: 出力ファイル名（Noneの場合は標準出力）
    """
    out = sys.stdout
    if output_file:
        out = open(output_file, 'w')
    
    try:
        out.write("#!/usr/bin/env python3\n")
        out.write("# 自動生成されたPythonスクリプト\n\n")
        
        # スカラー変数
        for name, info in data['variables'].items():
            if ' (scalar)' in name:
                var_name = name.split()[0]
                value = info['value']
                if value == 'undef':
                    out.write(f"{var_name} = None\n")
                elif value.startswith('ARRAY') or value.startswith('HASH') or value.startswith('OBJECT'):
                    out.write(f"# {var_name} = {value} # 複合型\n")
                elif value.isdigit() or (value and value[0] == '-' and value[1:].isdigit()):
                    out.write(f"{var_name} = {value}\n")
                else:
                    out.write(f"{var_name} = '{value}'\n")
        
        # 配列変数
        for name, info in data['variables'].items():
            if ' (array)' in name:
                var_name = name.split()[0]
                size = info['size']
                if size > 0 and size < 20:  # 小さな配列のみ再現
                    out.write(f"{var_name} = [\n")
                    for item in info['value']:
                        out.write(f"    '{item}',\n")
                    out.write("]\n")
                else:
                    out.write(f"# {var_name} - {size} 要素のリスト\n")
        
        # ハッシュ変数
        for name, info in data['variables'].items():
            if ' (hash)' in name:
                var_name = name.split()[0]
                keys = info['keys']
                if len(keys) > 0 and len(keys) < 20:  # 小さなハッシュのみ再現
                    out.write(f"{var_name} = {{\n")
                    for k, v in info['value'].items():
                        out.write(f"    '{k}': '{v}',\n")
                    out.write("}\n")
                else:
                    out.write(f"# {var_name} - {len(keys)} キーの辞書\n")
    
    finally:
        if output_file and out != sys.stdout:
            out.close()

def main():
    if len(sys.argv) < 2:
        print("使用法:")
        print("  表示: python script.py perl_vars.json")
        print("  特定の変数抽出: python script.py perl_vars.json --extract var1 var2 ...")
        print("  Perl出力: python script.py perl_vars.json --perl [output.pl]")
        print("  Python出力: python script.py perl_vars.json --python [output.py]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    # コマンドライン引数の解析
    if len(sys.argv) > 2:
        if sys.argv[2] == "--extract":
            # 特定の変数を抽出
            vars_to_extract = sys.argv[3:]
            data = load_perl_vars(json_file)
            extracted = extract_specific_vars(data, vars_to_extract)
            print(json.dumps(extracted, indent=2, ensure_ascii=False))
            return
        
        elif sys.argv[2] == "--perl":
            # Perl形式で出力
            output_file = sys.argv[3] if len(sys.argv) > 3 else None
            data = load_perl_vars(json_file)
            export_as_perl(data, output_file)
            return
        
        elif sys.argv[2] == "--python":
            # Python形式で出力
            output_file = sys.argv[3] if len(sys.argv) > 3 else None
            data = load_perl_vars(json_file)
            export_as_python(data, output_file)
            return
    
    # デフォルト: すべての情報を表示
    data = load_perl_vars(json_file)
    display_file_info(data)
    display_variables(data)
    display_subroutines(data)
    display_dependencies(data)

if __name__ == "__main__":
    main()
