FROM odoo:18

USER root

# Supprimer les dépôts PostgreSQL externes s’ils existent
RUN rm -f /etc/apt/sources.list.d/pgdg.list

# Forcer libpq5 compatible avec libpq-dev (v16)
RUN apt-get update && \
    apt-get install -y \
    libpq5=16.9-0ubuntu0.24.04.1 \
    libpq-dev=16.9-0ubuntu0.24.04.1 \
    python3-pip \
    python3-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libevent-dev \
    libsasl2-dev \
    libldap2-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY config/odoo.conf /etc/odoo/
COPY addons /mnt/extra-addons/
RUN chown -R odoo:odoo /mnt/extra-addons

USER odoo
EXPOSE 8069
CMD ["odoo"]
