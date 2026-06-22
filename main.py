from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sync import sync_ntu_cool, login
from db import init_db, seed_courses

def main():
    
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    login()
    print("初始化資料庫...")
    init_db()

    print("同步 NTU COOL...")
    data = sync_ntu_cool()

    print("匯入課程資料...")
    seed_courses()

    print("完成！")

if __name__ == "__main__":
    main()
    