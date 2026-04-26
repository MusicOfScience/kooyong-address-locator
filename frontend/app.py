from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.analysis.live_count import (
    count_status,
    current_margin,
    current_tcp,
    recount_risk_indicator,
    required_share_to_win,
    sensitivity_by_vote_type,
    votes_counted_ratio,
)
from backend.config import load_contest_config
from backend.exporters.reporting import simple_html_briefing, to_csv_bytes, to_xlsx_bytes
from backend.ingestion.loaders import load_sample_bundle
from backend.models.forecast import aggregate_polls, baseline_swing, monte_carlo_win_probability
from backend.models.preferences import tcp_from_preferences
from backend.models.scenarios import apply_scenario

st.set_page_config(page_title="Margin of Error (MOE)", layout="wide")

cfg = load_contest_config()
party_colors = cfg["parties"]

if "saved_scenario" not in st.session_state:
    st.session_state.saved_scenario = {}

bundle = load_sample_bundle()
live = bundle["live_count"]
declarations = bundle["declarations"]
historical = bundle["historical"]
polls = bundle["polls"]

st.title("Margin of Error / MOE")
st.caption("Australian election forecasting and live count analysis MVP")

with st.sidebar:
    st.header("Controls")
    dark_mode = st.toggle("Dark mode", value=False)
    pref_to_ind = st.slider("Labor preference to Independent", 0.0, 1.0, 0.65, 0.01)
    swing_a = st.slider("Primary vote swing to leading candidate (%)", -10.0, 10.0, 0.0, 0.1)
    turnout_mult = st.slider("Turnout change multiplier", 0.8, 1.2, 1.0, 0.01)
    postal_lean = st.slider("Postal lean to leader (%)", -10.0, 10.0, 0.0, 0.1)

    c1, c2 = st.columns(2)
    if c1.button("Save scenario"):
        st.session_state.saved_scenario = {
            "pref_to_ind": pref_to_ind,
            "swing_a": swing_a,
            "turnout_mult": turnout_mult,
            "postal_lean": postal_lean,
        }
    if c2.button("Load scenario") and st.session_state.saved_scenario:
        st.info("Saved scenario loaded for reference in this MVP (manual slider restore).")
    if st.button("Reset assumptions"):
        st.rerun()

ratio = votes_counted_ratio(live, declarations)
margin = current_margin(live)
status = count_status(ratio, cfg["contest"]["count_status_thresholds"])
req = required_share_to_win(live, declarations)
risk = recount_risk_indicator(margin)

scenario_live = apply_scenario(live, swing_a=swing_a, turnout_mult=turnout_mult)
scenario_margin = current_margin(scenario_live)

poll_agg = aggregate_polls(polls)
swing_table = baseline_swing(historical, poll_agg)
mc = monte_carlo_win_probability(scenario_margin)

tcp = current_tcp(live)
lead_name = tcp.iloc[0]["candidate"]
trail_name = tcp.iloc[1]["candidate"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Current margin", f"{margin:.2f}%")
k2.metric("Votes counted", f"{ratio*100:.1f}%")
k3.metric("Required share from outstanding", f"{req:.1f}%")
k4.metric("Win probability (leader)", f"{mc['win_probability']*100:.1f}%")
st.write(f"**Count status:** {status} | **Recount risk:** {risk}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Live Count", "Forecast", "Preferences", "Swingometer", "Map & Intel", "Commentary"
])

with tab1:
    st.subheader("Live TCP/TPP and Close Count")
    st.dataframe(tcp, use_container_width=True)
    st.dataframe(sensitivity_by_vote_type(live, declarations), use_container_width=True)
    fig_tcp = px.bar(tcp, x="candidate", y="votes", title="Current TCP votes")
    st.plotly_chart(fig_tcp, use_container_width=True)

with tab2:
    st.subheader("Prediction Engine")
    st.dataframe(swing_table, use_container_width=True)
    dist = pd.DataFrame({"margin": mc["distribution"]})
    fig_dist = px.histogram(dist, x="margin", nbins=40, title="Probability bell curve (simulated margins)")
    fig_dist.add_vline(x=mc["ci_5"], line_dash="dash")
    fig_dist.add_vline(x=mc["ci_95"], line_dash="dash")
    st.plotly_chart(fig_dist, use_container_width=True)

with tab3:
    st.subheader("Preference Modelling")
    prim = live.groupby("candidate")["votes"].sum().sort_values(ascending=False)
    primary_a = prim.iloc[0] / prim.sum()
    primary_b = prim.iloc[1] / prim.sum()
    other = max(0.0, 1 - primary_a - primary_b)
    a_tcp, b_tcp = tcp_from_preferences(primary_a, primary_b, other, pref_to_ind)
    st.write(
        f"Under current assumption, **{lead_name} TCP:** {a_tcp*100:.2f}% | **{trail_name} TCP:** {b_tcp*100:.2f}%"
    )

with tab4:
    st.subheader("Scenario Testing")
    scenario_tbl = pd.DataFrame([
        {"scenario": "Base", "winner": lead_name if margin > 0 else trail_name, "margin": margin},
        {"scenario": "User scenario", "winner": lead_name if scenario_margin > 0 else trail_name, "margin": scenario_margin},
    ])
    st.dataframe(scenario_tbl, use_container_width=True)
    fig_req = px.bar(declarations, x="vote_type", y="envelopes_remaining", title="Outstanding votes by type")
    st.plotly_chart(fig_req, use_container_width=True)

with tab5:
    st.subheader("Booth map and intelligence layering")
    booths = bundle["booths"]
    fig_map = px.scatter_mapbox(
        booths,
        lat="lat",
        lon="lon",
        color="swing",
        size="formal_votes",
        hover_name="booth",
        title="Booth swing map",
        zoom=10,
        map_style="open-street-map",
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.dataframe(bundle["intelligence"], use_container_width=True)

with tab6:
    st.subheader("Live Commentary Feed + Simulcast")
    commentary = bundle["commentary"].sort_values("timestamp", ascending=False)
    st.dataframe(commentary, use_container_width=True)
    ticker_items = [f"{r.timestamp}: {r.headline}" for r in commentary.head(5).itertuples()]
    st.markdown(" | ".join(ticker_items))
    st.info("OSINT/media module placeholder: safe manual source-entry only in MVP.")

st.markdown("---")
st.subheader("Exports")
summary = {
    "contest": cfg["contest"]["name"],
    "current_margin": margin,
    "projected_margin": mc["mean_margin"],
    "risk": risk,
}
scenario_table = pd.DataFrame([
    {"scenario": "Base", "winner": lead_name if margin > 0 else trail_name, "margin": margin},
    {"scenario": "Scenario", "winner": lead_name if scenario_margin > 0 else trail_name, "margin": scenario_margin},
])
html_report = simple_html_briefing(summary, scenario_table)

st.download_button("Export live count CSV", data=to_csv_bytes(live), file_name="live_count.csv")
st.download_button(
    "Export workbook XLSX",
    data=to_xlsx_bytes({"live_count": live, "declarations": declarations, "scenario": scenario_table}),
    file_name="moe_export.xlsx",
)
st.download_button("Export briefing HTML", data=html_report.encode("utf-8"), file_name="briefing.html")
st.download_button("Save scenario JSON", data=json.dumps(st.session_state.saved_scenario, indent=2), file_name="scenario.json")
