from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
import logging

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MongoDB URL Service",
    description="Servicio REST para consultar la colección 'url' de MongoDB Atlas",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo Pydantic para la respuesta
class UrlResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str

# Modelo Pydantic para actualizar URI
class UrlUpdate(BaseModel):
    uri: str

# Configuración de MongoDB Atlas
MONGODB_CONNECTION_STRING = os.getenv(
    "MONGODB_CONNECTION_STRING", 
    "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/"
)
DATABASE_NAME = "ngrok"
COLLECTION_NAME = "url"

# Cliente MongoDB
mongo_client = None
database = None
collection = None

def connect_to_mongodb():
    """Conectar a MongoDB Atlas"""
    global mongo_client, database, collection
    try:
        mongo_client = MongoClient(MONGODB_CONNECTION_STRING)
        database = mongo_client[DATABASE_NAME]
        collection = database[COLLECTION_NAME]
        
        # Verificar la conexión
        mongo_client.admin.command('ping')
        logger.info("✅ Conexión exitosa a MongoDB Atlas")
        return True
    except Exception as e:
        logger.error(f"❌ Error conectando a MongoDB: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    logger.info("🚀 Iniciando servicio MongoDB...")
    if not connect_to_mongodb():
        logger.error("No se pudo conectar a MongoDB Atlas")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación"""
    if mongo_client:
        mongo_client.close()
        logger.info("🔌 Conexión a MongoDB cerrada")

@app.get("/", response_model=UrlResponse)
async def root():
    """Endpoint raíz con información del servicio"""
    return UrlResponse(
        success=True,
        data={
            "service": "MongoDB URL Service",
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME,
            "endpoints": {
                "get_url": "/api/url",
                "update_url": "PUT /api/url",
                "health": "/api/health"
            }
        },
        message="Servicio funcionando correctamente"
    )

@app.get("/api/health", response_model=UrlResponse)
async def health_check():
    """Verificar el estado de la conexión a MongoDB"""
    try:
        if mongo_client is None:
            raise HTTPException(status_code=503, detail="MongoDB no conectado")
        
        # Ping a la base de datos
        mongo_client.admin.command('ping')
        
        return UrlResponse(
            success=True,
            data={"status": "healthy", "database": DATABASE_NAME},
            message="Conexión a MongoDB OK"
        )
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        raise HTTPException(status_code=503, detail=f"Error de conexión: {str(e)}")

@app.get("/api/url", response_model=UrlResponse)
async def get_url_record():
    """Obtener solo el valor de 'uri' de la colección 'url'"""
    try:
        if collection is None:
            raise HTTPException(status_code=503, detail="MongoDB no conectado")
        
        # Buscar el único registro en la colección
        record = collection.find_one()
        
        if record is None:
            logger.warning("⚠️ No se encontró ningún registro en la colección 'url'")
            return UrlResponse(
                success=False,
                data=None,
                message="No se encontró ningún registro en la colección"
            )
        
        # Extraer específicamente el valor de URI
        uri_value = record.get('uri', 'No encontrado')
        
        # Mostrar en consola el valor completo del registro
        logger.info("📄 Registro encontrado:")
        logger.info(f"   {record}")
        
        print("\n" + "="*60)
        print("🔍 REGISTRO COMPLETO DE LA COLECCIÓN 'URL':")
        print("="*60)
        for key, value in record.items():
            print(f"   {key}: {value}")
        print("="*60)
        print(f"🌐 VALOR DE URI: {uri_value}")
        print("="*60 + "\n")
        
        # También loggearlo de forma destacada
        logger.info(f"🌐 URI extraída: {uri_value}")
        
        # Devolver solo el valor de URI
        return UrlResponse(
            success=True,
            data={"uri": uri_value},
            message="Valor de URI obtenido exitosamente"
        )
        
    except Exception as e:
        logger.error(f"❌ Error consultando la colección: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.put("/api/url", response_model=UrlResponse)
async def update_url_record(url_data: UrlUpdate):
    """Actualizar el valor de 'uri' en la colección 'url'"""
    try:
        if collection is None:
            raise HTTPException(status_code=503, detail="MongoDB no conectado")
        
        # Buscar el registro existente
        existing_record = collection.find_one()
        
        if existing_record is None:
            logger.warning("⚠️ No se encontró ningún registro para actualizar")
            return UrlResponse(
                success=False,
                data=None,
                message="No se encontró ningún registro para actualizar"
            )
        
        # Actualizar el campo URI
        result = collection.update_one(
            {"_id": existing_record["_id"]},
            {"$set": {"uri": url_data.uri}}
        )
        
        if result.modified_count > 0:
            # Obtener el registro actualizado
            updated_record = collection.find_one({"_id": existing_record["_id"]})
            
            # Mostrar en consola la actualización
            logger.info("📝 Registro actualizado:")
            logger.info(f"   Valor anterior: {existing_record.get('uri', 'N/A')}")
            logger.info(f"   Valor nuevo: {url_data.uri}")
            
            print("\n" + "="*60)
            print("📝 ACTUALIZACIÓN DE URI EN LA COLECCIÓN:")
            print("="*60)
            print(f"   🔄 Valor anterior: {existing_record.get('uri', 'N/A')}")
            print(f"   ✅ Valor nuevo: {url_data.uri}")
            print(f"   🕒 Registro ID: {existing_record['_id']}")
            print("="*60 + "\n")
            
            # También loggearlo de forma destacada
            logger.info(f"✅ URI actualizada exitosamente: {url_data.uri}")
            
            return UrlResponse(
                success=True,
                data={
                    "uri": url_data.uri,
                    "previous_uri": existing_record.get('uri', 'N/A'),
                    "_id": str(existing_record["_id"])
                },
                message="URI actualizada exitosamente"
            )
        else:
            logger.warning("⚠️ No se pudo actualizar el registro")
            return UrlResponse(
                success=False,
                data=None,
                message="No se pudo actualizar el registro"
            )
        
    except Exception as e:
        logger.error(f"❌ Error actualizando la colección: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/url/count")
async def get_url_count():
    """Obtener el número de registros en la colección"""
    try:
        if collection is None:
            raise HTTPException(status_code=503, detail="MongoDB no conectado")
        
        count = collection.count_documents({})
        
        return UrlResponse(
            success=True,
            data={"count": count},
            message=f"La colección tiene {count} registro(s)"
        )
        
    except Exception as e:
        logger.error(f"Error contando registros: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    print("\n🚀 Iniciando servidor MongoDB Service...")
    print("📍 Endpoints disponibles:")
    print("   GET  /                  - Información del servicio")
    print("   GET  /api/health        - Estado de la conexión")
    print("   GET  /api/url           - Obtener valor de URI")
    print("   PUT  /api/url           - Actualizar valor de URI")
    print("   GET  /api/url/count     - Contar registros")
    print("\n💡 Para detener el servidor: Ctrl+C")
    print("="*60)
    
    uvicorn.run(
        "mongo_service:app", 
        host="0.0.0.0", 
        port=5100, 
        reload=True,
        log_level="info"
    )
