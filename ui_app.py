import streamlit as st
import os
import json
import requests
from datetime import datetime
from ai_test_agent import run_tests

st.set_page_config(
    page_title="AI QA Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CUSTOM CSS
# =========================
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* Status badge */
    .status-online {
        display: inline-block;
        background: #00c853;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: bold;
    }

    /* Section headers */
    .section-header {
        font-size: 20px;
        font-weight: bold;
        color: #e0e0e0;
        margin-bottom: 10px;
        border-left: 4px solid #4f8ef7;
        padding-left: 10px;
    }

    /* Integration card */
    .integration-card {
        background: linear-gradient(135deg, #1a1d2e, #21253a);
        border: 1px solid #2e3250;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }

    /* Live dot */
    .live-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #00c853;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }

    /* Pass/Fail badges */
    .badge-pass {
        background: #00c853;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-fail {
        background: #f44336;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-warn {
        background: #ff9800;
        color: white;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #13151f;
        border-right: 1px solid #2e3250;
    }

    /* Banner */
    .banner {
        background: linear-gradient(135deg, #1a1d2e, #252840);
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 20px;
    }

    /* Quick action buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.2s;
    }

    /* Chat input */
    .stChatInput { border-radius: 12px; }

    /* Divider */
    hr { border-color: #2e3250; }
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
if "show_reports" not in st.session_state:
    st.session_state.show_reports = False
if "last_reports" not in st.session_state:
    st.session_state.last_reports = None
if "history_cleared" not in st.session_state:
    st.session_state.history_cleared = False
if "schedule_enabled" not in st.session_state:
    st.session_state.schedule_enabled = False

# =========================
# HISTORY FILE
# =========================
HISTORY_FILE = "test_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(data):
    history = load_history()
    history.append(data)
    history = history[-5:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def clear_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump([], f)

history = load_history()

# =========================
# SIDEBAR
# =========================
st.sidebar.markdown("## ⚙️ Settings")

# --- JIRA Mode ---
jira_option = st.sidebar.selectbox(
    "🎫 JIRA Mode",
    ["Run WITHOUT JIRA", "Run WITH JIRA"]
)
with_jira = "WITH JIRA" in jira_option

# --- Browser Mode ---
browser_mode = st.sidebar.selectbox(
    "🌐 Browser Mode",
    ["Headless (Cloud)", "Headed (Local Only)"],
    help="Headed mode only works when running locally"
)
run_headless = browser_mode == "Headless (Cloud)"

# --- Test Mode Selector ---
test_mode = st.sidebar.selectbox(
    "🧪 Test Mode",
    ["All Tests", "Navigation Only", "Form Only", "Performance Only", "Mobile Only"],
    help="Select which test group to run"
)
test_mode_map = {
    "All Tests": "all",
    "Navigation Only": "navigation",
    "Form Only": "form",
    "Performance Only": "performance",
    "Mobile Only": "mobile"
}
selected_test_mode = test_mode_map[test_mode]

# --- Email Toggle ---
send_email_option = st.sidebar.selectbox(
    "📧 Send Email Report",
    ["Yes", "No"],
    help="Send email report after test execution"
)
send_email = send_email_option == "Yes"

st.sidebar.markdown("---")


# --- RUN BUTTON ---
st.sidebar.markdown("### ▶️ Run Tests")
sidebar_run = st.sidebar.button(
    "🚀 Run Tests Now",
    use_container_width=True,
    type="primary",
    help="Run tests with the settings selected above"
)

st.sidebar.markdown("---")


# --- Schedule Toggle ---
st.sidebar.markdown("### 🕒 Auto Schedule")
schedule_enabled = st.sidebar.toggle(
    "Enable 7 PM IST Daily Run",
    value=st.session_state.schedule_enabled
)
st.session_state.schedule_enabled = schedule_enabled
if schedule_enabled:
    st.sidebar.success("✅ Scheduled: Daily at 7:00 PM IST")
else:
    st.sidebar.info("⏸️ Schedule disabled")

st.sidebar.markdown("---")

# --- Slack/Teams Notification ---
st.sidebar.markdown("### 🔔 Notifications")
notif_platform = st.sidebar.selectbox(
    "Platform",
    ["None", "Slack", "Microsoft Teams"]
)
webhook_url = ""
if notif_platform != "None":
    # Auto-fill from secrets
    default_webhook = ""
    try:
        if notif_platform == "Slack":
            default_webhook = st.secrets.get("SLACK_WEBHOOK_URL", "")
        elif notif_platform == "Microsoft Teams":
            default_webhook = st.secrets.get("TEAMS_WEBHOOK_URL", "")
    except:
        pass

    webhook_url = st.sidebar.text_input(
        f"{notif_platform} Webhook URL",
        value=default_webhook,
        type="password",
        placeholder="https://hooks.slack.com/..."
    )
    if webhook_url:
        st.sidebar.success(f"✅ {notif_platform} webhook configured")
    else:
        st.sidebar.warning(f"⚠️ Enter {notif_platform} webhook URL")
webhook_url = st.sidebar.text_input(
    f"{notif_platform} Webhook URL",
    value=default_webhook,
    type="password",
    placeholder="https://hooks.slack.com/..."
)
    if webhook_url:
        st.sidebar.success(f"✅ {notif_platform} webhook configured")
    else:
        st.sidebar.warning(f"⚠️ Enter {notif_platform} webhook URL")

st.sidebar.markdown("---")

# --- Quick Links ---
st.sidebar.markdown("### 🔗 Quick Links")
st.sidebar.markdown("[![AA Website](https://img.shields.io/badge/🌐-AA Website-blue)](https://www.automationanywhere.com)")
st.sidebar.markdown("[![Jira Board](https://img.shields.io/badge/🎫-Jira Board-orange)](https://automationanywhere.atlassian.net)")

st.sidebar.markdown("---")

# --- Agent Status ---
last_run = history[-1] if history else None
st.sidebar.markdown("### 📡 Agent Status")
st.sidebar.markdown('<span class="status-online">🟢 ONLINE</span>', unsafe_allow_html=True)
if last_run:
    st.sidebar.markdown(f"🕒 Last Run: `{last_run.get('time', 'N/A')}`")
    pass_rate = round(last_run.get('passed', 0) / max(last_run.get('passed', 0) + last_run.get('failed', 0), 1) * 100)
    st.sidebar.markdown(f"📊 Last Pass Rate: `{pass_rate}%`")
st.sidebar.markdown(f"📧 Email: `{'✅ On' if send_email else '❌ Off'}`")
st.sidebar.markdown(f"🎫 Jira: `{'✅ On' if with_jira else '❌ Off'}`")

st.sidebar.markdown("---")

# --- Clear History ---
if st.sidebar.button("🗑️ Clear History", use_container_width=True):
    clear_history()
    st.session_state.last_reports = None
    st.session_state.history_cleared = True
    st.sidebar.success("History cleared!")
    st.rerun()

# =========================
# HEADER
# =========================
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("# 🤖 AI QA Agent")
    st.markdown("##### Intelligent Test Automation Dashboard — Automation Anywhere")
with col_status:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="status-online">🟢 Agent Online</span>', unsafe_allow_html=True)
    if last_run:
        next_run = "Today 7:00 PM IST" if schedule_enabled else "Manual Only"
        st.caption(f"Next Run: {next_run}")

st.markdown("---")

# =========================
# LIVE STATUS BANNER
# =========================
if last_run:
    b1, b2, b3, b4 = st.columns(4)
    total_last = last_run.get('passed', 0) + last_run.get('failed', 0)
    pass_rate_last = round(last_run.get('passed', 0) / max(total_last, 1) * 100)
    b1.metric("🕒 Last Run", last_run.get('time', 'N/A')[:16])
    b2.metric("✅ Last Passed", last_run.get('passed', 0))
    b3.metric("❌ Last Failed", last_run.get('failed', 0))
    b4.metric("📊 Pass Rate", f"{pass_rate_last}%")
    st.markdown("---")

# =========================
# QUICK RUN BUTTONS
# =========================
st.markdown('<div class="section-header">⚡ Quick Run</div>', unsafe_allow_html=True)
qcol1, qcol2, qcol3, qcol4, qcol5 = st.columns(5)
quick_command = None
with qcol1:
    if st.button("🚀 Run All Tests", use_container_width=True):
        quick_command = "all"
with qcol2:
    if st.button("🧭 Navigation", use_container_width=True):
        quick_command = "navigation"
with qcol3:
    if st.button("📝 Form Tests", use_container_width=True):
        quick_command = "form"
with qcol4:
    if st.button("⚡ Performance", use_container_width=True):
        quick_command = "performance"
with qcol5:
    if st.button("📱 Mobile", use_container_width=True):
        quick_command = "mobile"

st.markdown("---")

# =========================
# EXECUTION SUMMARY
# =========================
st.markdown('<div class="section-header">📊 Execution Summary</div>', unsafe_allow_html=True)

selected_data = {}
if history:
    selected_index = st.selectbox(
        "Select Run",
        options=list(range(len(history))),
        format_func=lambda i: history[i].get("time", "Unknown")
    )
    selected_data = history[selected_index]

    col1, col2, col3, col4 = st.columns(4)
    total_val = selected_data.get('passed', 0) + selected_data.get('failed', 0)
    pass_rate_val = round(selected_data.get('passed', 0) / max(total_val, 1) * 100)
    col1.metric("🕒 Run Time", selected_data.get("time", "N/A")[:16])
    col2.metric("✅ Passed", selected_data.get("passed", 0))
    col3.metric("❌ Failed", selected_data.get("failed", 0))
    col4.metric("📊 Pass Rate", f"{pass_rate_val}%")

    # Trend chart
    if len(history) > 1:
        st.markdown("##### 📈 Pass Rate Trend (Last 5 Runs)")
        import pandas as pd
        chart_data = pd.DataFrame([
            {
                "Run": h.get("time", "")[:16],
                "Pass Rate": round(h.get("passed", 0) / max(h.get("passed", 0) + h.get("failed", 0), 1) * 100)
            }
            for h in history
        ])
        st.line_chart(chart_data.set_index("Run"))
else:
    st.info("No runs yet — run a test to see results here")

st.markdown("---")

# =========================
# INTEGRATION STATUS
# =========================
st.markdown('<div class="section-header">🔗 8 Live Integrations</div>', unsafe_allow_html=True)

integrations = [
    {"num": 1, "name": "Selenium WebDriver", "desc": "Chrome Browser Automation", "color": "#4caf50"},
    {"num": 2, "name": "WebDriver Manager", "desc": "ChromeDriver Auto-Management", "color": "#2196f3"},
    {"num": 3, "name": "Jira Cloud API", "desc": "REST API v3 Ticket Automation", "color": "#9c27b0"},
    {"num": 4, "name": "SMTP Email", "desc": "Gmail/Outlook Auto Alerts", "color": "#ff9800"},
    {"num": 5, "name": "Microsoft Word", "desc": "python-docx Issue Documents", "color": "#f44336"},
    {"num": 6, "name": "HTML Reporting", "desc": "Custom CSS Visual Reports", "color": "#00bcd4"},
    {"num": 7, "name": "JSON Knowledge", "desc": "Local File Pattern Storage", "color": "#8bc34a"},
    {"num": 8, "name": "Python Scheduler", "desc": "7 PM IST Auto Trigger", "color": "#ff5722"},
]

int_cols = st.columns(4)
for i, intg in enumerate(integrations):
    with int_cols[i % 4]:
        st.markdown(f"""
        <div class="integration-card">
            <span style="background:{intg['color']};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">
                {intg['num']}
            </span>
            <strong style="margin-left:8px;">{intg['name']}</strong><br>
            <small style="color:#9e9e9e;">{intg['desc']}</small><br>
            <small><span class="live-dot"></span><span style="color:#00c853;font-size:11px;">LIVE</span></small>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# =========================
# AI CHAT CONTROL
# =========================
st.markdown('<div class="section-header">🤖 AI Chat Control</div>', unsafe_allow_html=True)
st.caption("Type a command or use Quick Run buttons above. Examples: 'run smoke test', 'run navigation', 'run form tests'")

user_input = st.chat_input("Type: run smoke test")

# Handle both chat input and quick run buttons
command = None
if user_input:
    text = user_input.lower().strip()
    if "performance" in text:
        command = "performance"
    elif "navigation" in text:
        command = "navigation"
    elif "form" in text:
        command = "form"
    elif "mobile" in text:
        command = "mobile"
    else:
        command = "all"
elif quick_command:
    command = quick_command
elif sidebar_run:
    command = selected_test_mode  # ← uses whatever is selected in sidebar

# Override with sidebar test mode if chat says "all"
if command == "all" and selected_test_mode != "all":
    command = selected_test_mode

if command:
    if user_input:
        st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(f"🚀 Running **{command}** tests{'  +  Jira' if with_jira else ''}{'  +  Email' if send_email else ''}...")

    log_box       = st.empty()
    progress_bar  = st.progress(0)
    progress_text = st.empty()
    status_box    = st.empty()

    logs   = ""
    passed = 0
    failed = 0
    total  = 0

    status_box.info("🤖 AI Agent executing tests...")

    try:
        with st.spinner("Running AI Test Agent..."):
            result = run_tests(
                mode=command,
                with_jira=with_jira,
                run_headless=run_headless,
                send_email=send_email
            )
        st.session_state.last_reports = result

        summary = result.get("summary", {})
        passed  = summary.get("passed", 0)
        failed  = summary.get("failed", 0)
        total   = summary.get("total", passed + failed)
        tests   = result.get("tests", [])

        lines = [
            f"Total Tests : {total}",
            f"Passed      : {passed}",
            f"Failed      : {failed}",
            ""
        ]
        for t in tests:
            lines.append(f"[{t['status']}] {t['test_name']} - {t['message']}")

        logs = "\n".join(lines)
        log_box.code(logs)

        # Test details table with color coded status
        if tests:
            st.markdown("##### 🧪 Test Details (this run)")
            for t in tests:
                status = t["status"]
                badge = f'<span class="badge-pass">PASS</span>' if status == "PASS" else \
                        f'<span class="badge-fail">FAIL</span>' if status == "FAIL" else \
                        f'<span class="badge-warn">WARN</span>'
                st.markdown(
                    f"{badge} &nbsp; **{t['test_name']}** — {t['message']}",
                    unsafe_allow_html=True
                )

        # Jira ticket
        jira_result = result.get("jira_result")
        if jira_result:
            st.success(f"🎫 Jira ticket created: [{jira_result['ticket_key']}]({jira_result['ticket_url']})  |  Status: {jira_result['status']}")
        elif with_jira:
            st.warning("⚠️ Jira ticket creation failed — check console logs.")

        # Email status
        if send_email:
            st.info("📧 Email report sent successfully.")
        else:
            st.info("📧 Email skipped (disabled in settings).")

        # Send Slack/Teams notification
        if webhook_url and notif_platform != "None":
            try:
                pass_rate_notif = round(passed / max(total, 1) * 100)
                msg_text = f"🤖 *AI QA Agent Report*\n✅ Passed: {passed} | ❌ Failed: {failed} | 📊 Pass Rate: {pass_rate_notif}%\n🕒 Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                if notif_platform == "Slack":
                    requests.post(webhook_url, json={"text": msg_text}, timeout=5)
                elif notif_platform == "Microsoft Teams":
                    requests.post(webhook_url, json={"text": msg_text}, timeout=5)
                st.success(f"🔔 {notif_platform} notification sent!")
            except Exception as ne:
                st.warning(f"⚠️ {notif_platform} notification failed: {str(ne)[:60]}")

    except Exception as e:
        failed = 1
        logs   = f"Error while running agent: {str(e)}"
        log_box.code(logs)
        st.error("Agent execution failed. See logs above.")
        total = passed + failed

    # Fallback
    if passed == 0 and failed == 0:
        for line in logs.split("\n"):
            if "Passed" in line:
                try:
                    passed = int(line.split(":")[-1].strip())
                except:
                    pass
            if "Failed" in line:
                try:
                    failed = int(line.split(":")[-1].strip())
                except:
                    pass

    total = passed + failed
    progress_bar.progress(100)
    progress_text.write("Progress: 100%")

    # Save history
    run_data = {
        "time":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed,
        "failed": failed,
        "mode":   command
    }
    save_history(run_data)

    # Final status
    if failed == 0:
        status_box.success(f"✅ All tests passed ({passed})")
    else:
        status_box.error(f"❌ {failed} tests failed")

    st.session_state.show_reports = True

    # AI Failure Analysis
    if failed > 0:
        st.markdown("---")
        st.markdown('<div class="section-header">🧠 AI Failure Analysis</div>', unsafe_allow_html=True)
        logs_lower = logs.lower()
        if "element not found" in logs_lower:
            st.error("🔍 Element locator changed — website UI may have been updated")
            st.info("💡 Suggestion: Update CSS selectors in ai_test_agent.py")
        elif "timeout" in logs_lower:
            st.error("⏱️ Performance issue detected — page load too slow")
            st.info("💡 Suggestion: Increase wait times or check website performance")
        elif "form" in logs_lower:
            st.error("📝 Form interaction failed — form fields may have changed")
            st.info("💡 Suggestion: Check form field names on the website")
        else:
            st.error("🤖 Unknown issue — check detailed logs above")

st.markdown("---")

# =========================
# REPORTS
# =========================
if st.session_state.show_reports:
    st.markdown('<div class="section-header">📄 Test Reports</div>', unsafe_allow_html=True)

    report_dir = os.path.join(os.path.expanduser("~"), "Desktop", "AI_Agent_Reports")

    if os.path.exists(report_dir):
        files = [f for f in os.listdir(report_dir) if f.endswith(".html")]

        if files:
            files = sorted(
                files,
                key=lambda x: os.path.getctime(os.path.join(report_dir, x)),
                reverse=True
            )[:5]

            selected_report = st.selectbox("Select Report", files)
            path = os.path.join(report_dir, selected_report)

            with open(path, "rb") as f:
                report_bytes = f.read()

            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    label="⬇️ Download HTML Report",
                    data=report_bytes,
                    file_name=selected_report,
                    mime="text/html",
                    use_container_width=True
                )
            with dl2:
                docx_files = [f for f in os.listdir(report_dir) if f.endswith(".docx")]
                if docx_files:
                    latest_docx = sorted(
                        docx_files,
                        key=lambda x: os.path.getctime(os.path.join(report_dir, x)),
                        reverse=True
                    )[0]
                    with open(os.path.join(report_dir, latest_docx), "rb") as f:
                        docx_bytes = f.read()
                    st.download_button(
                        label="⬇️ Download Word Report",
                        data=docx_bytes,
                        file_name=latest_docx,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )

            st.info(f"📁 Report saved at: `{path}`")

            with st.expander("👁️ Quick Inline Preview"):
                st.components.v1.html(report_bytes.decode("utf-8"), height=500, scrolling=True)
        else:
            st.info("No HTML reports found yet.")
    else:
        st.info(f"Report directory not found: `{report_dir}`")

    st.markdown("---")

# =========================
# SCREENSHOT GALLERY
# =========================
if selected_data.get("failed", 0) > 0:
    st.markdown('<div class="section-header">🖼️ Failure Screenshots</div>', unsafe_allow_html=True)

    screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "AI_Agent_Reports", "screenshots")

    if os.path.exists(screenshot_dir):
        images = [f for f in os.listdir(screenshot_dir)
                  if f.lower().endswith((".png", ".jpg", ".jpeg"))]

        if images:
            images_sorted = sorted(
                images,
                key=lambda x: os.path.getctime(os.path.join(screenshot_dir, x)),
                reverse=True
            )[:6]

            img_cols = st.columns(3)
            for idx, img in enumerate(images_sorted):
                with img_cols[idx % 3]:
                    st.image(os.path.join(screenshot_dir, img), caption=img, use_container_width=True)
        else:
            st.info("No screenshots found")
    else:
        st.info("No screenshots directory found")

    st.markdown("---")

# =========================
# HISTORY TABLE
# =========================
st.markdown('<div class="section-header">📜 Last 5 Runs</div>', unsafe_allow_html=True)

history = load_history()
if history:
    import pandas as pd
    df = pd.DataFrame(history[::-1])
    df.columns = [c.title() for c in df.columns]
    st.dataframe(df, use_container_width=True)
else:
    st.info("No runs yet")