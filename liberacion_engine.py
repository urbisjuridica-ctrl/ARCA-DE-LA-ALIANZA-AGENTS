"""
Motor ARCA — implementación cuantitativa de la ecuación de LIBERACIÓN:

    LIBERACION = [ INTEGRACION(C, N) - FRAGMENTACION(D) ] > Θ  =>  K -> P

Cada componente simbólico se traduce a una métrica de mercado normalizada
en [0, 1]. El resultado (`liberacion_score`) vive aproximadamente en
[-1, 1] y se compara contra los umbrales THETA / THETA_LOWER para
clasificar el estado del mercado en K (Kenoma), K* (transición) o
P (Pleroma).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

import config


def _normalize(series: pd.Series) -> pd.Series:
    """Normaliza a [0, 1] usando min-max sobre la propia ventana."""
    s_min, s_max = series.min(), series.max()
    if s_max - s_min < 1e-12:
        return pd.Series(0.5, index=series.index)
    return (series - s_min) / (s_max - s_min)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas técnicas intermedias necesarias para ARCA."""
    out = df.copy()

    # --- Tendencia (para trend_coherence) ---
    out["ema_fast"] = out["close"].ewm(span=config.EMA_FAST, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=config.EMA_SLOW, adjust=False).mean()
    out["ema_gap"] = (out["ema_fast"] - out["ema_slow"]) / out["close"]
    out["ema_gap_slope"] = out["ema_gap"].diff()

    # --- Retornos y volumen (para volume_confirmation / dislocación) ---
    out["ret"] = out["close"].pct_change()
    out["vol_chg"] = out["volume"].pct_change()

    # --- Volatilidad (para volatility_spike) ---
    out["volatility"] = out["ret"].rolling(config.VOL_WINDOW).std()
    out["volatility_avg"] = out["volatility"].rolling(config.VOL_WINDOW).mean()

    # --- Drawdown (para drawdown_severity) ---
    out["rolling_max"] = out["close"].rolling(config.DRAWDOWN_WINDOW).max()
    out["drawdown"] = (out["close"] - out["rolling_max"]) / out["rolling_max"]

    return out


def compute_integracion(df: pd.DataFrame) -> pd.Series:
    """
    INTEGRACION(C, N): coherencia entre estructura (Cristo) y momentum
    emergente reconocido por el volumen (Negra Nueva).
    """
    w = config.INTEGRACION_WEIGHTS

    # trend_coherence: EMA rápida por encima de la lenta y con pendiente
    # positiva => tendencia "coherente" y ascendente.
    trend_raw = df["ema_gap"] + df["ema_gap_slope"].fillna(0)
    trend_coherence = _normalize(trend_raw)

    # volume_confirmation: correlación local (signo) entre retorno y
    # cambio de volumen — el volumen "confirma" el movimiento de precio.
    confirmation_raw = np.sign(df["ret"]) * df["vol_chg"]
    volume_confirmation = _normalize(confirmation_raw.fillna(0))

    integracion = (
        w["trend_coherence"] * trend_coherence
        + w["volume_confirmation"] * volume_confirmation
    )
    return integracion.rename("integracion")


def compute_fragmentacion(df: pd.DataFrame) -> pd.Series:
    """
    FRAGMENTACION(D): distorsión / caos introducido por el Demiurgo —
    aquí, ruptura de estructura de mercado.
    """
    w = config.FRAGMENTACION_WEIGHTS

    # volatility_spike: volatilidad actual relativa a su propia media móvil
    vol_ratio = (df["volatility"] / df["volatility_avg"]).replace(
        [np.inf, -np.inf], np.nan
    )
    volatility_spike = _normalize(vol_ratio.fillna(1.0))

    # drawdown_severity: qué tan lejos está el precio de su máximo reciente
    drawdown_severity = _normalize(-df["drawdown"].fillna(0))  # invertido: más caída = más frag.

    # price_volume_dislocation: precio y volumen moviéndose en direcciones
    # "incoherentes" respecto al patrón esperado (aquí, divergencia
    # absoluta entre signo de retorno y signo de cambio de volumen).
    dislocation_raw = (np.sign(df["ret"]) - np.sign(df["vol_chg"])).abs()
    dislocation = _normalize(dislocation_raw.fillna(0))

    fragmentacion = (
        w["volatility_spike"] * volatility_spike
        + w["drawdown_severity"] * drawdown_severity
        + w["price_volume_dislocation"] * dislocation
    )
    return fragmentacion.rename("fragmentacion")


def classify_state(score: float) -> str:
    if score > config.THETA:
        return "P"       # Pleroma — señal de entrada
    if score < config.THETA_LOWER:
        return "K"        # Kenoma — sin posición / salida
    return "K*"            # transición — mantener


@dataclass
class ArcaState:
    timestamp: pd.Timestamp
    close: float
    integracion: float
    fragmentacion: float
    liberacion_score: float
    state: str


def compute_arca_states(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completo: indicadores -> integración/fragmentación ->
    liberacion_score -> estado K/K*/P, para cada fila del DataFrame.
    """
    ind = compute_indicators(df)
    integracion = compute_integracion(ind)
    fragmentacion = compute_fragmentacion(ind)

    result = pd.DataFrame(
        {
            "close": ind["close"],
            "integracion": integracion,
            "fragmentacion": fragmentacion,
        }
    )
    result["liberacion_score"] = result["integracion"] - result["fragmentacion"]
    result["state"] = result["liberacion_score"].apply(classify_state)
    return result.dropna()


def latest_state(df: pd.DataFrame) -> ArcaState:
    states = compute_arca_states(df)
    last = states.iloc[-1]
    return ArcaState(
        timestamp=states.index[-1],
        close=float(last["close"]),
        integracion=float(last["integracion"]),
        fragmentacion=float(last["fragmentacion"]),
        liberacion_score=float(last["liberacion_score"]),
        state=str(last["state"]),
    )
