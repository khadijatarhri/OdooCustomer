FROM odoo:18    
    
USER root    
  
# Créer les répertoires nécessaires  
RUN mkdir -p /var/lib/odoo/.local && \    
    chown -R odoo:odoo /var/lib/odoo   
  
# Installer les dépendances système et Python  
RUN apt-get update && \  
    apt-get install -y \  
    python3-pip \  
    python3-dev \  
    build-essential \  
    && pip3 install --break-system-packages --ignore-installed typing_extensions openai requests \  
    && rm -rf /var/lib/apt/lists/*  
      
# Copier les fichiers de configuration et addons    
COPY config/odoo.conf /etc/odoo/    
COPY addons /mnt/extra-addons/    
    
# Ajuster les permissions    
RUN chown -R odoo:odoo /mnt/extra-addons    
    
USER odoo    
EXPOSE 8069