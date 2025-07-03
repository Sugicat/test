import re
import sys
import os

def extract_task_flag(filepath):
    """ファイルからTASKとFLAGの値を抽出"""
    tasks = []
    flags = []
    
    with open(filepath, 'r') as f:
        for line in f:
            # TASKの値を抽出
            task_match = re.search(r'TASK=(\w+)', line)
            if task_match:
                tasks.append(task_match.group(1))
            
            # FLAGの値を抽出
            flag_match = re.search(r'FLG=(\w+)', line)
            if flag_match:
                flags.append(flag_match.group(1))
    
    return tasks, flags

def extract_saved_tasks(filepath):
    """FLG/LUNが変わる前のTASK値を抽出（元の仕様）"""
    saved_tasks = []
    prev_flg = prev_lun = prev_task = None
    
    with open(filepath, 'r') as f:
        for line in f:
            match = re.search(r'FLG=0x([0-9A-Fa-f]+).*LUN=0x([0-9A-Fa-f]+).*TASK=0x([0-9A-Fa-f]+)', line)
            if not match:
                continue
            
            flg, lun, task = match.groups()
            
            if prev_flg is not None and (flg != prev_flg or lun != prev_lun):
                saved_tasks.append(prev_task)
            
            prev_flg, prev_lun, prev_task = flg, lun, task
    
    return saved_tasks

def compare_task(tx_file, rx_file, output_file):
    """txファイルとrxファイルを比較"""
    try:
        # txファイルから保存すべきTASK値を抽出
        saved_tasks = extract_saved_tasks(tx_file)
        
        if not saved_tasks:
            output_file.write(f"SKIP: {tx_file} -> {rx_file} (No saved tasks)\n")
            return True
        
        # rxファイルをチェック
        with open(rx_file, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            output_file.write(f"SKIP: {rx_file} is empty\n")
            return True
        
        # 最後の行以外をチェック
        for i, line in enumerate(lines[:-1]):
            match = re.search(r'TASK=0x([0-9A-Fa-f]+)', line)
            if match and match.group(1) in saved_tasks:
                output_file.write(f"FAIL: {rx_file} line {i+1} - TASK=0x{match.group(1)} found in non-last line\n")
                return False
        
        output_file.write(f"PASS: {tx_file} -> {rx_file}\n")
        return True
    
    except Exception as e:
        output_file.write(f"ERROR: {tx_file} -> {rx_file} - {e}\n")
        return False

def main():
    # 出力ファイルをオープン
    with open('output_tasktag_compare_result.txt', 'w') as output_file:
        # ループの回数を定義
        num_files = 10
        
        overall_pass = True
        
        for i in range(num_files):
            tx_file = f"logger_tx_{i}.txt"
            rx_file = f"logger_rx_{i}.txt"
            
            # ファイルの存在確認
            if not os.path.exists(tx_file):
                output_file.write(f"SKIP: {tx_file} not found\n")
                continue
            
            if not os.path.exists(rx_file):
                output_file.write(f"SKIP: {rx_file} not found\n")
                continue
            
            # ファイルの比較
            result = compare_task(
                f"priority_commands_overtaking_check/{tx_file}",
                f"priority_commands_overtaking_check/{rx_file}",
                output_file
            )
            
            if not result:
                overall_pass = False
    
    # 結果を標準出力
    if overall_pass:
        print("PASS")
        sys.exit(0)
    else:
        print("FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()