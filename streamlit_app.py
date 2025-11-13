import streamlit as st
import pandas as pd
import altair as alt
from main import build_initial_state, process_chat_turn  # use existing functions
import json
st.set_page_config(page_title="QueryBridge: Unified Business Insights Across Systems", page_icon="🤖", layout="wide")

st.title("QueryBridge: Unified Business Insights Across Systems 🤖")
st.caption("Type a question. The agent picks SAP HANA, BigQuery, or Excel/CSV and returns insights + charts.")

# ---------- Session State Bootstrapping ----------
if "state" not in st.session_state or st.session_state.state is None:
    st.session_state.state = build_initial_state()
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        m for m in st.session_state.state["messages"] if m["role"] != "system"
    ]
def _parse_analysis_json(text: str):
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    required = {"Insights", "Chart_Type", "Columns"}
    if not required.issubset(data.keys()):
        return None
    return data


def _build_chart_from_spec(spec, df: pd.DataFrame):
    # spec: {"type": "bar", "columns": ["DIM","MEASURE", ...]} OR list of specs
    charts = []
    if isinstance(spec, dict):
        specs = [spec]
    elif isinstance(spec, list):
        specs = spec
    else:
        return None
    for single in specs:
        ctype = single.get("type", "").lower()
        cols = single.get("columns", [])
        if len(cols) < 2:
            continue
        dim, measure = cols[0], cols[1]
        if dim not in df.columns or measure not in df.columns:
            continue
        enc = dict(
            x=alt.X(dim, sort=None),
            y=alt.Y(measure),
            tooltip=[c for c in df.columns if c in cols][:10]
        )
        if ctype == "bar":
            chart = alt.Chart(df).mark_bar().encode(**enc)
        elif ctype == "line":
            chart = alt.Chart(df).mark_line(point=True).encode(**enc)
        elif ctype == "area":
            chart = alt.Chart(df).mark_area().encode(**enc)
        elif ctype == "pie":
            # build pie from aggregated data
            pie_df = df.groupby(dim, as_index=False)[measure].sum()
            chart = alt.Chart(pie_df).mark_arc().encode(
                theta=alt.Theta(field=measure, type="quantitative"),
                color=alt.Color(field=dim, type="nominal"),
                tooltip=[dim, measure]
            )
        else:
            # fallback scatter
            chart = alt.Chart(df).mark_point().encode(**enc)
        charts.append(chart)
    if not charts:
        return None
    if len(charts) == 1:
        return charts[0]
    # vertically concatenate if multiple
    combo = charts[0]
    for c in charts[1:]:
        combo = combo & c
    return combo
# ---------- Sidebar ----------
with st.sidebar:
    st.header("📝 How to use")
    examples = [
        "Show department expense trend last 2 years",
        "Profit margin by product",
        "Top 5 customers by loyalty points",
        "Customers with most money spent",
        "Product which was most sold",
        "Top 5 vendors by payments",
        "Show me the top 5 fixed assets by value"
    ]
    st.markdown("**Examples**\n" + "\n".join(f"- {e}" for e in examples))
    st.divider()
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.state = build_initial_state()
        st.session_state.chat_messages = []
        st.rerun()

    # If state has executed SQL, offer download
    if "sql" in st.session_state.state and st.session_state.state["sql"]:
        st.download_button(
            "⬇️ Download SQL",
            data=st.session_state.state["sql"],
            file_name="last_query.sql",
            mime="text/sql",
            use_container_width=True
        )

# ---------- Helper Functions ----------
def _raw_table_to_df(raw_table: dict) -> pd.DataFrame:
    if not raw_table:
        return pd.DataFrame()
    cols = raw_table.get("cols", [])
    rows = raw_table.get("rows", [])
    try:
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        return pd.DataFrame(rows)

def render_table_and_chart():
    raw_table = st.session_state.state.get("raw_table")
    if not raw_table or not raw_table.get("rows"):
        return
    df = _raw_table_to_df(raw_table)
    if df.empty:
        return
    st.subheader("Result Preview")
    st.dataframe(df, use_container_width=True)

    # Auto-detect columns
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    non_num_cols = [c for c in df.columns if c not in numeric_cols]

    with st.expander("📊 Quick Chart"):
        chart_type = st.selectbox("Chart type", ["None", "Bar", "Line", "Area", "Pie"])
        x_col = st.selectbox("X (dimension)", non_num_cols + numeric_cols, index=0 if non_num_cols else 0)
        y_col = st.selectbox("Y (measure)", numeric_cols, index=0 if numeric_cols else 0)
        if chart_type != "None" and x_col and y_col and not df.empty:
            if chart_type == "Bar":
                chart = alt.Chart(df).mark_bar().encode(x=x_col, y=y_col, tooltip=list(df.columns))
            elif chart_type == "Line":
                chart = alt.Chart(df).mark_line(point=True).encode(x=x_col, y=y_col, tooltip=list(df.columns))
            elif chart_type == "Area":
                chart = alt.Chart(df).mark_area().encode(x=x_col, y=y_col, tooltip=list(df.columns))
            elif chart_type == "Pie":
                # For pie, y_col as theta, x_col as color
                pie_df = df.groupby(x_col, as_index=False)[y_col].sum()
                chart = alt.Chart(pie_df).mark_arc().encode(
                    theta=alt.Theta(field=y_col, type="quantitative"),
                    color=alt.Color(field=x_col, type="nominal"),
                    tooltip=[x_col, y_col]
                )
            else:
                chart = None
            if chart:
                st.altair_chart(chart, use_container_width=True)

def add_assistant_message(content: str):
    st.session_state.chat_messages.append({"role": "assistant", "content": content})

def add_user_message(content: str):
    st.session_state.chat_messages.append({"role": "user", "content": content})

# ---------- Display Existing Chat ----------
raw_table_current = st.session_state.state.get("raw_table", {})
df_current = pd.DataFrame(raw_table_current.get("rows", []), columns=raw_table_current.get("cols", [])) if raw_table_current else pd.DataFrame()

for m in st.session_state.chat_messages:
    role = m["role"]
    parsed = _parse_analysis_json(m["content"]) if role == "assistant" else None
    with st.chat_message("user" if role == "user" else "assistant"):
        if parsed:
            insights = parsed["Insights"]
            if isinstance(insights, str):
                insights = [insights]
            st.markdown("**Insights:**")
            for ins in insights:
                st.markdown(f"- {ins}")
            # Chart(s)
            if not df_current.empty:
                chart = _build_chart_from_spec(parsed["Chart_Type"], df_current)
                if chart:
                    st.markdown("**Chart:**")
                    st.altair_chart(chart, use_container_width=True)
            # Show a toggle for raw JSON if needed
            with st.expander("Raw analysis JSON"):
                st.code(json.dumps(parsed, indent=2), language="json")
        else:
            st.markdown(m["content"])

# ---------- Chat Input ----------
user_input = st.chat_input("Ask a finance data question...")
if user_input:
    add_user_message(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            new_state, assistant_reply = process_chat_turn(st.session_state.state, user_input)
            st.session_state.state = new_state
            # Store assistant reply
            add_assistant_message(assistant_reply)
            parsed = _parse_analysis_json(assistant_reply)
            if parsed:
                insights = parsed["Insights"]
                if isinstance(insights, str):
                    insights = [insights]
                st.markdown("**Insights:**")
                for ins in insights:
                    st.markdown(f"- {ins}")
                raw_table = st.session_state.state.get("raw_table", {})
                df = pd.DataFrame(raw_table.get("rows", []), columns=raw_table.get("cols", [])) if raw_table else pd.DataFrame()
                if not df.empty:
                    chart = _build_chart_from_spec(parsed["Chart_Type"], df)
                    if chart:
                        st.markdown("**Chart:**")
                        st.altair_chart(chart, use_container_width=True)
            else:
                st.markdown(assistant_reply)
            followup = st.session_state.state.get("assistant_followup")
            if followup:
                st.markdown(f"_{followup}_")
                add_assistant_message(followup)
    st.rerun()

# ---------- Optional: show raw table & manual chart tools ----------
render_table_and_chart()

# ---------- Executed SQL ----------
if st.session_state.state.get("sql"):
    with st.expander("🧪 Executed SQL"):
        st.code(st.session_state.state["sql"], language="sql")
# ---------- Data / Chart (after)

