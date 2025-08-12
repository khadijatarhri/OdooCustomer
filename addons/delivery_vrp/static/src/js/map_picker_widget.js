/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MapPickerWidget extends Component {
    setup() {
        this.mapRef = useRef("mapContainer");
        this.state = useState({
            latitude: this.props.value ? parseFloat(this.props.value) : 33.5731,
            longitude: (this.props.record && this.props.record.data && this.props.record.data.longitude) ? parseFloat(this.props.record.data.longitude) : -7.5898,
            map: null,
            marker: null,
        });
        onMounted(() => this.initMap());
    }

    async loadLeaflet() {
        if (window.L) return;
        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(link);

            const script = document.createElement('script');
            script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    async initMap() {
        await this.loadLeaflet();
        const mapContainer = this.mapRef.el;
        // give the container a height if CSS missing
        mapContainer.style.height = mapContainer.style.height || '300px';

        this.state.map = L.map(mapContainer).setView([this.state.latitude, this.state.longitude], 10);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.state.map);

        if (this.state.latitude && this.state.longitude) {
            this.addMarker(this.state.latitude, this.state.longitude);
        }

        this.state.map.on('click', (e) => {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;
            this.onMapClick(lat, lng);
        });
    }

    addMarker(lat, lng) {
        if (this.state.marker) {
            this.state.map.removeLayer(this.state.marker);
        }
        this.state.marker = L.marker([lat, lng]).addTo(this.state.map);
        this.state.map.setView([lat, lng], this.state.map.getZoom());
    }

    onMapClick(lat, lng) {
        // mettre à jour l'état local (réactif)
        this.state.latitude = lat;
        this.state.longitude = lng;

        // positionner le marqueur
        this.addMarker(lat, lng);

        // mettre à jour le champ principal (latitude)
        if (this.props.update) {
            this.props.update(lat);
        }

        // mettre à jour la longitude dans le record (si présent)
        if (this.props.record && this.props.record.update) {
            // Mettre à jour en base le champ longitude
            this.props.record.update({ longitude: lng });
        }
    }
}

MapPickerWidget.template = "delivery_vrp.MapPickerTemplate";
MapPickerWidget.props = { ...standardFieldProps };

registry.category("fields").add("map_picker", MapPickerWidget);
