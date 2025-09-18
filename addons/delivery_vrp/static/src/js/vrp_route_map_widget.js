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
        if (!this.state.map) return;

        try {
            const depotLat = 34.0209;
            const depotLng = -6.8416;

            const depotMarker = L.marker([depotLat, depotLng], {
                icon: L.divIcon({
                    className: 'depot-marker-safe',
                    html: `<div style="
                        background: linear-gradient(45deg, #007bff, #0056b3);
                        color: white;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 16px;
                        border: 3px solid white;
                        box-shadow: 0 4px 8px rgba(0,123,255,0.4);
                    ">D</div>`,
                    iconSize: [30, 30],
                    iconAnchor: [15, 15]
                })
            });

            // CORRECTION CRITIQUE: Popup sécurisé avec vérification carte
            depotMarker.on('click', (e) => {
                if (this.state.map && !this.state.map._container._leaflet_pos) {
                    // Carte pas prête pour les popups
                    console.warn("Carte pas prête pour popup");
                    return;
                }

                L.popup({
                    closeOnClick: true,
                    autoClose: true,
                    closePopupOnClick: true
                })
                    .setLatLng([depotLat, depotLng])
                    .setContent(`
                    <div style="min-width: 180px; text-align: center;">
                        <div style="font-weight: bold; color: #007bff; font-size: 16px; margin-bottom: 8px;">
                            DÉPÔT PRINCIPAL
                        </div>
                        <div style="font-size: 13px; color: #666;">
                            <strong>Position:</strong> Point de départ/retour<br>
                            <strong>Coordonnées:</strong> ${depotLat}, ${depotLng}
                        </div>
                    </div>
                `)
                    .openOn(this.state.map);
            });

            depotMarker.addTo(this.state.map);
            this.state.markers.push(depotMarker);
            console.log("✅ Dépôt ajouté avec sécurité");

        } catch (error) {
            console.error('Erreur ajout dépôt:', error);
        }
    }

    
    // Correction pour le widget JavaScript - Traitement waypoints
processVehiclesSafely(vehiclesData) {
    if (!this.state.map) return;

    const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e'];
    let allValidPoints = [];

    console.log("=== TRAITEMENT VÉHICULES CORRIGÉ ===");

    vehiclesData.forEach((vehicleData, vehicleIndex) => {
        console.log(`🚛 Traitement véhicule: ${vehicleData.vehicle_name}`);

        if (!vehicleData.waypoints || !Array.isArray(vehicleData.waypoints)) {
            console.warn("❌ Pas de waypoints valides");
            return;
        }

        const vehicleColor = colors[vehicleIndex % colors.length];
        console.log(`Couleur assignée: ${vehicleColor}`);

        // CORRECTION CRITIQUE: Traiter TOUS les waypoints, pas seulement les clients
        const allWaypoints = vehicleData.waypoints.filter(wp => 
            wp.lat && wp.lng && 
            typeof wp.lat === 'number' && typeof wp.lng === 'number' &&
            wp.lat !== 0 && wp.lng !== 0
        );

        console.log(`Total waypoints valides: ${allWaypoints.length}`);
        console.log("Waypoints détail:", allWaypoints.map(wp => ({
            name: wp.name,
            type: wp.type,
            sequence: wp.sequence,
            coords: [wp.lat, wp.lng]
        })));

        // Séparer dépôts et clients pour traitement différent
        const depotWaypoints = allWaypoints.filter(wp => wp.type === 'depot' || wp.type === 'depot_return');
        const clientWaypoints = allWaypoints.filter(wp => wp.type === 'customer');

        console.log(`Dépôts: ${depotWaypoints.length}, Clients: ${clientWaypoints.length}`);

        // Trier les clients par séquence
        clientWaypoints.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));

        // CORRECTION: Ajouter les marqueurs CLIENTS avec une méthode corrigée
        clientWaypoints.forEach((client, index) => {
            console.log(`Ajout marqueur client: ${client.name} à ${client.lat}, ${client.lng}`);
            this.addClientMarkerCorrected(client, vehicleColor, vehicleData.vehicle_name, index + 1);
            allValidPoints.push(client);
        });

        // Créer la route si on a des clients
        if (clientWaypoints.length > 0) {
            console.log("Création route avec waypoints:", clientWaypoints.map(wp => wp.name));
            this.createRealRouteCorrected(clientWaypoints, vehicleData, vehicleColor);
        } else {
            console.warn("❌ Aucun client valide pour créer une route");
        }
    });

    // Ajuster la vue si on a des points
    if (allValidPoints.length > 0) {
        console.log(`Ajustement vue pour ${allValidPoints.length} points`);
        this.fitMapSafely(allValidPoints);
    } else {
        console.warn("❌ Aucun point valide pour ajuster la vue");
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
                                    <strong>Distance:</strong> ${(distance/1000).toFixed(2)} km<br>
                                    <strong>Durée:</strong> ${Math.round(duration/60)} min<br>
                                    <strong>Arrêts:</strong> ${waypoints.length - 2}
                                </div>
                            </div>
                        `)
                        .openOn(this.state.map);
                }
            });
            
            polyline.addTo(this.state.map);
            this.state.routes.push(polyline);
            console.log(`✅ Route OSRM créée: ${(distance/1000).toFixed(2)}km, ${Math.round(duration/60)}min`);
            
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
        try {
            console.log("=== DEBUG TRAITEMENT DONNÉES VÉHICULES ===");
            console.log("Props reçues:", this.props);
            console.log("Record data:", this.props.record?.data);
            console.log("Field name:", this.props.name);
            
            // Obtenir les données avec debugging détaillé
            const rawData = this.props.record?.data?.[this.props.name];
            console.log("Raw data type:", typeof rawData);
            console.log("Raw data content:", rawData);
            
            let vehiclesData;
    
            if (!rawData) {
                console.warn("❌ Aucune donnée brute trouvée");
                vehiclesData = [];
            } else if (typeof rawData === 'string') {
                console.log("📝 Traitement string JSON...");
                try {
                    vehiclesData = JSON.parse(rawData);
                    console.log("✅ JSON parsé avec succès:", vehiclesData);
                    
                    if (!Array.isArray(vehiclesData)) {
                        console.error("❌ JSON parsé n'est pas un array:", typeof vehiclesData);
                        vehiclesData = [];
                    }
                } catch (error) {
                    console.error('❌ Erreur parsing JSON:', error);
                    console.error('Contenu problématique:', rawData.substring(0, 200));
                    vehiclesData = [];
                }
            } else if (Array.isArray(rawData)) {
                console.log("📋 Données déjà sous forme d'array");
                vehiclesData = rawData;
            } else {
                console.error("❌ Type de données non supporté:", typeof rawData);
                vehiclesData = [];
            }
    
            console.log(`📊 RÉSULTAT FINAL: ${vehiclesData.length} véhicules`);
            
            // Debug détaillé de chaque véhicule
            vehiclesData.forEach((vehicle, index) => {
                console.log(`🚛 Véhicule ${index}:`, {
                    name: vehicle.vehicle_name,
                    waypoints: vehicle.waypoints?.length || 0,
                    waypoints_valid: vehicle.waypoints?.filter(wp => wp.lat && wp.lng && wp.lat !== 0 && wp.lng !== 0).length || 0
                });
                
                // Debug waypoints en détail
                if (vehicle.waypoints && vehicle.waypoints.length > 0) {
                    vehicle.waypoints.forEach((wp, wpIndex) => {
                        console.log(`  📍 Waypoint ${wpIndex}:`, {
                            name: wp.name,
                            type: wp.type,
                            sequence: wp.sequence,
                            coords: `${wp.lat}, ${wp.lng}`,
                            valid: wp.lat && wp.lng && wp.lat !== 0 && wp.lng !== 0
                        });
                    });
                }
            });
    
            // Toujours ajouter le dépôt
            this.addDepotMarkerSafe();
    
            if (!vehiclesData || vehiclesData.length === 0) {
                console.log("⚪ Aucune donnée véhicule - affichage dépôt seulement");
                this.state.isLoaded = true;
                return;
            }
    
            // Traiter les véhicules de manière sécurisée
            this.processVehiclesSafely(vehiclesData);
            this.state.isLoaded = true;
    
        } catch (error) {
            console.error('💥 Erreur critique traitement données:', error);
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