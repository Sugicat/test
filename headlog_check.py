import re
import sys
import glob

def extract_task_values(tx_file):
    """FLG/LUNが変わる前のTASK値を抽出"""
    saved_tasks = []
    prev_flg = prev_lun = prev_task = None
    
    with open(tx_file, 'r') as f:
        for line in f:
            match = re.search(r'FLG=0x([0-9A-Fa-f]+).*LUN=0x([0-9A-Fa-f]+).*TASK=0x([0-9A-Fa-f]+)', line)
            if not match:
                continue
            
            flg, lun, task = match.groups()
            
            if prev_flg is not None and (flg != prev_flg or lun != prev_lun):
                saved_tasks.append(prev_task)
            
            prev_flg, prev_lun, prev_task = flg, lun, task
    
    return saved_tasks

def check_rx_file(rx_file, saved_tasks):
    """rxファイルで保存されたTASK値が最後の行以外に出現するかチェック"""
    if not saved_tasks:
        return True
    
    with open(rx_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        return True
    
    # 最後の行以外をチェック
    for line in lines[:-1]:
        match = re.search(r'TASK=0x([0-9A-Fa-f]+)', line)
        if match and match.group(1) in saved_tasks:
            print(f"FAIL: {rx_file} - TASK=0x{match.group(1)} found in non-last line")
            return False
    
    return True

def main():
    tx_files = glob.glob("tx_*.txt")
    if not tx_files:
        print("Error: No tx_*.txt files found")
        sys.exit(1)
    
    overall_pass = True
    
    for tx_file in tx_files:
        try:
            saved_tasks = extract_task_values(tx_file)
            
            # 対応するrxファイルを検索
            rx_file = tx_file.replace('tx_', 'rx_')
            
            if rx_file in glob.glob("rx_*.txt"):
                if not check_rx_file(rx_file, saved_tasks):
                    overall_pass = False
            else:
                print(f"Warning: {rx_file} not found")
        
        except Exception as e:
            print(f"Error processing {tx_file}: {e}")
            overall_pass = False
    
    if overall_pass:
        print("PASS")
        sys.exit(0)
    else:
        print("FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()