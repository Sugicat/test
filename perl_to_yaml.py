import yaml
import re
from pathlib import Path
import logging
from enum import Enum
from typing import Optional, Any, Tuple

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParserState(Enum):
    NORMAL = "normal"
    IN_ARRAY = "in_array"
    IN_HASH = "in_hash"

class PerlConfigConverter:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state = ParserState.NORMAL
        self.current_variable = None
        self.current_content = []

    def _process_array_content(self, content: str) -> list:
        """配列の内容を処理する"""
        content = re.sub(r'^@\w+\s*=\s*\(', '', content)
        content = re.sub(r'\);$', '', content)
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s+', ' ', content)
        
        values = []
        for item in content.split(','):
            item = item.strip(' \'"')
            if item:
                values.append(item)
        return values

    def _process_hash_content(self, content: str) -> dict:
        """ハッシュの内容を処理する"""
        content = re.sub(r'^%\w+\s*=\s*\(', '', content)
        content = re.sub(r'\);$', '', content)
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s+', ' ', content)
        
        pairs = content.split('=>')
        result = {}
        
        for i in range(0, len(pairs)-1):
            key = pairs[i].strip().rstrip(',').strip(' \'"')
            value = pairs[i+1].strip().rstrip(',').strip(' \'"')
            if key and value:
                result[key] = value
                
        return result

    def _parse_perl_variable(self, line: str) -> Tuple[bool, Optional[Tuple[str, Any]]]:
        """Perl変数の行をパースする"""
        # 複数行配列の開始を検出
        array_start = re.match(r'@(\w+)\s*=\s*\(', line)
        if array_start:
            if line.strip().endswith(');'):
                name = array_start.group(1)
                return True, (name, self._process_array_content(line))
            else:
                self.state = ParserState.IN_ARRAY
                self.current_variable = array_start.group(1)
                self.current_content = [line]
                return False, None

        # 複数行ハッシュの開始を検出
        hash_start = re.match(r'%(\w+)\s*=\s*\(', line)
        if hash_start:
            if line.strip().endswith(');'):
                name = hash_start.group(1)
                return True, (name, self._process_hash_content(line))
            else:
                self.state = ParserState.IN_HASH
                self.current_variable = hash_start.group(1)
                self.current_content = [line]
                return False, None

        # スカラー変数のパース
        scalar_match = re.match(r'(?:our\s+)?\$(\w+)\s*=\s*[\'"]?(.*?)[\'"]?\s*;', line)
        if scalar_match:
            name, value = scalar_match.group(1), scalar_match.group(2).strip('\'"')
            return True, (name, value)

        return False, None

    def convert_file(self, perl_file: Path):
        """Perlファイルを解析してディクショナリに変換する"""
        logger.info(f"Converting file: {perl_file}")
        config_dict = {}
        
        # ディレクトリ名から製品名を取得
        product_name = perl_file.parent.name
        config_dict[product_name] = {}

        try:
            with perl_file.open('r', encoding='shift_jis') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # 複数行の配列やハッシュの処理中の場合
                    if self.state in [ParserState.IN_ARRAY, ParserState.IN_HASH]:
                        self.current_content.append(line)
                        if line.strip().endswith(');'):
                            # 複数行の終了
                            full_content = ' '.join(self.current_content)
                            if self.state == ParserState.IN_ARRAY:
                                values = self._process_array_content(full_content)
                                config_dict[product_name][self.current_variable] = values
                            else:  # IN_HASH
                                values = self._process_hash_content(full_content)
                                config_dict[product_name][self.current_variable] = values
                            
                            self.state = ParserState.NORMAL
                            self.current_content = []
                        continue

                    # 通常の行の処理
                    success, result = self._parse_perl_variable(line)
                    if success and result:
                        name, value = result
                        config_dict[product_name][name] = value

            logger.info(f"Conversion result: {config_dict}")
            return config_dict

        except Exception as e:
            logger.error(f"Error converting file: {e}", exc_info=True)
            raise

    def convert_all_files(self):
        """全てのPerlファイルを変換する"""
        logger.info("Starting conversion of all files")
        result_dict = {}
        
        # 入力ディレクトリ内の全サブディレクトリを走査
        for product_dir in [d for d in self.input_dir.iterdir() if d.is_dir()]:
            logger.info(f"Processing directory: {product_dir}")
            
            # 各ディレクトリ内のPerlファイルを処理
            for perl_file in product_dir.glob('*.pl'):
                try:
                    config_dict = self.convert_file(perl_file)
                    if config_dict:
                        result_dict.update(config_dict)
                except Exception as e:
                    logger.error(f"Error processing file {perl_file}: {e}", exc_info=True)

        # 結果をYAMLファイルに書き出し
        if result_dict:
            yaml_file = self.output_dir / "config.yml"
            with yaml_file.open('w', encoding='utf-8') as f:
                yaml.dump(result_dict, f, 
                         allow_unicode=True, 
                         default_flow_style=False,
                         sort_keys=False)
            logger.info(f"Successfully created YAML file: {yaml_file}")
        else:
            logger.warning("No data extracted from any files")

if __name__ == "__main__":
    converter = PerlConfigConverter("perl_configs", "yaml_configs")
    converter.convert_all_files()
