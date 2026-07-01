import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ai_verifier import evaluate_project_with_ai

def main():
    print("--- Probando Verificación Normativa con Gemini e Instructor ---")
    
    oguc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge", "OGUC_2026.md")
    if not os.path.exists(oguc_path):
        print(f"Error: No se encontró la OGUC en {oguc_path}")
        return
        
    print("Cargando OGUC para la prueba...")
    with open(oguc_path, "r", encoding="utf-8") as f:
        oguc_text = f.read()[:250000]
        
    plan_mock = (
        "PROYECTO: Edificio Residencial Los Andes\n"
        "PLANO DE ACCESO Y DISTRIBUCIÓN PISO 1\n"
        "- Ancho libre de la puerta de acceso principal: 0.75 metros.\n"
        "- Ancho de la puerta del baño de visitas: 0.65 metros.\n"
        "- Rampa de acceso PMR: longitud 5.0 metros, altura a salvar 0.90 metros (pendiente aprox. 18%).\n"
        "- Altura de piso a cielo en pasillo principal: 2.10 metros.\n"
        "- No cuenta con ruta accesible desde el límite de sitio hasta la puerta principal."
    )
    
    print("\nTexto de plano de prueba a evaluar:")
    print(plan_mock)
    print("-" * 40)
    
    print("\nEnviando petición a la API de Gemini... (esto puede tardar unos segundos)")
    try:
        result = evaluate_project_with_ai(plan_mock, oguc_text)
        print("\n¡Éxito! Respuesta estructurada recibida de Gemini:")
        print(f"Nombre del Proyecto: {result.project_name}")
        print(f"Viabilidad Normativa: {result.success_probability}%")
        print(f"Resumen General:\n{result.summary_notes}")
        print("\nInfracciones Detectadas:")
        for idx, inf in enumerate(result.infractions, 1):
            print(f"\n[{idx}] {inf.rule_id}: {inf.description}")
            print(f"    Severidad: {inf.severity}")
            print(f"    Evidencia en Plano: '{inf.evidence}'")
            print(f"    Justificación: {inf.justification}")
    except Exception as e:
        print(f"\nError durante la prueba de IA: {e}")

if __name__ == "__main__":
    main()