import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime
import re

def extract_chinese(text):
    if not text:
        return text

    text = str(text)

    # 保留：中文 + 數字 + 常見全形標點
    matches = re.findall(r'[\u4e00-\u9fff0-9：，。！？（）《》「」]+', text)

    return "".join(matches) if matches else text

class FocusAnalyticsDB:

    @staticmethod
    def get_hw_today_time(assignment_id):
        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(duration), 0)
            FROM focus_log
            WHERE assignment_id = ?
            AND DATE(start_time) = DATE('now')
        """, (assignment_id,))

        result = cursor.fetchone()[0]
        conn.close()

        return int(result or 0)
    @staticmethod
    def get_total_today_time():
        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(duration), 0)
            FROM focus_log
            WHERE DATE(start_time) = DATE('now')
        """)

        result = cursor.fetchone()[0]
        conn.close()

        return int(result or 0)

    @staticmethod
    def get_daily_focus_time():
        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DATE(start_time) as focus_date,
            SUM(duration) as total_seconds
            FROM focus_log
            GROUP BY DATE(start_time)
            ORDER BY DATE(start_time)
        """)

        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_total_hw_time(assignment_id):

        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(duration),0)
            FROM focus_log
            WHERE assignment_id = ?
        """, (assignment_id,))

        seconds = cursor.fetchone()[0]

        conn.close()

        return int(seconds)
    @staticmethod
    def get_course_time():
        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT a.course_name, SUM(f.duration) as total_seconds
            FROM focus_log f
            JOIN assignments a ON f.assignment_id = a.id
            GROUP BY a.course_name
            ORDER BY total_seconds DESC
        """)

        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_sunburst_data():
        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT a.course_name, a.assignment_name, SUM(f.duration) as total_seconds
            FROM focus_log f
            JOIN assignments a ON f.assignment_id = a.id
            GROUP BY a.course_name, a.assignment_name
        """)

        rows = cursor.fetchall()
        conn.close()
        cleaned = []
        for course, assignment, sec in rows:
            cleaned.append((
                extract_chinese(course),
                (assignment),
                sec
            ))

        return cleaned

    @staticmethod
    def get_heatmap_data(days=30):
        conn = sqlite3.connect("data/assignment.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT start_time, duration
            FROM focus_log
            WHERE start_time IS NOT NULL
            AND DATE(start_time) >= DATE('now', ?)
        """, (f"-{days} day",))

        rows = cursor.fetchall()
        conn.close()

        return rows
    
    
class FocusProcessor:

    @staticmethod
    def build_sunburst_df(rows):
        df = pd.DataFrame(rows, columns=["course", "assignment", "seconds"])
        df["hours"] = (df["seconds"] / 3600).round(2)
        return df

    @staticmethod
    def build_heatmap_df(rows):
        df = pd.DataFrame(rows, columns=["start_time", "duration"])
        df["start_time"] = pd.to_datetime(df["start_time"])

        df["weekday"] = df["start_time"].dt.day_name()
        df["hour"] = df["start_time"].dt.hour
        df["minutes"] = (df["duration"] / 60).round(2)

        return df.groupby(["weekday", "hour"])["minutes"].sum().reset_index()

    @staticmethod
    def daily(rows):
        df = pd.DataFrame(rows, columns=["date", "seconds"])
        df["hours"] = (df["seconds"] / 3600).round(2)
        return df
    
class FocusViz:

    @staticmethod
    def plot_sunburst(df):
        fig = px.sunburst(
            df,
            path=["course", "assignment"],
            values="hours"
        )

        fig.update_layout(width=700, height=700, margin=dict(t=40, l=0, r=0, b=0))
        st.plotly_chart(fig, width='stretch')

    @staticmethod
    def plot_heatmap(df):
        pivot = df.pivot_table(
            index="weekday",
            columns="hour",
            values="minutes",
            aggfunc="sum",
            fill_value=0
        )

        fig = px.imshow(
            pivot,
            color_continuous_scale="Blues",
            aspect="auto"
        )

        st.plotly_chart(fig, width='stretch')