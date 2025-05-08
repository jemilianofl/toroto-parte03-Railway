import os
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from models import Base, Proyecto, Cuadrilla, Responsable, Obra, Evidencia, generate_uuid

# Cargar variables de entorno
load_dotenv()
POSTGRES_URL = os.getenv("POSTGRES_URL")

# Conexión a PostgreSQL
engine = create_engine(POSTGRES_URL)
Session = sessionmaker(bind=engine)
session = Session()

# ------------------- Carga de datos -------------------
df = pd.read_excel("Datos.xlsx", sheet_name="Hoja 1")
df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)

# ------------------- Inserción de catálogos -------------------
print("🔄 Insertando catálogos (proyectos, cuadrillas, responsables)...")

for nombre in df['Proyecto'].dropna().unique():
    if not session.query(Proyecto).filter_by(nombre=nombre).first():
        session.add(Proyecto(nombre=nombre))

for nombre in df['Cuadrilla'].dropna().unique():
    if not session.query(Cuadrilla).filter_by(nombre=nombre).first():
        session.add(Cuadrilla(nombre=nombre))

responsables = df[['Responsable de reporte', 'Correo reponsable de reporte', 'Rol']].drop_duplicates()
for _, r in responsables.iterrows():
    if not session.query(Responsable).filter_by(correo=r['Correo reponsable de reporte']).first():
        session.add(Responsable(
            nombre=r['Responsable de reporte'],
            correo=r['Correo reponsable de reporte'],
            rol=r['Rol']
        ))

session.commit()
print("✅ Catálogos insertados correctamente.")

# ------------------- Mapas de ID -------------------
proy_map = {p.nombre: p.id for p in session.query(Proyecto).all()}
cuad_map = {c.nombre: c.id for c in session.query(Cuadrilla).all()}
resp_map = {r.correo: r.id for r in session.query(Responsable).all()}

# ------------------- Insertar obras y evidencias -------------------
print("🔄 Insertando obras y evidencias...")
nuevas_obras = 0

for _, row in df.iterrows():
    try:
        obra_excel_id = str(row['ID obra']).strip()
        if session.query(Obra).filter_by(obra_excel_id=obra_excel_id).first():
            print(f"⏭️ Obra ya existente, omitida: {obra_excel_id}")
            continue

        obra_id = generate_uuid()
        obra = Obra(
            id=obra_id,
            obra_excel_id=obra_excel_id,
            proyecto_id=proy_map.get(row['Proyecto']),
            cuadrilla_id=cuad_map.get(row['Cuadrilla']),
            responsable_id=resp_map.get(row['Correo reponsable de reporte']),
            fase=row.get('Fase'),
            actividad=row.get('Actividad'),
            tipo_obra=row.get('Tipo de Obra'),
            nombre_obra=row.get('Nombre de la obra'),
            estado=row.get('Estado'),
            fecha_inicio=pd.to_datetime(row.get('Fecha de inicio'), errors='coerce'),
            fecha_fin=pd.to_datetime(row.get('Fecha de finalización'), errors='coerce'),
            coordenadas=row.get('Coordenadas'),
            geometria=row.get('Geometría para la gráfica de la obra'),
            base_mayor_m=row.get('Base mayor (m)'),
            base_menor_m=row.get('Base menor (m)'),
            alto_m=row.get('Alto (m)'),
            largo_m=row.get('Largo (m)'),
            largo_azolve_m=row.get('Largo de azolve (m)'),
            volumen_construccion_m3=row.get('Volumen de construcción (m3)'),
            volumen_almacenamiento_m3=row.get('Volumen de almacenamiento (m3)'),
            area_m2=row.get('área (m2)'),
            observaciones=row.get('Observaciones') if pd.notna(row.get('Observaciones')) else ''
        )

        session.add(obra)
        session.flush()  # Importante para que obra_id esté disponible

        for i in range(1, 6):
            url = row.get(f"Evidencia fotográfica {i}")
            if pd.notna(url):
                session.add(Evidencia(obra_id=obra_id, url=url))

        print(f"✅ Obra nueva insertada: {obra.nombre_obra}")
        nuevas_obras += 1

    except Exception as e:
        print(f"❌ Error al insertar obra {row.get('Nombre de la obra', '')}: {str(e)}")
        session.rollback()

# ------------------- Commit final -------------------
session.commit()
print(f"\n🎉 Proceso finalizado. Obras nuevas insertadas: {nuevas_obras}")
total = session.query(Obra).count()
print(f"📊 Total de obras registradas en PostgreSQL: {total}")