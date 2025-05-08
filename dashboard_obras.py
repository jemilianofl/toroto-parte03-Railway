import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy import func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import pandas as pd
import streamlit as st
import plotly.express as px
import socket

original_getaddrinfo = socket.getaddrinfo
def force_ipv4_getaddrinfo(*args, **kwargs):
    return [info for info in original_getaddrinfo(*args, **kwargs) if info[0] == socket.AF_INET]
socket.getaddrinfo = force_ipv4_getaddrinfo

# Cargar variables de entorno
load_dotenv()
RAILWAY_URL = os.getenv("POSTGRES_URL")

# Configurar la base de datos
engine = create_engine(RAILWAY_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Declarar modelos ORM
Base = declarative_base()

class Proyecto(Base):
    __tablename__ = 'proyectos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    obras = relationship("Obra", back_populates="proyecto")

class Cuadrilla(Base):
    __tablename__ = 'cuadrillas'
    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    obras = relationship("Obra", back_populates="cuadrilla")

class Obra(Base):
    __tablename__ = 'obras'
    id = Column(Integer, primary_key=True)
    tipo_obra = Column(String)
    proyecto_id = Column(Integer, ForeignKey('proyectos.id'))
    cuadrilla_id = Column(Integer, ForeignKey('cuadrillas.id'))

    proyecto = relationship("Proyecto", back_populates="obras")
    cuadrilla = relationship("Cuadrilla", back_populates="obras")

# Consultas ORM para resumen de obras por proyecto
def obtener_resumen_por_proyecto():
    result = (
        session.query(Proyecto.nombre.label("proyecto"), Obra.tipo_obra, func.count(Obra.id).label("total_obras"))
        .join(Obra, Proyecto.id == Obra.proyecto_id)
        .group_by(Proyecto.nombre, Obra.tipo_obra)
        .order_by(Proyecto.nombre, func.count(Obra.id).desc())
        .all()
    )
    return pd.DataFrame(result, columns=["proyecto", "tipo_obra", "total_obras"])

# Consultas ORM para resumen de obras por cuadrilla
def obtener_resumen_por_cuadrilla():
    result = (
        session.query(Cuadrilla.nombre.label("cuadrilla"), Obra.tipo_obra, func.count(Obra.id).label("total_obras"))
        .join(Obra, Cuadrilla.id == Obra.cuadrilla_id)
        .group_by(Cuadrilla.nombre, Obra.tipo_obra)
        .order_by(Cuadrilla.nombre, func.count(Obra.id).desc())
        .all()
    )
    return pd.DataFrame(result, columns=["cuadrilla", "tipo_obra", "total_obras"])

# Estilo del dashboard
st.set_page_config(page_title="Dashboard de Obras", layout="wide")
st.markdown("""
    <style>
        body {
            background-color: #1e1e2f;
            color: white;
        }
        .stApp {
            background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Título
st.title("🏗️ Dashboard de Obras - Toroto")
st.markdown("""
    Este panel presenta un resumen visual e interactivo de las obras ejecutadas por **proyecto** y **cuadrilla**. 
    Se muestra la cantidad total de obras agrupadas por tipo, lo que permite analizar la distribución del trabajo en el tiempo.
""")

# Obtener datos
with st.spinner("Cargando datos desde Railway..."):
    df_proyecto = obtener_resumen_por_proyecto()
    df_cuadrilla = obtener_resumen_por_cuadrilla()

# Visualización por proyecto
st.subheader("Obras por tipo y proyecto")
st.dataframe(df_proyecto)

fig1 = px.bar(df_proyecto, x="proyecto", y="total_obras", color="tipo_obra", barmode="group",
                title="Distribución de Obras por Proyecto",
                labels={"total_obras": "Total de Obras", "proyecto": "Proyecto"})
fig1.update_layout(template="plotly_dark")
st.plotly_chart(fig1, use_container_width=True)

# Visualización por cuadrilla
st.subheader("Obras por tipo y cuadrilla")
st.dataframe(df_cuadrilla)

fig2 = px.bar(df_cuadrilla, x="cuadrilla", y="total_obras", color="tipo_obra", barmode="group",
                title="Distribución de Obras por Cuadrilla",
                labels={"total_obras": "Total de Obras", "cuadrilla": "Cuadrilla"})
fig2.update_layout(template="plotly_dark")
st.plotly_chart(fig2, use_container_width=True)
