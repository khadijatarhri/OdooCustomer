# VRP Delivery Optimization Module for Odoo 18

## 📋 Table des Matières
- [Vue d'ensemble](#vue-densemble)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Architecture Technique](#architecture-technique)
- [Contribution](#contribution)

---

## Vue d'ensemble
Module Odoo 18 pour l'optimisation automatique des tournées de livraison utilisant l'algorithme VRP (Vehicle Routing Problem) avec OR-Tools de Google. Le système assigne intelligemment les commandes aux véhicules disponibles en fonction de la proximité géographique des chauffeurs.
Fonctionnalités principales

- Optimisation automatique des tournées basée sur la position GPS des chauffeurs
- Visualisation cartographique interactive avec Leaflet.js
- Calcul de distances réelles via API OSRM
- Gestion du picking des produits
- Synchronisation automatique entre commandes de vente et VRP
---

## Prérequis
- Odoo 18
- Python 3.10+
- Docker >= 20.10
- Docker Compose >= 1.29 (ou Compose v2 >= 2.12)
- PostgreSQL 15+
---

## Installation
1. Étape 1 : Cloner le dépôt :
```bash
git clone https://github.com/ton-utilisateur/vrp-module.git
cd vrp-module
```


2. Étape 2 : Lancer les conteneurs Docker
```bash
# Construire les images
docker-compose build

# Démarrer les services
docker-compose up -d
```

3. Étape 3 : Accéder à Odoo
- Interface Odoo : http://localhost:8070
- Identifiants par défaut : admin / admin
- Base de données : Créer une nouvelle base (nom libre)

4. Étape 4 :Installer le module
- Activer le mode développeur : Settings > Developer Tools > Activate
- Aller dans Apps
- Retirer le filtre "Apps" dans la recherche
- Chercher "VRP"
- Cliquer sur Install
