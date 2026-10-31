# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

import talib.abstract as ta
from technical import qtpylib


class TrendRider(IStrategy):
    """
    TrendRider — estratégia trend-following defensiva.

    Filosofia (o oposto do problema da SampleStrategy):
      - Só compra a favor da tendência de alta (EMA50 > EMA200, preço acima da EMA200)
      - Entra em pullbacks (RSI recuperando de zona baixa dentro da tendência)
      - Corta perdas rápido: stoploss -4%
      - Deixa ganhos correrem: trailing stop ativado a partir de +3%
    """

    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short: bool = False

    # ROI generoso: a saída principal é o trailing stop / sinal de saída
    minimal_roi = {
        "0": 0.15,
        "720": 0.08,
        "1440": 0.04,
    }

    # Corta perdas rápido
    stoploss = -0.04

    # Deixa ganhos correrem: ativa trailing quando lucro > 3%, segue a 1.5%
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    process_only_new_candles = True
    startup_candle_count: int = 220  # EMA200 precisa de histórico

    # Parâmetros ajustáveis via hyperopt
    buy_rsi = IntParameter(30, 50, default=42, space="buy")
    buy_adx = IntParameter(15, 35, default=20, space="buy")
    sell_rsi = IntParameter(70, 85, default=78, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Tendência de alta confirmada
                (dataframe["ema50"] > dataframe["ema200"])
                & (dataframe["close"] > dataframe["ema200"])
                # Tendência com força
                & (dataframe["adx"] > self.buy_adx.value)
                # Pullback: RSI cruzando para cima do gatilho (recuperação)
                & qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)
                # Preço ainda próximo da média (não comprar topo esticado)
                & (dataframe["close"] < dataframe["ema20"] * 1.02)
                # Liquidez mínima
                & (dataframe["volume"] > dataframe["volume_mean20"] * 0.5)
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Sobrecomprado extremo: realiza lucro
                (dataframe["rsi"] > self.sell_rsi.value)
                # Ou tendência quebrou: fecha abaixo da EMA50
                | qtpylib.crossed_below(dataframe["close"], dataframe["ema50"])
            )
            & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe
