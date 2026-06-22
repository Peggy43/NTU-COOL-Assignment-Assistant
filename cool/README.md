# NTU COOL Assignment Manager

一個結合 **NTU COOL 課程同步、作業管理、專注計時與學習分析** 的 Streamlit 應用程式。

---

## 功能特色

### 課程與作業同步

* 自動登入 NTU COOL
* 透過 NTU COOL API 抓取目前學期課程
* 同步所有作業資訊
* 自動建立本地資料庫

---

### 作業管理

* 顯示所有課程作業
* 新增自訂作業
* 編輯開始時間、截止時間與 Soft Deadline
* 標記作業是否已繳交
* 顯示截止進度條

---

### 專注模式

* 選擇作業開始計時
* 記錄專注開始與結束時間
* 自動寫入 focus_log
* 顯示：

  * 本次專注時間
  * 今日該作業用時
  * 今日總專注時間

---

### 用時分析

#### 每日專注時間趨勢

* 每日學習時數折線圖

#### 課程時間分析

* 各課程總用時比較
* 課程時間占比分析

#### Sunburst Chart

課程 → 作業 → 專注時間分布

#### Heatmap

星期 × 小時 專注時間熱度圖

分析最有效率的學習時段

---

## 專案架構

```text
cool/
│
├── app.py
├── main.py
├── sync.py
├── db.py
├── analysis.py
│
├── data/
│   ├── assignment.db
│   ├── assignments.json
│   └── cool_state.json
│
└── README.md
```

---

## 系統流程

```text
NTU COOL
    ↓
Playwright 登入
    ↓
取得 Session Cookie
    ↓
呼叫 NTU COOL API
    ↓
assignments.json
    ↓
SQLite Database
    ↓
Streamlit Dashboard
    ↓
Focus Log Analysis
```

---

## Database Schema

### assignments

| 欄位              | 說明             |
| --------------- | -------------- |
| id              | 主鍵             |
| assignment_id   | NTU COOL 作業 ID |
| course_id       | 課程 ID          |
| course_name     | 課程名稱           |
| assignment_name | 作業名稱           |
| start_date      | 開始時間           |
| due_date        | 截止時間           |
| soft_deadline   | 自訂提醒時間         |
| status          | 狀態             |
| source          | 資料來源           |
| submitted       | 是否已繳交          |

---

### focus_log

| 欄位            | 說明    |
| ------------- | ----- |
| id            | 主鍵    |
| assignment_id | 作業 ID |
| start_time    | 開始時間  |
| end_time      | 結束時間  |
| duration      | 專注秒數  |
| created_at    | 建立時間  |

---

## 安裝

### 1. Clone Repository

```bash
git clone https://github.com/Peggy43/NTU-COOL-Assignment-Assistant.git
cd cool
```

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 安裝 Playwright Browser

```bash
playwright install
```

---

## 使用方式

### 第一次使用

登入 NTU COOL 並建立資料庫

```bash
python main.py
```

執行後會：

1. 開啟 NTU COOL 登入頁面
2. 儲存 Session Cookie
3. 同步課程與作業
4. 建立 SQLite Database

---

### 啟動 Dashboard

```bash
streamlit run app.py
```

---

## 使用技術

### Frontend

* Streamlit

### Data Processing

* Pandas

### Visualization

* Plotly

### Database

* SQLite

### Web Automation

* Playwright

### API Access

* Requests

---

## 未來發展

* 任務優先級推薦
* Deadline 預測與提醒
* 學習效率分析
* 學習習慣追蹤
* 番茄鐘模式
* Google Calendar 整合
* 學習時間預測模型

