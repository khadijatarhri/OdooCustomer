/** @odoo-module **/
// static/src/js/vrp_route_map_widget_corrected.js

import { registry } from '@web/core/registry';
import { Component, useState, useRef, onMounted } from '@odoo/owl';
import { standardFieldProps } from '@web/views/fields/standard_field_props';
import { loadJS, loadCSS } from "@web/core/assets";

export class VRPRouteMapWidget extends Component {
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
            console.log("=== VRP WIDGET MOUNTED (CORRECTED) ===");
            this.debugWidgetState();

            this.loadMapLibraries().then(() => {
                console.log("Libraries loaded, initializing corrected map...");
                setTimeout(() => {
                    this.initCorrectedMap();
                }, 100);
            }).catch(error => {
                console.error('Failed to load map libraries:', error);
                this.state.isLoaded = true;
            });
        });
    }

    debugWidgetState() {
        console.log("=== WIDGET DEBUG INFO (CORRECTED) ===");
        console.log("1. Widget mounted with corrections");
        console.log("2. MapRef element:", this.mapRef.el);
        console.log("3. Field value:", this.props.record?.data?.[this.props.name]);
        
        // Debugging spécifique pour les données véhicules
        const rawData = this.props.record?.data?.[this.props.name] || '[]';
        try {
            const vehiclesData = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
            console.log("4. Parsed vehicles data:", vehiclesData);
            console.log("5. Number of vehicles:", vehiclesData.length);
            
            vehiclesData.forEach((vehicle, idx) => {
                console.log(`   Vehicle ${idx + 1}: ${vehicle.vehicle_name} with ${vehicle.waypoints?.length || 0} waypoints`);
                if (vehicle.waypoints) {
                    vehicle.waypoints.forEach((wp, wpIdx) => {
                        console.log(`     Waypoint ${wpIdx + 1}: ${wp.name} (${wp.lat}, ${wp.lng}) seq:${wp.sequence} type:${wp.type}`);
                    });
                }
            });
        } catch (e) {
            console.error("Error parsing vehicle data:", e);
        }
        console.log("================================");
    }

    async loadMapLibraries() {
        console.log("=== LOADING LIBRARIES (CORRECTED) ===");

        if (window.L) {
            console.log("Leaflet already loaded, version:", window.L.version);
            return;
        }

        try {
            await loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
            await loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
            await loadCSS("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css");
            await loadJS("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js");
            
            console.log("All libraries loaded successfully (corrected)");
        } catch (error) {
            console.error("Library loading failed:", error);
            throw error;
        }
    }

    initCorrectedMap() {
        console.log("=== INITIALIZING CORRECTED MAP ===");

        try {
            // Validation et parsing des données
            let vehiclesData;
            const rawData = this.props.record?.data?.[this.props.name] || '[]';
            console.log("Raw vehicles data:", rawData);

            try {
                vehiclesData = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
                if (!Array.isArray(vehiclesData)) {
                    console.warn('Vehicles data is not an array, using empty array');
                    vehiclesData = [];
                }
            } catch (error) {
                console.error('Invalid JSON data:', error);
                vehiclesData = [];
            }

            // Configuration du conteneur
            const mapContainer = this.mapRef.el;
            if (!mapContainer) {
                console.error('Map container not found');
                this.state.isLoaded = true;
                return;
            }

            mapContainer.style.height = '500px';
            mapContainer.style.width = '100%';
            mapContainer.style.minHeight = '500px';
            mapContainer.style.position = 'relative';

            if (!window.L) {
                console.error("Leaflet not available!");
                this.state.isLoaded = true;
                return;
            }

            // Créer la carte centrée sur Rabat (dépôt par défaut)
            console.log("Creating Leaflet map centered on Rabat...");
            this.state.map = L.map(mapContainer).setView([34.0209, -6.8416], 10);

            // Ajouter les tuiles
            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: "&copy; OpenStreetMap contributors",
            }).addTo(this.state.map);

            // Si aucune donnée, afficher carte vide centrée sur Rabat
            if (!vehiclesData || vehiclesData.length === 0) {
                console.log("No vehicle data, showing empty map centered on Rabat");
                // Ajouter un marqueur pour le dépôt
                L.marker([34.0209, -6.8416])
                    .bindPopup('<b>Dépôt - Rabat</b><br>Point de départ des livraisons')
                    .addTo(this.state.map);
                this.state.isLoaded = true;
                return;
            }

            // Traiter chaque véhicule avec routes séquentielles
            this.processVehicleRoutesSequentially(vehiclesData);

            this.state.isLoaded = true;
            console.log("Corrected map initialization completed successfully");

        } catch (error) {
            console.error('Error initializing corrected map:', error);
            this.state.isLoaded = true;
        }
    }

    processVehicleRoutesSequentially(vehiclesData) {
        console.log(`=== PROCESSING ${vehiclesData.length} VEHICLES SEQUENTIALLY ===`);
        
        const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#34495e'];
        let allValidPoints = [];

        vehiclesData.forEach((vehicleData, index) => {
            console.log(`\n=== VEHICLE ${index + 1}: ${vehicleData.vehicle_name} ===`);
            
            if (!vehicleData.waypoints || vehicleData.waypoints.length === 0) {
                console.warn(`No waypoints for vehicle: ${vehicleData.vehicle_name}`);
                return;
            }

            const color = vehicleData.vehicle_color || colors[index % colors.length];
            console.log(`Using color: ${color}`);

            // Trier les waypoints par séquence pour assurer l'ordre correct
            const sortedWaypoints = [...vehicleData.waypoints].sort((a, b) => {
                return (a.sequence || 0) - (b.sequence || 0);
            });

            console.log(`Waypoints sorted by sequence:`);
            sortedWaypoints.forEach((wp, idx) => {
                console.log(`  ${idx + 1}. ${wp.name} (seq: ${wp.sequence}) - ${wp.lat}, ${wp.lng} [${wp.type}]`);
            });

            // Valider et filtrer les waypoints
            const validWaypoints = sortedWaypoints.filter(point => {
                const isValid = point.lat && point.lng && 
                               point.lat !== 0 && point.lng !== 0 &&
                               !isNaN(point.lat) && !isNaN(point.lng) &&
                               Math.abs(point.lat) <= 90 && Math.abs(point.lng) <= 180;
                
                if (!isValid) {
                    console.warn(`Invalid waypoint filtered out: ${point.name}`);
                }
                return isValid;
            });

            if (validWaypoints.length === 0) {
                console.warn(`No valid waypoints for vehicle: ${vehicleData.vehicle_name}`);
                return;
            }

            console.log(`Valid waypoints: ${validWaypoints.length}/${sortedWaypoints.length}`);

            // Ajouter les marqueurs séquentiels
            this.addSequentialMarkers(validWaypoints, vehicleData, color);

            // Créer la route si au moins 2 points
            if (validWaypoints.length >= 2) {
                this.createSequentialRoute(validWaypoints, vehicleData, color);
            }

            // Collecter tous les points valides pour l'ajustement de la vue
            allValidPoints.push(...validWaypoints);
        });

        // Ajuster la vue pour inclure tous les points
        if (allValidPoints.length > 0) {
            this.fitMapToAllPoints(allValidPoints);
        }
    }

    addSequentialMarkers(waypoints, vehicleData, color) {
        console.log(`Adding ${waypoints.length} sequential markers for ${vehicleData.vehicle_name}`);

        waypoints.forEach((point, index) => {
            try {
                let markerOptions = {
                    radius: 8,
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                };

                // Style différencié selon le type
                if (point.type === 'depot' || point.type === 'depot_return') {
                    markerOptions.color = '#28a745';
                    markerOptions.fillColor = '#28a745';
                    markerOptions.radius = 10;
                } else {
                    markerOptions.color = color;
                    markerOptions.fillColor = color;
                }

                const marker = L.circleMarker([point.lat, point.lng], markerOptions)
                    .bindPopup(`
                        <div class="vrp-marker-popup" style="min-width: 200px;">
                            <div style="font-weight: bold; color: ${color}; margin-bottom: 5px;">
                                ${vehicleData.vehicle_name}
                            </div>
                            <div style="font-size: 12px;">
                                <strong>Type:</strong> ${this.getTypeLabel(point.type)}<br>
                                <strong>Séquence:</strong> ${point.sequence}<br>
                                <strong>Nom:</strong> ${point.name || 'N/A'}<br>
                                <strong>Adresse:</strong> ${point.address || 'N/A'}
                                ${point.order_name ? '<br><strong>Commande:</strong> ' + point.order_name : ''}
                            </div>
                        </div>
                    `)
                    .addTo(this.state.map);

                this.state.markers.push(marker);
                console.log(`✓ Marker ${index + 1} added: ${point.name} (${point.lat}, ${point.lng})`);
            } catch (markerError) {
                console.error(`✗ Failed to add marker ${index + 1}:`, markerError);
            }
        });
    }

    createSequentialRoute(waypoints, vehicleData, color) {
        console.log(`Creating sequential route for ${vehicleData.vehicle_name} with ${waypoints.length} waypoints`);

        try {
            // Créer les waypoints pour Leaflet Routing Machine dans l'ordre séquentiel
            const routeWaypoints = waypoints.map(point => L.latLng(point.lat, point.lng));
            
            console.log(`Route waypoints order:`);
            routeWaypoints.forEach((wp, idx) => {
                console.log(`  ${idx + 1}. ${wp.lat}, ${wp.lng}`);
            });

            const routingControl = L.Routing.control({
                waypoints: routeWaypoints,
                routeWhileDragging: false,
                addWaypoints: false,
                createMarker: function() { return null; }, // Pas de marqueurs supplémentaires
                lineOptions: {
                    styles: [{
                        color: color,
                        weight: 4,
                        opacity: 0.8,
                        dashArray: null // Ligne continue
                    }]
                },
                router: L.Routing.osrmv1({
                    serviceUrl: 'https://router.project-osrm.org/route/v1',
                    timeout: 30000
                }),
                show: false, // Cacher le panneau d'instructions
                autoRoute: true,
                fitSelectedRoutes: false
            });

            // Gestion des erreurs de routage
            routingControl.on('routingerror', (e) => {
                console.warn(`Routing error for ${vehicleData.vehicle_name}:`, e.error);
                // Fallback: ligne droite simple
                const fallbackRoute = L.polyline(routeWaypoints, {
                    color: color,
                    weight: 3,
                    opacity: 0.6,
                    dashArray: '10, 10'
                }).bindPopup(`Route ${vehicleData.vehicle_name} (ligne directe)`).addTo(this.state.map);
                
                this.state.routes.push(fallbackRoute);
                console.log(`✓ Fallback route created for ${vehicleData.vehicle_name}`);
            });

            // Confirmation de création de route
            routingControl.on('routesfound', (e) => {
                console.log(`✓ Sequential route found for ${vehicleData.vehicle_name}`);
                
                // Ajouter des informations sur la route
                const routes = e.routes;
                if (routes.length > 0) {
                    const route = routes[0];
                    const distance = (route.summary.totalDistance / 1000).toFixed(2);
                    const time = Math.round(route.summary.totalTime / 60);
                    console.log(`   Distance: ${distance}km, Temps: ${time}min`);
                }
            });

            routingControl.addTo(this.state.map);
            this.state.routes.push(routingControl);
            
            console.log(`✓ Sequential routing control added for ${vehicleData.vehicle_name}`);

        } catch (routingError) {
            console.error(`✗ Failed to create sequential routing for ${vehicleData.vehicle_name}:`, routingError);
            
            // Fallback ultime: ligne droite simple
            try {
                const routeWaypoints = waypoints.map(point => L.latLng(point.lat, point.lng));
                const fallbackRoute = L.polyline(routeWaypoints, {
                    color: color,
                    weight: 3,
                    opacity: 0.5,
                    dashArray: '5, 10'
                }).bindPopup(`${vehicleData.vehicle_name} (route simplifiée)`).addTo(this.state.map);
                
                this.state.routes.push(fallbackRoute);
                console.log(`✓ Ultimate fallback route created for ${vehicleData.vehicle_name}`);
            } catch (fallbackError) {
                console.error(`✗ Even ultimate fallback failed for ${vehicleData.vehicle_name}:`, fallbackError);
            }
        }
    }

    fitMapToAllPoints(allPoints) {
        console.log(`Adjusting map bounds to fit ${allPoints.length} points...`);
        
        try {
            if (allPoints.length === 0) {
                console.log("No points to fit, keeping default view on Rabat");
                return;
            }

            const bounds = L.latLngBounds();
            allPoints.forEach(point => {
                bounds.extend([point.lat, point.lng]);
            });

            // S'assurer que Rabat (dépôt) est inclus
            bounds.extend([34.0209, -6.8416]);

            this.state.map.fitBounds(bounds, {
                padding: [20, 20],
                maxZoom: 15
            });
            
            console.log("✓ Map bounds adjusted successfully to include all sequential points");
        } catch (boundsError) {
            console.error("✗ Failed to adjust map bounds:", boundsError);
        }
    }

    getTypeLabel(type) {
        const labels = {
            'depot': 'Dépôt',
            'depot_return': 'Retour Dépôt',
            'customer': 'Client'
        };
        return labels[type] || 'Inconnu';
    }
}

// Enregistrement du widget corrigé
const vrpRouteMapWidget = {
    displayName: 'VRP Route Map Widget (Corrected)',
    component: VRPRouteMapWidget,
    supportedTypes: ['text'],
};

registry.category('fields').add('vrp_route_map', vrpRouteMapWidget);