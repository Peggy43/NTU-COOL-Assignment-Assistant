from playwright.sync_api import sync_playwright
import requests
import json
from datetime import datetime

STATE_PATH = "data/cool_state.json"


def login():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)

        context = None

        context = browser.new_context()
        page = context.new_page()

        page.goto("https://cool.ntu.edu.tw")

        print("請登入 NTU COOL...")

        page.wait_for_url(
            "https://cool.ntu.edu.tw/*",
            timeout=300000
        )

        # 存 session
        context.storage_state(path=STATE_PATH)

        print("登入成功，已儲存 session")

        return browser, context
    

# 讀 session
# 從 state 提取 cookies

def load_cookies(path="data/cool_state.json"):

    with open(path, "r") as f:
        state = json.load(f)

    return {c["name"]: c["value"] for c in state["cookies"]}


BASE = "https://cool.ntu.edu.tw/api/v1"


def get_courses(cookies):

    url = f"{BASE}/courses/"
    all_courses = []

    while url:

        res = requests.get(url, cookies=cookies)
        try:
            data = res.json()
        except:
            break

        if isinstance(data, list):
            all_courses.extend(data)

        url = res.links.get("next", {}).get("url")
    print("Total courses:", len(all_courses))
    return all_courses


def get_assignments(course_id, cookies):

    url = f"{BASE}/courses/{course_id}/assignments?per_page=100"
    results = []

    while url:

        res = requests.get(url, cookies=cookies)
        data = res.json()

        results.extend(data)

        url = res.links.get("next", {}).get("url")

    return results



def normalize_start_date(unlock_at, created_at):

    if unlock_at:
        return unlock_at

    if not created_at:
        return None

    dt = datetime.fromisoformat(created_at.replace("Z", ""))

    return dt.replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    
def sync_ntu_cool():

    cookies = load_cookies()

    all_courses = get_courses(cookies)

    # get current term 
    term_ids = [
        c.get("enrollment_term_id")
        for c in all_courses
        if c.get("enrollment_term_id") is not None
    ]

    if not term_ids:
        print("沒有在任何課程中找到 'enrollment_term_id'，跳過同步")
        return []

    current_term_id = max(term_ids)

    curr_courses = [
        c for c in all_courses
        if c.get("enrollment_term_id") == current_term_id
        and (c.get("enrollments") or [{}])[0].get("role") == "StudentEnrollment"
    ]

    all_assignments = []

    for course in curr_courses:

        course_name = course["name"]
        course_id = course["id"]

        assignments = get_assignments(course_id, cookies)

        for a in assignments:

            start_date = normalize_start_date(
                a.get("unlock_at"),
                a.get("created_at")
            )

            all_assignments.append({
                "course_id": course_id,
                "course_name": course_name,

                "assignment_id": a.get("id"),
                "assignment_name": a.get("name"),

                "start_date": start_date,
                "due_date": a.get("due_at"),

                "soft_deadline": None,
                "status": "not_started",
                "time_spent": 0,
                "submitted": 0,
                "source": "cool"
            })

    # save
    with open("data/assignments.json", "w", encoding="utf-8") as f:
        json.dump(all_assignments, f, ensure_ascii=False, indent=4)

    print(f"已同步 {len(all_assignments)} 筆作業資料")

    return all_assignments

if __name__ == "__main__":
    login()
    sync_ntu_cool()