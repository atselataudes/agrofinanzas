# Operation Categories and Rules

CATALOGO_OPS = {
    "Ingreso": {
        "💸 Anticipo / Amarre Cosecha":    {"kilos": False, "precio_unitario": False, "lote": "Obligatorio", "ayuda": "Dinero recibido por adelantado."},
        "🥑 Venta Cosecha (Exportación)": {"kilos": True,  "precio_unitario": True,  "lote": "Obligatorio", "ayuda": "Venta de fruta de primera calidad."},
        "🥑 Venta Cosecha (Nacional)":    {"kilos": True,  "precio_unitario": True,  "lote": "Obligatorio", "ayuda": "Fruta para mercado nacional."},
        "🗑️ Venta Descarte/Merma":        {"kilos": True,  "precio_unitario": True,  "lote": "Obligatorio", "ayuda": "Fruta pequeña o cacahuate."},
        "💰 Otros Ingresos":               {"kilos": False, "precio_unitario": False, "lote": "Opcional",    "ayuda": "Venta de chatarra, madera, etc."}
    },
    "Gasto Huerto": {
        "👷 Nómina / Raya Semanal":       {"kilos": False, "precio_unitario": False, "lote": "Opcional",    "ayuda": "Pago de trabajadores."},
        "🧪 Fertilizantes (Suelo)":       {"kilos": True,  "precio_unitario": False, "lote": "Opcional",    "ayuda": "Sacos o Granulados."},
        "☠️ Agroquímicos (Foliares)":     {"kilos": True,  "precio_unitario": False, "lote": "Opcional",    "ayuda": "Fumigaciones."},
        "⛽ Combustible":                 {"kilos": True,  "precio_unitario": False, "lote": "No",          "ayuda": "Gasolina/Diesel para trabajo."},
        "🚜 Mantenimiento":               {"kilos": False, "precio_unitario": False, "lote": "No",          "ayuda": "Refacciones, mecánico."},
        "🔧 Herramientas":                {"kilos": False, "precio_unitario": False, "lote": "Opcional",    "ayuda": "Tijeras, bombas, equipo."},
        "💡 Servicios (Luz/Agua)":        {"kilos": False, "precio_unitario": False, "lote": "Opcional",    "ayuda": "CFE Huerto, Derechos de agua."},
        "📑 Administrativo":              {"kilos": False, "precio_unitario": False, "lote": "No",          "ayuda": "Contador, trámites, cuotas."},
        "📦 Empaque":                     {"kilos": False, "precio_unitario": False, "lote": "Opcional",    "ayuda": "Cajas, materiales."}
    },
    "Gasto Personal": {
        "🏥 Salud / Médicos":             {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Consultas, medicinas."},
        "🛒 Víveres / Despensa":          {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Supermercado, comida."},
        "✈️ Vacaciones / Ocio":           {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Viajes, salidas."},
        "🏠 Gastos de Casa":              {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Luz casa, Internet casa."},
        "👗 Ropa y Calzado":              {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Compras personales."},
        "🎓 Educación":                   {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Colegiaturas."},
        "🚗 Transporte Personal":         {"kilos": False, "precio_unitario": False, "lote": "No", "ayuda": "Gasolina auto particular."}
    }
}

CATEGORIAS_PERSONALES = list(CATALOGO_OPS["Gasto Personal"].keys())
