import streamlit as st
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import sqlite3
import time
import re
import plotly.express as px
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cool.analysis import FocusAnalyticsDB, FocusProcessor, FocusViz
from cool.sync import sync_ntu_cool

def to_iso(x):
    if pd.isna(x):
        return None
    if isinstance(x, datetime):
        return x.isoformat()
    if isinstance(x, date):
        return datetime.combine(x, datetime.min.time()).isoformat()
    return x

def add_task(course_id, course_name, assignment_name,
             start_date, due_date, soft_deadline=None):

    start_date = to_iso(start_date)
    due_date = to_iso(due_date)
    soft_deadline = to_iso(soft_deadline)

    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assignments (
            course_id,
            course_name,
            assignment_name,
            start_date,
            due_date,
            soft_deadline,
            status,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        course_id,
        course_name,
        assignment_name,
        start_date,
        due_date,
        soft_deadline,
        "not_started",
        "manual"
    ))

    conn.commit()
    conn.close()

def safe_parse(x):
    if pd.isna(x):
        return None

    if isinstance(x, datetime):
        return x

    if str(x) in ["NaT", "None", "nan", "", "NULL"]:
        return None

    try:
        return datetime.fromisoformat(str(x).replace("Z", ""))
    except:
        return None

def update_task(task_id, soft_deadline=None, due_date=None, start_date=None):
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()
    soft_deadline = to_iso(soft_deadline)
    due_date = to_iso(due_date)
    start_date = to_iso(start_date)
    if soft_deadline:
        cursor.execute("""
            UPDATE assignments
            SET soft_deadline = ?
            WHERE id = ?
        """, (soft_deadline, task_id))

    if due_date:
        cursor.execute("""
            UPDATE assignments
            SET due_date = ?
            WHERE id = ?
        """, (due_date, task_id))

    if start_date:
        cursor.execute("""
            UPDATE assignments
            SET start_date = ?
            WHERE id = ?
        """, (start_date, task_id))

    conn.commit()
    conn.close()

def extract_chinese(text):
    if not text:
        return text

    text = str(text)

    # 保留：中文 + 數字 + 常見全形標點
    matches = re.findall(r'[\u4e00-\u9fff0-9：，。！？（）《》「」]+', text)

    return "".join(matches) if matches else text

def to_df(data):
    rows = []
    for task in data:
        (id, course, start, name,
         due, soft, status, submitted) = task
        # print(f"Raw data - ID: {id}, Course: {course}" )
        progress = calculate_progress(due, start)
        
        color = get_color(due, soft)
        

        rows.append({
            "id": id,
            "作業名稱": name,
            "開始時間": safe_parse(start),
            "Soft Deadline": safe_parse(soft),
            "截止時間": safe_parse(due),
            "目前用時": format_seconds(FocusAnalyticsDB.get_total_hw_time(id)),
            "狀態": color,
            "Progress": progress,
            "Submitted": bool(submitted)
        })

    return pd.DataFrame(rows)

def load_data(show_completed=False):
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    if show_completed:
        cursor.execute("""
            SELECT id, course_name, start_date, assignment_name,
                   due_date, soft_deadline, status, submitted
            FROM assignments
            ORDER BY due_date ASC
        """)
    else:
        cursor.execute("""
            SELECT id, course_name, start_date, assignment_name,
                due_date, soft_deadline, status, submitted
            FROM assignments
            WHERE submitted = 0
            ORDER BY due_date ASC
        """)

    rows = cursor.fetchall()
    conn.close()

    return rows

def calculate_progress(due_date, start_date):
    if not due_date:
        return 0

    try:
        due = safe_parse(due_date)
        start = safe_parse(start_date) if start_date else None
        now = datetime.now()
        if due is None or start is None:
            return 0
        if now > due:
            return 1.0
        total = (due - now).total_seconds()
        all_time = (due - start).total_seconds()

        progress = 1 - (total / all_time) if all_time > 0 else 1
        # print(f"Due: {due}, Start: {start}, Now: {now}, Total: {total}, All Time: {all_time}, Progress: {progress}")
        final_progress = round(max(0, min(1, progress)), 3)
        
        return final_progress

    except:
        return 0

def get_color(due_date, soft_deadline):
    now = datetime.now()

    due = safe_parse(due_date)
    soft = safe_parse(soft_deadline)

    if pd.isna(due):
        return "⚪ 未知"

    if not pd.isna(soft):
        if now > due:
            return "🔴 已逾期"
        elif now > soft:
            return "🟡 超過 Soft Deadline"
        else:
            return "🟢 尚未截止"

    # 沒 soft deadline
    if now > due:
        return "🔴 已逾期"

    if (due - now).total_seconds() <= 2 * 86400:
        return "🟡 即將截止"

    return "🟢 尚未截止"


def show_task(course_tasks, widget_key):

    df = to_df(course_tasks)
    df = df.sort_values(by=["Progress", "id"], ascending=[False, True])
    
    df = df.set_index("id")
    edited_df = st.data_editor(
    df,
    key=widget_key,
    width='stretch',
    column_config={
        
        "Progress": st.column_config.ProgressColumn(
            "距離截止日進度",
            min_value=0,
            max_value=1
        ),

        "開始時間": st.column_config.DatetimeColumn(
            "開始時間",
            format="YYYY-MM-DD HH:mm"
        ),

        "Soft Deadline": st.column_config.DatetimeColumn(
            "Soft Deadline",
            format="YYYY-MM-DD HH:mm"
        ),

        "截止時間": st.column_config.DatetimeColumn(
            "截止時間",
            format="YYYY-MM-DD HH:mm"
        ),
        "Submitted": st.column_config.CheckboxColumn("已繳交"),

        "id": None,
        
    },
    disabled=["作業名稱", "目前用時", "狀態", "id"]
    )
    return edited_df

    
def update_submission(task_id, submitted):
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE assignments
        SET submitted = ?
        WHERE id = ?
    """, (submitted, task_id))

    conn.commit()
    conn.close()

def save_all_changes(df):
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    success_count = 0
    fail_count = 0

    for task_id, row in df.iterrows():
        try:
            t_id = int(task_id)
            
            sub = 1 if row.get("Submitted", False) else 0

            def strict_iso(val):
                if pd.isna(val) or str(val).strip().lower() in ["nat", "none", "nan", "null", ""]:
                    return None
                if isinstance(val, datetime):
                    return val.isoformat()
                if isinstance(val, date):
                    return datetime.combine(val, datetime.min.time()).isoformat()
                return str(val)

            start = strict_iso(row.get("開始時間"))
            soft = strict_iso(row.get("Soft Deadline"))
            due = strict_iso(row.get("截止時間"))

            # print(f"準備寫入 -> ID: {t_id: <4} | Sub: {sub} | Start: {str(start): <20} | Soft: {str(soft): <20} | Due: {str(due)}")

            cursor.execute("""
                UPDATE assignments
                SET start_date = ?, soft_deadline = ?, due_date = ?, submitted = ?
                WHERE id = ?
            """, (start, soft, due, sub, t_id))
            
            if cursor.rowcount == 0:
                print(f"警告：找不到ID {t_id}，沒有更新任何資料！")
                fail_count += 1
            else:
                success_count += 1

        except Exception as e:
            print(f"錯誤：ID {task_id} 更新崩潰，原因：{e}")
            fail_count += 1

    conn.commit()
    conn.close()
    

def format_seconds(seconds):

    seconds = int(seconds)

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    return f"{h:02}:{m:02}:{s:02}"
    
@st.fragment(run_every="1s")
def focus_timer_ui(task_id, selected_task):
    elapsed = st.session_state.elapsed_seconds

    if st.session_state.timer_running:

        timer_start = st.session_state.timer_start
        if timer_start is None:
            timer_start = time.time()

        elapsed += (
            time.time()
            - timer_start
        )
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)

    focus_seconds = 0
    hw_seconds = FocusAnalyticsDB.get_hw_today_time(task_id)
    total_seconds = FocusAnalyticsDB.get_total_today_time()
    session_seconds = 0


    if st.session_state.active_assignment == task_id:

        session_seconds = st.session_state.elapsed_seconds

        if st.session_state.timer_running:

            timer_start = st.session_state.timer_start
            if timer_start is None:
                timer_start = time.time()

            session_seconds += (
                time.time()
                - timer_start
            )

        focus_seconds = session_seconds
        hw_seconds += session_seconds
        total_seconds += session_seconds

    
    if st.session_state.pause_mode:

        remaining = 60 - (
            time.time()
            - st.session_state.pause_start
        )

        if remaining > 0:

            st.warning(
                f"休息中，剩餘 {int(remaining)} 秒"
            )

        else:

            # 自動存檔
            elapsed = st.session_state.elapsed_seconds

            end_time = datetime.now()

            start_time = (
                end_time
                - timedelta(seconds=elapsed)
            )

            save_focus_log(
                assignment_id=st.session_state.active_assignment,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                duration=int(elapsed)
            )


            # 重置
            st.session_state.elapsed_seconds = 0
            st.session_state.timer_running = False
            st.session_state.pause_mode = False
            st.session_state.pause_start = None
            st.session_state.active_assignment = None

            st.rerun()
    st.metric(
        "專注時間",
        format_seconds(focus_seconds)
    )
    
    
    st.metric(
        "今日本作業用時",
        format_seconds(hw_seconds)
    )
    

    st.metric(
        "今日總用時",
        format_seconds(total_seconds)
    )
    
def save_focus_log(
    assignment_id,
    start_time,
    end_time,
    duration
):
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO focus_log (
            assignment_id,
            start_time,
            end_time,
            duration
        )
        VALUES (?, ?, ?, ?)
    """, (
        assignment_id,
        start_time,
        end_time,
        duration
    ))

    conn.commit()
    conn.close()
    
def get_hw_today_time(assignment_id):
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(duration), 0)
        FROM focus_log
        WHERE assignment_id = ?
        AND DATE(start_time) = DATE('now')
    """, (assignment_id,))

    seconds = cursor.fetchone()[0]

    conn.close()

    return seconds

    
# =========================
# UI
# =========================
st.set_page_config(page_title="NTU COOL 作業管理助手", layout="wide")

# Sidebar 
st.sidebar.title("NTU COOL 作業管理助手")

page = st.sidebar.radio(
    "功能",
    [
        "作業資訊總覽",
        "專注模式",
        "用時分析"
    ]
)            

if page == "作業資訊總覽":
    show_completed = st.checkbox("顯示已繳交", value=False)
    data = load_data(show_completed)
else:
    data = load_data(show_completed=True)
course_names = list(set(row[1] for row in data))

if st.sidebar.button("⟳ 與NTU COOL同步"):
        with st.spinner("同步中..."):
            sync_ntu_cool()

        st.toast("同步完成")
        st.rerun()
    
st.sidebar.header("課程篩選")
course_map = {
    extract_chinese(name): name
    for name in course_names
}

with st.sidebar.expander("選擇課程", expanded=True):
    shown_names = list(course_map.keys())
    selected_course = st.radio(
        "選擇課程",
        ["全部"] + shown_names,
        label_visibility="collapsed"
    )
    


# =========================
# Main page
# =========================
if page == "作業資訊總覽":
            
    if selected_course == "全部":

        st.title("全部課程總覽")

        for course in course_names:

            st.subheader(f" {course}")

            course_tasks = [a for a in data if a[1] == course]
            editor_key = f"editor_{course}"
            
            with st.form(key=f"form_{course}"):
                
                edited_df = show_task(course_tasks, widget_key=editor_key)
                
                if st.form_submit_button("儲存變更"):
                    save_all_changes(edited_df)

                    if editor_key in st.session_state:
                        del st.session_state[editor_key]

                    st.success("已儲存！")
                    st.rerun()

                

    else:
        selected_course = course_map[selected_course]
        st.title(f" {selected_course}")

        course_tasks = [a for a in data if a[1] == selected_course]
        editor_key = f"editor_{selected_course}"
        
        with st.form(key=f"form_{selected_course}"):
            
            edited_df = show_task(course_tasks, widget_key=editor_key)
            
            if st.form_submit_button("儲存變更"):
                save_all_changes(edited_df)

                if editor_key in st.session_state:
                    del st.session_state[editor_key]

                st.success("已儲存！")
                st.rerun()
    

elif page == "專注模式":

    st.title("專注模式")
    all_tasks = []

    for row in data:
        task_id = row[0]
        course_name = extract_chinese(row[1])
        assignment_name = row[3]

        all_tasks.append(
            (
                task_id,
                f"[{course_name}]  {assignment_name}"
            )
        )
    task_options = {
        label: task_id
        for task_id, label in all_tasks
    }
    
    selected_task = st.selectbox(
        "選擇要專注的作業",
        sorted(task_options.keys())
    )

    task_id = task_options[selected_task]
    
    if "active_assignment" not in st.session_state:
        st.session_state.active_assignment = None

    if "timer_running" not in st.session_state:
        st.session_state.timer_running = False

    if "timer_start" not in st.session_state:
        st.session_state.timer_start = None

    if "elapsed_seconds" not in st.session_state:
        st.session_state.elapsed_seconds = 0
        
    if "pause_start" not in st.session_state:
        st.session_state.pause_start = None

    if "pause_mode" not in st.session_state:
        st.session_state.pause_mode = False
        

    col1, col2, col3, col4, col5, col6, c7,c8,c9,c10 = st.columns(10)
    
    with col1:

        if st.button("▶ 開始", key=f"start_{task_id}"):

            if (
                st.session_state.active_assignment == task_id
                and
                st.session_state.timer_running
            ):

                st.toast("這個作業已經在計時中")

            elif (
                st.session_state.active_assignment is not None
                and
                st.session_state.active_assignment != task_id
                and
                st.session_state.timer_running
            ):

                st.toast(
                    "已有其他作業正在計時"
                )

            else:

                st.session_state.active_assignment = task_id

                st.session_state.timer_start = time.time()

                st.session_state.timer_running = True
                
                st.session_state.pause_mode = False
                st.session_state.pause_start = None
        
    
    with col2:

        if st.button(
            "⏸ 暫停",
            key=f"pause_{task_id}"
        ):

            if (
                st.session_state.active_assignment == task_id
                and
                st.session_state.timer_running
            ):

                timer_start = st.session_state.timer_start
                if timer_start is None:
                    timer_start = time.time()

                st.session_state.elapsed_seconds += (
                    time.time()
                    - timer_start
                )

                st.session_state.timer_running = False
                st.session_state.pause_mode = True
                st.session_state.pause_start = time.time()
                      
    
    focus_timer_ui(task_id, selected_task)
    
elif page == "用時分析":

    st.title("用時分析")
    focus_data = FocusAnalyticsDB.get_daily_focus_time()

    df_focus = pd.DataFrame(
        focus_data,
        columns=[
            "Date",
            "Seconds"
        ]
    )

    df_focus["Hours"] = (
        df_focus["Seconds"] / 3600
    ).round(2)
    st.subheader("每日專注時間趨勢")

    st.line_chart(
        df_focus.set_index("Date")["Hours"]
    )
    df_course = pd.DataFrame(
        FocusAnalyticsDB.get_course_time(),
        columns=["Course", "Seconds"]
    )

    df_course["時間（小時）"] = (df_course["Seconds"] / 3600).round(2)
    st.subheader("每門課花費時間")
    df_course["課程"] = df_course["Course"].apply(extract_chinese)

    st.bar_chart(
        df_course.set_index("課程")["時間（小時）"]
    )
    df_course["比例"] = (
        df_course["Seconds"] / df_course["Seconds"].sum() * 100
    ).round(1)
    st.dataframe(df_course[["課程", "時間（小時）", "比例"]])
    
    rows = FocusAnalyticsDB.get_sunburst_data()
    df = FocusProcessor.build_sunburst_df(rows)
    st.subheader("課程與作業花費時間比例")
    FocusViz.plot_sunburst(df)
    
    st.subheader("專注時間分布")
    days = st.selectbox(
        "時間範圍（近？天）",
        [7, 30, 90, 365],
        index=1
    )

    rows = FocusAnalyticsDB.get_heatmap_data(days)
    df = FocusProcessor.build_heatmap_df(rows)
    FocusViz.plot_heatmap(df)
    

    
    
st.sidebar.header("＋ 新增作業")
course_options = sorted(shown_names)
course_options.append("（＋ 新增課程）")

selected_course = st.sidebar.selectbox(
        "課程名稱",
        course_options
    )

use_soft_deadline = st.sidebar.checkbox("設定 Soft Deadline")

soft_deadline = None
soft_deadline_datetime = None
    
with st.sidebar.form("add_task_form"):
    

    if selected_course == "（＋ 新增課程）":
        course_name = st.text_input("請輸入課程名稱")
    else:
        course_name = course_map[selected_course]
    
    assignment_name = st.text_input("作業名稱")

    start_date = st.date_input("開始日期")
    start_time = st.time_input("開始時間")
    due_date = st.date_input("截止日期")
    due_time = st.time_input("截止時間")
    start_datetime = datetime.combine(
        start_date,
        start_time
    )

    due_datetime = datetime.combine(
        due_date,
        due_time
    )
    if use_soft_deadline:
        soft_deadline = st.date_input("Soft Deadline 日期")
        soft_deadline_time = st.time_input("Soft Deadline 時間")
        soft_deadline_datetime = datetime.combine(
            soft_deadline,
            soft_deadline_time
        )

    added = st.form_submit_button("新增作業")

    if added:
        add_task(
            course_id=0,  # 你如果還沒 course_id mapping 可以先 0
            course_name=course_name,
            assignment_name=assignment_name,
            start_date=start_datetime,
            due_date=due_datetime,
            soft_deadline=soft_deadline_datetime if use_soft_deadline else None
        )
        st.session_state["task_added"] = True
        st.rerun()
        
if st.session_state.get("task_added"):
    st.toast("已新增作業！")
    del st.session_state["task_added"]
 