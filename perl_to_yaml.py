import yaml
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerlConfigConverter:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        logger.info(f"Input directory: {self.input_dir.absolute()}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _parse_perl_variable(self, line: str):
        """Perl変数の行をパースする"""
        # デバッグ出力を追加
        print(f"Parsing line: [{line}]")  # 行の内容を[]で囲んで表示
        
        # 空行チェック
        if not line or line.isspace():
            print("Empty line detected")
            return None, None

        # Product行の処理
        if 'Product:' in line:
            product = line.split('Product:')[1].strip()
            print(f"Found product: {product}")
            return 'Product', product

        # スカラー変数のパース（ourの有無に対応）
        scalar_match = re.match(r'(?:our\s+)?\$(\w+)\s*=\s*[\'"]?(.*?)[\'"]?\s*;', line)
        if scalar_match:
            name, value = scalar_match.group(1), scalar_match.group(2).strip('\'"')
            print(f"Matched scalar: name={name}, value={value}")
            return name, value

        # 配列のパース（複数行対応）
        array_match = re.match(r'(?:our\s+)?@(\w+)\s*=\s*\((.*)', line)
        if array_match:
            name = array_match.group(1)
            values_str = array_match.group(2)
            if not values_str.endswith(');'):
                print(f"Multi-line array detected: {name}")
                return 'array_start', name
            values = [v.strip(' \'"') for v in values_str.rstrip(');').split(',')]
            print(f"Matched array: name={name}, values={values}")
            return name, values

        # ハッシュのパース（複数行対応）
        hash_match = re.match(r'(?:our\s+)?%(\w+)\s*=\s*\((.*)', line)
        if hash_match:
            name = hash_match.group(1)
            if not line.rstrip().endswith(');'):
                print(f"Multi-line hash detected: {name}")
                return 'hash_start', name
            pairs = [p.strip(' \'"') for p in hash_match.group(2).rstrip(');').split('=>')]
            hash_dict = dict(zip(pairs[::2], pairs[1::2]))
            print(f"Matched hash: name={name}, dict={hash_dict}")
            return name, hash_dict

        print(f"No match for line: [{line}]")
        return None, None

    def convert_file(self, perl_file: Path):
        """Perlファイルを解析してディクショナリに変換する"""
        logger.info(f"Converting file: {perl_file}")
        config_dict = {}
        current_product = None

        try:
            with perl_file.open('r', encoding='shift_jis') as f:
                print(f"\nReading file: {perl_file}")
                content = f.read()
                print("File content:")
                print("-" * 50)
                print(content)
                print("-" * 50)
                
                lines = content.splitlines()
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    print(f"\nProcessing line {i+1}: [{line}]")
                    
                    if not line or line.startswith('#') and 'Product:' not in line:
                        i += 1
                        continue

                    name, value = self._parse_perl_variable(line)
                    
                    if name == 'Product':
                        current_product = value
                        config_dict[current_product] = {}
                    elif name and current_product:
                        if name == 'array_start':
                            # 複数行の配列を処理
                            array_lines = []
                            while i < len(lines) and not lines[i].rstrip().endswith(');'):
                                array_lines.append(lines[i].strip())
                                i += 1
                            if i < len(lines):
                                array_lines.append(lines[i].strip())
                            array_str = ' '.join(array_lines)
                            print(f"Complete array: {array_str}")
                            # ここで配列を解析
                        elif name == 'hash_start':
                            # 複数行のハッシュを処理
                            hash_lines = []
                            while i < len(lines) and not lines[i].rstrip().endswith(');'):
                                hash_lines.append(lines[i].strip())
                                i += 1
                            if i < len(lines):
                                hash_lines.append(lines[i].strip())
                            hash_str = ' '.join(hash_lines)
                            print(f"Complete hash: {hash_str}")
                            # ここでハッシュを解析
                        else:
                            config_dict[current_product][name] = value
                    
                    i += 1

            print("\nFinal config_dict:", config_dict)
            return config_dict

        except Exception as e:
            logger.error(f"Error converting file: {e}", exc_info=True)
            raise

    def convert_all_files(self):
        logger.info("Starting conversion of all files")
        
        perl_files = list(self.input_dir.glob('*.pl'))
        print(f"Found Perl files: {perl_files}")
        
        for perl_file in perl_files:
            try:
                config_dict = self.convert_file(perl_file)
                if not config_dict:
                    print(f"No data extracted from {perl_file}")
                    continue
                    
                yaml_file = self.output_dir / f"{perl_file.stem}.yml"
                
                with yaml_file.open('w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, 
                             allow_unicode=True, 
                             default_flow_style=False,
                             sort_keys=False)
                print(f"Created YAML file: {yaml_file}")
                
            except Exception as e:
                logger.error(f"Error processing file {perl_file}: {e}", exc_info=True)

if __name__ == "__main__":
    converter = PerlConfigConverter("perl_configs", "yaml_configs")
    converter.convert_all_files()
