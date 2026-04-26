from __future__ import annotations

from io import BytesIO
import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_xlsx_bytes(named_frames: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in named_frames.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
    output.seek(0)
    return output.read()


def simple_html_briefing(summary: dict, scenario_table: pd.DataFrame) -> str:
    rows = "".join(f"<tr><td>{r['scenario']}</td><td>{r['winner']}</td><td>{r['margin']:.2f}%</td></tr>" for _, r in scenario_table.iterrows())
    return f"""
    <html><body>
    <h1>Margin of Error Briefing Report</h1>
    <p><strong>Contest:</strong> {summary['contest']}</p>
    <p><strong>Current Margin:</strong> {summary['current_margin']:.2f}%</p>
    <p><strong>Projected Margin:</strong> {summary['projected_margin']:.2f}%</p>
    <p><strong>Risk Rating:</strong> {summary['risk']}</p>
    <h2>Scenario Table</h2>
    <table border='1' cellpadding='5'>
      <tr><th>Scenario</th><th>Winner</th><th>Projected Margin</th></tr>
      {rows}
    </table>
    </body></html>
    """
