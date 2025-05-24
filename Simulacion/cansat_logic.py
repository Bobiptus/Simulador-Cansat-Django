import rocketpy as rp
from rocketpy import Environment, Rocket, Flight, SolidMotor
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import datetime
import os
import sqlite3
import logging
import matplotlib

matplotlib.use('Agg')

from django.conf import settings

logger = logging.getLogger(__name__)

# --- Función para inicializar la base de datos y su esquema ---
def init_db():
    db_path = settings.SIMULATION_DB_PATH
    print(f"DEBUG: init_db intentando conectar/crear DB en: {db_path}")

    # Asegura que el directorio para la DB exista si se especificó una subcarpeta
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                inclination REAL,
                heading REAL,
                rail_length REAL,
                cansat_mass REAL,
                drag_coeff REAL,
                burn_time REAL,
                avg_thrust REAL,
                elevation REAL,
                apogee REAL,
                graph_image_url TEXT
            )
        ''')
        conn.commit()
        print(f"Base de datos inicializada o verificada en: {db_path}")
    except sqlite3.Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# --- La función principal de simulación ---
def simulate_cansat(user_inclination, user_heading, user_rail_length, user_cansat_mass, user_drag_coeff, user_burn_time, user_avg_thrust, user_elevation):
    try:
        # Llama a init_db para asegurar que la tabla existe
        init_db()

        # --- Configuración del Entorno ---
        env = rp.Environment(
            latitude=31.8664,
            longitude=-116.5959,
            elevation=user_elevation
        )

        simulation_datetime = datetime.datetime.now()
        env.set_date(simulation_datetime, timezone="America/Tijuana")
        env.set_atmospheric_model(type="standard_atmosphere")

        # --- Motor ---
        gas_motor = rp.SolidMotor(
            thrust_source=user_avg_thrust,
            burn_time=user_burn_time,
            dry_mass=0.5,
            dry_inertia=(0.02, 0.02, 0.001),
            center_of_dry_mass_position=0.15,
            grains_center_of_mass_position=0.2,
            grain_number=1,
            grain_separation=0.005,
            grain_density=1700.0,
            grain_outer_radius=0.02,
            grain_initial_inner_radius=0.005,
            grain_initial_height=0.08,
            nozzle_radius=0.01,
            throat_radius=0.005,
            interpolation_method='linear',
            nozzle_position=0.0,
            coordinate_system_orientation='nozzle_to_combustion_chamber'
        )

        # --- CanSat ---
        can_sat = rp.Rocket(
            radius=0.033,
            mass=user_cansat_mass,
            inertia=(0.0001, 0.0001, 0.0002),
            center_of_mass_without_motor=0.15,
            coordinate_system_orientation='nose_to_tail',
            power_off_drag=user_drag_coeff,
            power_on_drag=user_drag_coeff
        )
        can_sat.add_motor(gas_motor, position=0.3)

        # --- Vuelo ---
        flight = rp.Flight(
            rocket=can_sat,
            environment=env,
            rail_length=user_rail_length,
            inclination=user_inclination,
            heading=user_heading
        )
        flight.post_process()

        apogee = round(flight.apogee, 2) if flight.apogee else None

        # --- Obtener la solución de vuelo ---
        solution_array = np.array(flight.solution)
        if solution_array.size == 0:
            return {
                "success": False,
                "message": "La simulación no generó resultados válidos o el vuelo no pudo procesarse."
            }

        # --- Generar gráficas ---
        plt.figure(figsize=(10, 8))
        plt.subplot(2, 1, 1)
        plt.plot(solution_array[:, 0], solution_array[:, 3], label="Altitud (z)")
        plt.legend()
        plt.title("Altitud y Velocidad Vertical vs Tiempo")
        plt.xlabel("Tiempo (s)")
        plt.ylabel("Altitud (m)")

        plt.subplot(2, 1, 2)
        plt.plot(solution_array[:, 0], solution_array[:, 6], label="Velocidad Vertical (vz)")
        plt.legend()
        plt.xlabel("Tiempo (s)")
        plt.ylabel("Velocidad Vertical (m/s)")
        plt.tight_layout()

        # Gráfica 3D de la trayectoria
        fig3d = plt.figure(figsize=(10, 8))
        ax3d = fig3d.add_subplot(111, projection='3d')
        ax3d.plot(solution_array[:, 1], solution_array[:, 2], solution_array[:, 3], label='Trayectoria')
        ax3d.set_xlabel("Eje X (m)")
        ax3d.set_ylabel("Eje Y (m)")
        ax3d.set_zlabel("Altitud (m)")
        ax3d.set_title("Trayectoria de Vuelo 3D")
        ax3d.legend()
        ax3d.grid(True)

        # --- Guardar imagen ---
        output_dir = os.path.join(os.path.dirname(__file__), "static", "generated_plots")
        os.makedirs(output_dir, exist_ok=True)

        file_name = simulation_datetime.strftime("%Y%m%d_%H%M%S") + ".png"
        full_image_path = os.path.join(output_dir, file_name)

        print(f"DEBUG: Intentando guardar la imagen en: {full_image_path}")

        plt.savefig(full_image_path, dpi=300, bbox_inches='tight')
        plt.close('all')

        relative_image_url = os.path.join("generated_plots", file_name)

        # --- Guardar en la base de datos ---
        insert_into_db(
            simulation_datetime, flight, user_inclination, user_heading, user_rail_length,
            user_cansat_mass, user_drag_coeff, user_burn_time, user_avg_thrust, user_elevation, relative_image_url 
        )

        return {
            "success": True,
            "apogee": apogee,
            "graphImage": relative_image_url
        }

    except Exception as e:
        logger.error(f"Error durante la simulación: {str(e)}", exc_info=True) 
        return {
            "success": False,
            "message": f"Error durante la simulación: {str(e)}"
        }

# --- Función para insertar resultados en la base de datos ---
def insert_into_db(
    simulation_datetime,
    flight,
    user_inclination,
    user_heading,
    user_rail_length,
    user_cansat_mass,
    user_drag_coeff,
    user_burn_time,
    user_avg_thrust,
    user_elevation,
    image_url 
):
    db_path = settings.SIMULATION_DB_PATH
    print(f"DEBUG: insert_into_db está intentando conectar a la DB en: {db_path}")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(simulation_results);")
            columns = [info[1] for info in cursor.fetchall()]
            if 'graph_image_url' not in columns:
                cursor.execute("ALTER TABLE simulation_results ADD COLUMN graph_image_url TEXT;")
                conn.commit()
                logger.info("Columna 'graph_image_url' añadida a la tabla 'simulation_results'.")
        except sqlite3.Error as e:
            logger.warning(f"No se pudo verificar/añadir la columna 'graph_image_url': {e}. Es posible que ya exista.")

        timestamp_str = simulation_datetime.strftime("%Y-%m-%d %H:%M:%S")
        apogee_value = round(flight.apogee, 2) if flight.apogee else None

        cursor.execute('''
            INSERT INTO simulation_results (
                timestamp, apogee, inclination, heading, rail_length,
                cansat_mass, drag_coeff, burn_time, avg_thrust, elevation, graph_image_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        ''', (
            timestamp_str,
            apogee_value,
            user_inclination,
            user_heading,
            user_rail_length,
            user_cansat_mass,
            user_drag_coeff,
            user_burn_time,
            user_avg_thrust,
            user_elevation,
            image_url 
        ))
        conn.commit()
        logger.info("Resultados guardados en la base de datos.")

        return {
            "success": True,
            "message": "Resultados guardados correctamente.",
            "apogee": apogee_value
        }

    except sqlite3.Error as e:
        logger.error(f"Error en la base de datos al insertar: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error en la base de datos: {e}"
        }
    except Exception as e:
        logger.error(f"Error inesperado en insert_into_db: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error inesperado: {e}"
        }
    finally:
        if 'conn' in locals() and conn: 
            conn.close()

# --- Función para consultar la base de datos ---
def consult_db():
    db_path = settings.SIMULATION_DB_PATH
    print(f"DEBUG: consult_db está intentando conectar a la DB en: {db_path}")

    conn = None
    results = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, inclination, heading, rail_length, cansat_mass, drag_coeff, burn_time, avg_thrust, elevation, apogee, graph_image_url FROM simulation_results ORDER BY timestamp DESC")
        rows = cursor.fetchall()

        if not rows:
            logger.info("No hay resultados en la base de datos.")
            return [] 

        logger.info(f"Resultados obtenidos de la base de datos: {len(rows)} filas.")
        return rows 

    except sqlite3.Error as e:
        logger.error(f"Error en la base de datos al consultar: {e}", exc_info=True)
        return [] 
    except Exception as e:
        logger.error(f"Error inesperado en consult_db: {e}", exc_info=True)
        return [] 
    finally:
        if conn:
            conn.close()

# --- Función para limpiar la base de datos ---
def limpiar_bd():
    db_path = settings.SIMULATION_DB_PATH
    logger.info(f"DEBUG: limpiar_bd está intentando conectar a la DB en: {db_path}")
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS simulation_results")
        conn.commit()
        logger.info(f"Tabla 'simulation_results' eliminada de la base de datos en: {db_path}")
        return {
            "success": True,
            "message": "Resultados de simulación eliminados de la base de datos."
        }
    except sqlite3.Error as e:
        logger.error(f"Error al limpiar la base de datos: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error al limpiar la base de datos: {e}"
        }
    except Exception as e:
        logger.error(f"Error inesperado en limpiar_bd: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error inesperado: {e}"
        }
    finally:
        if conn:
            conn.close()