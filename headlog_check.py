import re, sys, glob

def main():
    for tx_file in glob.glob("tx_*.txt"):
        saved_tasks = []
        prev_flg = prev_lun = prev_task = None
        
        # txファイル処理
        with open(tx_file, 'r') as f:
            for line in f:
                m = re.search(r'FLG=0x([0-9A-Fa-f]+).*LUN=0x([0-9A-Fa-f]+).*TASK=0x([0-9A-Fa-f]+)', line)
                if not m: continue
                flg, lun, task = m.groups()
                if prev_flg and (flg != prev_flg or lun != prev_lun):
                    saved_tasks.append(prev_task)
                prev_flg, prev_lun, prev_task = flg, lun, task
        
        # rxファイル処理
        rx_file = tx_file.replace('tx_', 'rx_')
        try:
            with open(rx_file, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
            for line in lines[:-1]:
                m = re.search(r'TASK=0x([0-9A-Fa-f]+)', line)
                if m and m.group(1) in saved_tasks:
                    print("FAIL"); sys.exit(1)
        except: pass
    
    print("PASS"); sys.exit(0)

if __name__ == "__main__": main()