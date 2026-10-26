import streamlit as st
import google.genai as genai
from PIL import Image
import json
import uuid
from datetime import datetime

st.set_page_config(page_title="CampusFix AI", page_icon="🏫", layout="wide")

# Inicialización de la base de datos temporal en sesión
if "tickets" not in st.session_state:
    st.session_state.tickets = []

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "¡Hola! ¿Cómo estás? Somos el equipo de Mantenimiento e Infraestructura Universitaria. ¿En qué te podemos servir hoy? Por favor, cuéntanos qué problema observas y adjunta una imagen del daño para procesar la reparación."
        }
    ]

# Configuración del cliente Gemini leyendo la API Key de Streamlit Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY", "PEGA_AQUI_TU_API_KEY_SI_PRUEBAS_LOCAL")
client = genai.Client(api_key=API_KEY)

# Navegación por perfiles en el menú lateral
st.sidebar.title("👥 Perfiles del Sistema")
perfil = st.sidebar.radio("Selecciona tu rol:", ["💬 Usuario (Reportar Daño)", "🛠️ Técnico (Mesa de Despacho)"])

# -----------------------------------------------------------------------------
# PERFIL 1: CHATBOT DE REPORTES (ESTUDIANTE / DOCENTE)
# -----------------------------------------------------------------------------
if perfil == "💬 Usuario (Reportar Daño)":
    st.title("🤖 Chatbot de Mantenimiento Campus")
    st.caption("CampusFix AI - Motor Multimodal para Infraestructura Universitaria")

    # Historial de conversación
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Entrada de mensaje del usuario
    if user_input := st.chat_input("Escribe los detalles del daño aquí..."):
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

    # Subida de imagen
    uploaded_image = st.file_uploader("Adjuntar foto del daño para procesar:", type=["jpg", "png", "jpeg"])

    if st.button("Enviar Reporte a Mantenimiento"):
        if not uploaded_image or len(st.session_state.chat_messages) < 2:
            st.warning("Por favor escribe la descripción en el chat y adjunta la fotografía del daño.")
        else:
            with st.spinner("Analizando la imagen y el texto con Google AI Studio..."):
                img = Image.open(uploaded_image)
                ultima_desc = st.session_state.chat_messages[-1]["content"]

                prompt_sys = """
                Eres CampusFix AI, el asistente virtual oficial de mantenimiento de la universidad.
                Analiza la imagen y la descripción enviada. Responde ÚNICAMENTE en formato JSON estricto con la siguiente estructura:
                {
                  "reporte_valido": true,
                  "categoria": "Categoría asignada (Plomería, Electricidad, Mobiliario, TI, Infraestructura, Otro)",
                  "nivel_urgencia": "Crítica | Alta | Media | Baja",
                  "cuadrilla_asignada": "Nombre de la cuadrilla o departamento",
                  "diagnostico_tecnico": "Dictamen detallado con instrucciones y repuestos para el trabajador de reparación",
                  "mensaje_estudiante": "Mensaje amable de confirmación para el usuario indicando que el reporte fue recibido y su ticket está en proceso"
                }
                """

                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[ultima_desc, img],
                    config=genai.types.GenerateContentConfig(
                        system_instruction=prompt_sys,
                        response_mime_type="application/json"
                    )
                )

                data = json.loads(response.text)

                if data.get("reporte_valido"):
                    ticket_id = f"TCK-{uuid.uuid4().hex[:5].upper()}"
                    
                    nuevo_ticket = {
                        "id": ticket_id,
                        "fecha": datetime.now().strftime("%H:%M - %d/%m/%Y"),
                        "descripcion": ultima_desc,
                        "categoria": data.get("categoria"),
                        "urgencia": data.get("nivel_urgencia"),
                        "cuadrilla": data.get("cuadrilla_asignada"),
                        "diagnostico": data.get("diagnostico_tecnico"),
                        "estado": "En Proceso"
                    }
                    st.session_state.tickets.append(nuevo_ticket)

                    # Respuesta conversacional generada para el usuario
                    respuesta_bot = f"🤖 **CampusFix AI:** {data.get('mensaje_estudiante')}\n\n🎟️ **Ticket:** `{ticket_id}`\n📂 **Categoría:** {data.get('categoria')}\n⚡ **Estado:** `En Proceso` (Cuadrilla: {data.get('cuadrilla_asignada')})"
                    st.session_state.chat_messages.append({"role": "assistant", "content": respuesta_bot})
                    st.rerun()

# -----------------------------------------------------------------------------
# PERFIL 2: TÉCNICO DE REPARACIONES / MANTENIMIENTO
# -----------------------------------------------------------------------------
else:
    st.title("🛠️ Mesa de Despacho y Solución de Incidencias")
    st.caption("Recepción operativa de órdenes generadas por la IA para el personal de reparación")

    if not st.session_state.tickets:
        st.info("No hay tickets pendientes registrados.")
    else:
        for idx, tck in enumerate(st.session_state.tickets):
            with st.expander(f"📌 Ticket {tck['id']} | {tck['categoria']} | Urgencia: {tck['urgencia']} | Estado: {tck['estado']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Fecha:** {tck['fecha']}")
                    st.write(f"**Descripción del usuario:** {tck['descripcion']}")
                    st.write(f"**Cuadrilla encargada:** {tck['cuadrilla']}")
                with col2:
                    st.subheader("📋 Dictamen Técnico de la IA:")
                    st.info(tck["diagnostico"])

                # Actualización de estado por el técnico
                estado_actual = tck["estado"]
                nuevo_estado = st.selectbox(
                    f"Actualizar estado del Ticket {tck['id']}:",
                    ["En Proceso", "Solucionado"],
                    index=0 if estado_actual == "En Proceso" else 1,
                    key=f"estado_tec_{idx}"
                )

                if nuevo_estado != tck["estado"]:
                    st.session_state.tickets[idx]["estado"] = nuevo_estado
                    notif = f"📢 **Notificación de Mantenimiento:** El ticket `{tck['id']}` fue marcado como **{nuevo_estado.upper()}** por el equipo de reparación."
