#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, List

import ccxt.pro as ccxtpro
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import joblib
from loguru import logger

CONFIG = {
    'exchange': 'binance',
    'symbol': 'BTC/USDT',
    'timeframe': '4h',
    'limit': 500,
    'capital_inicial': 10000,
    'riesgo_por_trade': 0.01,
    'max_trade_pct': 0.5,
    'confianza_minima': 0.68,
    'stop_loss_pct': 0.005,
    'take_profit_pct': 0.010,
    'model_path': 'models/arca_elite.joblib',
    'log_file': 'arca_elite.log'
}

logger.remove()
logger.add(CONFIG['log_file'], rotation="1 day", retention="7 days", format="{time:HH:mm:ss} | {level} | {message}")
logger.add(sys.stdout, format="{time:HH:mm:ss} | {level} | {message}")

class PaperTrading:
    def __init__(self, capital: float = 10000):
        self.capital_inicial = capital
        self.balances = {'USDT': capital}
        self.posiciones = []
        self.historial = []
        self.precios = {}

    def update_price(self, symbol: str, price: float):
        self.precios[symbol] = price

    def get_total_capital(self) -> float:
        total = self.balances.get('USDT', 0)
        for asset, balance in self.balances.items():
            if asset != 'USDT' and balance > 0:
                precio = self.precios.get(f"{asset}/USDT", 0)
                total += balance * precio
        return total

    def create_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        asset = symbol.split('/')[0]
        cost = amount * price
        if side == 'buy':
            if cost > self.balances.get('USDT', 0):
                return {'error': 'Saldo insuficiente', 'status': 'error'}
            self.balances['USDT'] -= cost
            self.balances[asset] = self.balances.get(asset, 0) + amount
            self.posiciones.append({
                'symbol': symbol, 'side': side, 'entry_price': price,
                'amount': amount, 'entry_time': datetime.now().isoformat(), 'status': 'open'
            })
            logger.info(f"📈 COMPRA: {amount:.6f} {asset} @ ${price:,.2f}")
        else:
            if amount > self.balances.get(asset, 0):
                return {'error': f'Saldo insuficiente de {asset}', 'status': 'error'}
            self.balances[asset] -= amount
            self.balances['USDT'] += cost
            for pos in self.posiciones:
                if pos['symbol'] == symbol and pos['status'] == 'open':
                    pos['status'] = 'closed'
                    pos['exit_price'] = price
                    pos['pnl'] = (price - pos['entry_price']) * amount
                    self.historial.append(pos)
                    break
            logger.info(f"📉 VENTA: {amount:.6f} {asset} @ ${price:,.2f}")
        return {'status': 'filled', 'paper': True}

    def get_metricas(self) -> Dict:
        capital = self.get_total_capital()
        trades = [p for p in self.historial if p.get('status') == 'closed']
        ganadores = [p for p in trades if p.get('pnl', 0) > 0]
        pnl_neto_usd = capital - self.capital_inicial
        total_return_pct = (pnl_neto_usd / self.capital_inicial) * 100
        return {
            'capital_actual': capital,
            'pnl_usd': pnl_neto_usd,
            'total_return': total_return_pct,
            'trades_totales': len(trades),
            'win_rate': len(ganadores) / max(1, len(trades))
        }
class ExchangeConnector:
    def __init__(self):
        self.exchange = None
        self.conectado = False
        self.paper = PaperTrading(CONFIG['capital_inicial'])
        self._init()

    def _init(self):
        try:
            self.exchange = ccxtpro.binance({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
            self.conectado = True
            logger.info("✅ Conectado a Binance")
        except Exception as e:
            logger.error(f"❌ Error: {e}")

    async def get_ohlcv(self, symbol: str, timeframe: str = '4h', limit: int = 500):
        try:
            data = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"❌ Error OHLCV: {e}")
            return pd.DataFrame()

    async def get_ticker(self, symbol: str):
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {'last': ticker['last']}
        except Exception as e:
            return {'last': 0}

    async def close(self):
        if self.exchange:
            await self.exchange.close()

class SistemaML:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = xgb.XGBClassifier(n_estimators=50, max_depth=3, random_state=42)
        self.entrenado = False
        logger.info("✅ Modelo ML inicializado")

    def extract_features(self, df: pd.DataFrame) -> np.ndarray:
        features = [df['close'].values, df['close'].pct_change().values, df['volume'].values, (df['high'] - df['low']).values]
        periodos_rolling = (5, 10, 20)
        for p in periodos_rolling:
            features.append(df['close'].rolling(p).mean().values)
            features.append(df['close'].rolling(p).std().values)
        X = np.column_stack(features)
        return np.nan_to_num(X, nan=0)

    def prepare_labels(self, df: pd.DataFrame) -> np.ndarray:
        returns = df['close'].pct_change(3).shift(-3)
        labels = np.zeros(len(df))
        labels[returns > 0.01] = 1
        labels[returns < -0.01] = 0
        labels[abs(returns) <= 0.01] = -1
        return labels

    async def train(self, df: pd.DataFrame):
        logger.info("🧠 Entrenando modelo...")
        X = self.extract_features(df)
        y = self.prepare_labels(df)
        valid = y != -1
        X, y = X[valid], y[valid]
        if len(X) < 20:
            return {'error': 'Datos insuficientes'}
        split = int(len(X) * 0.8)
        X_train = self.scaler.fit_transform(X[:split])
        X_test = self.scaler.transform(X[split:])
        self.model.fit(X_train, y[:split])
        self.entrenado = True
        acc = self.model.score(X_test, y[split:])
        logger.info(f"✅ Modelo entrenado | Accuracy: {acc:.2%}")
        return {'accuracy': acc}
    async def predict(self, df: pd.DataFrame) -> Dict:
        if not self.entrenado:
            return {'estado': 'K*', 'confianza': 0.5}
        X = self.extract_features(df.tail(30))
        X_last = self.scaler.transform(X[-1:].copy())
        proba = self.model.predict_proba(X_last)
        probabilidad_subida = float(proba[0][1]) if len(proba[0]) > 1 else float(proba[0][0])
        if probabilidad_subida >= CONFIG['confianza_minima']:
            return {'estado': 'P', 'confianza': probabilidad_subida}
        elif probabilidad_subida <= (1.0 - CONFIG['confianza_minima']):
            return {'estado': 'K', 'confianza': (1.0 - probabilidad_subida)}
        return {'estado': 'K*', 'confianza': probabilidad_subida}

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({'model': self.model, 'scaler': self.scaler}, path)

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        data = joblib.load(path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.entrenado = True
        return True

class SistemaArcaElite:
    def __init__(self):
        self.exchange = ExchangeConnector()
        self.ml = SistemaML()
        self.running = False

    async def run(self):
        self.running = True
        logger.info("🚀 Sistema Arca Elite v2 Operativo")
        if self.ml.load(CONFIG['model_path']):
            logger.info("💾 Modelo histórico cargado con éxito")
        else:
            logger.warning("⚠️ No se encontró modelo previo. Entrenando base inicial...")
            df_inicial = await self.exchange.get_ohlcv(CONFIG['symbol'], CONFIG['timeframe'], CONFIG['limit'])
            await self.ml.train(df_inicial)
            self.ml.save(CONFIG['model_path'])

        while self.running:
            try:
                df = await self.exchange.get_ohlcv(CONFIG['symbol'], CONFIG['timeframe'], CONFIG['limit'])
                ticker = await self.exchange.get_ticker(CONFIG['symbol'])
                precio_actual = ticker['last']
                if df.empty or precio_actual == 0:
                    await asyncio.sleep(10)
                    continue
                self.exchange.paper.update_price(CONFIG['symbol'], precio_actual)
                prediccion = await self.ml.predict(df)
                estado = prediccion['estado']
                confianza = prediccion['confianza']
                metricas = self.exchange.paper.get_metricas()
                logger.info(f"📊 ARCA: estado={estado}, score={confianza:.3f}")
                logger.info(f"💰 Balance: ${metricas['capital_actual']:,.2f} | Return: {metricas['total_return']:+.4f}% | PnL: ${metricas['pnl_usd']:+.2f}")
                posiciones_activas = [p for p in self.exchange.paper.posiciones if p.get('status') == 'open']
                if not posiciones_activas:
                    if estado == 'P':
                        cantidad = (metricas['capital_actual'] * CONFIG['max_trade_pct']) / precio_actual
                        self.exchange.paper.create_order(CONFIG['symbol'], 'buy', cantidad, precio_actual)
                else:
                    for pos in posiciones_activas:
                        if estado == 'K':
                            self.exchange.paper.create_order(CONFIG['symbol'], 'sell', pos['amount'], precio_actual)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"❌ Error en el bucle principal: {e}")
                await asyncio.sleep(10)

if __name__ == '__main__':
    bot = SistemaArcaElite()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("🛑 Bot detenido por el usuario.")
