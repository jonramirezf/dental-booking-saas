# ============================================================
# ARCHIVO 7 de 9: ia/services.py
# UBICACIÓN: ia/services.py
# ACCIÓN: REEMPLAZAR el archivo completo
# ERRORES CORREGIDOS:
#   - Manejo de errores completo (API key faltante, timeout, respuesta inválida)
#   - API key tomada desde settings, no directamente desde os.environ
#   - Timeout en la request HTTP para evitar que cuelgue
#   - Validación de la respuesta de OpenAI antes de acceder a choices[0]
# NOTA: ia/views.py ya no se usa. El endpoint está en agenda/views.py::chat_ia
# ============================================================

import os
import requests
from django.conf import settings


def responder(mensaje: str) -> str:
    """
    Envía un mensaje al LLM y retorna la respuesta como string.
    Lanza Exception con mensaje claro si algo falla.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')

    if not api_key:
        raise Exception(
            'OPENAI_API_KEY no configurada. Agrega la variable de entorno al archivo .env'
        )

    url = 'https://api.openai.com/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [
            {
                'role': 'system',
                'content': (
                    'Eres el asistente virtual de una clínica dental. '
                    'Responde de forma amigable, breve y profesional. '
                    'Solo responde preguntas relacionadas con la clínica, '
                    'citas, servicios o salud dental. '
                    'Si no sabes algo, pide que se contacten directamente con la clínica.'
                )
            },
            {'role': 'user', 'content': mensaje}
        ],
        'max_tokens': 300,
        'temperature': 0.7,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise Exception('El servicio de IA tardó demasiado. Intenta de nuevo.')
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise Exception('API key de OpenAI inválida.')
        if response.status_code == 429:
            raise Exception('Demasiadas solicitudes. Intenta en un momento.')
        raise Exception(f'Error del servicio de IA: {response.status_code}')
    except requests.exceptions.RequestException:
        raise Exception('No se pudo conectar al servicio de IA.')

    try:
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, ValueError):
        raise Exception('Respuesta inesperada del servicio de IA.')
