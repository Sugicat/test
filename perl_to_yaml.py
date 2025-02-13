import yaml
import re
from pathlib import Path
import logging
from typing import Dict, Any, Optional
import operator

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerlExpression:
    def __init__(self, expression: str, variables: Dict[str, Any]):
        self.expression = expression
        self.variables = variables
        
    def _resolve_variable(self, var_name: str) -> Any:
        """変数名から値を解決する"""
        # $記号を除去してから変数名を取得
        clean_name = var_name.strip('$')
        value = self.variables.get(clean_name)
        logger.debug(f"Resolving variable {var_name} -> {value}")
        return value
        
    def evaluate(self) -> Any:
        """式を評価する"""
        try:
            # 単純な変数参照の場合
            if self.expression.startswith('$') and not any(op in self.expression for op in ['+', '-', '*', '/', '**']):
                return self._resolve_variable(self.expression)
            
            # 演算式の場合
            expr = self.expression
            # 変数をその値に置換
            var_pattern = r'\$(\w+)'
            for var_match in re.finditer(var_pattern, expr):
                var_name = var_match.group(0)
                value = self._resolve_variable(var_name)
                if value is not None:
                    expr = expr.replace(var_name, str(value))
            
            logger.debug(f"Evaluating expression: {expr}")
            
            # 基本的な演算子のみを許可
            allowed_operators = {
                '+': operator.add,
                '-': operator.sub,
                '*': operator.mul,
                '/': operator.truediv,
                '**': operator.pow
            }
            
            # 式の安全性チェック
            if not all(c.isdigit() or c.isspace() or c in '+-*/.()' for c in expr):
                raise ValueError(f"Invalid characters in expression: {expr}")
            
            # 式を評価
            result = eval(expr, {"__builtins__": {}}, {})
            logger.debug(f"Evaluation result: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Could not evaluate expression '{self.expression}': {e}")
            return self.expression

# 使用例：
# perl_code = """
# $base = 100;
# $rate = 1.5;
# $result = $base * $rate;  # 150になる
# $squared = $base ** 2;    # 10000になる
# """

class PerlConfigConverter:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.in_multiline = False
        self.current_variable = None
        self.multiline_content = []
        self.variables = {}  # 変数の値を保持

    def _parse_value(self, value_str: str) -> Any:
        """値をパースする"""
        # 数値の場合
        if value_str.isdigit():
            return int(value_str)
        if value_str.replace('.', '').isdigit():
            return float(value_str)
            
        # 変数参照や演算式の場合
        if '$' in value_str:
            expr = PerlExpression(value_str, self.variables)
            return expr.evaluate()
            
        # 文字列の場合
        return value_str.strip('\'"')

    def _parse_line(self, line: str):
        """1行をパースする"""
        line = line.strip()
        
        # 空行やコメントをスキップ
        if not line or (line.startswith('#') and 'Product:' not in line):
            return None, None

        # 複数行の配列/ハッシュの途中
        if self.in_multiline:
            self.multiline_content.append(line)
            if line.endswith(');'):
                content = ' '.join(self.multiline_content)
                if content.startswith('@'):
                    # 配列の処理
                    values = re.findall(r'[\'"](.*?)[\'"]|(\$\w+)', content)
                    values = [self._parse_value(v[0] or v[1]) for v in values if v[0] or v[1]]
                    result = values if values else []
                elif content.startswith('%'):
                    # ハッシュの処理
                    pairs = re.findall(r'[\'"]?([\w\-]+)[\'"]?\s*=>\s*([\'"][\w\-]+[\'"]|\$\w+)', content)
                    result = {k: self._parse_value(v) for k, v in pairs} if pairs else {}
                
                self.in_multiline = False
                self.multiline_content = []
                return self.current_variable, result
            return None, None

        # スカラー変数
        scalar_match = re.match(r'\$(\w+)\s*=\s*(.+?)\s*;', line)
        if scalar_match:
            name = scalar_match.group(1)
            value_str = scalar_match.group(2)
            value = self._parse_value(value_str)
            self.variables[name] = value  # 変数の値を保存
            return name, value

        # 配列の開始
        array_match = re.match(r'@(\w+)\s*=\s*\(', line)
        if array_match:
            if line.endswith(');'):
                # 1行の配列
                name = array_match.group(1)
                values = re.findall(r'[\'"](.*?)[\'"]|(\$\w+)', line)
                values = [self._parse_value(v[0] or v[1]) for v in values if v[0] or v[1]]
                return name, values
            else:
                # 複数行の開始
                self.in_multiline = True
                self.current_variable = array_match.group(1)
                self.multiline_content = [line]
                return None, None

        # ハッシュの開始
        hash_match = re.match(r'%(\w+)\s*=\s*\(', line)
        if hash_match:
            if line.endswith(');'):
                # 1行のハッシュ
                name = hash_match.group(1)
                pairs = re.findall(r'[\'"]?([\w\-]+)[\'"]?\s*=>\s*([\'"][\w\-]+[\'"]|\$\w+)', line)
                return name, {k: self._parse_value(v) for k, v in pairs}
            else:
                # 複数行の開始
                self.in_multiline = True
                self.current_variable = hash_match.group(1)
                self.multiline_content = [line]
                return None, None

        return None, None

    def convert_file(self, perl_file: Path):
        """Perlファイルを解析してディクショナリに変換する"""
        logger.info(f"Converting file: {perl_file}")
        
        # ディレクトリ名から製品名を取得
        product_name = perl_file.parent.name
        config_dict = {product_name: {}}
        self.variables.clear()  # 変数をクリア

        try:
            with perl_file.open('r', encoding='shift_jis') as f:
                content = f.read()
                logger.debug(f"File content:\n{content}")

            for line in content.splitlines():
                name, value = self._parse_line(line)
                if name and value is not None:
                    config_dict[product_name][name] = value
                    logger.debug(f"Added to config: {name} = {value}")

            logger.info(f"Conversion result for {perl_file}: {config_dict}")
            return config_dict

        except Exception as e:
            logger.error(f"Error converting file: {e}", exc_info=True)
            raise

    def convert_all_files(self):
        """全てのPerlファイルを変換する"""
        logger.info("Starting conversion of all files")
        result_dict = {}
        
        # サブディレクトリの検索
        subdirs = [d for d in self.input_dir.iterdir() if d.is_dir()]
        logger.info(f"Found subdirectories: {subdirs}")

        if not subdirs:
            # ルートディレクトリのファイルを処理
            perl_files = list(self.input_dir.glob('*.pl'))
            if perl_files:
                for perl_file in perl_files:
                    try:
                        config_dict = self.convert_file(perl_file)
                        if config_dict:
                            result_dict.update(config_dict)
                    except Exception as e:
                        logger.error(f"Error processing file {perl_file}: {e}")
        else:
            # サブディレクトリ内のファイルを処理
            for product_dir in subdirs:
                logger.info(f"Processing directory: {product_dir}")
                perl_files = list(product_dir.glob('*.pl'))
                
                for perl_file in perl_files:
                    try:
                        config_dict = self.convert_file(perl_file)
                        if config_dict:
                            result_dict.update(config_dict)
                    except Exception as e:
                        logger.error(f"Error processing file {perl_file}: {e}")

        # 結果の保存
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
