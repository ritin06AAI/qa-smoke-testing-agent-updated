import streamlit as st
import subprocess
import os
import json
from datetime import datetime
from ai_test_agent import run_tests


st.set_page_config(page_title="AI QA Agent", layout="wide")

# =========================
# SESSION STATE
# =========================
if "show_reports" not in st.session_state:
    st.session_state.show_reports = False
if "last_reports" not in st.session_state:
    st.session_state.last_reports = None

# =========================
# HISTORY FILE
# =========================
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

# Always reload fresh on every page run
history = load_history()
# =========================
# HEADER
# =========================
st.markdown("""
<style>
.title { font-size:36px; font-weight:bold; }
.sub { color:gray; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🤖 AI QA Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Intelligent Test Automation Dashboard</div>', unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Settings")

jira_option = st.sidebar.selectbox(
    "JIRA Mode",
    ["Run WITHOUT JIRA", "Run WITH JIRA"]
)

# Browser Mode Dropdown
browser_mode = st.sidebar.selectbox(
    "Browser Mode",
    ["Headless (Cloud)", "Headed (Local Only)"],
    help="Headed mode only works when running locally"
)
run_headless = browser_mode == "Headless (Cloud)"

# Clear History Button
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear History"):
    clear_history()
    st.session_state.last_reports = None
    st.sidebar.success("History cleared!")
    st.rerun()
    
    # Email Toggle
send_email = st.sidebar.selectbox(
    "Send Email Report",
    ["Yes", "No"],
    help="Send email report after test execution"
)
send_email = send_email == "Yes"
    
# =========================
# EXECUTION SUMMARY
# =========================
st.subheader("📊 Execution Summary")

selected_data = {}

if history:
    selected_index = st.selectbox(
        "Select Run",
        options=list(range(len(history))),
        format_func=lambda i: history[i].get("time", "Unknown")
    )
    selected_data = history[selected_index]

col1, col2, col3 = st.columns(3)

if selected_data:
    col1.metric("🕒 Run Time", selected_data.get("time", "N/A"))
    col2.metric("✅ Passed", selected_data.get("passed", 0))
    col3.metric("❌ Failed", selected_data.get("failed", 0))

# =========================
# CHAT CONTROL
# =========================
st.subheader("🤖 AI Chat Control")

user_input = st.chat_input("Type: run smoke test")

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

    st.write(f"DEBUG – mode selected: {command}")

    with_jira = ("WITH JIRA" in jira_option)

    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(f"🚀 Running **{command}** tests{'  +  Jira' if with_jira else ''}...")

    log_box      = st.empty()
    progress_bar = st.progress(0)
    progress_text = st.empty()
    status_box   = st.empty()

    logs   = ""
    passed = 0
    failed = 0
    total  = 0

    status_box.info("🤖 AI Agent executing...")

    try:
        # ------------------------------------------------------------------
        # FIX: pass with_jira boolean directly — email is always sent,
        # Jira ticket is created only when with_jira=True
        # ------------------------------------------------------------------
        with st.spinner("Running AI Test Agent..."):
            result = run_tests(mode=command, with_jira=with_jira, run_headless=run_headless, send_email=send_email)
        # Store result in session state so Reports section can use it
        st.session_state.last_reports = result

        # Extract summary
        summary = result.get("summary", {})
        passed  = summary.get("passed", 0)
        failed  = summary.get("failed", 0)
        total   = summary.get("total", passed + failed)
        tests   = result.get("tests", [])

        # Build log text
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

        # Show per-test table
        if tests:
            st.subheader("🧪 Test Details (this run)")
            st.table([
                {
                    "Test":    t["test_name"],
                    "Status":  t["status"],
                    "Message": t["message"],
                    "Time":    t["timestamp"],
                }
                for t in tests
            ])

        # ------------------------------------------------------------------
        # FIX: show Jira ticket link if one was created
        # ------------------------------------------------------------------
        jira_result = result.get("jira_result")
        if jira_result:
            st.success(f"🎫 Jira ticket created: [{jira_result['ticket_key']}]({jira_result['ticket_url']})  |  Status: {jira_result['status']}")
        elif with_jira:
            st.warning("⚠️ Jira ticket creation failed — check console logs for details.")

        # Email is always attempted; result is printed to console by the agent
        st.info("📧 Email report has been sent (check console for delivery status).")

    except Exception as e:
        failed = 1
        logs   = f"Error while running agent: {str(e)}"
        log_box.code(logs)
        st.error("Agent execution failed. See logs above.")
        total = passed + failed

    # =========================
    # FINAL FALLBACK
    # =========================
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

    # =========================
    # SAVE HISTORY
    # =========================
    run_data = {
        "time":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed,
        "failed": failed
    }
    save_history(run_data)

    # =========================
    # FINAL STATUS
    # =========================
    if failed == 0:
        status_box.success(f"✅ All tests passed ({passed})")
    else:
        status_box.error(f"❌ {failed} tests failed")

    st.session_state.show_reports = True

    # =========================
    # AI FAILURE ANALYSIS
    # =========================
    if failed > 0:
        st.subheader("🧠 AI Failure Analysis")
        logs_lower = logs.lower()
        if "element not found" in logs_lower:
            st.error("🔍 Element locator changed")
        elif "timeout" in logs_lower:
            st.error("⏱️ Performance issue detected")
        else:
            st.error("🤖 Unknown issue — check logs")

# =========================
# REPORTS
# FIX: replaced st.components.v1.html (renders inside Streamlit) with
#      st.download_button so the file opens in a real browser tab
# =========================
if st.session_state.show_reports:
    st.subheader("📄 Test Reports")

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

            # ------------------------------------------------------------------
            # FIX: use download button so the HTML opens in the real browser,
            # not rendered inside the Streamlit iframe
            # ------------------------------------------------------------------
            with open(path, "rb") as f:
                report_bytes = f.read()

            st.download_button(
                label="⬇️ Download & Open Report in Browser",
                data=report_bytes,
                file_name=selected_report,
                mime="text/html",
            )

            # Also show a quick inline preview (summary only, not full render)
            st.info(f"📁 Report saved at: `{path}`")

            # Optional: show raw HTML in expander for quick inspection
            with st.expander("👁️ Quick inline preview (summary cards only)"):
                st.components.v1.html(report_bytes.decode("utf-8"), height=500, scrolling=True)

        else:
            st.info("No HTML reports found yet.")
    else:
        st.info(f"Report directory not found: `{report_dir}`")

# =========================
# SCREENSHOT
# =========================
if selected_data.get("failed", 0) > 0:
    st.subheader("🖼️ Failure Screenshot")

    screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "AI_Agent_Reports", "screenshots")

    if os.path.exists(screenshot_dir):
        images = [f for f in os.listdir(screenshot_dir)
                  if f.lower().endswith((".png", ".jpg", ".jpeg"))]

        if images:
            latest_img = max(images, key=lambda x: os.path.getctime(os.path.join(screenshot_dir, x)))
            st.image(os.path.join(screenshot_dir, latest_img))

# =========================
# HISTORY
# =========================
st.subheader("📜 Last 5 Runs")

if history:
    st.table(history[::-1])
else:
    st.info("No runs yet")
