import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
import asyncio
import time
import json
import gzip
from typing import List, Optional, Dict, Any
import mysql.connector
from mysql.connector import pooling
import uuid
from datetime import datetime
import logging
from collections import defaultdict

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🚂 CONFIGURACIÓN PARA RAILWAY - MySQL en la nube
# Railway inyecta estas variables automáticamente cuando agregas MySQL service
DB_CONFIG = {
    # ⭐ Railway llena estos valores automáticamente, NO uses localhost
    'host': os.getenv('MYSQL_HOST'),         # Railway: containers-us-west-xxx.railway.app
    'database': os.getenv('MYSQL_DATABASE'), # Railway: railway (por defecto)
    'user': os.getenv('MYSQL_USER'),         # Railway: root (por defecto)
    'password': os.getenv('MYSQL_PASSWORD'), # Railway: genera automáticamente
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'autocommit': True,
    'charset': 'utf8mb4',
    'use_unicode': True
}

# Log para debugging - verificar que Railway inyectó las variables
logger.info(f"🔗 MySQL Host: {DB_CONFIG['host']}")
logger.info(f"🔗 MySQL Database: {DB_CONFIG['database']}")
logger.info(f"🔗 MySQL User: {DB_CONFIG['user']}")
logger.info(f"🔗 MySQL Port: {DB_CONFIG['port']}")

# Pool de conexiones MySQL
mysql_pool = None

def init_mysql_pool():
    """Inicializar pool de conexiones MySQL en Railway"""
    global mysql_pool
    try:
        # Verificar que las variables de entorno estén configuradas
        if not DB_CONFIG['host']:
            logger.error("❌ MYSQL_HOST no está configurado - ¿Agregaste MySQL service en Railway?")
            return False
            
        mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mina_pool",
            pool_size=3,  # Pool pequeño para Railway free tier
            pool_reset_session=True,
            **DB_CONFIG
        )
        logger.info("✅ Pool de conexiones MySQL creado exitosamente en Railway")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando pool de conexiones: {e}")
        logger.error("🔧 Verifica que MySQL service esté agregado en Railway")
        mysql_pool = None
        return False

app = FastAPI(
    title="Mina Connectivity Test API - Railway Cloud",
    description="API para probar optimizaciones de conectividad en minas de altura - Desplegada en Railway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware de CORS - Permitir todos los orígenes para app móvil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de compresión GZIP
app.add_middleware(GZipMiddleware, minimum_size=100)

# Métricas simplificadas para Railway
class MetricsCollector:
    def __init__(self):
        self.request_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
    
    def record_request_time(self, endpoint: str, duration: float):
        self.request_times[endpoint].append(duration)
        # Limitar memoria en Railway
        if len(self.request_times[endpoint]) > 50:
            self.request_times[endpoint].pop(0)
    
    def record_success(self, endpoint: str):
        self.success_counts[endpoint] += 1
    
    def record_error(self, endpoint: str):
        self.error_counts[endpoint] += 1

metrics = MetricsCollector()

# Modelos Pydantic (sin cambios)
class MarcacionStandard(BaseModel):
    userName: str
    userEmail: str
    userDni: str
    qrCode: str
    marcationType: str
    latitude: float
    longitude: float
    deviceId: str
    timestamp: Optional[str] = None

class MarcacionCompacta(BaseModel):
    u: str = Field(alias="userName")
    e: str = Field(alias="userEmail") 
    d: str = Field(alias="userDni")
    q: str = Field(alias="qrCode")
    t: str = Field(alias="marcationType")
    lat: float = Field(alias="latitude")
    lon: float = Field(alias="longitude")
    dev: str = Field(alias="deviceId")
    ts: Optional[str] = Field(alias="timestamp", default=None)

    class Config:
        allow_population_by_field_name = True

class MarcacionConToken(BaseModel):
    token_idempotencia: str
    data: MarcacionStandard

# Cache en memoria para tokens de idempotencia
processed_tokens = {}

# Middleware de timeout y métricas
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path
    
    try:
        # Timeout más corto para Railway
        response = await asyncio.wait_for(call_next(request), timeout=20.0)
        duration = time.time() - start_time
        
        metrics.record_request_time(endpoint, duration)
        metrics.record_success(endpoint)
        
        response.headers["X-Process-Time"] = str(duration)
        response.headers["X-Server-Info"] = "Mina-Railway-Cloud"
        response.headers["X-Environment"] = "Railway"
        return response
        
    except asyncio.TimeoutError:
        metrics.record_error(endpoint)
        raise HTTPException(
            status_code=504,
            detail={"error": "Request timeout", "retry_after": 20}
        )
    except Exception as e:
        metrics.record_error(endpoint)
        logger.error(f"Error in {endpoint}: {str(e)}")
        raise

def get_db_connection():
    """Obtener conexión del pool MySQL"""
    if mysql_pool is None:
        logger.error("❌ MySQL pool no disponible")
        raise HTTPException(
            status_code=500, 
            detail="Database not available - check Railway MySQL service"
        )
    return mysql_pool.get_connection()

def init_database():
    """Inicializar tabla de pruebas en MySQL Railway"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear tabla si no existe
        create_table_query = """
        CREATE TABLE IF NOT EXISTS marcaciones_test (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_name VARCHAR(255) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            user_dni VARCHAR(20) NOT NULL,
            qr_code VARCHAR(255) NOT NULL,
            marcation_type VARCHAR(50) NOT NULL,
            latitude DECIMAL(10, 8) NOT NULL,
            longitude DECIMAL(11, 8) NOT NULL,
            device_id VARCHAR(255) NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            test_type VARCHAR(50) NOT NULL,
            payload_size INT DEFAULT 0,
            processing_time DECIMAL(10, 4) DEFAULT 0,
            compression_ratio DECIMAL(5, 4) DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_test_type (test_type),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        conn.commit()
        logger.info("✅ Tabla 'marcaciones_test' creada en MySQL Railway")
        
        # Insertar datos de prueba inicial
        test_data_query = """
        INSERT IGNORE INTO marcaciones_test 
        (user_name, user_email, user_dni, qr_code, marcation_type, 
         latitude, longitude, device_id, test_type, payload_size, processing_time)
        VALUES 
        ('Railway Test User', 'test@railway.app', '12345678', 'QR_RAILWAY_INIT', 'Ingreso', 
         -12.0464, -77.0428, 'RAILWAY_DEVICE', 'init', 250, 0.1)
        """
        cursor.execute(test_data_query)
        conn.commit()
        logger.info("✅ Datos de prueba insertados en Railway MySQL")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        # No lanzar excepción para permitir que Railway inicie
        pass
    finally:
        if 'conn' in locals():
            conn.close()

# Funciones auxiliares (sin cambios)
def calculate_payload_size(data: Any) -> int:
    """Calcular tamaño del payload en bytes"""
    json_str = json.dumps(data.dict() if hasattr(data, 'dict') else data, default=str)
    return len(json_str.encode('utf-8'))

def simulate_compression(data: str, compression_type: str = "gzip") -> tuple:
    """Simular compresión y retornar ratio"""
    original_size = len(data.encode('utf-8'))
    
    if compression_type == "gzip":
        compressed = gzip.compress(data.encode('utf-8'))
        compressed_size = len(compressed)
    else:
        compressed_size = int(original_size * 0.4)
    
    ratio = compressed_size / original_size if original_size > 0 else 1.0
    return compressed_size, ratio

def save_marcacion_to_db(marcacion_data: dict, test_type: str, payload_size: int, 
                        processing_time: float, compression_ratio: float = 1.0):
    """Guardar marcación en MySQL Railway"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO marcaciones_test 
        (user_name, user_email, user_dni, qr_code, marcation_type, 
         latitude, longitude, device_id, test_type, payload_size, 
         processing_time, compression_ratio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            marcacion_data.get('userName', marcacion_data.get('u', '')),
            marcacion_data.get('userEmail', marcacion_data.get('e', '')),
            marcacion_data.get('userDni', marcacion_data.get('d', '')),
            marcacion_data.get('qrCode', marcacion_data.get('q', '')),
            marcacion_data.get('marcationType', marcacion_data.get('t', '')),
            marcacion_data.get('latitude', marcacion_data.get('lat', 0)),
            marcacion_data.get('longitude', marcacion_data.get('lon', 0)),
            marcacion_data.get('deviceId', marcacion_data.get('dev', '')),
            test_type,
            payload_size,
            processing_time,
            compression_ratio
        ))
        
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"✅ Marcación guardada en Railway MySQL, ID: {record_id}")
        return record_id
        
    except Exception as e:
        logger.error(f"❌ Error guardando en base de datos: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Inicializar aplicación en Railway"""
    logger.info("🚀 Iniciando Mina Connectivity Test API en Railway")
    logger.info(f"🌐 Variables de entorno Railway cargadas:")
    logger.info(f"   MYSQL_HOST: {os.getenv('MYSQL_HOST', 'NO CONFIGURADO')}")
    logger.info(f"   MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE', 'NO CONFIGURADO')}")
    logger.info(f"   PORT: {os.getenv('PORT', '8000')}")
    
    try:
        mysql_initialized = init_mysql_pool()
        if mysql_initialized:
            init_database()
            logger.info("✅ API iniciada exitosamente en Railway con MySQL")
        else:
            logger.warning("⚠️ API iniciada sin conexión a MySQL")
    except Exception as e:
        logger.error(f"❌ Error durante startup: {e}")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup al cerrar"""
    logger.info("🛑 Cerrando Mina Connectivity Test API")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🏔️ Mina Connectivity Test API - Railway Cloud",
        "version": "1.0.0",
        "environment": "Railway Production",
        "mysql_status": "connected" if mysql_pool else "not connected",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "health": "/api/health",
            "metrics": "/api/metrics", 
            "test_standard": "/api/test/1-standard",
            "test_compressed": "/api/test/2-compressed",
            "test_idempotent": "/api/test/3-idempotent",
            "results": "/api/test-results"
        }
    }

# Health endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint para Railway"""
    db_status = "not connected"
    mysql_info = "N/A"
    
    try:
        if mysql_pool:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Test básico de conexión
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            # Información de la base de datos
            cursor.execute("SELECT DATABASE() as db_name")
            db_result = cursor.fetchone()
            
            if result and result[0] == 1:
                db_status = "healthy"
                mysql_info = f"Connected to: {db_result[0] if db_result else 'unknown'}"
            
            conn.close()
        else:
            db_status = "pool not initialized"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        mysql_info = str(e)
    
    return {
        "status": "healthy",
        "database": db_status,
        "mysql_info": mysql_info,
        "environment": "Railway",
        "mysql_host": os.getenv('MYSQL_HOST', 'not configured'),
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Metrics endpoint
@app.get("/api/metrics")
async def get_metrics():
    """Obtener métricas de rendimiento"""
    return {
        "avg_response_times": {
            endpoint: sum(times)/len(times) if times else 0
            for endpoint, times in metrics.request_times.items()
        },
        "success_counts": dict(metrics.success_counts),
        "error_counts": dict(metrics.error_counts),
        "processed_tokens_count": len(processed_tokens),
        "total_requests": sum(metrics.success_counts.values()) + sum(metrics.error_counts.values()),
        "environment": "Railway",
        "mysql_pool_status": "active" if mysql_pool else "inactive"
    }

# Test endpoints
@app.post("/api/test/1-standard")
async def test_standard_payload(marcacion: MarcacionStandard):
    """Botón 1: Payload estándar sin optimizaciones"""
    start_time = time.time()
    
    payload_size = calculate_payload_size(marcacion)
    marcacion_dict = marcacion.dict()
    processing_time = time.time() - start_time
    
    record_id = save_marcacion_to_db(
        marcacion_dict, "standard", payload_size, processing_time
    )
    
    return {
        "success": True,
        "test_type": "standard_payload",
        "record_id": record_id,
        "payload_size_bytes": payload_size,
        "processing_time_ms": round(processing_time * 1000, 2),
        "message": "Marcación estándar guardada en Railway MySQL",
        "environment": "Railway",
        "server_time": datetime.now().isoformat()
    }

@app.post("/api/test/2-compressed")
async def test_compressed_payload(marcacion: MarcacionCompacta):
    """Botón 2: Payload comprimido con campos cortos"""
    start_time = time.time()
    
    payload_size = calculate_payload_size(marcacion)
    
    # Simular compresión GZIP
    json_data = json.dumps(marcacion.dict(), default=str)
    compressed_size, compression_ratio = simulate_compression(json_data, "gzip")
    
    marcacion_dict = marcacion.dict()
    processing_time = time.time() - start_time
    
    record_id = save_marcacion_to_db(
        marcacion_dict, "compressed", compressed_size, processing_time, compression_ratio
    )
    
    return {
        "success": True,
        "test_type": "compressed_payload",
        "record_id": record_id,
        "original_size_bytes": payload_size,
        "compressed_size_bytes": compressed_size,
        "compression_ratio": round(compression_ratio, 3),
        "savings_percent": round((1 - compression_ratio) * 100, 1),
        "processing_time_ms": round(processing_time * 1000, 2),
        "message": "Marcación comprimida guardada en Railway MySQL",
        "environment": "Railway",
        "server_time": datetime.now().isoformat()
    }

@app.post("/api/test/3-idempotent")
async def test_idempotent_request(marcacion: MarcacionConToken):
    """Botón 3: Request con token de idempotencia"""
    start_time = time.time()
    
    # Verificar si ya se procesó este token
    if marcacion.token_idempotencia in processed_tokens:
        result = processed_tokens[marcacion.token_idempotencia].copy()
        result["is_duplicate"] = True
        result["processing_time_ms"] = 0
        result["environment"] = "Railway"
        return result
    
    payload_size = calculate_payload_size(marcacion.data)
    marcacion_dict = marcacion.data.dict()
    processing_time = time.time() - start_time
    
    record_id = save_marcacion_to_db(
        marcacion_dict, "idempotent", payload_size, processing_time
    )
    
    result = {
        "success": True,
        "test_type": "idempotent_request",
        "record_id": record_id,
        "token": marcacion.token_idempotencia,
        "payload_size_bytes": payload_size,
        "processing_time_ms": round(processing_time * 1000, 2),
        "message": "Marcación con token guardada en Railway MySQL",
        "is_duplicate": False,
        "environment": "Railway",
        "server_time": datetime.now().isoformat()
    }
    
    # Guardar en cache
    processed_tokens[marcacion.token_idempotencia] = result.copy()
    
    return result

# Endpoint para ver resultados
@app.get("/api/test-results")
async def get_test_results():
    """Obtener resultados de las pruebas desde Railway MySQL"""
    try:
        if not mysql_pool:
            return {
                "success": False,
                "message": "MySQL no disponible en Railway",
                "test_results": [],
                "total_tests": 0
            }
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener estadísticas por tipo de prueba
        query = """
        SELECT 
            test_type,
            COUNT(*) as total_requests,
            AVG(payload_size) as avg_payload_size,
            AVG(processing_time) as avg_processing_time,
            AVG(compression_ratio) as avg_compression_ratio,
            MIN(created_at) as first_test,
            MAX(created_at) as last_test
        FROM marcaciones_test 
        GROUP BY test_type
        ORDER BY last_test DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Convertir datetime a string para JSON
        for result in results:
            if result['first_test']:
                result['first_test'] = result['first_test'].isoformat()
            if result['last_test']:
                result['last_test'] = result['last_test'].isoformat()
        
        return {
            "success": True,
            "test_results": results,
            "total_tests": sum(r['total_requests'] for r in results),
            "environment": "Railway",
            "mysql_host": os.getenv('MYSQL_HOST', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo resultados: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Obtener puerto dinámico de Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    logger.info(f"🚀 Iniciando servidor en puerto {port} (Railway)")
    uvicorn.run(app, host="0.0.0.0", port=port)