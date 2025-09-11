FROM odoo:18      
      
USER root      
    
# Créer les répertoires nécessaires    
RUN mkdir -p /var/lib/odoo/.local && \      
    chown -R odoo:odoo /var/lib/odoo     
  
# Installer les dépendances système  
RUN apt-get update && apt-get install -y \  
    build-essential \  
    libjpeg-dev \  
    zlib1g-dev \  
    libfreetype6-dev \  
    liblcms2-dev \  
    libwebp-dev \  
    python3-tk \  
    && rm -rf /var/lib/apt/lists/*  
  
# Installer les dépendances Python  
RUN pip3 install --break-system-packages protobuf    
RUN pip3 install --break-system-packages --no-deps ortools  
RUN pip3 install --break-system-packages matplotlib numpy  
RUN mkdir -p /var/lib/odoo/.local /var/lib/odoo/.cache && \  
    chown -R odoo:odoo /var/lib/odoo && \  
    chmod -R 755 /var/lib/odoo


RUN mkdir -p /var/lib/odoo/.local/share/Odoo && \  
    chown -R odoo:odoo /var/lib/odoo/.local && \  
    chmod -R 755 /var/lib/odoo/.local
  
# Copier les fichiers de configuration et addons      
COPY config/odoo.conf /etc/odoo/      
      
# Ajuster les permissions      
RUN chown -R odoo:odoo /mnt/extra-addons      
      
USER odoo      
EXPOSE 8069