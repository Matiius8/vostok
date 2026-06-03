import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Vostok Control", page_icon="🚀", layout="centered")

if "form_reset" not in st.session_state:
    st.session_state.form_reset = 0

# ==================== CONEXIÓN CON GOOGLE SHEETS ====================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    if "df_libros" not in st.session_state:
        st.session_state.df_libros = conn.read(worksheet="Libros", ttl="0m")
    if "df_ventas" not in st.session_state:
        st.session_state.df_ventas = conn.read(worksheet="Ventas", ttl="0m")
    if "df_insumos" not in st.session_state:
        st.session_state.df_insumos = conn.read(worksheet="Insumos", ttl="0m")
    if "df_gastos" not in st.session_state:
        st.session_state.df_gastos = conn.read(worksheet="Gastos", ttl="0m")
        
    df_libros = st.session_state.df_libros
    df_ventas = st.session_state.df_ventas
    df_insumos = st.session_state.df_insumos
    df_gastos = st.session_state.df_gastos

    if not df_libros.empty:
        df_libros["Costo Adquisición"] = pd.to_numeric(df_libros["Costo Adquisición"], errors='coerce').fillna(0)
    if not df_insumos.empty:
        df_insumos["Cantidad Comprada"] = pd.to_numeric(df_insumos["Cantidad Comprada"], errors='coerce').fillna(0)
        df_insumos["Costo Total"] = pd.to_numeric(df_insumos["Costo Total"], errors='coerce').fillna(0)
    if not df_ventas.empty:
        df_ventas["Cantidad Cafés"] = pd.to_numeric(df_ventas["Cantidad Cafés"], errors='coerce').fillna(0)
        df_ventas["Total Cobrado"] = pd.to_numeric(df_ventas["Total Cobrado"], errors='coerce').fillna(0)
        df_ventas["Costo Total"] = pd.to_numeric(df_ventas["Costo Total"], errors='coerce').fillna(0)
        df_ventas["Ganancia Real"] = pd.to_numeric(df_ventas["Ganancia Real"], errors='coerce').fillna(0)
    if not df_gastos.empty:
        df_gastos["Monto"] = pd.to_numeric(df_gastos["Monto"], errors='coerce').fillna(0)

except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.exception(e)
    st.stop()

# ==================== PANEL LATERAL: RECETA Y CONFIGURACIÓN ====================
st.sidebar.title("🛸 Comando Lateral")
menu = st.sidebar.radio("Navegación", [
    "📊 Tablero de Mando", 
    "🛒 Registrar Venta", 
    "📚 Cargar Libro", 
    "📦 Compras de Insumos",
    "💸 Tesorería (Gastos y Retiros)"
])

st.sidebar.markdown("---")

with st.sidebar.expander("📐 Configurar Receta y Precio"):
    PRECIO_CAFE_LISTA = st.number_input("Precio de Venta Café ($U):", value=130, step=10)
    RECETA_CAFE_G = st.number_input("Gramos de Café (g):", value=15, step=1)
    RECETA_VASOS = st.number_input("Cantidad de Vasos:", value=1, step=1)

with st.sidebar.expander("🚀 Capital Activo Fijo"):
    VALOR_NAVE = st.number_input("Valor de la Nave (Moto, equipos, etc) $U:", value=0, step=1000, help="Esto suma directo a tu patrimonio total.")

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


# ==================== PANTALLA 0: TABLERO DE MANDO ====================
if menu == "📊 Tablero de Mando":
    st.title("🚀 Vostok — Radar Principal")
    st.write("Finanzas reales al estilo Vostok.")
    st.markdown("---")
    
    # 1. MÉTRICAS DIARIAS
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    df_hoy = df_ventas[df_ventas["Fecha"].str.startswith(hoy_str, na=False)] if not df_ventas.empty else pd.DataFrame()
    
    st.markdown("### 🌊 Actividad de Hoy")
    col_h1, col_h2, col_h3 = st.columns(3)
    if not df_hoy.empty:
        col_h1.metric("Ingreso Hoy", f"$U {df_hoy['Total Cobrado'].sum():,.0f}")
        col_h2.metric("Ganancia Limpia Hoy", f"$U {df_hoy['Ganancia Real'].sum():,.0f}")
        col_h3.metric("Cafés Servidos", f"{df_hoy['Cantidad Cafés'].sum():.0f} tazas")
    else:
        col_h1.metric("Ingreso Hoy", "$U 0")
        col_h2.metric("Ganancia Limpia Hoy", "$U 0")
        col_h3.metric("Cafés Servidos", "0 tazas")
        
    st.markdown("---")

    # 2. GRÁFICO DE VENTAS
    st.markdown("### 📈 Evolución Diaria")
    if not df_ventas.empty:
        df_grafico = df_ventas.copy()
        df_grafico["Día"] = df_grafico["Fecha"].str[:10]
        ventas_por_dia = df_grafico.groupby("Día")["Total Cobrado"].sum()
        st.bar_chart(ventas_por_dia, color="#FF4B4B")
    else:
        st.info("Sin ventas para graficar.")

    st.markdown("---")
    
    # 3. LÓGICA FINANCIERA REALISTA
    st.markdown("### 💼 Tesorería y Patrimonio")
    
    # Sumarizadores de Tesorería
    ingresos_ventas = df_ventas["Total Cobrado"].sum() if not df_ventas.empty else 0
    costos_ventas_hist = df_ventas["Costo Total"].sum() if not df_ventas.empty else 0
    gastos_op = df_gastos[df_gastos["Tipo"].str.contains("Gasto Operativo")]["Monto"].sum() if not df_gastos.empty else 0
    retiros = df_gastos[df_gastos["Tipo"].str.contains("Retiro")]["Monto"].sum() if not df_gastos.empty else 0
    aportes = df_gastos[df_gastos["Tipo"].str.contains("Aporte")]["Monto"].sum() if not df_gastos.empty else 0
    
    inversion_insumos = df_insumos["Costo Total"].sum() if not df_insumos.empty else 0
    inversion_libros = df_libros["Costo Adquisición"].sum() if not df_libros.empty else 0
    
    # EFECTIVO FÍSICO: (Aportes + Ventas) - (Todas las compras + Gastos + Retiros)
    efectivo_caja = (aportes + ingresos_ventas) - (inversion_insumos + inversion_libros + gastos_op + retiros)
    
    # GANANCIA NETA DEL NEGOCIO: Ingresos por Ventas - Costo de lo Vendido - Gastos Operativos
    ganancia_neta_negocio = ingresos_ventas - costos_ventas_hist - gastos_op
    
    # CAPITAL INMOVILIZADO
    capital_libros = df_libros[df_libros["Estado"] == "🟢 En Órbita"]["Costo Adquisición"].sum() if not df_libros.empty else 0
    capital_cafe = stock_actual_cafe_g * costo_gramo_cafe
    capital_vasos = stock_actual_vasos * costo_vaso_unidad
    capital_stock = capital_libros + capital_cafe + capital_vasos
    
    patrimonio_total = efectivo_caja + capital_stock + VALOR_NAVE
    
    col_t1, col_t2 = st.columns(2)
    col_t1.metric("💵 Efectivo en Caja", f"$U {efectivo_caja:,.0f}", help="La plata física que deberías tener en mano (o cuenta).")
    col_t2.metric("📈 Ganancia Neta Global", f"$U {ganancia_neta_negocio:,.0f}", help="Rentabilidad real de la empresa (Ventas menos costos y gastos operativos).")
    
    st.markdown("#### Desglose de Capital")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stock Físico", f"$U {capital_stock:,.0f}")
    c2.metric("La Nave", f"$U {VALOR_NAVE:,.0f}")
    c3.metric("🏆 PATRIMONIO TOTAL", f"$U {patrimonio_total:,.0f}")


# ==================== PANTALLA 1: REGISTRAR VENTA ====================
elif menu == "🛒 Registrar Venta":
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
        opciones_libros = {f"[{row['ID Libro']}] {row['Título']} - {row['Autor']} (${row['Precio Lista']})": row for idx, row in libros_disponibles.iterrows()}
    
    libros_seleccionados = st.multiselect("Seleccioná los libros:", options=list(opciones_libros.keys()), key=f"w_libros_{st.session_state.form_reset}")
    cant_cafes = st.number_input("Cantidad de cafés entregados:", min_value=0, max_value=max(0, cafes_maximos_disponibles), step=1, key=f"w_cafes_{st.session_state.form_reset}")
    
    if cafes_maximos_disponibles == 0:
        st.error("⚠️ ¡Alerta! Sin insumos suficientes.")

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
    
    with st.expander("📊 Datos de Comandancia (Oculto al cliente)"):
        st.metric(label="Ganancia Real (Limpia)", value=f"$U {ganancia_real:.2f}")
        st.write(f"• Costo por taza: $U {COSTO_INSUMO_CAFE:.2f}")
    
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
                del st.session_state.df_libros
                del st.session_state.df_ventas
                st.session_state.form_reset += 1
                st.rerun()

# ==================== PANTALLA 2: CARGAR STOCK LIBROS ====================
elif menu == "📚 Cargar Libro":
    st.title("🚀 Vostok — Sistema de Comando")
    st.subheader("📥 Cargar Libro al Inventario")
    
    with st.form("nuevo_libro_form", clear_on_submit=True):
        id_libro = st.text_input("ID único base (Ej: VS-001):")
        titulo = st.text_input("Título del Libro:")
        autor = st.text_input("Autor:")
        genero = st.selectbox("Género:", ["Science Fiction", "Narrativa Local", "Misterio/Suspenso", "Otros"])
        cantidad_ejemplares = st.number_input("Cantidad de ejemplares:", min_value=1, step=1, value=1)
        costo = st.number_input("Costo de Adquisición C/U ($U):", min_value=0.0, step=10.0, value=None, placeholder="Ej: 150")
        precio = st.number_input("Precio de Lista C/U ($U):", min_value=0.0, step=10.0, value=None, placeholder="Ej: 450")
        
        submit = st.form_submit_button("🛰️ Lanzar a Órbita")
        
        if submit:
            ids_a_crear = [id_libro] if cantidad_ejemplares == 1 else [f"{id_libro}-{i+1}" for i in range(int(cantidad_ejemplares))]
            if not id_libro or not titulo or costo is None or precio is None:
                st.error("Faltan datos obligatorios.")
            elif not df_libros.empty and any(id_new in df_libros["ID Libro"].values for id_new in ids_a_crear):
                st.error("ID existente. Cambiá el código base.")
            else:
                nuevos_registros = []
                for i in range(int(cantidad_ejemplares)):
                    id_final = id_libro if cantidad_ejemplares == 1 else f"{id_libro}-{i+1}"
                    nuevos_registros.append({"ID Libro": id_final, "Título": titulo, "Autor": autor, "Género": genero, "Estado": "🟢 En Órbita", "Costo Adquisición": costo, "Precio Lista": precio})
                df_libros = pd.concat([df_libros, pd.DataFrame(nuevos_registros)], ignore_index=True)
                conn.update(worksheet="Libros", data=df_libros)
                del st.session_state.df_libros
                st.success("¡Libro(s) en órbita!")

# ==================== PANTALLA 3: REGISTRAR COMPRA DE INSUMOS ====================
elif menu == "📦 Compras de Insumos":
    st.title("🚀 Vostok — Reabastecimiento")
    st.subheader("🛒 Registrar Insumos (Solo componentes directos del café)")
    st.caption("Aclaración: El azúcar, edulcorante o removedores cargalos en la pestaña Tesorería como Gasto Operativo.")
    
    with st.form("nuevo_insumo_form", clear_on_submit=True):
        insumo_tipo = st.selectbox("Seleccioná el Insumo:", ["Café", "Vasos"])
        cantidad = st.number_input("Cantidad comprada (g o unidades):", min_value=1, step=10, value=None, placeholder="Ej: 1000")
        unidad_texto = "g" if insumo_tipo == "Café" else "unidades"
        costo_total_compra = st.number_input("Costo Total ($U):", min_value=0.0, step=50.0, value=None, placeholder="Ej: 1200")
        
        submit_insumo = st.form_submit_button("📦 Guardar en bodega")
        if submit_insumo:
            if cantidad is None or costo_total_compra is None:
                st.error("Completá todos los números, bo.")
            else:
                nueva_compra = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Insumo": insumo_tipo, "Cantidad Comprada": cantidad, "Unidad": unidad_texto, "Costo Total": costo_total_compra}
                df_insumos = pd.concat([df_insumos, pd.DataFrame([nueva_compra])], ignore_index=True)
                conn.update(worksheet="Insumos", data=df_insumos)
                del st.session_state.df_insumos
                st.success("¡Stock actualizado!")
                st.rerun()

# ==================== PANTALLA 4: TESORERÍA ====================
elif menu == "💸 Tesorería (Gastos y Retiros)":
    st.title("🚀 Vostok — Tesorería")
    st.write("Registrá aportes, gastos varios y retiros.")
    
    with st.form("nuevo_gasto_form", clear_on_submit=True):
        tipo_movimiento = st.radio("Tipo de Movimiento:", [
            "Aporte de Capital (Inyección de plata)",
            "Gasto Operativo (Nafta, Azúcar, Remitos, etc.)", 
            "Retiro de Gerencia"
        ])
        
        descripcion = st.text_input("Detalle (Ej: 'Azúcar y vasos', 'Bolsillo'):")
        monto_salida = st.number_input("Monto total ($U):", min_value=0.0, step=100.0, value=None, placeholder="Ej: 500")
        
        submit_gasto = st.form_submit_button("⚖️ Registrar Movimiento")
        if submit_gasto:
            if monto_salida is None or not descripcion:
                st.error("Faltan datos.")
            else:
                nuevo_movimiento = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Tipo": tipo_movimiento, "Descripción": descripcion, "Monto": monto_salida}
                df_gastos = pd.concat([df_gastos, pd.DataFrame([nuevo_movimiento])], ignore_index=True)
                conn.update(worksheet="Gastos", data=df_gastos)
                del st.session_state.df_gastos
                st.success("¡Caja actualizada!")
                st.rerun()
