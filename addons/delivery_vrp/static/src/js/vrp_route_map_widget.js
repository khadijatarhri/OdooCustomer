/** @odoo-module **/
// static/src/js/vrp_route_map_widget_popup_fix.js

import { registry } from '@web/core/registry';
import { Component, useState, useRef, onMounted, onWillUnmount } from '@odoo/owl';
import { standardFieldProps } from '@web/views/fields/standard_field_props';
import { loadJS, loadCSS } from "@web/core/assets";

export class VRPRouteMapWidgetPopupFix extends Component {
    static template = 'delivery_vrp.VRPRouteMapTemplate';
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.mapRef = useRef("map");
        this.state = useState({
            isLoaded: false,
            map: null,
            markers: [],
            routes: []
        });

        onMounted(() => {
            console.log("=== VRP WIDGET - POPUP FIX ===");
            this.loadMapLibraries().then(() => {
                // Attendre que le DOM soit complètement stable
                setTimeout(() => {
                    this.initMapWithPopupFix();
                }, 200);
            }).catch(error => {
                console.error('Failed to load map libraries:', error);
                this.state.isLoaded = true;
            });
        });

        onWillUnmount(() => {
            // CRUCIAL: Nettoyer proprement la carte pour éviter les erreurs de popup
            this.cleanupMap();
        });
    }

    cleanupMap() {
        console.log("Nettoyage de la carte...");
        try {
            if (this.state.map) {
                // Fermer tous les popups avant destruction
                this.state.map.closePopup();

                // Supprimer tous les marqueurs
                this.state.markers.forEach(marker => {
                    if (marker && this.state.map.hasLayer(marker)) {
                        this.state.map.removeLayer(marker);
                    }
                });

                // Supprimer toutes les routes
                this.state.routes.forEach(route => {
                    if (route && this.state.map.hasLayer(route)) {
                        this.state.map.removeLayer(route);
                    }
                });

                // Détruire la carte
                this.state.map.remove();
                this.state.map = null;
            }

            this.state.markers = [];
            this.state.routes = [];
            console.log("✅ Carte nettoyée avec succès");
        } catch (error) {
            console.error("Erreur lors du nettoyage:", error);
        }
    }

    async loadMapLibraries() {
        if (window.L) return;

        try {
            await loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
            await loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
            await loadCSS("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css");
            await loadJS("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js");
        } catch (error) {
            console.error("Library loading failed:", error);
            throw error;
        }
    }

    initMapWithPopupFix() {
        console.log("=== INITIALISATION CARTE AVEC CORRECTION POPUP ===");

        try {
            const mapContainer = this.mapRef.el;
            if (!mapContainer) {
                console.error('Conteneur carte non trouvé');
                this.state.isLoaded = true;
                return;
            }

            if (!window.L) {
                console.error("Leaflet non disponible");
                this.state.isLoaded = true;
                return;
            }

            // CORRECTION CRITIQUE: Vider et reconfigurer le conteneur
            mapContainer.innerHTML = '';
            mapContainer.style.height = '500px';
            mapContainer.style.width = '100%';
            mapContainer.style.position = 'relative';
            mapContainer.style.minHeight = '500px';

            // Attendre que le style soit appliqué
            setTimeout(() => {
                this.createMapSafely(mapContainer);
            }, 50);

        } catch (error) {
            console.error('Erreur initialisation carte:', error);
            this.state.isLoaded = true;
        }
    }

    createMapSafely(mapContainer) {
        try {
            console.log("Création sécurisée de la carte...");

            // Vérifier que le conteneur a les bonnes dimensions
            const rect = mapContainer.getBoundingClientRect();
            console.log(`Dimensions conteneur: ${rect.width}x${rect.height}`);

            if (rect.width === 0 || rect.height === 0) {
                console.error("Conteneur a des dimensions nulles");
                this.state.isLoaded = true;
                return;
            }

            // Créer la carte avec des options de sécurité
            this.state.map = L.map(mapContainer, {
                center: [34.0209, -6.8416],
                zoom: 10,
                zoomControl: true,
                attributionControl: true,
                preferCanvas: false, // Éviter les problèmes de canvas
                maxBounds: [[-90, -180], [90, 180]], // Limites mondiales
                maxBoundsViscosity: 1.0
            });

            console.log("Carte créée, ajout des tuiles...");

            // Ajouter les tuiles avec gestion d'erreur
            const tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: "&copy; OpenStreetMap contributors",
                maxZoom: 18,
                minZoom: 1
            });

            tileLayer.on('tileerror', (e) => {
                console.warn('Erreur de chargement tuile:', e);
            });

            tileLayer.addTo(this.state.map);

            // Attendre que la carte soit prête avant d'ajouter du contenu
            this.state.map.whenReady(() => {
                console.log("Carte prête, traitement des données...");
                this.processVehicleDataSafely();
            });

        } catch (error) {
            console.error('Erreur création carte:', error);
            this.state.isLoaded = true;
        }
    }

    processVehicleDataSafely() {
        try {
            // Obtenir les données
            const rawData = this.props.record?.data?.[this.props.name] || '[]';
            let vehiclesData;

            try {
                vehiclesData = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
                if (!Array.isArray(vehiclesData)) {
                    vehiclesData = [];
                }
            } catch (error) {
                console.error('Données JSON invalides:', error);
                vehiclesData = [];
            }

            console.log(`Données reçues: ${vehiclesData.length} véhicules`);

            // Toujours ajouter le dépôt
            this.addDepotMarkerSafe();

            if (!vehiclesData || vehiclesData.length === 0) {
                console.log("Aucune donnée véhicule - affichage dépôt seulement");
                this.state.isLoaded = true;
                return;
            }

            // Traiter les véhicules de manière sécurisée
            this.processVehiclesSafely(vehiclesData);
            this.state.isLoaded = true;

        } catch (error) {
            console.error('Erreur traitement données:', error);
            this.state.isLoaded = true;
        }
    }

    addDepotMarkerSafe() {
        // OBSOLÈTE: Cette méthode n'est plus utilisée avec dépôts chauffeurs
        // Gardée pour compatibilité mais ne fait plus rien
        console.log("addDepotMarkerSafe: Méthode obsolète avec dépôts chauffeurs");
    }


    processVehiclesSafely(vehiclesData) {
        /**
         * MODIFIÉ: Traitement véhicules avec dépôts chauffeurs
         */
        if (!this.state.map) return;
    
        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e'];
        let allValidPoints = [];
    
        console.log("=== TRAITEMENT VÉHICULES AVEC DÉPÔTS CHAUFFEURS ===");
    
        vehiclesData.forEach((vehicleData, vehicleIndex) => {
            console.log(`🚛 Traitement véhicule: ${vehicleData.vehicle_name}`);
            console.log(`Type de dépôt: ${vehicleData.depot_type || 'legacy'}`);
    
            if (!vehicleData.waypoints || !Array.isArray(vehicleData.waypoints)) {
                console.warn("❌ Pas de waypoints valides");
                return;
            }
    
            const vehicleColor = colors[vehicleIndex % colors.length];
            console.log(`Couleur assignée: ${vehicleColor}`);
    
            // Séparer les différents types de waypoints
            const driverDepots = vehicleData.waypoints.filter(wp => 
                wp.type === 'driver_depot' || wp.type === 'driver_depot_return'
            );
            const clientWaypoints = vehicleData.waypoints.filter(wp => wp.type === 'customer');
    
            console.log(`Dépôts chauffeur: ${driverDepots.length}, Clients: ${clientWaypoints.length}`);
    
            // Ajouter marqueur dépôt chauffeur (une seule fois)
            if (vehicleData.driver_coords && driverDepots.length > 0) {
                this.addDriverDepotMarker(vehicleData.driver_coords, vehicleColor);
            }
    
            // Trier et ajouter les clients
            clientWaypoints.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
    
            clientWaypoints.forEach((client, index) => {
                console.log(`Ajout client: ${client.name} à ${client.lat}, ${client.lng}`);
                this.addClientMarkerCorrected(client, vehicleColor, vehicleData.vehicle_name, index + 1);
                allValidPoints.push(client);
            });
    
            // Créer la route avec le nouveau système
            if (clientWaypoints.length > 0 && vehicleData.driver_coords) {
                console.log("Création route avec dépôt chauffeur");
                this.createDriverBasedRoute(clientWaypoints, vehicleData, vehicleColor);
            }
        });
    
        // Ajuster la vue pour tous les points
        if (allValidPoints.length > 0) {
            console.log(`Ajustement vue pour ${allValidPoints.length} points`);
            this.fitMapSafely(allValidPoints);
        }
    }



    addDriverDepotMarker(driverData, color) {
        /**
         * NOUVEAU: Ajouter un marqueur pour la position d'un chauffeur (nouveau dépôt)
         */
        if (!this.state.map || !driverData) return;
    
        try {
            const lat = parseFloat(driverData.lat);
            const lng = parseFloat(driverData.lng);
            const driverName = driverData.name || 'Chauffeur';
    
            if (isNaN(lat) || isNaN(lng)) {
                console.error('Coordonnées chauffeur invalides:', driverData);
                return;
            }
    
            console.log(`Ajout marqueur chauffeur: ${driverName} à [${lat}, ${lng}]`);
    
            const driverMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    className: 'driver-depot-marker',
                    html: `<div style="
                        background: linear-gradient(45deg, ${color}, ${this.darkenColor(color, 0.2)});
                        color: white;
                        border-radius: 50%;
                        width: 35px;
                        height: 35px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 18px;
                        border: 4px solid white;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        position: relative;
                    ">🚗</div>
                    <div style="
                        position: absolute;
                        top: -8px;
                        right: -8px;
                        background: #28a745;
                        color: white;
                        border-radius: 50%;
                        width: 16px;
                        height: 16px;
                        font-size: 10px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border: 2px solid white;
                    ">D</div>`,
                    iconSize: [35, 35],
                    iconAnchor: [17, 17]
                })
            });
    
            // Popup détaillé pour le chauffeur
            const popupContent = `
                <div style="min-width: 250px; font-family: system-ui;">
                    <div style="text-align: center; margin-bottom: 12px;">
                        <div style="font-weight: bold; color: ${color}; font-size: 18px; margin-bottom: 4px;">
                            🚗 DÉPÔT CHAUFFEUR
                        </div>
                        <div style="font-size: 16px; color: #333; font-weight: 500;">
                            ${driverName}
                        </div>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <strong>📍 Position:</strong>
                            <span>Point de départ/retour</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <strong>🌍 Coordonnées:</strong>
                            <span>${lat.toFixed(4)}, ${lng.toFixed(4)}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <strong>🎯 Type:</strong>
                            <span>Dépôt mobile</span>
                        </div>
                    </div>
                    
                    <div style="text-align: center; font-size: 12px; color: #666; font-style: italic;">
                        Le chauffeur démarre et termine sa tournée à cette position
                    </div>
                </div>
            `;
    
            driverMarker.bindPopup(popupContent, {
                closeOnClick: true,
                autoClose: true,
                maxWidth: 300,
                className: 'driver-depot-popup'
            });
    
            driverMarker.addTo(this.state.map);
            this.state.markers.push(driverMarker);
    
            console.log(`✅ Marqueur chauffeur ajouté: ${driverName}`);
            return driverMarker;
    
        } catch (error) {
            console.error(`❌ Erreur création marqueur chauffeur:`, error);
        }
    }
    
    darkenColor(color, factor) {
        /**
         * Utilitaire pour assombrir une couleur
         */
        const hex = color.replace('#', '');
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        
        const newR = Math.max(0, Math.floor(r * (1 - factor)));
        const newG = Math.max(0, Math.floor(g * (1 - factor)));
        const newB = Math.max(0, Math.floor(b * (1 - factor)));
        
        return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
    }

    
    
    createDriverBasedRoute(clientWaypoints, vehicleData, color) {
        /**
         * NOUVEAU: Créer une route basée sur la position du chauffeur
         */
        if (!this.state.map || clientWaypoints.length === 0 || !vehicleData.driver_coords) {
            console.warn("❌ Données insuffisantes pour créer route chauffeur");
            return;
        }
    
        try {
            console.log(`🛣️ Création route pour ${vehicleData.vehicle_name} depuis position chauffeur`);
    
            const driverCoords = vehicleData.driver_coords;
            
            // Points de route: Position chauffeur -> Clients -> Position chauffeur
            const routeWaypoints = [
                L.latLng(driverCoords.lat, driverCoords.lng), // Départ chauffeur
                ...clientWaypoints.map(wp => {
                    console.log(`Ajout client route: ${wp.name} [${wp.lat}, ${wp.lng}]`);
                    return L.latLng(wp.lat, wp.lng);
                }),
                L.latLng(driverCoords.lat, driverCoords.lng)  // Retour chauffeur
            ];
    
            console.log(`Route avec ${routeWaypoints.length} points (départ/retour: position chauffeur)`);
    
            // Utiliser Leaflet Routing Machine si disponible
            if (typeof L.Routing !== 'undefined' && L.Routing.control) {
                console.log("🔄 Utilisation Leaflet Routing Machine");
    
                const routingControl = L.Routing.control({
                    waypoints: routeWaypoints,
                    routeWhileDragging: false,
                    addWaypoints: false,
                    createMarker: () => null, // Pas de marqueurs auto
                    lineOptions: {
                        styles: [{
                            color: color,
                            weight: 5,
                            opacity: 0.8,
                            dashArray: '5, 5' // Style pointillé pour distinguer des routes dépôt fixe
                        }]
                    },
                    router: L.Routing.osrmv1({
                        serviceUrl: 'https://router.project-osrm.org/route/v1',
                        profile: 'driving'
                    }),
                    show: false,
                    collapsible: false
                });
    
                routingControl.on('routesfound', (e) => {
                    const routes = e.routes;
                    const summary = routes[0].summary;
                    const distance = (summary.totalDistance / 1000).toFixed(2);
                    const duration = Math.round(summary.totalTime / 60);
                    console.log(`✅ Route chauffeur trouvée: ${distance} km, ${duration} min`);
                });
    
                routingControl.on('routingerror', (e) => {
                    console.error('❌ Erreur routing chauffeur:', e.error);
                    this.createDriverFallbackRoute(routeWaypoints, color, vehicleData);
                });
    
                routingControl.addTo(this.state.map);
                this.state.routes.push(routingControl);
    
            } else {
                console.log("⚠️ Leaflet Routing Machine non disponible, route fallback");
                this.createDriverFallbackRoute(routeWaypoints, color, vehicleData);
            }
    
        } catch (error) {
            console.error(`❌ Erreur création route chauffeur pour ${vehicleData.vehicle_name}:`, error);
            this.createDriverFallbackRoute(routeWaypoints, color, vehicleData);
        }
    }
    
    createDriverFallbackRoute(waypoints, color, vehicleData) {
        /**
         * NOUVEAU: Route fallback pour dépôt chauffeur
         */
        console.log("🔄 Création route fallback avec dépôt chauffeur");
    
        try {
            const polyline = L.polyline(waypoints, {
                color: color,
                weight: 4,
                opacity: 0.7,
                dashArray: '8, 12', // Style pointillé
                smoothFactor: 1
            });
    
            polyline.bindPopup(`
                <div style="text-align: center; min-width: 200px;">
                    <div style="font-weight: bold; color: ${color}; margin-bottom: 8px;">
                        ${vehicleData.vehicle_name}
                    </div>
                    <div style="font-size: 13px; margin-bottom: 6px;">
                        <strong>Chauffeur:</strong> ${vehicleData.driver_name}
                    </div>
                    <div style="font-size: 13px; margin-bottom: 6px;">
                        <strong>Type:</strong> Dépôt mobile (position chauffeur)
                    </div>
                    <div style="font-size: 13px; color: #666;">
                        Route approximative - ${waypoints.length - 2} arrêts clients
                    </div>
                </div>
            `);
    
            polyline.addTo(this.state.map);
            this.state.routes.push(polyline);
    
            console.log("✅ Route fallback chauffeur créée");
        } catch (error) {
            console.error("❌ Erreur création route fallback chauffeur:", error);
        }
    }
    
    

    addClientMarkerCorrected(client, color, vehicleName, sequenceDisplay) {
        if (!this.state.map) {
            console.error("❌ Pas de carte pour ajouter marqueur");
            return;
        }

        try {
            console.log(`Création marqueur pour ${client.name} à [${client.lat}, ${client.lng}]`);

            // Vérifier que les coordonnées sont valides
            if (!client.lat || !client.lng || typeof client.lat !== 'number' || typeof client.lng !== 'number') {
                console.error(`❌ Coordonnées invalides pour ${client.name}:`, client.lat, client.lng);
                return;
            }

            if (client.lat < -90 || client.lat > 90 || client.lng < -180 || client.lng > 180) {
                console.error(`❌ Coordonnées hors limites pour ${client.name}:`, client.lat, client.lng);
                return;
            }

            const clientMarker = L.marker([client.lat, client.lng], {
                icon: L.divIcon({
                    className: 'client-marker-corrected',
                    html: `<div style="
                    background: ${color};
                    color: white;
                    border-radius: 50%;
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 14px;
                    border: 3px solid white;
                    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
                    position: relative;
                ">${sequenceDisplay}</div>`,
                    iconSize: [28, 28],
                    iconAnchor: [14, 14]
                })
            });

            // Popup avec informations détaillées
            const popupContent = `
            <div style="min-width: 220px; font-family: system-ui;">
                <div style="font-weight: bold; color: ${color}; margin-bottom: 8px; font-size: 16px;">
                    🚛 ${vehicleName}
                </div>
                <div style="background: #f8f9fa; padding: 8px; border-radius: 4px; margin-bottom: 8px;">
                    <strong>📍 Client:</strong> ${client.name}<br>
                    <strong>📋 Séquence:</strong> ${client.sequence || sequenceDisplay}<br>
                    <strong>📊 Type:</strong> ${client.type || 'customer'}
                </div>
                <div style="font-size: 12px; color: #666;">
                    <strong>📍 Adresse:</strong><br>
                    ${client.address || 'Adresse non disponible'}<br>
                    <strong>🌍 Coordonnées:</strong> ${client.lat.toFixed(4)}, ${client.lng.toFixed(4)}
                    ${client.order_name ? '<br><strong>📝 Commande:</strong> ' + client.order_name : ''}
                </div>
            </div>
        `;

            clientMarker.bindPopup(popupContent, {
                closeOnClick: true,
                autoClose: true,
                maxWidth: 300
            });

            // Ajouter à la carte
            clientMarker.addTo(this.state.map);
            this.state.markers.push(clientMarker);

            console.log(`✅ Marqueur client ajouté: ${client.name}`);

        } catch (error) {
            console.error(`❌ Erreur création marqueur pour ${client.name}:`, error);
        }
    }

    createRealRouteCorrected(clientWaypoints, vehicleData, color) {
        if (!this.state.map || clientWaypoints.length === 0) {
            console.warn("❌ Pas de carte ou waypoints pour créer route");
            return;
        }

        try {
            console.log(`🛣️  Création route pour ${vehicleData.vehicle_name}`);


            // Points de route: Dépôt -> Clients -> Dépôt
            const routeWaypoints = [
                L.latLng(34.0209, -6.8416), // Dépôt début
                ...clientWaypoints.map(wp => {
                    console.log(`Ajout waypoint route: ${wp.name} [${wp.lat}, ${wp.lng}]`);
                    return L.latLng(wp.lat, wp.lng);
                }),
                L.latLng(34.0209, -6.8416)  // Dépôt retour
            ];
            console.log(`Route avec ${routeWaypoints.length} points`);

            // Utiliser Leaflet Routing Machine si disponible
            if (typeof L.Routing !== 'undefined' && L.Routing.control) {
                console.log("🔄 Utilisation Leaflet Routing Machine");

                const routingControl = L.Routing.control({
                    waypoints: routeWaypoints,
                    routeWhileDragging: false,
                    addWaypoints: false,
                    createMarker: () => null, // Pas de marqueurs auto
                    lineOptions: {
                        styles: [{
                            color: color,
                            weight: 5,
                            opacity: 0.8
                        }]
                    },
                    router: L.Routing.osrmv1({
                        serviceUrl: 'https://router.project-osrm.org/route/v1',
                        profile: 'driving'
                    }),
                    show: false,
                    collapsible: false
                });

                // Événements
                routingControl.on('routesfound', (e) => {
                    const routes = e.routes;
                    const summary = routes[0].summary;
                    const distance = (summary.totalDistance / 1000).toFixed(2);
                    const duration = Math.round(summary.totalTime / 60);
                    console.log(`✅ Route trouvée: ${distance} km, ${duration} min`);
                });

                routingControl.on('routingerror', (e) => {
                    console.error('❌ Erreur routing:', e.error);
                    this.createFallbackRouteCorrected(routeWaypoints, color, vehicleData);
                });

                routingControl.addTo(this.state.map);
                this.state.routes.push(routingControl);

            } else {
                console.log("⚠️  Leaflet Routing Machine non disponible, route fallback");
                this.createFallbackRouteCorrected(routeWaypoints, color, vehicleData);
            }

        } catch (error) {
            console.error(`❌ Erreur création route pour ${vehicleData.vehicle_name}:`, error);
            this.createFallbackRouteCorrected(routeWaypoints, color, vehicleData);
        }
    }

    createFallbackRouteCorrected(waypoints, color, vehicleData) {
        console.log("🔄 Création route fallback (lignes droites)");

        try {
            const polyline = L.polyline(waypoints, {
                color: color,
                weight: 4,
                opacity: 0.7,
                dashArray: '8, 12',
                smoothFactor: 1
            });

            polyline.bindPopup(`
            <div style="text-align: center;">
                <strong style="color: ${color};">${vehicleData.vehicle_name}</strong><br>
                <em style="color: #666;">Route approximative</em><br>
                ${waypoints.length - 2} arrêts clients
            </div>
        `);

            polyline.addTo(this.state.map);
            this.state.routes.push(polyline);

            console.log("✅ Route fallback créée");
        } catch (error) {
            console.error("❌ Erreur création route fallback:", error);
        }
    }





    async createOSRMRoute(waypoints, color, vehicleData) {
        try {
            // Construire URL OSRM
            const coords = waypoints.map(wp => `${wp.lng},${wp.lat}`).join(';');
            const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`;

            console.log("Requête OSRM directe...");

            const response = await fetch(osrmUrl);
            if (!response.ok) {
                throw new Error(`OSRM HTTP error: ${response.status}`);
            }

            const data = await response.json();

            if (data.code !== 'Ok' || !data.routes || data.routes.length === 0) {
                throw new Error('OSRM: Aucune route trouvée');
            }

            // Extraire la géométrie
            const geometry = data.routes[0].geometry;
            if (!geometry || !geometry.coordinates) {
                throw new Error('OSRM: Géométrie invalide');
            }

            // Convertir coordonnées GeoJSON en LatLng Leaflet
            const routeCoords = geometry.coordinates.map(coord => [coord[1], coord[0]]);

            // Créer la polyline avec la vraie route
            const polyline = L.polyline(routeCoords, {
                color: color,
                weight: 4,
                opacity: 0.8,
                smoothFactor: 1
            });

            // Ajouter popup avec infos route
            const distance = data.routes[0].distance;
            const duration = data.routes[0].duration;

            polyline.on('click', (e) => {
                if (this.state.map) {
                    L.popup()
                        .setLatLng(e.latlng)
                        .setContent(`
                            <div style="min-width: 200px;">
                                <div style="font-weight: bold; color: ${color}; margin-bottom: 5px;">
                                    ${vehicleData.vehicle_name}
                                </div>
                                <div style="font-size: 12px;">
                                    <strong>Distance:</strong> ${(distance / 1000).toFixed(2)} km<br>
                                    <strong>Durée:</strong> ${Math.round(duration / 60)} min<br>
                                    <strong>Arrêts:</strong> ${waypoints.length - 2}
                                </div>
                            </div>
                        `)
                        .openOn(this.state.map);
                }
            });

            polyline.addTo(this.state.map);
            this.state.routes.push(polyline);
            console.log(`✅ Route OSRM créée: ${(distance / 1000).toFixed(2)}km, ${Math.round(duration / 60)}min`);

        } catch (error) {
            console.error('Erreur OSRM API:', error);
            this.createFallbackRoute(waypoints, color, vehicleData);
        }
    }

    createFallbackRoute(waypoints, color, vehicleData) {
        console.log("Création route fallback (ligne droite)");

        const polyline = L.polyline(waypoints, {
            color: color,
            weight: 3,
            opacity: 0.6,
            dashArray: '10, 10', // Ligne pointillée pour indiquer que c'est approximatif
            smoothFactor: 1
        });

        polyline.on('click', (e) => {
            if (this.state.map) {
                L.popup()
                    .setLatLng(e.latlng)
                    .setContent(`
                        <div>
                            <strong>${vehicleData.vehicle_name}</strong><br>
                            <em>Route approximative</em><br>
                            ${waypoints.length - 2} arrêts
                        </div>
                    `)
                    .openOn(this.state.map);
            }
        });

        polyline.addTo(this.state.map);
        this.state.routes.push(polyline);
    }

    processVehicleDataSafely() {
        /**
         * MODIFIÉ: Traitement principal des données avec détection du type de dépôt
         */
        try {
            console.log("=== TRAITEMENT DONNÉES AVEC DÉPÔTS DYNAMIQUES ===");
            
            const rawData = this.props.record?.data?.[this.props.name];
            console.log("Raw data type:", typeof rawData);
    
            let vehiclesData = [];
            
            if (rawData) {
                if (typeof rawData === 'string') {
                    try {
                        vehiclesData = JSON.parse(rawData);
                    } catch (error) {
                        console.error('Erreur parsing JSON:', error);
                    }
                } else if (Array.isArray(rawData)) {
                    vehiclesData = rawData;
                }
            }
    
            console.log(`📊 ${vehiclesData.length} véhicules à traiter`);
    
            // Détecter le type de dépôt
            const hasDriverDepots = vehiclesData.some(v => v.depot_type === 'driver_based');
            console.log(`Type de dépôt détecté: ${hasDriverDepots ? 'Chauffeurs' : 'Fixe (legacy)'}`);
    
            if (!hasDriverDepots) {
                // Mode legacy avec dépôt fixe
                console.log("Mode legacy: ajout dépôt fixe");
                this.addDepotMarkerSafe(); // Ancienne méthode
            }
    
            // Traiter les véhicules avec le bon algorithme
            this.processVehiclesSafely(vehiclesData);
            this.state.isLoaded = true;
    
        } catch (error) {
            console.error('Erreur critique traitement données:', error);
            this.state.isLoaded = true;
        }
    }


    fitMapSafely(points) {
        if (!this.state.map || points.length === 0) return;

        try {
            const bounds = L.latLngBounds();

            // Ajouter tous les points
            points.forEach(point => {
                bounds.extend([point.lat, point.lng]);
            });

            // Ajouter le dépôt
            bounds.extend([34.0209, -6.8416]);

            // Ajuster avec padding
            this.state.map.fitBounds(bounds, {
                padding: [20, 20],
                maxZoom: 15
            });

            console.log("✅ Vue carte ajustée avec sécurité");

        } catch (error) {
            console.error("Erreur ajustement vue:", error);
        }
    }
}

// Enregistrement
const vrpRouteMapWidgetPopupFix = {
    displayName: 'VRP Route Map - Popup Fix',
    component: VRPRouteMapWidgetPopupFix,
    supportedTypes: ['text'],
};

registry.category('fields').add('vrp_route_map', vrpRouteMapWidgetPopupFix);