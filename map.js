// Initialize the map centered on Loudoun County, VA
var map = L.map('map').setView([39.0768, -77.6437], 10);

// Add a tile layer (OpenStreetMap)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Load GeoJSON data with robust coordinate handling
fetch('nova_data_centers_improved.geojson')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('GeoJSON data loaded:', data);
        console.log('Total features:', data.features.length);
        
        let validFeatures = 0;
        let invalidFeatures = 0;
        
        // Process each feature individually with validation
        data.features.forEach((feature, index) => {
            try {
                // Validate the feature structure
                if (!feature.geometry || !feature.geometry.coordinates) {
                    console.warn(`Feature ${index} missing geometry or coordinates:`, feature);
                    invalidFeatures++;
                    return;
                }
                
                let coords = feature.geometry.coordinates;
                console.log(`Feature ${index} (${feature.properties.name}):`, coords);
                
                // GeoJSON coordinates are [longitude, latitude]
                let lng = parseFloat(coords[0]);
                let lat = parseFloat(coords[1]);
                
                // Validate coordinates
                if (isNaN(lng) || isNaN(lat)) {
                    console.error(`Invalid coordinates for ${feature.properties.name}: [${coords[0]}, ${coords[1]}]`);
                    invalidFeatures++;
                    return;
                }
                
                // Check if coordinates are within reasonable bounds
                if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
                    console.error(`Coordinates out of bounds for ${feature.properties.name}: [${lng}, ${lat}]`);
                    invalidFeatures++;
                    return;
                }
                
                // Create the marker
                let marker = L.circleMarker([lat, lng], {
                    radius: 8,
                    fillColor: "#ff7800",
                    color: "#000",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
                
                // Create popup content
                let popupContent = `<b>${feature.properties.name || 'Unnamed'}</b><br>`;
                if (feature.properties.company) {
                    popupContent += `Company: ${feature.properties.company}<br>`;
                }
                if (feature.properties.address) {
                    popupContent += `Address: ${feature.properties.address}<br>`;
                }
                popupContent += `Coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                
                marker.bindPopup(popupContent);
                marker.addTo(map);
                
                validFeatures++;
                
            } catch (error) {
                console.error(`Error processing feature ${index}:`, error, feature);
                invalidFeatures++;
            }
        });
        
        console.log(`Successfully added ${validFeatures} markers`);
        if (invalidFeatures > 0) {
            console.warn(`${invalidFeatures} features had invalid coordinates`);
        }
        
        // Display summary
        document.body.insertAdjacentHTML('afterbegin', 
            `<div style="background: #e8f5e8; color: #2e7d2e; padding: 10px; margin: 10px;">
                Loaded ${validFeatures} data centers successfully
                ${invalidFeatures > 0 ? `<br>⚠️ ${invalidFeatures} features had invalid coordinates` : ''}
            </div>`
        );
        
    })
    .catch(error => {
        console.error('Error loading GeoJSON:', error);
        document.body.insertAdjacentHTML('afterbegin', 
            `<div style="background: #ffebee; color: #c62828; padding: 10px; margin: 10px;">
                Error loading data centers: ${error.message}
            </div>`
        );
    });