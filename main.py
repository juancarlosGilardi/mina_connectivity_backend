import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
import asyncio
import time
import json
import gzip
from typing import Optional
import mysql.connector
from mysql.connector import pooling
import uuid
from datetime import datetime
import logging
from collections import defaultdict

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🚂 CONFIGURACIÓN RAILWAY - Lee variables de entorno
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'database': os.getenv('MYSQL_DATABASE'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'autocommit': True,
    'charset': 'utf8mb4',
    'use_unicode': True
}

# Log para debugging
logger.info(f"🔗 MYSQL_HOST: {DB_CONFIG['host']}")
logger.info(f"🔗 MYSQL_DATABASE: {DB_CONFIG['database']}")
logger.info(f"🔗 MYSQL_USER: {DB_CONFIG['user']}")
logger.info(f"🔗 MYSQL_PORT: {DB_CONFIG['port']}")

mysql_pool = None

def init_mysql_pool():
    """Inicializar pool de conexiones MySQL"""
    global mysql_pool
    try:
        # Verificar que las variables estén configuradas
        if not DB_CONFIG['host']:
            logger.error("❌ MYSQL_HOST no configurado")
            return False
        if not DB_CONFIG['user']:
            logger.error("❌ MYSQL_USER no configurado")
            return False
        if not DB_CONFIG['password']:
            logger.error("❌ MYSQL_PASSWORD no configurado")
            return False
            
        logger.info(f"🔄 Intentando conectar a: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        
        mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mina_pool",
            pool_size=3,
            pool_reset_session=True,
            **DB_CONFIG
        )
        logger.info("✅ Pool de conexiones MySQL creado exitosamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error creando pool de conexiones: {e}")
        mysql_pool = None
        return False

app = FastAPI(
    title="Mina Connectivity Test API - Railway",
    description="API para pruebas de conectividad en minas - Desplegada en Railway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=100)

# Métricas
class MetricsCollector:
    def __init__(self):
        self.request_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)

metrics = MetricsCollector()

# Modelos
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

    class Config:
        allow_population_by_field_name = True

class MarcacionConToken(BaseModel):
    token_idempotencia: str
    data: MarcacionStandard

processed_tokens = {}

def get_db_connection():
    """Obtener conexión del pool"""
    if mysql_pool is None:
        raise HTTPException(status_code=500, detail="Database pool not available")
    return mysql_pool.get_connection()

def init_database():
    """Inicializar tabla de pruebas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        cursor.execute(create_table_query)
        conn.commit()
        logger.info("✅ Tabla 'marcaciones_test' creada/verificada")
        
    except Exception as e:
        logger.error(f"❌ Error inicializando database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# Funciones auxiliares
def calculate_payload_size(data):
    json_str = json.dumps(data.dict() if hasattr(data, 'dict') else data, default=str)
    return len(json_str.encode('utf-8'))

def simulate_compression(data, compression_type="gzip"):
    original_size = len(data.encode('utf-8'))
    if compression_type == "gzip":
        compressed = gzip.compress(data.encode('utf-8'))
        compressed_size = len(compressed)
    else:
        compressed_size = int(original_size * 0.4)
    ratio = compressed_size / original_size if original_size > 0 else 1.0
    return compressed_size, ratio

def save_marcacion_to_db(marcacion_data, test_type, payload_size, processing_time, compression_ratio=1.0):
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
            test_type, payload_size, processing_time, compression_ratio
        ))
        
        conn.commit()
        return cursor.lastrowid
        
    except Exception as e:
        logger.error(f"❌ Error guardando en database: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Inicializar aplicación"""
    logger.info("🚀 Iniciando Mina Connectivity Test API en Railway")
    logger.info("🔍 Verificando variables de entorno...")
    logger.info(f"   MYSQL_HOST: {os.getenv('MYSQL_HOST', 'NO CONFIGURADO')}")
    logger.info(f"   MYSQL_USER: {os.getenv('MYSQL_USER', 'NO CONFIGURADO')}")
    logger.info(f"   MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE', 'NO CONFIGURADO')}")
    logger.info(f"   MYSQL_PORT: {os.getenv('MYSQL_PORT', 'NO CONFIGURADO')}")
    
    try:
        mysql_initialized = init_mysql_pool()
        if mysql_initialized:
            init_database()
            logger.info("✅ API iniciada con MySQL exitosamente")
        else:
            logger.warning("⚠️ API iniciada sin MySQL")
    except Exception as e:
        logger.error(f"❌ Error durante startup: {e}")

@app.get("/")
async def root():
    return {
        "message": "🏔️ Mina Connectivity Test API - Railway",
        "version": "1.0.0",
        "environment": "Railway Production",
        "mysql_status": "connected" if mysql_pool else "not connected",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    mysql_info = "N/A"
    db_status = "not connected"
    
    # Verificar variables de entorno
    env_status = {
        "MYSQL_HOST": "✅" if os.getenv('MYSQL_HOST') else "❌",
        "MYSQL_USER": "✅" if os.getenv('MYSQL_USER') else "❌", 
        "MYSQL_PASSWORD": "✅" if os.getenv('MYSQL_PASSWORD') else "❌",
        "MYSQL_DATABASE": "✅" if os.getenv('MYSQL_DATABASE') else "❌",
        "MYSQL_PORT": "✅" if os.getenv('MYSQL_PORT') else "❌"
    }
    
    try:
        if mysql_pool:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            if result and result[0] == 1:
                db_status = "healthy"
                mysql_info = f"Connected to {DB_CONFIG['database']}@{DB_CONFIG['host']}"
            conn.close()
        else:
            db_status = "pool not initialized"
            
    except Exception as e:
        db_status = f"error: {str(e)}"
        mysql_info = str(e)
    
    return {
        "status": "healthy",
        "database": db_status,
        "mysql_info": mysql_info,
        "environment": "Railway",
        "mysql_host": os.getenv('MYSQL_HOST', 'not configured'),
        "env_variables": env_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/metrics")
async def get_metrics():
    return {
        "success_counts": dict(metrics.success_counts),
        "error_counts": dict(metrics.error_counts),
        "total_requests": sum(metrics.success_counts.values()) + sum(metrics.error_counts.values()),
        "environment": "Railway",
        "mysql_pool_status": "active" if mysql_pool else "inactive"
    }

# Test endpoints
@app.post("/api/test/1-standard")
async def test_standard_payload(marcacion: MarcacionStandard):
    start_time = time.time()
    payload_size = calculate_payload_size(marcacion)
    marcacion_dict = marcacion.dict()
    processing_time = time.time() - start_time
    
    record_id = save_marcacion_to_db(marcacion_dict, "standard", payload_size, processing_time)
    
    return {
        "success": True,
        "test_type": "standard_payload",
        "record_id": record_id,
        "payload_size_bytes": payload_size,
        "processing_time_ms": round(processing_time * 1000, 2),
        "message": "Marcación estándar guardada en Railway",
        "environment": "Railway"
    }

@app.post("/api/test/2-compressed")
async def test_compressed_payload(marcacion: MarcacionCompacta):
    start_time = time.time()
    payload_size = calculate_payload_size(marcacion)
    
    json_data = json.dumps(marcacion.dict(), default=str)
    compressed_size, compression_ratio = simulate_compression(json_data, "gzip")
    
    marcacion_dict = marcacion.dict()
    processing_time = time.time() - start_time
    
    record_id = save_marcacion_to_db(marcacion_dict, "compressed", compressed_size, processing_time, compression_ratio)
    
    return {
        "success": True,
        "test_type": "compressed_payload",
        "record_id": record_id,
        "original_size_bytes": payload_size,
        "compressed_size_bytes": compressed_size,
        "compression_ratio": round(compression_ratio, 3),
        "savings_percent": round((1 - compression_ratio) * 100, 1),
        "processing_time_ms": round(processing_time * 1000, 2),
        "message": "Marcación comprimida guardada en Railway"
    }

@app.post("/api/test/3-idempotent")
async def test_idempotent_request(marcacion: MarcacionConToken):
    start_time = time.time()
    
    if marcacion.token_idempotencia in processed_tokens:
        result = processed_tokens[marcacion.token_idempotencia].copy()
        result["is_duplicate"] = True
        result["processing_time_ms"] = 0
        return result
    
    payload_size = calculate_payload_size(marcacion.data)
    marcacion_dict = marcacion.data.dict()
    processing_time = time.time() - start_time
    
    record_id = save_marcacion_to_db(marcacion_dict, "idempotent", payload_size, processing_time)
    
    result = {
        "success": True,
        "test_type": "idempotent_request",
        "record_id": record_id,
        "token": marcacion.token_idempotencia,
        "payload_size_bytes": payload_size,
        "processing_time_ms": round(processing_time * 1000, 2),
        "message": "Marcación con token guardada en Railway",
        "is_duplicate": False
    }
    
    processed_tokens[marcacion.token_idempotencia] = result.copy()
    return result

@app.get("/api/test-results")
async def get_test_results():
    try:
        if not mysql_pool:
            return {"success": False, "message": "Database not available", "test_results": [], "total_tests": 0}
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT test_type, COUNT(*) as total_requests, AVG(payload_size) as avg_payload_size,
               AVG(processing_time) as avg_processing_time, AVG(compression_ratio) as avg_compression_ratio,
               MIN(created_at) as first_test, MAX(created_at) as last_test
        FROM marcaciones_test GROUP BY test_type ORDER BY last_test DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        for result in results:
            if result['first_test']:
                result['first_test'] = result['first_test'].isoformat()
            if result['last_test']:
                result['last_test'] = result['last_test'].isoformat()
        
        return {
            "success": True,
            "test_results": results,
            "total_tests": sum(r['total_requests'] for r in results),
            "environment": "Railway"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching results: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Puerto dinámico para Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)