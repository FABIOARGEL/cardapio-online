"""
Utility functions for Cardápio Online.

Helpers globais reutilizáveis em todo o projeto.
"""
import re
import uuid
import html
from datetime import datetime
from slugify import slugify as _slugify


def gerar_numero_pedido() -> str:
    """
    Generate a unique order number in format: ORD-YYYYMMDD-XXXX

    Example: ORD-20260503-A1B2
    """
    date_part = datetime.now().strftime('%Y%m%d')
    unique_part = uuid.uuid4().hex[:4].upper()
    return f"ORD-{date_part}-{unique_part}"


def generate_slug(text: str) -> str:
    """
    Generate a URL-safe slug from text.

    Example: "Pizzaria do João" → "pizzaria-do-joao"
    """
    return _slugify(text, max_length=100)


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS attacks.
    Escapes HTML entities.
    """
    if not text:
        return text
    return html.escape(str(text), quote=True)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets requirements:
    - Minimum 8 characters
    - At least 1 number
    - At least 1 special character

    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres."

    if not re.search(r'\d', password):
        return False, "Senha deve conter pelo menos 1 número."

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Senha deve conter pelo menos 1 caractere especial."

    return True, ""


def format_money(value: float) -> str:
    """Format a monetary value in Brazilian Real format."""
    return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename using UUID to prevent collisions.

    Example: "foto.jpg" → "a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg"
    """
    ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else 'jpg'
    return f"{uuid.uuid4().hex}.{ext}"
