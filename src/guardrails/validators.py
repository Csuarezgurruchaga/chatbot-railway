def validar_tema_incendios(texto: str) -> bool:
    """Verifica si el tema está relacionado con seguridad contra incendios"""
    palabras_permitidas = [
        "matafuego", "matafuegos", "extintor", "extintores", "incendio", "incendios", 
        "fuego", "seguridad", "inspeccion", "inspecciones", "habilitacion", 
        "habilitaciones", "bomba", "bombas", "hidrante", "hidrantes", 
        "sprinkler", "sprinklers", "detector", "detectores", "humo", "alarma", 
        "alarmas", "prevencion", "proteccion", "emergencia", "emergencias",
        "evacuacion", "riesgo", "riesgos", "instalacion", "instalaciones",
        "mantenimiento", "certificacion", "certificaciones", "norma", "normas",
        "iram", "nfpa", "bombero", "bomberos", "argenfuego", "eva",
        "servicio", "servicios", "consultoria", "asesoramiento", "capacitacion"
    ]
    
    texto_lower = texto.lower()
    return any(palabra in texto_lower for palabra in palabras_permitidas)

def validar_sin_palabrotas(texto: str) -> bool:
    """Verifica que no haya vocabulario obsceno"""
    palabras_prohibidas = [
        "puto", "puta", "carajo", "concha", "pelotudo", "pelotuda",
        "boludo", "boluda", "idiota", "estupido", "estupida", "mierda",
        "cagar", "joder", "coger", "verga", "pija", "choto", "gil",
        "tarado", "tarada", "forro", "la concha", "negro de mierda",
        "hijo de puta", "la puta madre", "que se vayan", "villero"
    ]
    
    texto_lower = texto.lower()
    return not any(palabra in texto_lower for palabra in palabras_prohibidas)

def validar_mensaje_completo(texto: str) -> dict:
    """Valida un mensaje completo con ambos filtros"""
    es_tema_valido = validar_tema_incendios(texto)
    sin_palabrotas = validar_sin_palabrotas(texto)
    
    return {
        "es_valido": es_tema_valido and sin_palabrotas,
        "tema_valido": es_tema_valido,
        "lenguaje_apropiado": sin_palabrotas,
        "razon_rechazo": get_razon_rechazo(es_tema_valido, sin_palabrotas)
    }

def get_razon_rechazo(tema_valido: bool, lenguaje_apropiado: bool) -> str:
    """Obtiene la razón específica del rechazo"""
    if not tema_valido and not lenguaje_apropiado:
        return "tema_y_lenguaje"
    elif not tema_valido:
        return "tema_fuera_alcance"
    elif not lenguaje_apropiado:
        return "lenguaje_inapropiado"
    else:
        return None