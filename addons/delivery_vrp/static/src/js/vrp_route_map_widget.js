/** @odoo-module **/

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
            console.log("=== VRP WIDGET MOUNTED ===");
            this.debugWidgetState();

            this.loadMapLibraries().then(() => {
                console.log("Libraries loaded, calling initMap...");
                this.initMap();
            }).catch(error => {
                console.error('Failed to load map libraries:', error);
            });
        });
    }

    debugWidgetState() {
        console.log("=== WIDGET DEBUG INFO ===");
        console.log("1. Widget mounted");
        console.log("2. MapRef element:", this.mapRef.el);
        console.log("3. Props:", this.props);
        console.log("4. State:", this.state);

        if (this.mapRef.el) {
            const rect = this.mapRef.el.getBoundingClientRect();
            console.log("5. Container dimensions:", rect);
            console.log("6. Container styles:", {
                height: this.mapRef.el.style.height,
                width: this.mapRef.el.style.width,
                display: this.mapRef.el.style.display
            });
        } else {
            console.warn("5. Container element not found!");
        }
        console.log("================================");
    }

    async loadMapLibraries() {
        console.log("=== LIBRARY LOADING DEBUG ===");
        console.log("Starting library loading...");

        if (window.L) {
            console.log("Leaflet already loaded, version:", window.L.version);
            if (window.L.Routing) {
                console.log("Leaflet Routing Machine already loaded");
            }
            return;
        }

        try {
            console.log("Loading Leaflet CSS...");
            await loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
            console.log("✓ Leaflet CSS loaded");

            console.log("Loading Leaflet JS...");
            await loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
            console.log("✓ Leaflet JS loaded, version:", window.L?.version);

            console.log("Loading Leaflet Routing Machine CSS...");
            await loadCSS("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css");
            console.log("✓ Leaflet Routing Machine CSS loaded");

            console.log("Loading Leaflet Routing Machine JS...");
            await loadJS("https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js");
            console.log("✓ Leaflet Routing Machine JS loaded");

            console.log("All libraries loaded successfully");
            console.log("Window.L available:", !!window.L);
            console.log("Window.L.Routing available:", !!(window.L && window.L.Routing));

        } catch (error) {
            console.error("Library loading failed:", error);
            throw error;
        }
        console.log("=== END LIBRARY LOADING ===");
    }

    initMap() {
        console.log("=== INIT MAP DEBUG ===");

        try {
            // Debug des données reçues  
            console.log("1. Starting initMap");
            console.log("2. Props received:", this.props);

            // Validation et parsing des données JSON  
            let vehiclesData;
            try {
                const rawData = this.props.record.data[this.props.name] || '[]';
                console.log("3. Raw vehicles data:", rawData);
                console.log("4. Data type:", typeof rawData);

                vehiclesData = typeof rawData === 'string' ? JSON.parse(rawData) : rawData;
                console.log("5. Parsed vehicles data:", vehiclesData);
                console.log("6. Is array:", Array.isArray(vehiclesData));
                console.log("7. Array length:", vehiclesData?.length);

                if (!Array.isArray(vehiclesData)) {
                    console.warn('Vehicles data is not an array, using empty array');
                    vehiclesData = [];
                }
            } catch (error) {
                console.error('Invalid JSON data:', error);
                console.error('Raw data was:', this.props.record.data[this.props.name]);
                vehiclesData = [];
            }

            if (!vehiclesData.length) {
                console.log("8. No vehicles data, setting isLoaded = true and returning");
                this.state.isLoaded = true;
                return;
            }

            // Debug du conteneur  
            console.log("9. Getting map container reference...");
            const mapContainer = this.mapRef.el;
            console.log("10. Map container element:", mapContainer);

            if (!mapContainer) {
                console.error('Map container not found');
                return;
            }

            // Debug des dimensions avant modification  
            const rectBefore = mapContainer.getBoundingClientRect();
            console.log("11. Container dimensions before styling:", rectBefore);
            console.log("12. Container computed styles before:", window.getComputedStyle(mapContainer));

            // Forcer les dimensions du conteneur  
            console.log("13. Forcing container dimensions...");
            mapContainer.style.height = mapContainer.style.height || '500px';
            mapContainer.style.width = mapContainer.style.width || '100%';
            mapContainer.style.minHeight = '500px';

            // Debug des dimensions après modification  
            const rectAfter = mapContainer.getBoundingClientRect();
            console.log("14. Container dimensions after styling:", rectAfter);
            console.log("15. Container styles after:", {
                height: mapContainer.style.height,
                width: mapContainer.style.width,
                minHeight: mapContainer.style.minHeight
            });

            // Vérifier que Leaflet est disponible  
            console.log("16. Checking Leaflet availability...");
            console.log("17. window.L available:", !!window.L);
            if (!window.L) {
                console.error("Leaflet not available!");
                return;
            }

            // Initialiser la carte Leaflet  
            console.log("18. Initializing Leaflet map...");
            try {
                this.state.map = L.map(mapContainer).setView([33.5731, -7.5898], 10);
                console.log("19. ✓ Map created successfully:", this.state.map);
            } catch (mapError) {
                console.error("20. ✗ Map creation failed:", mapError);
                return;
            }

            // Ajouter les tuiles  
            console.log("21. Adding tile layer...");
            try {
                L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                    attribution: "&copy; OpenStreetMap contributors",
                }).addTo(this.state.map);
                console.log("22. ✓ Tile layer added successfully");
            } catch (tileError) {
                console.error("23. ✗ Tile layer failed:", tileError);
            }

            // Couleurs pour différencier les véhicules  
            const colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen'];
            console.log("24. Processing vehicles data...");

            // Traiter chaque véhicule  
            vehiclesData.forEach((vehicleData, index) => {
                console.log(`25.${index + 1}. Processing vehicle:`, vehicleData.vehicle_name);
                const color = colors[index % colors.length];
                this.addVehicleRoute(vehicleData, color);
            });

            console.log("26. Setting isLoaded = true");
            this.state.isLoaded = true;
            console.log("27. ✓ Map initialization completed successfully");

        } catch (error) {
            console.error('28. ✗ Error initializing map:', error);
            console.error('Error stack:', error.stack);
            this.state.isLoaded = true;
        }

        console.log("=== END INIT MAP DEBUG ===");
    }

    addVehicleRoute(vehicleData, color) {
        console.log(`=== ADDING ROUTE FOR ${vehicleData.vehicle_name} ===`);

        if (!vehicleData.waypoints || !vehicleData.waypoints.length) {
            console.warn('No waypoints for vehicle:', vehicleData.vehicle_name);
            return;
        }

        console.log(`Waypoints for ${vehicleData.vehicle_name}:`, vehicleData.waypoints);

        const waypoints = vehicleData.waypoints.map(point => {
            console.log(`Creating waypoint: lat=${point.lat}, lng=${point.lng}`);
            return L.latLng(point.lat, point.lng);
        });

        // Ajouter des marqueurs pour chaque point  
        vehicleData.waypoints.forEach((point, index) => {
            console.log(`Adding marker ${index + 1} for ${vehicleData.vehicle_name}`);
            try {
                const marker = L.marker([point.lat, point.lng])
                    .bindPopup(`  
                        <strong>${vehicleData.vehicle_name}</strong><br>  
                        Séquence: ${point.sequence}<br>  
                        Client: ${point.name}<br>  
                        Adresse: ${point.address}  
                    `)
                    .addTo(this.state.map);

                this.state.markers.push(marker);
                console.log(`✓ Marker ${index + 1} added successfully`);
            } catch (markerError) {
                console.error(`✗ Failed to add marker ${index + 1}:`, markerError);
            }
        });

        // Créer le contrôle de routage avec OSRM  
        console.log(`Creating routing control for ${vehicleData.vehicle_name}...`);
        try {
            const routingControl = L.Routing.control({
                waypoints: waypoints,
                routeWhileDragging: false,
                addWaypoints: false,
                createMarker: function () { return null; }, // Pas de marqueurs supplémentaires  
                lineOptions: {
                    styles: [{ color: color, weight: 4, opacity: 0.7 }]
                },
                router: L.Routing.osrmv1({
                    serviceUrl: 'https://router.project-osrm.org/route/v1'
                })
            }).addTo(this.state.map);

            this.state.routes.push(routingControl);
            console.log(`✓ Routing control added for ${vehicleData.vehicle_name}`);
        } catch (routingError) {
            console.error(`✗ Failed to create routing control for ${vehicleData.vehicle_name}:`, routingError);
        }

        // Ajuster la vue pour inclure tous les points  
        if (waypoints.length > 0 && this.state.markers.length > 0) {
            console.log("Adjusting map bounds to fit all markers...");
            try {
                const group = new L.featureGroup(this.state.markers);
                this.state.map.fitBounds(group.getBounds().pad(0.1));
                console.log("✓ Map bounds adjusted successfully");
            } catch (boundsError) {
                console.error("✗ Failed to adjust map bounds:", boundsError);
            }
        }

        console.log(`=== END ROUTE FOR ${vehicleData.vehicle_name} ===`);
    }
}

const vrpRouteMapWidget = {
    displayName: 'VRP Route Map Widget',
    component: VRPRouteMapWidget,
    supportedTypes: ['text'],
};

registry.category('fields').add('vrp_route_map', vrpRouteMapWidget);
