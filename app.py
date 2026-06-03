import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página - Modo Cápsula Espacial
st.set_page_config(page_title="Vostok Control", page_icon="🚀", layout="centered")

# ==================== CONEXIÓN CON GOOGLE SHEETS ====================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Mantenemos los datos en memoria local para fluidez en la calle
    if "df_libros" not in st.session_state:
        st.session_state.df_libros = conn.read(worksheet="Libros", ttl="5m")
    if "df_ventas" not in st.session_state:
        st.session_state.df_ventas = conn.read(worksheet="Ventas", ttl="5m")
    if "df_insumos" not in st.session_state:
        st.session_state.df_insumos = conn.read(worksheet="Insumos", ttl="5m")
        
    df_libros = st.session_state.df_libros
    df_ventas = st.session_state.df_ventas
    df_insumos = st.session_state.df_insumos
except Exception as e:
    st.error("Error de conexión. Revisá los Secrets de Streamlit.")
    st.stop()

# ==================== PANEL LATERAL: RECETA Y CONFIGURACIÓN ====================
st.sidebar.title("🛸 Comando Lateral")
menu = st.sidebar.radio("Navegación", ["🛒 Registrar Venta", "📚 Cargar Libro", "📦 Compras de Insumos"])

st.sidebar.markdown("---")

# CONFIGURACIÓN DE LA RECETA Y PRECIO
with st.sidebar.expander("📐 Configurar Receta y Precio"):
    PRECIO_CAFE_LISTA = st.number_input("Precio de Venta Café ($U):", value=130, step=10)
    st.markdown("**Porciones por taza:**")
    RECETA_CAFE_G = st.number_input("Gramos de Café (g):", value=15, step=1)
    RECETA_VASOS = st.number_input("Cantidad de Vasos:", value=1, step=1)

# ==================== ALGORITMO DE MATEMÁTICA INTERNA (COSTOS Y STOCK) ====================
# 1. Calcular costos unitarios promedio ponderados de tus compras reales
def calcular_costo_unitario(df, nombre_insumo):
    filtro = df[df["Insumo"].str.lower() == nombre_insumo.lower()] if not df.empty else pd.DataFrame()
    total_cant = filtro["Cantidad Comprada"].sum() if not filtro.empty else 0
    total_costo = filtro["Costo Total"].sum() if not filtro.empty else 0
    return total_costo / total_cant if total_cant > 0 else 0.0

costo_gramo_cafe = calcular_costo_unitario(df_insumos, "Café")
costo_vaso_unidad = calcular_costo_unitario(df_insumos, "Vasos")

# Costo real de una taza según tu receta
COSTO_INSUMO_CAFE = (RECETA_CAFE_G * costo_gramo_cafe) + (RECETA_VASOS * costo_vaso_unidad)

# 2. Calcular Stock Actual Disponible (Comprado histórico - Consumido histórico)
total_cafes_vendidos = df_ventas["Cantidad Cafés"].sum() if not df_ventas.empty else 0

total_cafe_comprado = df_insumos[df_insumos["Insumo"].str.lower() == "café"]["Cantidad Comprada"].sum() if not df_insumos.empty else 0
total_vasos_comprados = df_insumos[df_insumos["Insumo"].str.lower() == "vasos"]["Cantidad Comprada"].sum() if not df_insumos.empty else 0

stock_actual_cafe_g = max(0.0, total_cafe_comprado - (total_cafes_vendidos * RECETA_CAFE_G))
stock_actual_vasos = max(0, int(total_vasos_comprados - (total_cafes_vendidos * RECETA_VASOS)))

# ¿Cuántos cafés puedo armar con lo que me queda en la nave?
posibles_por_cafe = int(stock_actual_cafe_g // RECETA_CAFE_G) if RECETA_CAFE_G > 0 else 999
posibles_por_vasos = int(stock_actual_vasos // RECETA_VASOS) if RECETA_VASOS > 0 else 999
cafes_maximos_disponibles = min(posibles_por_cafe, posibles_por_vasos)


# ==================== PANTALLA 1: REGISTRAR VENTA ====================
if menu == "🛒 Registrar Venta":
    st.title("🚀 Vostok — Sistema de Comando")
    st.subheader("📝 Nueva Venta (Modo Rambla)")
    
    # Estado de los tanques de insumos para control del capitán
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.caption(f"☕ Stock Café: {stock_actual_cafe_g:.0f}g ({posibles_por_cafe} tazas)")
    with col_st2:
        st.caption(f"🥤 Stock Vasos: {stock_actual_vasos} un. ({posibles_por_vasos} tazas)")
        
    st.markdown("---")
    
    libros_disponibles = df_libros[df_libros["Estado"] == "🟢 En Órbita"] if not df_libros.empty else pd.DataFrame()
    
    # Selector de libros
    opciones_libros = {}
    if not libros_disponibles.empty:
        opciones_libros = {f"{row['Título']} - ${row['Precio Lista']}": row for idx, row in libros_disponibles.iterrows()}
    
    libros_seleccionados = st.multiselect(
        "Seleccioná los libros que se llevan:",
        options=list(opciones_libros.keys()),
        key="w_libros"
    )
    
    # Control de cafés con límite dinámico según stock real
    cant_cafes = st.number_input(
        "Cantidad de cafés entregados:", 
        min_value=0, 
        max_value=max(0, cafes_maximos_disponibles),
        step=1,
        key="w_cafes",
        help=f"Máximo disponible por stock de insumos: {cafes_maximos_disponibles} tazas."
    )
    
    if cafes_maximos_disponibles == 0:
        st.error("⚠️ ¡Alerta! Sin insumos suficientes en los tanques para preparar café.")

    st.markdown("---")
    
    # --- EL ALGORITMO VOSTOK ---
    cant_libros = len(libros_seleccionados)
    cupo_cafes_gratis = cant_libros
    
    if cant_cafes <= cupo_cafes_gratis:
        cafes_gratis = cant_cafes
        cafes_cobrados = 0
    else:
        cafes_gratis = cupo_cafes_gratis
        cafes_cobrados = cant_cafes - cupo_cafes_gratis
        
    libros_en_carrito = [opciones_libros[nombre] for nombre in libros_seleccionados]
    total_libros = sum(float(l['Precio Lista']) for l in libros_en_carrito)
    total_cafes = cafes_cobrados * PRECIO_CAFE_LISTA
    total_a_cobrar = total_libros + total_cafes
    
    costo_libros_total = sum(float(l['Costo Adquisición']) for l in libros_en_carrito)
    costo_cafes_total = cant_cafes * COSTO_INSUMO_CAFE
    costo_total_operacion = costo_libros_total + costo_cafes_total
    ganancia_real = total_a_cobrar - costo_total_operacion
    
    # Interfaz limpia para el cliente
    st.subheader("💵 Resumen de Venta")
    st.metric(label="TOTAL A COBRAR", value=f"$U {total_a_cobrar:.0f}")
    st.caption(f"Detalle: {cant_libros} libro(s) y {cant_cafes} café(s) ({cafes_gratis} en promo / {cafes_cobrados} cobrados)")
    
    # Datos ocultos de Ganancia
    with st.expander("📊 Datos de Comandancia (Oculto al cliente)", expanded=False):
        st.metric(label="Ganancia Real (Limpia)", value=f"$U {ganancia_real:.2f}")
        st.write(f"• Costo real calculado por taza: $U {COSTO_INSUMO_CAFE:.2f}")
        st.write(f"  *(Café: $U {costo_gramo_cafe*RECETA_CAFE_G:.2f} | Vaso: $U {costo_vaso_unidad*RECETA_VASOS:.2f})*")
    
    st.markdown("---")
    
    if st.button("🚀 Liquidar y Registrar Venta", use_container_width=True):
        if cant_libros == 0 and cant_cafes == 0:
            st.error("El carrito está vacío, bo.")
        else:
            with st.spinner("Sincronizando telemetría..."):
                for libro in libros_en_carrito:
                    idx_libro = df_libros[df_libros["ID Libro"] == libro["ID Libro"]].index[0]
                    df_libros.at[idx_libro, "Estado"] = "🔴 Vendido"
                
                nueva_venta = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Libros Vendidos": ", ".join([l["Título"] for l in libros_en_carrito]),
                    "Cantidad Cafés": cant_cafes,
                    "Total Cobrado": total_a_cobrar,
                    "Costo Total": costo_total_operacion,
                    "Ganancia Real": ganancia_real
                }
                df_ventas = pd.concat([df_ventas, pd.DataFrame([nueva_venta])], ignore_index=True)
                
                # Subida de datos
                conn.update(worksheet="Libros", data=df_libros)
                conn.update(worksheet="Ventas", data=df_ventas)
                
                # Reseteo de memoria
                del st.session_state.df_libros
                del st.session_state.df_ventas
                st.session_state.w_libros = []
                st.session_state.w_cafes = 0
                
                st.toast("¡Venta registrada con éxito!")
                st.rerun()

# ==================== PANTALLA 2: CARGAR STOCK LIBROS ====================
elif menu == "📚 Cargar Libro":
    st.title("🚀 Vostok — Sistema de Comando")
    st.subheader("📥 Cargar Libro al Inventario")
    
    with st.form("nuevo_libro_form", clear_on_submit=True):
        id_libro = st.text_input("ID único del Libro (Ej: VS-001):")
        titulo = st.text_input("Título del Libro:")
        autor = st.text_input("Autor:")
        genero = st.selectbox("Género:", ["Science Fiction", "Narrativa Local", "Misterio/Suspenso", "Otros"])
        costo = st.number_input("Costo de Adquisición ($U):", min_value=0.0, step=10.0)
        precio = st.number_input("Precio de Lista al Público ($U):", min_value=0.0, step=10.0)
        
        submit = st.form_submit_button("🛰️ Lanzar libro a Órbita")
        
        if submit:
            if not id_libro or not titulo:
                st.error("Faltan datos obligatorios.")
            elif not df_libros.empty and id_libro in df_libros["ID Libro"].values:
                st.error("Ese ID ya existe.")
            else:
                nuevo_registro = {
                    "ID Libro": id_libro, "Título": titulo, "Autor": autor, "Género": genero,
                    "Estado": "🟢 En Órbita", "Costo Adquisición": costo, "Precio Lista": precio
                }
                df_libros = pd.concat([df_libros, pd.DataFrame([nuevo_registro])], ignore_index=True)
                conn.update(worksheet="Libros", data=df_libros)
                del st.session_state.df_libros
                st.success(f"¡{titulo} listo en órbita!")

# ==================== PANTALLA 3: REGISTRAR COMPRA DE INSUMOS ====================
elif menu == "📦 Compras de Insumos":
    st.title("🚀 Vostok — Reabastecimiento")
    st.subheader("🛒 Registrar Compra de Insumos/Materia Prima")
    
    with st.form("nuevo_insumo_form", clear_on_submit=True):
        insumo_tipo = st.selectbox("Seleccioná el Insumo:", ["Café", "Vasos"])
        cantidad = st.number_input("Cantidad comprada (en gramos para café, unidades para vasos):", min_value=1, value=1000)
        unidad_texto = "g" if insumo_tipo == "Café" else "unidades"
        costo_total_compra = st.number_input("Costo Total de la Compra ($U):", min_value=0.0, step=50.0)
        
        submit_insumo = st.form_submit_button("📦 Guardar en bodega")
        
        if submit_insumo:
            nueva_compra = {
                "Fecha": datetime.now().strftime("%Y-%m-%d"),
                "Insumo": insumo_tipo,
                "Cantidad Comprada": cantidad,
                "Unidad": intensity_texto = "g" if insumo_tipo == "Café" else "unidades",
                "Costo Total": costo_total_compra
            }
            # Evitamos errores de formato de strings en la asignación directa de unidades
            nueva_compra["Unidad"] = unidad_texto
            
            df_insumos = pd.concat([df_insumos, pd.DataFrame([nueva_compra])], ignore_index=True)
            conn.update(worksheet="Insumos", data=df_insumos)
            del st.session_state.df_insumos
            st.success(f"¡Se registraron {cantidad} {unidad_texto} de {insumo_tipo} correctamente!")
            st.rerun()
