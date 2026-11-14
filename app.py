"""Streamlit dashboard for the SupeRR Selector pressure-analysis outputs."""

import os
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent
configured_output_dir = Path(os.environ.get("OUT_DIR", "outputs")).expanduser()
OUTPUT_DIR = (
    configured_output_dir
    if configured_output_dir.is_absolute()
    else ROOT_DIR / configured_output_dir
)

DATA_FILES = {
    "batters": "all_ranked_batters.csv",
    "bowlers": "all_ranked_bowlers.csv",
    "evidence": "pressure_vs_ordinary.csv",
    "squad": "rr_squad_pressure_ratings.csv",
    "validation": "validation_early_vs_late.csv",
    "prior_caps": "validation_prior_cap.csv",
    "sensitivity": "weight_sensitivity.csv",
    "batter_profiles": "top10_batters_profile.csv",
    "bowler_profiles": "top10_bowlers_profile.csv",
}

st.set_page_config(
    page_title="SupeRR Selector | Pressure dashboard",
    page_icon=":material/sports_cricket:",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_csv(path: str, modified_at_ns: int, file_size: int) -> pd.DataFrame:
    """Cache dashboard output while invalidating the cache when its file changes."""
    return pd.read_csv(path)


st.title("SupeRR Selector")
st.caption("Round 1 · Pressure performance dashboard · IPL and T20I")

with st.sidebar:
    st.subheader("SupeRR Selector")
    st.caption("Explore pressure ratings, Rajasthan Royals squad coverage, and model checks.")
    st.divider()
    st.caption("Refresh the analysis outputs by running `rr_pressure_analysis.py`.")

data: dict[str, pd.DataFrame] = {}
for key, filename in DATA_FILES.items():
    path = OUTPUT_DIR / filename
    if not path.is_file():
        st.error(
            f"Dashboard data is missing: `{path}`. "
            "Run `rr_pressure_analysis.py` to generate the analysis outputs."
        )
        st.stop()
    file_stat = path.stat()
    data[key] = load_csv(str(path), file_stat.st_mtime_ns, file_stat.st_size)

page = st.segmented_control(
    "Dashboard section",
    ["Overview", "Player rankings", "RR squad", "Model checks"],
    default="Overview",
)

batters = data["batters"]
bowlers = data["bowlers"]
evidence = data["evidence"]
squad = data["squad"]


def player_table(frame: pd.DataFrame, role: str) -> pd.DataFrame:
    """Return a readable, role-specific player ranking table."""
    if role == "Batters":
        columns = [
            "rank", "name", "ipl_team", "p_balls", "pressure_innings",
            "p_sr", "b_sr", "p_avg", "lift", "boot_prob_top10", "score",
        ]
        labels = {
            "rank": "Rank", "name": "Player", "ipl_team": "IPL team",
            "p_balls": "Pressure balls", "pressure_innings": "Pressure innings",
            "p_sr": "Pressure SR", "b_sr": "Baseline SR", "p_avg": "Pressure average",
            "lift": "Lift", "boot_prob_top10": "Top-10 probability", "score": "Score",
        }
    else:
        columns = [
            "rank", "name", "ipl_team", "p_balls", "pressure_innings",
            "p_wkts", "p_econ", "b_econ", "lift", "boot_prob_top10", "score",
        ]
        labels = {
            "rank": "Rank", "name": "Player", "ipl_team": "IPL team",
            "p_balls": "Pressure balls", "pressure_innings": "Pressure innings",
            "p_wkts": "Pressure wickets", "p_econ": "Pressure economy",
            "b_econ": "Baseline economy", "lift": "Lift",
            "boot_prob_top10": "Top-10 probability", "score": "Score",
        }
    return frame.loc[:, columns].rename(columns=labels)


def show_player_leaderboard(frame: pd.DataFrame, role: str) -> None:
    """Render a compact leaderboard and its score chart."""
    display = player_table(frame.head(5), role)
    if "Top-10 probability" in display:
        display = display.style.format({"Top-10 probability": "{:.0%}"})
    st.dataframe(display, hide_index=True, alt=f"Top five pressure-rated {role.lower()}")


if page == "Overview":
    pressure_balls = int(evidence.loc[evidence.pressure, "deliveries"].sum())
    bat_ranked = int(batters["name"].nunique())
    bowl_ranked = int(bowlers["name"].nunique())
    squad_bat_ranked = int(squad["bat_rank"].notna().sum())
    squad_bowl_ranked = int(squad["bowl_rank"].notna().sum())

    with st.container(horizontal=True):
        st.metric("Eligible batters", f"{bat_ranked:,}", border=True)
        st.metric("Eligible bowlers", f"{bowl_ranked:,}", border=True)
        st.metric("Pressure deliveries", f"{pressure_balls:,}", border=True)
        st.metric(
            "RR squad ranked",
            f"{squad_bat_ranked} batters · {squad_bowl_ranked} bowlers",
            border=True,
        )

    st.subheader("Pressure leaders")
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**Batting**")
            show_player_leaderboard(batters, "Batters")
    with right:
        with st.container(border=True):
            st.markdown("**Bowling**")
            show_player_leaderboard(bowlers, "Bowlers")

    st.subheader("What pressure looks like")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        leverage_chart = OUTPUT_DIR / "chart_leverage_by_over.png"
        if not leverage_chart.is_file():
            st.error(f"Dashboard chart is missing: `{leverage_chart}`.")
        else:
            st.image(
                str(leverage_chart),
                width="stretch",
                alt="Average win-probability leverage by over for both innings",
            )
    with chart_right:
        pressure_chart = OUTPUT_DIR / "chart_pressure_vs_ordinary.png"
        if not pressure_chart.is_file():
            st.error(f"Dashboard chart is missing: `{pressure_chart}`.")
        else:
            st.image(
                str(pressure_chart),
                width="stretch",
                alt="Comparison of leverage and match closeness in pressure and ordinary situations",
            )

    with st.expander("Pressure vs ordinary deliveries"):
        evidence_display = evidence.copy()
        evidence_display["innings"] = "Innings " + evidence_display["innings"].astype(str)
        evidence_display["pressure"] = evidence_display["pressure"].map(
            {True: "Pressure", False: "Ordinary"}
        )
        evidence_display["role"] = evidence_display["role"].map(
            {"bat": "Batting", "bowl": "Bowling"}
        )
        st.dataframe(
            evidence_display.rename(
                columns={
                    "role": "Role",
                    "innings": "Innings",
                    "pressure": "Context",
                    "deliveries": "Deliveries",
                    "mean_leverage": "Mean leverage",
                    "mean_abs_wp_from_50": "Distance from 50% win probability",
                    "wkts_in_hand": "Wickets in hand",
                    "run_rate": "Run rate",
                    "dot_pct": "Dot-ball %",
                    "dismissals_per_100": "Dismissals per 100",
                }
            ),
            hide_index=True,
            alt="Delivery-level comparison of pressure and ordinary situations",
        )

elif page == "Player rankings":
    st.subheader("Player rankings")
    role = st.segmented_control(
        "Player role", ["Batters", "Bowlers"], default="Batters", key="ranking_role"
    )
    source = batters if role == "Batters" else bowlers
    maximum_balls = int(source["p_balls"].max())
    with st.container(horizontal=True, vertical_alignment="bottom"):
        teams = ["All teams", *sorted(source["ipl_team"].dropna().unique().tolist())]
        selected_team = st.selectbox("IPL team", teams)
        min_balls = st.slider(
            "Minimum pressure balls",
            min_value=0,
            max_value=maximum_balls,
            value=0,
            step=10,
        )
        search = st.text_input("Search player")
        row_limit = st.selectbox("Rows", [10, 25, 50, 100], index=1)

    filtered = source.loc[source["p_balls"] >= min_balls].copy()
    if selected_team != "All teams":
        filtered = filtered.loc[filtered["ipl_team"] == selected_team]
    if search:
        filtered = filtered.loc[
            filtered["name"].astype("string").str.contains(search, case=False, na=False)
        ]

    st.caption(f"{len(filtered):,} players match the selected filters.")
    if filtered.empty:
        st.info("No players match these filters. Try a lower ball threshold or another team.")
    else:
        chart_frame = filtered.head(10).sort_values("score")
        st.bar_chart(
            chart_frame,
            x="name",
            y="score",
            horizontal=True,
            alt=f"Top pressure scores among the filtered {role.lower()}",
        )

        selected_name = st.selectbox("Player details", filtered["name"].tolist())
        player = filtered.loc[filtered["name"] == selected_name].iloc[0]
        with st.container(horizontal=True):
            st.metric("Pressure score", f"{player['score']:.2f}", border=True)
            st.metric("Lift over baseline", f"{player['lift']:.1f}", border=True)
            st.metric("Pressure balls", f"{int(player['p_balls']):,}", border=True)
            st.metric("Bootstrap top-10 probability", f"{player['boot_prob_top10']:.0%}", border=True)

        table = player_table(filtered.head(row_limit), role)
        table = table.style.format(
            {
                "Pressure SR": "{:.1f}",
                "Baseline SR": "{:.1f}",
                "Pressure average": "{:.1f}",
                "Pressure economy": "{:.2f}",
                "Baseline economy": "{:.2f}",
                "Top-10 probability": "{:.0%}",
                "Lift": "{:.1f}",
                "Score": "{:.2f}",
            },
            na_rep="",
        )
        st.dataframe(
            table,
            hide_index=True,
            height=560,
            alt=f"Filtered pressure ratings for {role.lower()}",
        )
        st.download_button(
            "Download filtered rankings",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"filtered_{role.lower()}_rankings.csv",
            mime="text/csv",
        )

elif page == "RR squad":
    st.subheader("Rajasthan Royals squad")
    st.caption("Pressure ratings and eligible-player ranks in the analysis dataset.")
    squad_display = squad.rename(
        columns={
            "squad_name": "Squad player",
            "data_name": "Matched data name",
            "bat_pressure_balls": "Batting pressure balls",
            "bat_rank": "Batting rank",
            "bat_score": "Batting score",
            "bat_level": "Batting level",
            "bowl_pressure_balls": "Bowling pressure balls",
            "bowl_rank": "Bowling rank",
            "bowl_score": "Bowling score",
            "bowl_level": "Bowling level",
        }
    )
    st.dataframe(
        squad_display,
        hide_index=True,
        alt="Rajasthan Royals squad players and their pressure ratings",
    )
    st.download_button(
        "Download squad ratings",
        data=squad.to_csv(index=False).encode("utf-8"),
        file_name="rr_squad_pressure_ratings.csv",
        mime="text/csv",
    )
    st.info(
        "A blank rank means the player did not meet the model's minimum eligibility "
        "threshold for that role; it does not mean a zero rating."
    )

else:
    st.subheader("Model checks")
    validation = data["validation"].copy()
    validation["spearman_vs_later_pressure"] = pd.to_numeric(
        validation["spearman_vs_later_pressure"], errors="coerce"
    )
    st.markdown("**Early-to-late validation**")
    st.caption("Higher Spearman correlation means better agreement with later pressure performance.")
    st.bar_chart(
        validation,
        x="spearman_vs_later_pressure",
        y="method",
        color="group",
        horizontal=True,
        stack=False,
        alt="Early-to-late validation correlations for each model and baseline",
    )
    st.dataframe(
        validation.rename(
            columns={
                "group": "Player group",
                "method": "Method",
                "n_players": "Players tested",
                "spearman_vs_later_pressure": "Spearman correlation",
            }
        ),
        hide_index=True,
        alt="Out-of-sample early-to-late validation results",
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Prior-strength cap sweep**")
        cap_data = data["prior_caps"].copy()
        cap_data["cap"] = cap_data.apply(
            lambda row: f"{row['cap_runs']:g} runs / {row['cap_wkts']:g} wickets",
            axis=1,
        )
        st.dataframe(
            cap_data.rename(
                columns={
                    "group": "Player group",
                    "cap_runs": "Run cap",
                    "cap_wkts": "Wicket cap",
                    "n_players": "Players tested",
                    "spearman_vs_later_pressure": "Spearman correlation",
                }
            ).drop(columns="cap"),
            hide_index=True,
            alt="Validation results across prior-strength caps",
        )
    with right:
        st.markdown("**Top-10 ranking sensitivity**")
        st.dataframe(
            data["sensitivity"].rename(
                columns={
                    "weights": "Level / lift / consistency weights",
                    "batters_overlap": "Batter overlap",
                    "bowlers_overlap": "Bowler overlap",
                }
            ),
            hide_index=True,
            alt="Top-10 overlap under alternative score weights",
        )

    with st.expander("Player pressure profiles"):
        profile_role = st.segmented_control(
            "Profile role", ["Batters", "Bowlers"], default="Batters", key="profile_role"
        )
        profile_key = "batter_profiles" if profile_role == "Batters" else "bowler_profiles"
        st.dataframe(
            data[profile_key],
            hide_index=True,
            alt=f"Pressure situation profiles for top {profile_role.lower()}",
        )
