'''py
import yaml
import re
from pathlib import Path
import logging

# ロギングの設定
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerlConfigConverter:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        logger.info(f"Input directory: {self.input_dir.absolute()}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        
        # 出力ディレクトリの作成
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _parse_perl_variable(self, line: str):
        """Perl変数の行をパースする"""
        logger.debug(f"Parsing line: {line}")
        
        # スカラー変数のパース
        scalar_match = re.match(r'\$(\w+)\s*=\s*[\'"]?(.*?)[\'"]?\s*;', line)
        if scalar_match:
            name, value = scalar_match.group(1), scalar_match.group(2)
            logger.debug(f"Parsed scalar: {name} = {value}")
            return name, value

        # 配列のパース
        array_match = re.match(r'@(\w+)\s*=\s*\((.*?)\);', line)
        if array_match:
            name = array_match.group(1)
            values = [v.strip(' \'"') for v in array_match.group(2).split(',')]
            logger.debug(f"Parsed array: {name} = {values}")
            return name, values

        # ハッシュのパース
        hash_match = re.match(r'%(\w+)\s*=\s*\((.*?)\);', line)
        if hash_match:
            name = hash_match.group(1)
            pairs = [p.strip(' \'"') for p in hash_match.group(2).split(',')]
            hash_dict = {}
            for i in range(0, len(pairs), 2):
                if i + 1 < len(pairs):
                    hash_dict[pairs[i]] = pairs[i + 1]
            logger.debug(f"Parsed hash: {name} = {hash_dict}")
            return name, hash_dict

        logger.debug("No match found for line")
        return None, None

    def convert_file(self, perl_file: Path):
        """Perlファイルを解析してディクショナリに変換する"""
        logger.info(f"Converting file: {perl_file}")
        config_dict = {}
        current_product = None

        try:
            with perl_file.open('r', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"File content:\n{content}")
                
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#') and not 'Product:' in line:
                        continue

                    if 'Product:' in line:
                        current_product = line.split('Product:')[1].strip()
                        logger.info(f"Found product: {current_product}")
                        config_dict[current_product] = {}
                        continue

                    name, value = self._parse_perl_variable(line)
                    if name and current_product:
                        logger.debug(f"Adding to config: {current_product}.{name} = {value}")
                        config_dict[current_product][name] = value

            logger.info(f"Conversion result: {config_dict}")
            return config_dict

        except Exception as e:
            logger.error(f"Error converting file: {e}", exc_info=True)
            raise

    def convert_all_files(self):
        """全てのPerlファイルを変換する"""
        logger.info("Starting conversion of all files")
        
        perl_files = list(self.input_dir.glob('*.pl'))
        logger.info(f"Found Perl files: {perl_files}")
        
        for perl_file in perl_files:
            try:
                config_dict = self.convert_file(perl_file)
                yaml_file = self.output_dir / f"{perl_file.stem}.yml"
                
                logger.info(f"Writing to YAML file: {yaml_file}")
                with yaml_file.open('w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
                logger.info(f"Successfully converted {perl_file} to {yaml_file}")
                
            except Exception as e:
                logger.error(f"Error processing file {perl_file}: {e}", exc_info=True)

if __name__ == "__main__":
    print("Current working directory:", Path.cwd())
    
    converter = PerlConfigConverter("perl_configs", "yaml_configs")
    converter.convert_all_files()
'''
