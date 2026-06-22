import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect("data/assignment.db")
cursor = conn.cursor()

assignment_id = 70  

base_date = datetime.now()

for assignment_id in range(1, 80):  
    for i in range(100):  # 最近 100 天
        day = base_date - timedelta(days=i)

        # 每天 1~3 次專注
        for _ in range(random.randint(0, 1)):
            start = day.replace(hour=random.randint(8, 23), minute=random.randint(0, 59))
            duration = random.randint(60, 540)  # 10min ~ 90min

            end = start + timedelta(seconds=duration)

            cursor.execute("""
                INSERT INTO focus_log (assignment_id, start_time, end_time, duration)
                VALUES (?, ?, ?, ?)
            """, (
                assignment_id,
                start.isoformat(),
                end.isoformat(),
                duration
            ))
            

conn.commit()
conn.close()

print("✅ 假資料已建立完成")