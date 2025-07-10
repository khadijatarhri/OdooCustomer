FROM odoo:18    
    
USER root    
  
# Créer les répertoires nécessaires  
RUN mkdir -p /var/lib/odoo/.local && \    
    chown -R odoo:odoo /var/lib/odoo   


# Installer Java et les dépendances  
RUN apt-get update && apt-get install -y \  
    openjdk-11-jdk \  
    python3-pip \  
    build-essential \  
    unzip \
    && rm -rf /var/lib/apt/lists/*  
  
# Installer JPype pour l'intégration Java-Python  
RUN pip3 install --break-system-packages jpype1 matplotlib numpy  
  
# Télécharger OptaPlanner JAR  
RUN curl -L -o optaplanner.zip https://download.jboss.org/optaplanner/release/8.44.0.Final/optaplanner-distribution-8.44.0.Final.zip \  
    && unzip optaplanner.zip \  
    && mv optaplanner-distribution-8.44.0.Final /opt/optaplanner \  
    && rm optaplanner.zip

# Copier les fichiers de configuration et addons    
COPY config/odoo.conf /etc/odoo/    
COPY addons /mnt/extra-addons/    
    
# Ajuster les permissions    
RUN chown -R odoo:odoo /mnt/extra-addons    
    
USER odoo    
EXPOSE 8069