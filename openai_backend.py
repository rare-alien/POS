"""
Backend reutilizable para analisis de negocio con OpenAI.

Usa la API moderna de OpenAI mediante Responses API y mantiene la API key
fuera del codigo.
"""

import json
import os
from typing import Any, Optional


_OPENAI_IMPORT_ERROR = None

try:
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
        OpenAI,
        RateLimitError,
    )
except ImportError as error:
    OpenAI = None
    APIConnectionError = APIError = APITimeoutError = AuthenticationError = RateLimitError = Exception
    _OPENAI_IMPORT_ERROR = error


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
DEFAULT_INSTRUCTIONS = """
Eres un analista de negocio para un punto de venta.
Responde en espanol claro, profesional y accionable.
Prioriza:
1. Hallazgos clave del negocio.
2. Riesgos u oportunidades detectadas.
3. Recomendaciones practicas y concretas.
4. Explicaciones basadas unicamente en los datos recibidos.

Si faltan datos para una conclusion, dilo explicitamente.
""".strip()


class OpenAIBackendError(RuntimeError):
    """Error controlado para integraciones con OpenAI."""


def get_openai_client(api_key: Optional[str] = None) -> Any:
    """
    Crea un cliente OpenAI usando una API key externa al codigo.

    Busca la clave en `OPENAI_API_KEY` si no se pasa manualmente.
    """
    if OpenAI is None:
        raise OpenAIBackendError(
            "La libreria 'openai' no esta instalada. Instala con: pip install openai"
        ) from _OPENAI_IMPORT_ERROR

    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise OpenAIBackendError(
            "No se encontro la variable de entorno OPENAI_API_KEY."
        )

    try:
        return OpenAI(api_key=resolved_api_key)
    except Exception as error:
        raise OpenAIBackendError(
            f"No fue posible inicializar el cliente de OpenAI: {error}"
        ) from error


def generate_response(prompt: str, data: Any) -> str:
    """
    Genera una respuesta de negocio a partir de un prompt y datos estructurados.

    - `prompt`: instruccion o pregunta del usuario
    - `data`: diccionario, lista u objeto serializable con el contexto del negocio
    """
    prompt_text = _normalize_prompt(prompt)
    serialized_data = _serialize_data(data)
    client = get_openai_client()

    try:
        response = client.responses.create(
            model=DEFAULT_MODEL,
            instructions=DEFAULT_INSTRUCTIONS,
            input=(
                "Analiza el siguiente contexto de negocio y responde en espanol.\n\n"
                f"Objetivo del analisis:\n{prompt_text}\n\n"
                "Datos estructurados del negocio en formato JSON:\n"
                f"{serialized_data}"
            ),
        )
    except AuthenticationError as error:
        raise OpenAIBackendError(
            "Autenticacion fallida con OpenAI. Revisa OPENAI_API_KEY."
        ) from error
    except RateLimitError as error:
        raise OpenAIBackendError(
            "Se alcanzo el limite de uso de OpenAI. Intenta nuevamente mas tarde."
        ) from error
    except APITimeoutError as error:
        raise OpenAIBackendError(
            "La solicitud a OpenAI excedio el tiempo de espera."
        ) from error
    except APIConnectionError as error:
        raise OpenAIBackendError(
            "No fue posible conectar con OpenAI. Verifica red o firewall."
        ) from error
    except APIError as error:
        raise OpenAIBackendError(
            f"OpenAI devolvio un error de API: {error}"
        ) from error
    except Exception as error:
        raise OpenAIBackendError(
            f"Error inesperado al generar respuesta con OpenAI: {error}"
        ) from error

    output_text = _extract_output_text(response)
    if not output_text:
        raise OpenAIBackendError(
            "OpenAI devolvio una respuesta vacia o sin texto util."
        )

    return output_text


def _normalize_prompt(prompt: str) -> str:
    """Valida el prompt de entrada."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise OpenAIBackendError("'prompt' debe ser un texto no vacio.")
    return prompt.strip()


def _serialize_data(data: Any) -> str:
    """Convierte datos de negocio a JSON legible para el modelo."""
    try:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        fallback_payload = {
            "raw_data": str(data),
        }
        return json.dumps(fallback_payload, indent=2, ensure_ascii=False)


def _extract_output_text(response: Any) -> str:
    """Extrae texto util desde la respuesta del SDK moderno."""
    direct_text = getattr(response, "output_text", None)
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    fragments = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text_value = getattr(content, "text", None)
            if isinstance(text_value, str) and text_value.strip():
                fragments.append(text_value.strip())

    return "\n".join(fragments).strip()


__all__ = [
    "DEFAULT_INSTRUCTIONS",
    "DEFAULT_MODEL",
    "OpenAIBackendError",
    "generate_response",
    "get_openai_client",
]
