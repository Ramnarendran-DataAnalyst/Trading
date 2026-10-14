"""Streamlit UI for the settlement-window calculations in prime.py."""

import csv
import io

import pandas as pd
import streamlit as st

from prime import calculate_window, display, to_date


st.set_page_config(page_title="NIFTY Settlement Analyzer", page_icon="📈", layout="wide")


def read_uploaded_csv(uploaded_file):
    content = uploaded_file.getvalue().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    required = {"Date", "Option Type", "Strike Price", "Settlement Price"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing)))
    return list(reader)


st.title("NIFTY Settlement Analyzer")
st.caption("Settlement-price window calculated from the latest available date in the uploaded CSV.")

with st.sidebar:
    uploaded_file = st.file_uploader("Upload NSE option CSV", type="csv")
    base_strike = st.number_input("ATM / base strike", min_value=0.0, value=22700.0, step=50.0)
    calculate = st.button("Calculate", type="primary", use_container_width=True)

if uploaded_file is None:
    st.info("Upload the NSE option CSV to calculate the nine-strike window.")
    st.stop()

try:
    rows = read_uploaded_csv(uploaded_file)
    latest_date = max(to_date(row["Date"]) for row in rows if to_date(row["Date"]) is not None)
except (UnicodeDecodeError, ValueError) as error:
    st.error(f"Could not read the CSV: {error}")
    st.stop()

st.write(f"**Latest data date used:** {latest_date:%d-%b-%Y}")

if not calculate:
    st.stop()

try:
    _, result = calculate_window(rows, float(base_strike))
except ValueError as error:
    st.error(str(error))
    st.stop()

table = pd.DataFrame(
    [
        {
            "Strike": display(strike),
            "CE": display(ce),
            "PE": display(pe),
            "Total (CE + PE)": display(total),
            "Average": display(average),
        }
        for strike, ce, pe, total, average in result
    ]
)

st.subheader("Final processed NIFTY option window")
st.dataframe(table, hide_index=True, use_container_width=True)
st.download_button(
    "Download result as CSV",
    table.to_csv(index=False).encode("utf-8"),
    file_name=f"nifty_settlement_window_{latest_date:%Y-%m-%d}_{int(base_strike)}.csv",
    mime="text/csv",
)
