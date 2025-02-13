# test

import re
import yaml
from pathlib import Path
from typing import Dict, Any

class PerlConfigConverter:
    """Perlの設定ファイルをYAMLに変換するコンバーター"""

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _parse_perl_variable(self, line: str) -> tuple[Optional[str], Any]:
        """Perl変数の行をパースする"""
        # スカラー変数のパース
        scalar_match = re.match(r'\$(\w+)\s*=\s*[\'"]?(.*?)[\'"]?\s*;', line)
        if scalar_match:
            return scalar_match.group(1), scalar_match.group(2)

        # 配列のパース
        array_match = re.match(r'@(\w+)\s*=\s*\((.*?)\);', line)
        if array_match:
            values = [v.strip(' \'\"') for v in array_match.group(2).split(',')]
            return array_match.group(1), values

        # ハッシュのパース
        hash_match = re.match(r'%(\w+)\s*=\s*\((.*?)\);', line)
        if hash_match:
            pairs = [p.strip(' \'\"') for p in hash_match.group(2).split(',')]
            hash_dict = {}
            for i in range(0, len(pairs), 2):
                if i + 1 < len(pairs):
                    hash_dict[pairs[i]] = pairs[i + 1]
            return hash_match.group(1), hash_dict

        return None, None

    def convert_file(self, perl_file: Path) -> Dict[str, Any]:
        """Perlファイルを解析してディクショナリに変換する"""
        config_dict = {}
        current_product = None

        with perl_file.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 製品セクションの開始を検出
                if line.startswith('# Product:'):
                    current_product = line.split(':')[1].strip()
                    config_dict[current_product] = {}
                    continue

                # 変数定義の解析
                name, value = self._parse_perl_variable(line)
                if name and current_product:
                    config_dict[current_product][name] = value

        return config_dict

    def convert_all_files(self):
        """全てのPerlファイルを変換する"""
        for perl_file in self.input_dir.glob('*.pl'):
            config_dict = self.convert_file(perl_file)
            
            # YAMLファイルとして出力
            yaml_file = self.output_dir / f"{perl_file.stem}.yml"
            with yaml_file.open('w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)

# 使用例
if __name__ == "__main__":
    converter = PerlConfigConverter("./perl_configs", "./yaml_configs")
    converter.convert_all_files()
