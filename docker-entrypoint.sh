#!/bin/bash
set -e

echo "=========================================="
echo "🚀 DÉMARRAGE ODOO AVEC KAFKA"
echo "=========================================="

# =============================================================================
# VÉRIFICATIONS PRÉ-DÉMARRAGE
# =============================================================================

echo "📋 Vérification de l'environnement..."

# 1. Vérifier que kafka-python est installé
echo "🔍 Test kafka-python..."
python3 -c "from kafka import KafkaProducer; print('  ✅ kafka-python installé')" || {
    echo "  ❌ ERREUR: kafka-python non disponible"
    echo "  💡 Reconstruisez l'image: docker-compose build --no-cache"
    exit 1
}

# 2. Vérifier les variables d'environnement Kafka
echo "🔍 Variables d'environnement Kafka:"
echo "  KAFKA_BOOTSTRAP_SERVERS: ${KAFKA_BOOTSTRAP_SERVERS:-non défini}"
echo "  KAFKA_ENABLED: ${KAFKA_ENABLED:-non défini}"

# 3. Attendre que PostgreSQL soit prêt
echo "⏳ Attente de PostgreSQL..."
until nc -z ${HOST:-db} 5432; do
    echo "  PostgreSQL pas encore prêt..."
    sleep 2
done
echo "  ✅ PostgreSQL accessible"

# 4. Attendre que Kafka soit prêt (si activé)
if [ "${KAFKA_ENABLED}" = "true" ]; then
    echo "⏳ Attente de Kafka..."
    KAFKA_HOST=$(echo ${KAFKA_BOOTSTRAP_SERVERS} | cut -d: -f1)
    KAFKA_PORT=$(echo ${KAFKA_BOOTSTRAP_SERVERS} | cut -d: -f2)
    
    RETRY=0
    MAX_RETRY=30
    
    until nc -z ${KAFKA_HOST} ${KAFKA_PORT} 2>/dev/null; do
        RETRY=$((RETRY+1))
        if [ $RETRY -ge $MAX_RETRY ]; then
            echo "  ⚠️  ATTENTION: Kafka non accessible après ${MAX_RETRY} tentatives"
            echo "  📌 Odoo démarrera mais Kafka sera désactivé"
            export KAFKA_ENABLED=false
            break
        fi
        echo "  Kafka pas encore prêt... (${RETRY}/${MAX_RETRY})"
        sleep 2
    done
    
    if [ "${KAFKA_ENABLED}" = "true" ]; then
        echo "  ✅ Kafka accessible"
    fi
fi

# =============================================================================
# DÉMARRAGE ODOO
# =============================================================================

echo "=========================================="
echo "🎯 Lancement d'Odoo..."
echo "=========================================="

# Exécuter la commande Odoo avec tous les arguments passés
exec "$@"