// =============================================================================
// SINIA-UY — Inicialización MongoDB
// =============================================================================
// Este script crea el usuario de la aplicación y la base de datos.
// Se ejecuta automáticamente en el primer arranque del contenedor MongoDB.
// =============================================================================

db = db.getSiblingDB("sinia_uy");

// Crear usuario con permisos de lectura+escritura sobre sinia_uy
db.createUser({
    user: "sinia_etl_user",
    pwd:  "sinia_etl_2026",
    roles: [
        { role: "readWrite", db: "sinia_uy" }
    ]
});

// Crear usuario de solo lectura para el dashboard
db.createUser({
    user: "sinia_dash_user",
    pwd:  "sinia_dash_2026",
    roles: [
        { role: "read", db: "sinia_uy" }
    ]
});

// Crear las colecciones con las validaciones básicas
// (el setup completo con JSON Schema lo hace load_mongo.py)
db.createCollection("ejecuciones_etl");
db.createCollection("alertas");
db.createCollection("focos_snapshots");

print("MongoDB sinia_uy inicializado correctamente.");
