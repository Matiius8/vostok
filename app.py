import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página - Modo Cápsula Espacial
st.set_page_config(page_title="Vostok Control", page_icon="🚀", layout="centered")

# ==================== CONEXIÓN CON GOOGLE SHEETS ====================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Caché en 0m para que no te muestre fantasmas y siempre traiga lo último
    if "df_libros" not in st.session_state:
        st.session_state.df_libros = conn.read(worksheet="Libros", ttl="0m")
    if "df_ventas" not in st.session_state:
        st.session_state.df_ventas = conn.read(worksheet="Ventas", ttl="0m")
    if "df_insumos" not in st.session_state:
        st.session_state.df_insumos = conn.read(worksheet="Insumos", ttl="0m")
        
    df_libros = st.session_state.df_libros
    df_ventas = st.session_state.df_ventas
    df_insumos = st.session_state.df_insumos

    if not df_insumos.empty:
        df_insumos["Cantidad Comprada"] = pd.to_numeric(df_insumos["Cantidad Comprada"], errors='coerce').fillna(0)
        df_insumos["Costo Total"] = pd.to_numeric(df_insumos["Costo Total"], errors='coerce').fillna(0)
    if not df_ventas.empty:
        df_ventas["Cantidad Cafés"] = pd.to_numeric(df_ventas["Cantidad Cafés"], errors='coerce').fillna(0)

except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.exception(e)
    st.stop()

# ==================== PANEL LATERAL: RECETA Y CONFIGURACIÓN ====================
st.sidebar.title("🛸 Comando Lateral")
menu = st.sidebar.radio("Navegación", ["🛒 Registrar Venta", "📚 Cargar Libro", "📦 Compras de Insumos"])

st.sidebar.markdown("---")

with st.sidebar.expander("📐 Configurar Receta y Precio"):
    PRECIO_CAFE_LISTA = st.number_input("Precio de Venta Café ($U):", value=130, step=10)
    st.markdown("**Porciones por taza:**")
    RECETA_CAFE_G = st.number_input("Gramos de Café (g):", value=15, step=1)
    RECETA_VASOS = st.number_input("Cantidad de Vasos:", value=1, step=1)

# ==================== ALGORITMO DE MATEMÁTICA INTERNA ====================
def calcular_costo_unitario(df, palabra_clave):
    if df.empty: return 0.0
    filtro = df[df["Insumo"].str.lower().str.contains(palabra_clave, na=False)]
    total_cant = filtro["Cantidad Comprada"].sum()
    total_costo = filtro["Costo Total"].sum()
    return total_costo / total_cant if total_cant > 0 else 0.0

costo_gramo_cafe = calcular_costo_unitario(df_insumos, "caf")
costo_vaso_unidad = calcular_costo_unitario(df_insumos, "vaso")

COSTO_INSUMO_CAFE = (RECETA_CAFE_G * costo_gramo_cafe) + (RECETA_VASOS * costo_vaso_unidad)

total_cafes_vendidos = df_ventas["Cantidad Cafés"].sum() if not df_ventas.empty else 0
total_cafe_comprado = df_insumos[df_insumos["Insumo"].str.lower().str.contains("caf", na=False)]["Cantidad Comprada"].sum() if not df_insumos.empty else 0
total_vasos_comprados = df_insumos[df_insumos["Insumo"].str.lower().str.contains("vaso", na=False)]["Cantidad Comprada"].sum() if not df_insumos.empty else 0

stock_actual_cafe_g = max(0.0, total_cafe_comprado - (total_cafes_vendidos * RECETA_CAFE_G))
stock_actual_vasos = max(0, int(total_vasos_comprados - (total_cafes_vendidos * RECETA_VASOS)))

posibles_por_cafe = int(stock_actual_cafe_g // RECETA_CAFE_G) if RECETA_CAFE_G > 0 else 999
posibles_por_vasos = int(stock_actual_vasos // RECETA_VASOS) if RECETA_VASOS > 0 else 999
cafes_maximos_disponibles = min(posibles_por_cafe, posibles_por_vasos)


# ==================== PANTALLA 1: REGISTRAR VENTA ====================
if menu == "🛒 Registrar Venta":
    st.title("🚀 Vostok — Sistema de Comando")
    st.subheader("📝 Nueva Venta (Modo Rambla)")
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        st.caption(f"☕ Stock Café: {stock_actual_cafe_g:.0f}g ({posibles_por_cafe} tazas)")
    with col_st2:
        st.caption(f"🥤 Stock Vasos: {stock_actual_vasos} un. ({posibles_por_vasos} tazas)")
        
    st.markdown("---")
    
    libros_disponibles = df_libros[df_libros["Estado"] == "🟢 En Órbita"] if not df_libros.empty else pd.DataFrame()
    
    opciones_libros = {}
    if not libros_disponibles.empty:
        opciones_libros = {
            f"[{row['ID Libro']}] {row['Título']} - ${row['Precio Lista']}": row 
            for idx, row in libros_disponibles.iterrows()
        }
    
    libros_seleccionados = st.multiselect(
        "Seleccioná los libros (podés escribir el código o título para buscar):",
        options=list(opciones_libros.keys()),
        key="w_libros"
    )
    
    cant_cafes = st.number_input(
        "Cantidad de cafés entregados:", 
        min_value=0, 
        max_value=max(0, cafes_maximos_disponibles),
        step=1,
        key="w_cafes"
    )
    
    if cafes_maximos_disponibles == 0:
        st.error("⚠️ ¡Alerta! Sin insumos suficientes en los tanques para preparar café.")

    st.markdown("---")
    
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
    
    st.subheader("💵 Resumen de Venta")
    st.metric(label="TOTAL A COBRAR", value=f"$U {total_a_cobrar:.0f}")
    st.caption(f"Detalle: {cant_libros} libro(s) y {cant_cafes} café(s) ({cafes_gratis} en promo / {cafes_cobrados} cobrados)")
    
    with st.expander("📊 Datos de Comandancia (Oculto al cliente)", expanded=False):
        st.metric(label="Ganancia Real (Limpia)", value=f"$U {ganancia_real:.2f}")
        st.write(f"• Costo real calculado por taza: $U {COSTO_INSUMO_CAFE:.2f}")
    
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
                
                conn.update(worksheet="Libros", data=df_libros)
                conn.update(worksheet="Ventas", data=df_ventas)
                
                # RESETEO SEGURO: Borramos los casilleros de la memoria sin reasignarlos.
                claves_a_borrar = ["df_libros", "df_ventas", "w_libros", "w_cafes"]
                for clave in claves_a_borrar:
                    if clave in st.session_state:
                        del st.session_state[clave]
                
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
        
        # SIN CEROS: Cajas vacías con placeholder
        costo = st.number_input("Costo de Adquisición ($U):", min_value=0.0, step=10.0, value=None, placeholder="Ej: 150")
        precio = st.number_input("Precio de Lista al Público ($U):", min_value=0.0, step=10.0, value=None, placeholder="Ej: 450")
        
        submit = st.form_submit_button("🛰️ Lanzar libro a Órbita")
        
        if submit:
            if not id_libro or not titulo or costo is None or precio is None:
                st.error("Faltan datos obligatorios para el lanzamiento (ID, Título, Costo o Precio).")
            elif not df_libros.empty and id_libro in df_libros["ID Libro"].values:
                st.error("Ese ID ya existe en la base.")
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
        
        # SIN CEROS
        cantidad = st.number_input("Cantidad comprada (g o unidades):", min_value=1, step=10, value=None, placeholder="Ej: 1000")
        unidad_texto = "g" if insumo_tipo == "Café" else "unidades"
        costo_total_compra = st.number_input("Costo Total de la Compra ($U):", min_value=0.0, step=50.0, value=None, placeholder="Ej: 1200")
        
        submit_insumo = st.form_submit_button("📦 Guardar en bodega")
        
        if submit_insumo:
            if cantidad is None or costo_total_compra is None:
                st.error("Completá todos los campos numéricos, bo.")
            else:
                nueva_compra = {
                    "Fecha": datetime.now().strftime("%Y-%m-%d"),
                    "Insumo": insumo_tipo,
                    "Cantidad Comprada": cantidad,
                    "Unidad": unidad_texto,
                    "Costo Total": costo_total_compra
                }
                
                df_insumos = pd.concat([df_insumos, pd.DataFrame([nueva_compra])], ignore_index=True)
                conn.update(worksheet="Insumos", data=df_insumos)
                del st.session_state.df_insumos
                st.success(f"¡Se registraron {cantidad} {unidad_texto} de {insumo_tipo} correctamente!")
                st.rerun()
