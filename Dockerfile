FROM odoo:18

USER root

# =============================================================================
# INSTALLATION DES DÉPENDANCES SYSTÈME
# =============================================================================
RUN apt-get update && apt-get install -y \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    python3-tk \
    netcat-openbsd \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# INSTALLATION DES PACKAGES PYTHON
# =============================================================================
RUN pip3 install --upgrade --ignore-installed pip setuptools wheel --break-system-packages

RUN pip3 install --no-cache-dir --break-system-packages protobuf==3.20.3

RUN pip3 install --no-cache-dir --break-system-packages --no-deps ortools

RUN pip3 install --no-cache-dir --break-system-packages numpy matplotlib

RUN pip3 install --no-cache-dir --break-system-packages kafka-python>=2.1.0

RUN python3 -c "from kafka import KafkaProducer; print('✅ Kafka-python OK')"

# =============================================================================
# CONFIGURATION DES RÉPERTOIRES ODOO - ORDRE IMPORTANT !
# =============================================================================
# 1. Créer TOUS les répertoires nécessaires en tant que root
RUN mkdir -p /var/lib/odoo/.local/share/Odoo/sessions && \
    mkdir -p /var/lib/odoo/.local/share/Odoo/filestore && \
    mkdir -p /var/log/odoo && \
    mkdir -p /mnt/extra-addons

# 2. Changer le propriétaire de TOUS les répertoires
RUN chown -R odoo:odoo /var/lib/odoo && \
    chown -R odoo:odoo /var/log/odoo && \
    chown -R odoo:odoo /mnt/extra-addons

# 3. Définir les permissions appropriées
RUN chmod -R 755 /var/lib/odoo && \
    chmod -R 755 /var/log/odoo && \
    chmod -R 755 /mnt/extra-addons

# Copier la configuration Odoo
COPY config/odoo.conf /etc/odoo/
RUN chown odoo:odoo /etc/odoo/odoo.conf

# =============================================================================
# SCRIPT DE DÉMARRAGE
# =============================================================================
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    chown odoo:odoo /usr/local/bin/docker-entrypoint.sh

# ⚠️ IMPORTANT: Passer à l'utilisateur odoo APRÈS avoir créé les répertoires
USER odoo

EXPOSE 8069

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["odoo"]