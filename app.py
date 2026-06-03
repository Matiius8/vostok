import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuración de la página - Modo Cápsula Espacial
st.set_page_config(page_title="Vostok Control", page_icon="🚀", layout="centered")

# Valores fijos de la cafetería para la matemática interna
PRECIO_CAFE_LISTA = 130
COSTO_INSUMO_CAFE = 23

st.title("🚀 Vostok — Sistema de Comando")
st.write("Gestión de stock y bitácora de ventas en tiempo real.")
st.markdown("---")

# Conexión segura con Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_libros = conn.read(worksheet="Libros", ttl="0m")
    df_ventas = conn.read(worksheet="Ventas", ttl="0m")
    df_insumos = conn.read(worksheet="Insumos", ttl="0m")
except Exception as e:
    st.error("Error al conectar con Google Sheets. Revisá las credenciales en los Secrets de Streamlit.")
    st.stop()

# Menú lateral para cambiar de pantalla fácilmente en el celular
menu = st.sidebar.radio("Navegación de la Nave", ["🛒 Registrar Venta", "📚 Cargar Stock Nuevo"])

# ==================== PANTALLA 1: REGISTRAR VENTA ====================
if menu == "🛒 Registrar Venta":
    st.subheader("📝 Nueva Venta (Modo Rambla)")
    
    # Filtrar solo los libros que están disponibles
    libros_disponibles = df_libros[df_libros["Estado"] == "🟢 En Órbita"]
    
    if libros_disponibles.empty:
        st.warning("No hay libros disponibles en órbita. ¡Cargá stock primero!")
    else:
        # Mapeo de títulos para el selector
        opciones_libros = {f"{row['Título']} - ${row['Precio Lista']}": row for idx, row in libros_disponibles.iterrows()}
        
        libros_seleccionados = st.multiselect(
            "Seleccioná los libros que se llevan:",
            options=list(opciones_libros.keys())
        )
        
        cant_cafes = st.number_input("Cantidad de cafés entregados:", min_value=0, value=0, step=1)
        st.markdown("---")
        
        # --- EL ALGORITMO VOSTOK (Lógica de Promos) ---
        cant_libros = len(libros_seleccionados)
        cupo_cafes_gratis = cant_libros
        
        if cant_cafes <= cupo_cafes_gratis:
            cafes_gratis = cant_cafes
            cafes_cobrados = 0
        else:
            cafes_gratis = cupo_cafes_gratis
            cafes_cobrados = cant_cafes - cupo_cafes_gratis
            
        # Cálculo monetario
        libros_en_carrito = [opciones_libros[nombre] for nombre in libros_seleccionados]
        total_libros = sum(float(l['Precio Lista']) for l in libros_en_carrito)
        total_cafes = cafes_cobrados * PRECIO_CAFE_LISTA
        total_a_cobrar = total_libros + total_cafes
        
        # Costos ocultos e insumos retirados
        costo_libros_total = sum(float(l['Costo Adquisición']) for l in libros_en_carrito)
        costo_cafes_total = cant_cafes * COSTO_INSUMO_CAFE
        costo_total_operacion = costo_libros_total + costo_cafes_total
        
        ganancia_real = total_a_cobrar - costo_total_operacion
        
        # Bloque visual de totales
        st.subheader("💵 Resumen de Caja")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="TOTAL A COBRAR", value=f"$U {total_a_cobrar}")
        with col2:
            st.metric(label="Ganancia Real (Limpia)", value=f"$U {ganancia_real}")
            
        st.write(f"• Detalle: {cant_libros} libro(s) y {cant_cafes} café(s) ({cafes_gratis} gratis / {cafes_cobrados} cobrados)")
        st.markdown("---")
        
        # Botón de ejecución en calle
        if st.button("🚀 Liquidar y Registrar Venta", use_container_width=True):
            if cant_libros == 0 and cant_cafes == 0:
                st.error("El carrito está vacío, bo. Poné algún producto.")
            else:
                with st.spinner("Sincronizando telemetría con Google Sheets..."):
                    # 1. Pasar libros seleccionados a 'Vendido'
                    for libro in libros_en_carrito:
                        idx_libro = df_libros[df_libros["ID Libro"] == libro["ID Libro"]].index[0]
                        df_libros.at[idx_libro, "Estado"] = "🔴 Vendido"
                    
                    # 2. Crear nueva fila en la bitácora de Ventas
                    nueva_venta = {
                        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Libros Vendidos": ", ".join([l["Título"] for l in libros_en_carrito]),
                        "Cantidad Cafés": cant_cafes,
                        "Total Cobrado": total_a_cobrar,
                        "Costo Total": costo_total_operacion,
                        "Ganancia Real": ganancia_real
                    }
                    df_ventas = pd.concat([df_ventas, pd.DataFrame([nueva_venta])], ignore_index=True)
                    
                    # 3. Reescribir los cambios en la nube
                    conn.update(worksheet="Libros", data=df_libros)
                    conn.update(worksheet="Ventas", data=df_ventas)
                    
                    st.success("¡Venta registrada con éxito! Stock actualizado en el Google Sheet.")
                    st.balloons()

# ==================== PANTALLA 2: CARGAR STOCK ====================
elif menu == "📚 Cargar Stock Nuevo":
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
                st.error("El ID y el Título son mandatorios para mantener la base sana.")
            elif id_libro in df_libros["ID Libro"].values:
                st.error("Ese ID ya existe en la base. Poné uno nuevo.")
            else:
                nuevo_registro = {
                    "ID Libro": id_libro,
                    "Título": titulo,
                    "Autor": autor,
                    "Género": genero,
                    "Estado": "🟢 En Órbita",
                    "Costo Adquisición": costo,
                    "Precio Lista": precio
                }
                df_libros = pd.concat([df_libros, pd.DataFrame([nuevo_registro])], ignore_index=True)
                conn.update(worksheet="Libros", data=df_libros)
                st.success(f"¡{titulo} se agregó correctamente al Google Sheet!")
