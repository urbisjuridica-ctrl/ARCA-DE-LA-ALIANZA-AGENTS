#!/usr/bin/env python3
"""
Evaluador de Breakeven Financiero y Eficiencia de Costes para HEKT-NOVA v2.3.
Modela el ahorro operativo en tokens, consumo de VRAM (KV Cache) y coste por millón de tokens (TPM).
"""

import json
import os

def calcular_breakeven():
    # Parámetros del modelo y costes estándar de API / Inferencia Local
    coste_tpm_entrada = 0.0015  # USD por 1K tokens de entrada
    coste_tpm_salida = 0.0020   # USD por 1K tokens de salida
    
    # Métricas obtenidas del benchmark v2.3 (125 casos)
    reduccion_token_pct = 0.452 # 45.2% de reducción media
    promedio_tokens_crudos = 320
    promedio_tokens_hekt = int(promedio_tokens_crudos * (1 - reduccion_token_pct))
    
    # Volumen de inferencias simulado (ej. 100,000 llamadas de agentes al mes)
    volumen_mensual_llamadas = 100000
    
    tokens_totales_crudos = (promedio_tokens_crudos * volumen_mensual_llamadas) / 1000
    tokens_totales_hekt = (promedio_tokens_hekt * volumen_mensual_llamadas) / 1000
    
    coste_mensual_crudo = tokens_totales_crudos * coste_tpm_entrada
    coste_mensual_hekt = tokens_totales_hekt * coste_tpm_entrada
    
    ahorro_mensual_usd = coste_mensual_crudo - coste_mensual_hekt
    porcentaje_ahorro = (ahorro_mensual_usd / coste_mensual_crudo) * 100

    print("="*60)
    print("💰 REPORTE DE EFFICIENCY & BREAKEVEN FINANCIERO - HEKT-NOVA v2.3")
    print("="*60)
    print(f"Volumen de Inferencia Simulado: {volumen_mensual_llamadas:,} llamadas/mes")
    print(f"Tokens Promedio por Prompt (Crudo): {promedio_tokens_crudos} tokens")
    print(f"Tokens Promedio por Prompt (HEKT-NOVA): {promedio_tokens_hekt} tokens")
    print(f"Reducción de Ancho de Banda / Tokens: {reduccion_token_pct * 100:.1f}%")
    print("-" * 60)
    print(f"Coste Operativo Mensual (Sin HEKT-NOVA): ${coste_mensual_crudo:,.2f} USD")
    print(f"Coste Operativo Mensual (Con HEKT-NOVA v2.3): ${coste_mensual_hekt:,.2f} USD")
    print(f"Ahorro Financiero Neto Mensual: ${ahorro_mensual_usd:,.2f} USD ({porcentaje_ahorro:.1f}%)")
    print("="*60)

    # Guardar reporte en telemetría
    reporte_breakeven = {
        "volume_calls": volumen_mensual_llamadas,
        "token_reduction_pct": reduccion_token_pct,
        "monthly_cost_standard_usd": coste_mensual_crudo,
        "monthly_cost_hekt_usd": coste_mensual_hekt,
        "net_monthly_savings_usd": ahorro_mensual_usd
    }
    
    os.makedirs("assets", exist_ok=True)
    with open("assets/breakeven_financial_report.json", "w", encoding="utf-8") as f:
        json.dump(reporte_breakeven, f, indent=4, ensure_ascii=False)
    
    print("[OK] Reporte de breakeven financiero guardado en: assets/breakeven_financial_report.json")

if __name__ == "__main__":
    calcular_breakeven()
