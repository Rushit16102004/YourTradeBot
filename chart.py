"""Interactive Plotly charts for NIFTY 50 trading strategy with on-chart drawing tools."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from config import StrategyConfig
from strategy import StrategySignalState as StrategyState

# Strict NSE Market Hours: Hide overnight non-trading hours (15:30 to 09:15) and weekends
MARKET_HOURS_RANGEBREAKS = [
    dict(bounds=[15.5, 9.25], pattern="hour"),  # hide overnight non-trading hours
    dict(bounds=["sat", "mon"]),                 # hide weekend gaps
]

# ModeBar configuration with advanced zoom tools, measurement lines, zone boxes, and screenshot
CHART_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    "doubleClick": "reset",
    "modeBarButtonsToAdd": [
        "zoom2d",         # Box Zoom
        "pan2d",          # Drag / Pan
        "zoomIn2d",       # Zoom In (+)
        "zoomOut2d",      # Zoom Out (-)
        "autoScale2d",    # Auto Scale
        "resetScale2d",   # Reset Scale / Home (⟲)
        "drawline",       # Measurement & Trend lines
        "drawrect",       # Supply / Demand Zone rectangles & squares
        "drawcircle",     # Circle highlighter
        "drawopenpath",   # Freehand drawing
        "eraseshape",     # Delete drawn lines / zones
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "nifty50_analysis",
        "height": 1080,
        "width": 1920,
        "scale": 2,
    },
}


def _get_x_series(df: pd.DataFrame) -> pd.Series:
    if "timestamp" in df.columns:
        return df["timestamp"]
    return pd.Series(df.index, index=df.index)


def _extract_signals(
    df: pd.DataFrame,
    confirmed_signals: list[dict] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    buys = []
    sells = []

    if confirmed_signals:
        df_by_idx = df.copy()
        if "timestamp" in df_by_idx.columns:
            df_by_idx = df_by_idx.set_index("timestamp")

        for sig in confirmed_signals:
            stype = str(sig.get("signal") or sig.get("type", "")).upper()
            ts = sig.get("timestamp")
            price = sig.get("price")

            high = price
            low = price
            if ts in df_by_idx.index:
                row = df_by_idx.loc[ts]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
                high = row.get("high", price)
                low = row.get("low", price)

            if "BUY" in stype:
                buys.append({"timestamp": ts, "price": price, "plot_y": low * 0.9992})
            elif "SELL" in stype:
                sells.append({"timestamp": ts, "price": price, "plot_y": high * 1.0008})

    elif "signal" in df.columns:
        x_series = _get_x_series(df)
        for idx, row in df.iterrows():
            sig = str(row.get("signal", "")).upper()
            ts_val = x_series.loc[idx] if idx in x_series.index else row.get("timestamp", idx)
            if "BUY" in sig:
                buys.append({
                    "timestamp": ts_val,
                    "price": row["close"],
                    "plot_y": row["low"] * 0.9992,
                })
            elif "SELL" in sig:
                sells.append({
                    "timestamp": ts_val,
                    "price": row["close"],
                    "plot_y": row["high"] * 1.0008,
                })

    buy_df = pd.DataFrame(buys) if buys else pd.DataFrame(columns=["timestamp", "price", "plot_y"])
    sell_df = pd.DataFrame(sells) if sells else pd.DataFrame(columns=["timestamp", "price", "plot_y"])
    return buy_df, sell_df


def create_trading_chart(
    df: pd.DataFrame,
    state: StrategyState | None = None,
    signals_or_config: list[dict] | StrategyConfig | None = None,
    symbol: str = "NIFTY 50",
    timeframe: str = "5m",
    *args,
    **kwargs,
) -> go.Figure:
    """Creates an expansive (920px), multi-day Candlestick chart with on-chart drawing tools."""
    confirmed_signals = None
    cfg_obj = None
    if isinstance(signals_or_config, list):
        confirmed_signals = signals_or_config
    elif isinstance(signals_or_config, StrategyConfig):
        cfg_obj = signals_or_config
        confirmed_signals = kwargs.get("confirmed_signals", args[0] if len(args) > 0 else None)
    if confirmed_signals is None:
        confirmed_signals = kwargs.get("confirmed_signals")
    if cfg_obj is None and "config" in kwargs and isinstance(kwargs["config"], StrategyConfig):
        cfg_obj = kwargs["config"]

    fig = go.Figure()

    if df.empty or len(df) == 0:
        fig.update_layout(
            template="plotly_dark",
            height=920,
            annotations=[
                dict(
                    text="Waiting for NIFTY 50 Market Data...",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=18, color="#787b86"),
                )
            ],
        )
        return fig

    x_vals = _get_x_series(df)

    # 1. Z-Score Green Highlight Zones (TradingView bgcolor parity)
    if "z" in df.columns:
        z_threshold = getattr(cfg_obj, "z_threshold", 2.0) if cfg_obj else 2.0
        z_mask = (df["z"] > z_threshold).fillna(False)
        in_zone = False
        zone_start = None
        for i, val in enumerate(z_mask):
            ts = x_vals.iloc[i] if hasattr(x_vals, "iloc") else x_vals[i]
            if val and not in_zone:
                in_zone = True
                zone_start = ts
            elif not val and in_zone:
                in_zone = False
                prev_ts = x_vals.iloc[i - 1] if hasattr(x_vals, "iloc") else x_vals[i - 1]
                fig.add_vrect(
                    x0=zone_start,
                    x1=prev_ts,
                    fillcolor="rgba(0, 230, 118, 0.08)",
                    line_width=0,
                    layer="below",
                )
        if in_zone and zone_start is not None:
            last_ts = x_vals.iloc[-1] if hasattr(x_vals, "iloc") else x_vals[-1]
            fig.add_vrect(
                x0=zone_start,
                x1=last_ts,
                fillcolor="rgba(0, 230, 118, 0.08)",
                line_width=0,
                layer="below",
            )

    # 2. 20-Day Candlestick Trace (Emerald `#089981` & Ruby `#f23645`)
    fig.add_trace(
        go.Candlestick(
            x=x_vals,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=f"{symbol} ({timeframe})",
            increasing=dict(line=dict(color="#089981", width=1.5), fillcolor="#089981"),
            decreasing=dict(line=dict(color="#f23645", width=1.5), fillcolor="#f23645"),
            hoverinfo="none",
        )
    )

    # 3. Rolling Mean SMA 20 (Orange line)
    if "mean" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=df["mean"],
                mode="lines",
                name="Rolling Mean (SMA 20)",
                line=dict(color="#ff9800", width=2),
                hoverinfo="none",
            )
        )

    # 4. Confirmed BUY and SELL Signal Badges
    buy_df, sell_df = _extract_signals(df, confirmed_signals)

    if not buy_df.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_df["timestamp"],
                y=buy_df["plot_y"],
                mode="markers+text",
                name="BUY Signal",
                marker=dict(symbol="triangle-up", size=13, color="#00e676"),
                text="▲ BUY",
                textposition="bottom center",
                textfont=dict(color="#00e676", size=12, family="Arial Black"),
                hoverinfo="none",
            )
        )

    if not sell_df.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_df["timestamp"],
                y=sell_df["plot_y"],
                mode="markers+text",
                name="SELL Signal",
                marker=dict(symbol="triangle-down", size=13, color="#f23645"),
                text="▼ SELL",
                textposition="top center",
                textfont=dict(color="#f23645", size=12, family="Arial Black"),
                hoverinfo="none",
            )
        )

    # 5. Target (+6%) & Stop (-3%) Levels (When in position)
    if state and state.in_position and state.entry_price:
        if state.target_price:
            fig.add_hline(
                y=state.target_price,
                line_dash="dot",
                line_color="#00e676",
                line_width=1.5,
                annotation_text=f"Target: ₹{state.target_price:.2f} (+6%)",
                annotation_position="top right",
                annotation_font=dict(color="#00e676", size=11),
            )
        if state.stop_loss:
            fig.add_hline(
                y=state.stop_loss,
                line_dash="dot",
                line_color="#ff5252",
                line_width=1.5,
                annotation_text=f"Stop: ₹{state.stop_loss:.2f} (-3%)",
                annotation_position="bottom right",
                annotation_font=dict(color="#ff5252", size=11),
            )

    # 6. Rangebreaks (only for intraday timeframes like 5m, 15m, 1h; not for 1d)
    is_intraday = "d" not in timeframe.lower()
    rbreaks = MARKET_HOURS_RANGEBREAKS if is_intraday else [dict(bounds=["sat", "mon"])]

    # 7. Full-Screen Layout with Clean Crosshairs & Better Zoom
    fig.update_layout(
        height=920,
        margin=dict(l=20, r=85, t=45, b=40),
        template="plotly_dark",
        plot_bgcolor="#131722",
        paper_bgcolor="#131722",
        dragmode="pan",  # default click-drag mode is smooth Pan
        uirevision="stay_put_" + str(timeframe),  # NEVER auto-adjusts or resets user pan/zoom on updates!
        newshape=dict(
            line=dict(color="#2962ff", width=2),
            fillcolor="rgba(41, 98, 255, 0.18)",  # clean translucent zone fill
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#d1d4dc"),
        ),
        xaxis=dict(
            type="date",
            rangeslider=dict(visible=False),
            rangebreaks=rbreaks,
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=2, label="2D", step="day", stepmode="backward"),
                    dict(count=5, label="5D", step="day", stepmode="backward"),
                    dict(count=10, label="10D", step="day", stepmode="backward"),
                    dict(step="all", label="ALL (20D)"),
                ],
                bgcolor="#1e222d",
                activecolor="#2962ff",
                font=dict(color="#d1d4dc", size=11),
                x=0.0,
                y=1.02,
                xanchor="left",
                yanchor="bottom",
            ),
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            gridwidth=1,
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikedash="dash",
            spikecolor="#787b86",
            fixedrange=False,
            automargin=True,
        ),
        yaxis=dict(
            side="right",
            title=f"{symbol} Price (₹)",
            title_font=dict(color="#787b86", size=12),
            tickfont=dict(color="#d1d4dc", size=11),
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            gridwidth=1,
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikedash="dash",
            spikecolor="#787b86",
            tickformat=",.2f",
            fixedrange=False,
            automargin=True,
        ),
        hovermode=False,  # Completely disable intrusive tooltip popup
    )

    return fig


def create_accessible_chart(
    df: pd.DataFrame,
    state: StrategyState | None = None,
    signals_or_config: list[dict] | StrategyConfig | None = None,
    symbol: str = "NIFTY 50",
    timeframe: str = "5m",
    *args,
    **kwargs,
) -> go.Figure:
    """Accessible line view with drawing tools."""
    fig = go.Figure()
    if df.empty:
        fig.update_layout(template="plotly_dark", height=920)
        return fig

    x_vals = _get_x_series(df)
    fig.add_trace(go.Scatter(x=x_vals, y=df["close"], mode="lines", name=f"{symbol} Close", line=dict(color="#2962ff", width=2)))
    fig.update_layout(height=920, template="plotly_dark", plot_bgcolor="#131722", paper_bgcolor="#131722", yaxis=dict(side="right"))
    return fig
