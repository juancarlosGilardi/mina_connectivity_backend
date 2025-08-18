#!/usr/bin/env python3
"""
Script para configurar la base de datos MySQL para el proyecto Mina Connectivity Test
Versión para Windows
"""
import mysql.connector
import sys

# Configuración de conexión
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'infoplus1234',
    'port': 3306,
    'autocommit': True,
    'charset': 'utf8mb4',
    'use_unicode': True
}

def test_mysql_connection():
    """Probar conexión básica a MySQL"""
    print("🔍 Probando conexión a MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ MySQL conectado. Versión: {version[0]}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        print("🔧 Verifica que MySQL esté corriendo y las credenciales sean correctas")
        return False

def create_database():
    """Crear base de datos si no existe"""
    try:
        # Conectar sin especificar base de datos
        config_without_db = {k: v for k, v in DB_CONFIG.items()}
        conn = mysql.connector.connect(**config_without_db)
        cursor = conn.cursor()
        
        # Crear base de datos
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS mina_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Base de datos 'mina_test' creada/verificada")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creando base de datos: {e}")
        return False

def create_tables():
    """Crear tablas necesarias"""
    try:
        # Conectar a la base de datos específica
        config_with_db = DB_CONFIG.copy()
        config_with_db['database'] = 'mina_test'
        
        conn = mysql.connector.connect(**config_with_db)
        cursor = conn.cursor()
        
        # Crear tabla principal
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
            INDEX idx_created_at (created_at),
            INDEX idx_user_email (user_email),
            INDEX idx_device_id (device_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_query)
        print("✅ Tabla 'marcaciones_test' creada/verificada")
        
        # Insertar datos de prueba
        insert_test_data = """
        INSERT IGNORE INTO marcaciones_test 
        (user_name, user_email, user_dni, qr_code, marcation_type, 
         latitude, longitude, device_id, test_type, payload_size, processing_time)
        VALUES 
        ('Test User', 'test@mina.com', '12345678', 'QR_INIT_001', 'Ingreso', 
         -12.0464, -77.0428, 'DEV_INIT', 'init', 250, 0.1),
        ('Demo User', 'demo@mina.com', '87654321', 'QR_DEMO_001', 'Salida', 
         -12.0500, -77.0400, 'DEV_DEMO', 'demo', 300, 0.2)
        """
        
        cursor.execute(insert_test_data)
        print("✅ Datos de prueba insertados")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return False

def test_database():
    """Probar operaciones en la base de datos"""
    try:
        config_with_db = DB_CONFIG.copy()
        config_with_db['database'] = 'mina_test'
        
        conn = mysql.connector.connect(**config_with_db)
        cursor = conn.cursor()
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM marcaciones_test")
        count = cursor.fetchone()[0]
        
        # Verificar estructura
        cursor.execute("DESCRIBE marcaciones_test")
        columns = cursor.fetchall()
        
        print(f"✅ Conexión exitosa. Registros en marcaciones_test: {count}")
        print(f"✅ Tabla tiene {len(columns)} columnas")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error probando base de datos: {e}")
        return False

def main():
    print("🗄️ CONFIGURACIÓN DE BASE DE DATOS - MINA CONNECTIVITY TEST")
    print("=" * 70)
    print(f"Host: localhost")
    print(f"Usuario: root")
    print(f"Base de datos: mina_test")
    print("=" * 70)
    
    print("\n1. Probando conexión a MySQL...")
    if not test_mysql_connection():
        print("\n❌ No se puede conectar a MySQL. Verifica:")
        print("   - MySQL está corriendo (servicios de Windows)")
        print("   - Usuario y password son correctos")
        print("   - Puerto 3306 está disponible")
        sys.exit(1)
    
    print("\n2. Creando base de datos...")
    if not create_database():
        sys.exit(1)
    
    print("\n3. Creando tablas...")
    if not create_tables():
        sys.exit(1)
    
    print("\n4. Probando operaciones...")
    if not test_database():
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🎉 ¡BASE DE DATOS CONFIGURADA EXITOSAMENTE!")
    print("✅ Puedes ejecutar el servidor FastAPI: python main.py")
    print("📖 Documentación: http://localhost:8000/docs")
    print("🔍 Health check: http://localhost:8000/api/health")

if __name__ == "__main__":
    main()
