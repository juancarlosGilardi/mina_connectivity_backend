# 🏔️ Mina Connectivity Test - Backend FastAPI (Windows)

API backend para probar optimizaciones de conectividad en minas de altura.
Configurado específicamente para **Windows con MySQL local**.

## 🚀 Inicio Rápido

### 1️⃣ Instalar Dependencias
```bash
# Ejecutar como administrador o usuario normal
install_dependencies.bat
```

### 2️⃣ Configurar Base de Datos
```bash
# Asegúrate de que MySQL esté corriendo
setup_database.bat
```

### 3️⃣ Ejecutar API
```bash
# Iniciar servidor FastAPI
run_api.bat
```

### 4️⃣ Probar API
```bash
# En otra ventana, ejecutar tests
run_tests.bat
```

## 🌐 URLs Importantes

- **API Principal**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Métricas**: http://localhost:8000/api/metrics

## 🔘 Endpoints de Prueba

| Endpoint | Descripción | Optimización |
|----------|-------------|-------------|
| `POST /api/test/1-standard` | Payload estándar | Baseline |
| `POST /api/test/2-compressed` | Payload comprimido | GZIP + campos cortos |
| `POST /api/test/3-idempotent` | Con token idempotencia | Evita duplicados |

## 🛠️ Configuración MySQL

**Base de datos configurada:**
- Host: `localhost`
- Usuario: `root`
- Base de datos: `mina_test`
- Puerto: `3306`

## 🧪 Ejemplos de Uso

### Test Payload Estándar
```bash
curl -X POST "http://localhost:8000/api/test/1-standard" ^
  -H "Content-Type: application/json" ^
  -d "{"userName": "Test User", "userEmail": "test@test.com", "userDni": "12345678", "qrCode": "QR_001", "marcationType": "Ingreso", "latitude": -12.0464, "longitude": -77.0428, "deviceId": "test_device"}"
```

### Test Payload Comprimido
```bash
curl -X POST "http://localhost:8000/api/test/2-compressed" ^
  -H "Content-Type: application/json" ^
  -d "{"u": "Test User", "e": "test@test.com", "d": "12345678", "q": "QR_002", "t": "Ingreso", "lat": -12.0464, "lon": -77.0428, "dev": "test_device"}"
```

## 🔧 Comandos Útiles

### Desarrollo
```bash
# Activar entorno virtual manualmente
venv\Scripts\activate.bat

# Ejecutar con hot reload
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Ver logs en tiempo real
python main.py
```

### Base de Datos
```bash
# Conectar a MySQL desde cmd
mysql -u root -pinfoplus1234 -h localhost

# Ver datos de prueba
mysql -u root -pinfoplus1234 -e "USE mina_test; SELECT * FROM marcaciones_test LIMIT 10;"
```

## 🚨 Troubleshooting Windows

### Error: "MySQL connection failed"
```bash
# 1. Verificar que MySQL esté corriendo
net start mysql80
# o
services.msc  # Buscar MySQL80 y iniciar

# 2. Verificar puerto 3306
netstat -an | findstr :3306

# 3. Probar conexión manual
mysql -u root -pinfoplus1234
```

### Error: "Puerto 8000 en uso"
```bash
# Ver qué proceso usa el puerto
netstat -ano | findstr :8000

# Matar proceso (reemplaza PID)
taskkill /PID <PID> /F

# O usar puerto diferente
python main.py --port 8001
```

### Error: "Python no encontrado"
```bash
# Verificar instalación Python
python --version
python3 --version

# Agregar Python al PATH si es necesario
# Variables de entorno > PATH > Agregar ruta de Python
```

### Error: "pip no encontrado"
```bash
# Reinstalar pip
python -m ensurepip --upgrade

# O descargar get-pip.py
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

## 📊 Estructura del Proyecto

```
mina_connectivity_backend/
├── main.py                     # ✅ Aplicación FastAPI principal
├── requirements.txt            # ✅ Dependencias Python
├── install_dependencies.bat    # ✅ Instalar dependencias
├── setup_database.bat         # ✅ Configurar BD MySQL
├── run_api.bat                # ✅ Ejecutar API
├── run_tests.bat              # ✅ Ejecutar tests
├── scripts/
│   ├── setup_database.py      # ✅ Script configuración BD
│   └── test_api.py            # ✅ Script de pruebas
└── README.md                  # ✅ Este archivo
```

## 🎯 Próximos Pasos

1. **Ejecutar**: `install_dependencies.bat`
2. **Configurar BD**: `setup_database.bat`
3. **Iniciar API**: `run_api.bat`
4. **Probar**: `run_tests.bat`
5. **Abrir docs**: http://localhost:8000/docs

## 🔒 Notas de Seguridad

⚠️ **IMPORTANTE**: Esta configuración es para desarrollo local.

Para producción:
- Cambiar password de MySQL
- Usar HTTPS
- Configurar firewall
- Variables de entorno para credenciales

## 📞 Soporte

Para problemas:
1. Verificar que MySQL esté corriendo
2. Ejecutar `setup_database.bat`
3. Revisar logs en la ventana de `run_api.bat`
4. Probar health check: http://localhost:8000/api/health

---

**Generado automáticamente para Windows con MySQL local**
