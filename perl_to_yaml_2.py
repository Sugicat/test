import yaml
import re
from pathlib import Path
import logging
from typing import Dict, Any, List, Tuple, Set

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RequireResolver:
    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self.required_files: List[Path] = []

    def _find_require_file(self) -> Path:
        """requireをまとめているファイルを探す"""
        # まず、明示的に指定されたrequireファイルを探す
        require_patterns = ['require.pl', 'requires.pl', 'require_all.pl']
        for pattern in require_patterns:
            for file in self.input_dir.rglob(pattern):
                logger.info(f"Found main require file: {file}")
                return file

        # 見つからない場合は、requireが最も多いファイルを探す
        max_requires = 0
        require_file = None
        
        for file in self.input_dir.rglob('*.pl'):
            try:
                with file.open('r', encoding='shift_jis') as f:
                    content = f.read()
                    require_count = len(re.findall(r'require\s+[\'"].*?[\'"];', content))
                    if require_count > max_requires:
                        max_requires = require_count
                        require_file = file
            except Exception as e:
                logger.error(f"Error reading {file}: {e}")

        if require_file:
            logger.info(f"Found require file with most requires ({max_requires}): {require_file}")
            return require_file
        
        raise FileNotFoundError("No require file found")

    def _resolve_path(self, require_path: str, base_path: Path) -> Path:
        """requireパスを絶対パスに解決する"""
        # まず相対パスとして試す
        resolved_path = base_path.parent / require_path
        if resolved_path.exists():
            return resolved_path
            
        # 次にinput_dirからの相対パスとして試す
        resolved_path = self.input_dir / require_path
        if resolved_path.exists():
            return resolved_path
            
        # 最後に完全検索
        for file in self.input_dir.rglob(require_path):
            return file
            
        raise FileNotFoundError(f"Could not resolve require path: {require_path}")

    def _parse_requires(self, file_path: Path) -> List[Path]:
        """ファイルからrequire文を抽出し、パスを解決する"""
        requires = []
        try:
            with file_path.open('r', encoding='shift_jis') as f:
                content = f.read()
                logger.debug(f"Parsing requires from {file_path}")
                
                # require 'file.pl'; またはrequire "file.pl"; の形式を検出
                for match in re.finditer(r'require\s+[\'"](.*?)[\'"];', content):
                    required_file = match.group(1)
                    resolved_path = self._resolve_path(required_file, file_path)
                    logger.debug(f"Resolved {required_file} to {resolved_path}")
                    requires.append(resolved_path)
                    
        except Exception as e:
            logger.error(f"Error parsing requires from {file_path}: {e}")
            
        return requires

    def get_file_order(self) -> List[Path]:
        """requireファイルから依存関係の順序を取得"""
        main_require = self._find_require_file()
        self.required_files = self._parse_requires(main_require)
        logger.info(f"Found {len(self.required_files)} required files in order")
        for i, file in enumerate(self.required_files, 1):
            logger.debug(f"{i}. {file}")
        return self.required_files

class VariableCollector:
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.expressions: Dict[str, str] = {}

    def _parse_line(self, line: str) -> Tuple[Optional[str], Optional[Any]]:
        """1行をパースして変数名と値（または式）を抽出"""
        line = line.strip()
        
        # 空行やコメントをスキップ
        if not line or line.startswith('#'):
            return None, None

        # スカラー変数
        scalar_match = re.match(r'\$(\w+)\s*=\s*(.+?)\s*;', line)
        if scalar_match:
            name, value = scalar_match.group(1), scalar_match.group(2)
            # 計算式かどうかを判定
            if re.search(r'[\+\-\*\/\$]', value):
                return name, ('expression', value)
            # 数値かどうかを判定
            if value.isdigit():
                return name, ('value', int(value))
            if value.replace('.', '').isdigit():
                return name, ('value', float(value))
            # それ以外は文字列として扱う
            return name, ('value', value.strip('\'"'))
            
        return None, None

    def collect_from_file(self, file_path: Path) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """ファイルから変数と式を収集"""
        variables = {}
        expressions = {}
        
        try:
            with file_path.open('r', encoding='shift_jis') as f:
                for line in f:
                    result = self._parse_line(line)
                    if result and result[0]:
                        name, (type_, value) = result
                        if type_ == 'expression':
                            expressions[name] = value
                        else:
                            variables[name] = value
                            
        except Exception as e:
            logger.error(f"Error collecting variables from {file_path}: {e}")
            
        return variables, expressions

class ExpressionEvaluator:
    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables
        
    def evaluate(self, expression: str) -> Any:
        """式を評価"""
        try:
            # 変数を値に置換
            expr = expression
            for var_name, value in self.variables.items():
                expr = expr.replace(f'${var_name}', str(value))
                
            # 基本的な演算のみを許可
            if not all(c.isdigit() or c.isspace() or c in '+-*/.()' for c in expr):
                raise ValueError(f"Invalid characters in expression: {expr}")
                
            return eval(expr, {"__builtins__": {}}, {})
            
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            return expression

class PerlConfigConverter:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def convert_files(self):
        """ファイルの変換メイン処理"""
        logger.info("Starting conversion")
        
        # requireの解決
        resolver = RequireResolver(self.input_dir)
        ordered_files = resolver.get_file_order()
        
        # 変数の収集と式の評価
        collector = VariableCollector()
        all_variables = {}
        all_expressions = {}
        
        # まず全ての変数を収集
        for file_path in ordered_files:
            product_name = file_path.parent.name
            if product_name not in all_variables:
                all_variables[product_name] = {}
                all_expressions[product_name] = {}
                
            vars_, exprs_ = collector.collect_from_file(file_path)
            all_variables[product_name].update(vars_)
            all_expressions[product_name].update(exprs_)
            
        # 式の評価
        result_dict = {}
        for product_name in all_variables:
            result_dict[product_name] = all_variables[product_name].copy()
            evaluator = ExpressionEvaluator(all_variables[product_name])
            
            for var_name, expr in all_expressions[product_name].items():
                result = evaluator.evaluate(expr)
                result_dict[product_name][var_name] = result
                
        # YAML形式で出力
        yaml_file = self.output_dir / "config.yml"
        with yaml_file.open('w', encoding='utf-8') as f:
            yaml.dump(result_dict, f,
                     allow_unicode=True,
                     default_flow_style=False,
                     sort_keys=False)
        logger.info(f"Successfully created {yaml_file}")






"""aaa"""

class VariableCollector:
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.expressions: Dict[str, str] = {}
        self.current_state = None  # 'array' または 'hash'
        self.current_name = None
        self.current_content = []

    def _parse_multiline_array(self, content: List[str]) -> List[Any]:
        """複数行の配列をパース"""
        # 最初と最後の行から@name = (と); を除去
        content[0] = re.sub(r'@\w+\s*=\s*\(', '', content[0])
        content[-1] = re.sub(r'\);.*$', '', content[-1])
        
        # 全ての行を結合
        joined = ' '.join(content)
        
        # コメントを除去
        joined = re.sub(r'#.*?($|\n)', '', joined)
        
        # カンマで分割して各要素をクリーンアップ
        elements = []
        for item in joined.split(','):
            item = item.strip()
            if not item:
                continue
                
            # クォートを除去
            item = item.strip('\'"')
            
            # 数値変換を試みる
            try:
                if '.' in item:
                    elements.append(float(item))
                else:
                    elements.append(int(item))
            except ValueError:
                elements.append(item)
                
        return elements

    def _parse_multiline_hash(self, content: List[str]) -> Dict[str, Any]:
        """複数行のハッシュをパース"""
        # 最初と最後の行から%name = (と); を除去
        content[0] = re.sub(r'%\w+\s*=\s*\(', '', content[0])
        content[-1] = re.sub(r'\);.*$', '', content[-1])
        
        # 全ての行を結合
        joined = ' '.join(content)
        
        # コメントを除去
        joined = re.sub(r'#.*?($|\n)', '', joined)
        
        # キーと値のペアを抽出
        result = {}
        # =>で分割してペアを処理
        pairs = re.findall(r'[\'"]*([^\'",=>\s]+)[\'"]*\s*=>\s*[\'"]*([^\'",\s]+)[\'"]*', joined)
        
        for key, value in pairs:
            # 数値変換を試みる
            try:
                if '.' in value:
                    result[key] = float(value)
                else:
                    result[key] = int(value)
            except ValueError:
                result[key] = value
                
        return result

    def _parse_line(self, line: str) -> Tuple[Optional[str], Optional[Any]]:
        """1行をパースして変数名と値（または式）を抽出"""
        line = line.strip()
        
        # 空行やコメントをスキップ
        if not line or line.startswith('#'):
            return None, None

        # 複数行処理の途中
        if self.current_state:
            self.current_content.append(line)
            if line.strip().endswith(');'):
                # 複数行の終了
                if self.current_state == 'array':
                    result = self._parse_multiline_array(self.current_content)
                else:  # hash
                    result = self._parse_multiline_hash(self.current_content)
                    
                name = self.current_name
                self.current_state = None
                self.current_name = None
                self.current_content = []
                return name, ('value', result)
            return None, None

        # 複数行配列の開始を検出
        array_match = re.match(r'@(\w+)\s*=\s*\(', line)
        if array_match:
            if line.strip().endswith(');'):
                # 1行の配列
                name = array_match.group(1)
                content = [line]
                return name, ('value', self._parse_multiline_array(content))
            else:
                # 複数行の開始
                self.current_state = 'array'
                self.current_name = array_match.group(1)
                self.current_content = [line]
                return None, None

        # 複数行ハッシュの開始を検出
        hash_match = re.match(r'%(\w+)\s*=\s*\(', line)
        if hash_match:
            if line.strip().endswith(');'):
                # 1行のハッシュ
                name = hash_match.group(1)
                content = [line]
                return name, ('value', self._parse_multiline_hash(content))
            else:
                # 複数行の開始
                self.current_state = 'hash'
                self.current_name = hash_match.group(1)
                self.current_content = [line]
                return None, None

        # スカラー変数
        scalar_match = re.match(r'\$(\w+)\s*=\s*(.+?)\s*;', line)
        if scalar_match:
            name, value = scalar_match.group(1), scalar_match.group(2)
            # 計算式かどうかを判定
            if re.search(r'[\+\-\*\/\$]', value):
                return name, ('expression', value)
            # 数値かどうかを判定
            if value.isdigit():
                return name, ('value', int(value))
            if value.replace('.', '').isdigit():
                return name, ('value', float(value))
            # それ以外は文字列として扱う
            return name, ('value', value.strip('\'"'))
            
        return None, None

    def collect_from_file(self, file_path: Path) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """ファイルから変数と式を収集"""
        variables = {}
        expressions = {}
        
        try:
            with file_path.open('r', encoding='shift_jis') as f:
                for line in f:
                    result = self._parse_line(line)
                    if result and result[0]:
                        name, (type_, value) = result
                        if type_ == 'expression':
                            expressions[name] = value
                        else:
                            variables[name] = value
                            
        except Exception as e:
            logger.error(f"Error collecting variables from {file_path}: {e}")
            
        return variables, expressions





if __name__ == "__main__":
    converter = PerlConfigConverter("perl_configs", "yaml_configs")
    converter.convert_files()
