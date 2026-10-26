import unicodedata


def slugify(text: str) -> str:
    """
    Convierte un nombre de ciudad en un identificador seguro para nombres de archivo.
    Elimina tildes para que 'Bahía Blanca' y 'Bahia Blanca' generen el mismo archivo.
    """
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return "_".join(ascii_text.lower().split())
