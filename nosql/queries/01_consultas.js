// =============================================================================
// SINIA-UY — Consultas representativas MongoDB
// =============================================================================
// Ejecutar desde mongosh:
//   mongosh sinia_uy 01_consultas.js
// o pegar cada bloque en mongosh interactivo.
// =============================================================================

// ── Q1: Últimas 5 ejecuciones ETL exitosas ────────────────────────────────────
db.ejecuciones_etl.find(
    { estado: "ok" },
    { fuente: 1, etapa: 1, iniciado_en: 1, "metricas.registros_insertados": 1 }
).sort({ iniciado_en: -1 }).limit(5);

// ── Q2: Alertas activas ordenadas por severidad ───────────────────────────────
db.alertas.find(
    { activa: true },
    { tipo_alerta: 1, nivel: 1, fecha_generacion: 1, mensaje: 1, puntos_afectados: 1 }
).sort({ fecha_generacion: -1 });

// ── Q3: Snapshot del día más reciente con sus focos ───────────────────────────
db.focos_snapshots.find({}).sort({ fecha: -1 }).limit(1);

// ── Q4: Días con más de 5 focos (agregación) ─────────────────────────────────
db.focos_snapshots.aggregate([
    { $match: { total_focos: { $gt: 5 } } },
    { $project: {
        fecha: 1,
        total_focos: 1,
        "resumen.frp_maximo": 1,
        "riesgo_del_dia.nivel_maximo": 1
    }},
    { $sort: { total_focos: -1 } },
    { $limit: 10 }
]);

// ── Q5: Resumen de ejecuciones ETL por fuente y estado ───────────────────────
db.ejecuciones_etl.aggregate([
    { $group: {
        _id: { fuente: "$fuente", estado: "$estado" },
        cantidad: { $sum: 1 },
        duracion_promedio: { $avg: "$duracion_segundos" },
        total_insertados: { $sum: "$metricas.registros_insertados" }
    }},
    { $sort: { "_id.fuente": 1 } }
]);

// ── Q6: Alertas por nivel en el último mes ────────────────────────────────────
var hace30dias = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
db.alertas.aggregate([
    { $match: { fecha_generacion: { $gte: hace30dias } } },
    { $group: {
        _id: "$nivel",
        cantidad: { $sum: 1 }
    }},
    { $sort: { cantidad: -1 } }
]);

// ── Q7: Snapshots con riesgo muy_alto y focos simultáneos ────────────────────
// Justificación: documentos auto-contenidos permiten esta correlación SIN JOIN
db.focos_snapshots.find(
    {
        total_focos: { $gt: 0 },
        "riesgo_del_dia.nivel_maximo": "muy_alto"
    },
    { fecha: 1, total_focos: 1, "resumen.frp_maximo": 1, "riesgo_del_dia": 1 }
).sort({ fecha: -1 }).limit(5);
