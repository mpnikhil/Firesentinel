// MapBox access token
const mapboxToken = 'pk.eyJ1IjoiYWdoYXRhZ2UiLCJhIjoiY203eWQ1ZnFwMDkyaTJtb290ZGliczcxMiJ9.0hsxL2cPXOtNyPhb1p3a1A';

// San Francisco coordinates (center of the city)
const sfCoordinates = {
    lng: -122.4194,
    lat: 37.7749
};

// Initialize the map
document.addEventListener('DOMContentLoaded', () => {
    mapboxgl.accessToken = mapboxToken;
    
    const map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/dark-v11', // Dark style for the map
        center: [sfCoordinates.lng, sfCoordinates.lat],
        zoom: 12
    });

    // Add navigation controls (zoom in/out)
    map.addControl(new mapboxgl.NavigationControl(), 'top-left');

    // Keep track of drawn circles
    let drawnCircles = [];
    
    // Wildfire simulation variables
    let drawingMode = false;
    let simulationActive = false;
    let firePoints = [];
    let fuelModelData = null;

    // Get DOM elements
    const addressInput = document.getElementById('address-input');
    const submitBtn = document.getElementById('submit-address');
    const statusMessage = document.getElementById('status-message');
    const mapOverlay = document.getElementById('map-overlay');

    // Add map loading event
    map.on('load', () => {
        console.log('Map loaded successfully');
        initializeAddressSearch();
        initializeWildfireSimulation();
        loadFuelModelLayer();
    });

    // Add error handling
    map.on('error', (e) => {
        console.error('Map error:', e);
    });

    // Initialize address search functionality
    function initializeAddressSearch() {
        // Handle button click
        submitBtn.addEventListener('click', searchAddress);
        
        // Handle enter key press
        addressInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchAddress();
            }
        });
    }

    // Search for an address and place a marker
    async function searchAddress() {
        const address = addressInput.value.trim();
        
        if (!address) {
            setStatusMessage('Please enter an address', 'error');
            return;
        }

        setStatusMessage('Searching...', 'info');

        try {
            // Add "San Francisco" to the search if not already included
            let searchQuery = address;
            if (!address.toLowerCase().includes('san francisco')) {
                searchQuery += ', San Francisco, CA';
            }

            // Use Mapbox Geocoding API
            const response = await fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(searchQuery)}.json?access_token=${mapboxToken}&limit=1`);
            const data = await response.json();

            if (data.features && data.features.length > 0) {
                const location = data.features[0];
                const coordinates = location.center; // [longitude, latitude]
                
                // Draw circle at the location
                drawCircleAtLocation(coordinates);
                
                // Fly to the location
                map.flyTo({
                    center: coordinates,
                    zoom: 15,
                    speed: 1.5
                });

                setStatusMessage(`Found: ${location.place_name}`, 'success');
            } else {
                setStatusMessage('Address not found. Try being more specific.', 'error');
            }
        } catch (error) {
            console.error('Error searching address:', error);
            setStatusMessage('Error searching address. Please try again.', 'error');
        }
    }

    // Draw a circle at the specified location
    function drawCircleAtLocation(coordinates) {
        // Clear any previously drawn circles first
        clearDrawnCircles();
        
        // Create a circle element
        const circle = document.createElement('div');
        circle.className = 'location-circle';
        circle.style.position = 'absolute';
        circle.style.width = '20px';
        circle.style.height = '20px';
        circle.style.backgroundColor = 'rgba(76, 175, 80, 0.6)';
        circle.style.border = '2px solid #4CAF50';
        circle.style.borderRadius = '50%';
        circle.style.transform = 'translate(-50%, -50%)';
        circle.style.zIndex = '100';
        
        // Add pulse animation
        circle.style.boxShadow = '0 0 0 rgba(76, 175, 80, 0.4)';
        circle.style.animation = 'pulse 2s infinite';

        // Add the circle to the overlay
        mapOverlay.appendChild(circle);
        
        // Store reference to the circle for later removal
        drawnCircles.push(circle);
        
        // Position the circle correctly using map's project method
        positionCircle(circle, coordinates);
        
        // Update circle position when map moves
        map.on('move', () => {
            positionCircle(circle, coordinates);
        });

        // Add CSS for the pulse animation if it doesn't exist yet
        if (!document.getElementById('circle-animation-style')) {
            const style = document.createElement('style');
            style.id = 'circle-animation-style';
            style.innerHTML = `
                @keyframes pulse {
                    0% {
                        box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4);
                    }
                    70% {
                        box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
                    }
                    100% {
                        box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Position the circle at the correct pixel coordinates
    function positionCircle(circle, coordinates) {
        const pixels = map.project(coordinates);
        circle.style.left = `${pixels.x}px`;
        circle.style.top = `${pixels.y}px`;
    }

    // Clear all drawn circles
    function clearDrawnCircles() {
        drawnCircles.forEach(circle => {
            if (circle.parentNode) {
                circle.parentNode.removeChild(circle);
            }
        });
        drawnCircles = [];
    }

    // Set status message with appropriate styling
    function setStatusMessage(message, type = 'info') {
        statusMessage.textContent = message;
        
        // Reset classes
        statusMessage.className = '';
        
        // Add appropriate class
        switch (type) {
            case 'error':
                statusMessage.style.color = '#ff6b6b';
                break;
            case 'success':
                statusMessage.style.color = '#4CAF50';
                break;
            default:
                statusMessage.style.color = '#ccc';
        }
    }

    // Load the fuel model layer from LANDFIRE data
    function loadFuelModelLayer() {
        try {
            // Use Mapbox's land cover data
            map.addSource('fuel-models', {
                type: 'vector',
                url: 'mapbox://mapbox.mapbox-land-cover-v4'
            });
            
            // Add a fill layer using the land cover data
            map.addLayer({
                id: 'fuel-model-layer',
                type: 'fill',
                source: 'fuel-models',
                'source-layer': 'land-cover',
                paint: {
                    'fill-color': [
                        'match',
                        ['get', 'class'],
                        0, '#ffffbe', // No data
                        1, '#ffff00', // Water
                        2, '#4CAF50', // Trees
                        3, '#8BC34A', // Grass
                        4, '#CDDC39', // Crops
                        5, '#FFEB3B', // Shrub/Scrub
                        6, '#FFC107', // Built area
                        7, '#FF9800', // Bare
                        8, '#FF5722', // Snow/Ice
                        9, '#795548', // Clouds
                        10, '#9E9E9E', // Rangeland
                        /* other */ '#FFFFFF'
                    ],
                    'fill-opacity': 0.7
                }
            }, 'waterway-label'); // Insert below labels
            
            // Set the map view to Northern California
            map.fitBounds([
                [-124.5, 37.0], // Southwest coordinates
                [-119.0, 42.0]  // Northeast coordinates
            ]);
            
            // Load the fuel model data (this would be asynchronous in a real implementation)
            loadFuelModelData();
            
            // Create and populate the legend
            createFuelModelLegend();
        } catch (error) {
            console.error('Error loading fuel model layer:', error);
            // Fallback to static data for demo
            loadFuelModelData();
        }
    }
    
    // Load the fuel model data based on Mapbox land cover classification
    function loadFuelModelData() {
        // Mapbox land cover classification with informative descriptions
        fuelModelData = {
            0: { 
                name: 'No Data', 
                color: '#ffffbe', 
                burnRate: 0.1, 
                description: 'Areas with no classified land cover data' 
            },
            1: { 
                name: 'Water', 
                color: '#0077FF', 
                burnRate: 0, 
                description: 'Lakes, rivers, oceans - non-burnable' 
            },
            2: { 
                name: 'Trees', 
                color: '#4CAF50', 
                burnRate: 0.4, 
                description: 'Dense forest with moderate burn rate' 
            },
            3: { 
                name: 'Grass', 
                color: '#8BC34A', 
                burnRate: 0.8, 
                description: 'Open grasslands - fast burning, high spread' 
            },
            4: { 
                name: 'Crops', 
                color: '#CDDC39', 
                burnRate: 0.5, 
                description: 'Agricultural lands with medium fire risk' 
            },
            5: { 
                name: 'Shrub', 
                color: '#FFEB3B', 
                burnRate: 0.7, 
                description: 'Shrublands with high intensity burns' 
            },
            6: { 
                name: 'Built', 
                color: '#FF5722', 
                burnRate: 0.1, 
                description: 'Urban areas with limited vegetation' 
            },
            7: { 
                name: 'Bare', 
                color: '#795548', 
                burnRate: 0.05, 
                description: 'Bare soil, rock - minimal fuel for fire' 
            },
            8: { 
                name: 'Snow/Ice', 
                color: '#FFFFFF', 
                burnRate: 0, 
                description: 'Permanent snow/ice cover - non-burnable' 
            },
            9: { 
                name: 'Clouds', 
                color: '#9E9E9E', 
                burnRate: 0, 
                description: 'Data obscured by cloud cover' 
            },
            10: { 
                name: 'Rangeland', 
                color: '#FFA726', 
                burnRate: 0.6, 
                description: 'Mixed grass/shrubs with moderate fire risk' 
            }
        };
        
        console.log('Fuel model data loaded');
    }
    
    // Create and populate the legend
    function createFuelModelLegend() {
        const legendContainer = document.getElementById('fuel-legend');
        
        // Clear any existing legend
        legendContainer.innerHTML = '';
        
        // Add a title for the legend
        const legendTitle = document.createElement('div');
        legendTitle.className = 'legend-title';
        legendTitle.textContent = 'Land Cover Types and Fire Risk';
        legendTitle.style.fontWeight = 'bold';
        legendTitle.style.marginBottom = '8px';
        legendContainer.appendChild(legendTitle);
        
        // Sort by burn rate (fire risk) - highest to lowest
        const sortedEntries = Object.entries(fuelModelData).sort((a, b) => {
            return b[1].burnRate - a[1].burnRate;
        });
        
        // Add legend items for each fuel model
        for (const [value, data] of sortedEntries) {
            // Skip cloud and no data categories to save space
            if (value == 9 || value == 0) continue;
            
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';
            
            const colorSwatch = document.createElement('div');
            colorSwatch.className = 'legend-color';
            colorSwatch.style.backgroundColor = data.color;
            
            const label = document.createElement('div');
            label.className = 'legend-label';
            
            const name = document.createElement('span');
            name.textContent = data.name;
            name.style.fontWeight = 'bold';
            
            const description = document.createElement('span');
            description.textContent = ` - ${data.description}`;
            description.style.fontSize = '0.9em';
            
            label.appendChild(name);
            label.appendChild(description);
            
            legendItem.appendChild(colorSwatch);
            legendItem.appendChild(label);
            legendContainer.appendChild(legendItem);
        }
    }
    
    // Initialize the wildfire simulation controls and events
    function initializeWildfireSimulation() {
        // Get control elements
        const drawPointBtn = document.getElementById('draw-point-btn');
        const startSimulationBtn = document.getElementById('start-simulation-btn');
        const resetSimulationBtn = document.getElementById('reset-simulation-btn');
        const simulationData = document.getElementById('simulation-data');
        
        // Event listener for draw point button
        drawPointBtn.addEventListener('click', () => {
            drawingMode = !drawingMode;
            
            // Toggle button active state
            if (drawingMode) {
                drawPointBtn.classList.add('active');
                setStatusMessage('Click on the map to place a fire ignition point', 'info');
            } else {
                drawPointBtn.classList.remove('active');
                setStatusMessage('Drawing mode disabled', 'info');
            }
        });
        
        // Event listener for map click to place fire point
        map.on('click', (e) => {
            if (!drawingMode) return;
            
            // Get clicked coordinates
            const coordinates = [e.lngLat.lng, e.lngLat.lat];
            
            // Clear existing fire points
            clearFirePoints();
            
            // Add new fire point
            addFirePoint(coordinates);
            
            // Disable drawing mode
            drawingMode = false;
            drawPointBtn.classList.remove('active');
            
            // Enable start simulation button
            startSimulationBtn.disabled = false;
            
            setStatusMessage('Fire point placed. Click "Start Simulation" to begin.', 'success');
        });
        
        // Event listener for start simulation button
        startSimulationBtn.addEventListener('click', () => {
            if (firePoints.length === 0) {
                setStatusMessage('Place a fire point first', 'error');
                return;
            }
            
            // Start the wildfire simulation
            startWildfireSimulation();
            
            // Disable start button during simulation
            startSimulationBtn.disabled = true;
        });
        
        // Event listener for reset simulation button
        resetSimulationBtn.addEventListener('click', () => {
            // Reset the simulation
            resetWildfireSimulation();
            
            // Enable draw point mode
            drawingMode = false;
            drawPointBtn.classList.remove('active');
            
            // Disable start simulation button until new point is drawn
            startSimulationBtn.disabled = true;
            
            setStatusMessage('Simulation reset', 'info');
        });
    }
    
    // Add a fire point to the map
    function addFirePoint(coordinates) {
        // Create a fire point element
        const point = document.createElement('div');
        point.className = 'fire-point';
        point.style.position = 'absolute';
        point.style.width = '12px';
        point.style.height = '12px';
        point.style.backgroundColor = 'red';
        point.style.borderRadius = '50%';
        point.style.border = '2px solid rgba(255, 255, 255, 0.8)';
        point.style.transform = 'translate(-50%, -50%)';
        point.style.boxShadow = '0 0 10px rgba(255, 0, 0, 0.8)';
        point.style.zIndex = '100';
        
        // Add the point to the map overlay
        mapOverlay.appendChild(point);
        
        // Position the point
        const pixels = map.project(coordinates);
        point.style.left = `${pixels.x}px`;
        point.style.top = `${pixels.y}px`;
        
        // Store the fire point data
        firePoints.push({
            element: point,
            coordinates: coordinates
        });
        
        // Update point position on map move
        map.on('move', () => {
            const updatedPixels = map.project(coordinates);
            point.style.left = `${updatedPixels.x}px`;
            point.style.top = `${updatedPixels.y}px`;
        });
    }
    
    // Clear all fire points
    function clearFirePoints() {
        // Remove points from the DOM
        firePoints.forEach(point => {
            if (point.element && point.element.parentNode) {
                point.element.parentNode.removeChild(point.element);
            }
        });
        
        // Clear the array
        firePoints = [];
    }
    
    // Start the wildfire simulation
    function startWildfireSimulation() {
        // Set simulation active flag
        simulationActive = true;
        
        // Update UI
        document.getElementById('simulation-data').innerHTML = `
            <p>Simulation active</p>
            <p>Time elapsed: <span id="sim-time">0</span> minutes</p>
            <p>Area burned: <span id="area-burned">0</span> hectares</p>
            <p>Fire intensity: <span id="fire-intensity">Low</span></p>
        `;
        
        setStatusMessage('Wildfire simulation in progress...', 'info');
        
        // Get starting point
        const startPoint = firePoints[0].coordinates;
        
        // Determine fuel model at ignition point
        const fuelType = simulateFuelModelAt(startPoint[0], startPoint[1]);
        
        // Create an initial marker for the fire point
        const fireMarker = document.createElement('div');
        fireMarker.className = 'fire-point-marker';
        fireMarker.style.position = 'absolute';
        fireMarker.style.borderRadius = '50%';
        fireMarker.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
        fireMarker.style.width = '10px';
        fireMarker.style.height = '10px';
        fireMarker.style.transform = 'translate(-50%, -50%)';
        fireMarker.style.zIndex = '100';
        fireMarker.style.boxShadow = '0 0 8px rgba(255, 0, 0, 0.8)';
        
        // Add the marker to the map overlay
        mapOverlay.appendChild(fireMarker);
        
        // Position the marker at the starting point
        const pixels = map.project(startPoint);
        fireMarker.style.left = `${pixels.x}px`;
        fireMarker.style.top = `${pixels.y}px`;
        
        // Update marker position on map move
        map.on('move', () => {
            const updatedPixels = map.project(startPoint);
            fireMarker.style.left = `${updatedPixels.x}px`;
            fireMarker.style.top = `${updatedPixels.y}px`;
        });
        
        // Calculated burned area
        let burnedAreaSize = 1;
        
        // Growth rates based on fuel types (meters per minute)
        const growthRates = {
            0: 0.5,  // No Data
            1: 0,    // Water
            2: 1.0,  // Trees
            3: 2.0,  // Grass
            4: 1.5,  // Crops
            5: 1.8,  // Shrub
            6: 0.3,  // Built/Urban
            7: 0.2,  // Bare
            8: 0,    // Snow/Ice
            9: 0,    // Clouds
            10: 1.7  // Rangeland
        };
        
        // Base growth rate (meters per minute)
        const baseGrowthRate = growthRates[fuelType] || 1.0;
        
        // Simulation time counter
        let simTime = 0;
        let fireRadius = 7.5; // Starting radius in pixels
        
        const timeElement = document.getElementById('sim-time');
        const areaElement = document.getElementById('area-burned');
        const intensityElement = document.getElementById('fire-intensity');
        
        // Run simulation steps
        const simulationInterval = setInterval(() => {
            if (!simulationActive) {
                clearInterval(simulationInterval);
                return;
            }
            
            // Update simulation time
            simTime += 5;
            timeElement.textContent = simTime.toString();
            
            // Calculate current fire spread radius based on time and growth rate
            // Each minute, fire spreads by growthRate meters
            const metersSpread = baseGrowthRate * simTime;
            
            // Get the current zoom level to adjust pixel scaling
            const zoom = map.getZoom();
            const pixelsPerMeter = Math.pow(2, zoom) / 156543.03392; // Rough conversion at equator
            
            // Calculate current radius in pixels for spot placement
            fireRadius = metersSpread * pixelsPerMeter;
            
            // Calculate burned area (in square meters, convert to hectares)
            const areaInMeters = Math.PI * Math.pow(metersSpread, 2);
            const areaInHectares = (areaInMeters / 10000).toFixed(2);
            burnedAreaSize = areaInHectares;
            areaElement.textContent = areaInHectares;
            
            // Create multiple fire spots growing outward
            // Create more spots for faster burning fuels
            const spotsToCreate = fuelType === 3 ? 6 : // More for grass
                               fuelType === 5 ? 4 : // Medium for shrub
                               fuelType === 2 ? 3 : // Trees
                               2; // Default for others
                                
            // Only create spots if not on water and if there's room to grow
            if (fuelType !== 1 && fireRadius > 0) {
                for (let i = 0; i < spotsToCreate; i++) {
                    createFireSpot(startPoint, fireRadius, fuelType);
                }
            }
            
            // Update fire intensity based on size and add color coding
            let intensity = 'Low';
            let intensityColor = '#FFC107'; // Yellow/orange for low
            let fireOpacity = 0.4;
            
            if (burnedAreaSize > 1) {
                intensity = 'Moderate';
                intensityColor = '#FF9800'; // Orange for moderate
                fireOpacity = 0.5;
            }
            if (burnedAreaSize > 5) {
                intensity = 'High';
                intensityColor = '#FF5722'; // Deep orange for high
                fireOpacity = 0.6;
            }
            if (burnedAreaSize > 15) {
                intensity = 'Extreme';
                intensityColor = '#F44336'; // Red for extreme
                fireOpacity = 0.7;
            }
            
            // No need to update main fire appearance since we removed it
            
            intensityElement.textContent = intensity;
            intensityElement.style.color = intensityColor;
            
            // End simulation after reaching max time or area
            if (simTime >= 180 || burnedAreaSize >= 50) {
                clearInterval(simulationInterval);
                simulationActive = false;
                setStatusMessage('Simulation complete', 'success');
            }
        }, 1500); // Run every 1.5 seconds
    }
    
    // Create a fire spot growing outward from the ignition point
    function createFireSpot(centerPoint, maxRadius, fuelType) {
        // Random angle around the center point
        const angle = Math.random() * Math.PI * 2;
        
        // Get a random distance from center, within the maximum radius
        // Use different distributions based on fuel type
        let minDistanceFactor, maxDistanceFactor;
        
        switch(fuelType) {
            case 3: // Grass - more uniform distribution
                minDistanceFactor = 0.1;
                maxDistanceFactor = 1.0;
                break;
            case 5: // Shrub - more clumped
                minDistanceFactor = 0.2;
                maxDistanceFactor = 0.8;
                break;
            case 2: // Trees - more concentrated
                minDistanceFactor = 0.3;
                maxDistanceFactor = 0.7;
                break;
            default:
                minDistanceFactor = 0.2;
                maxDistanceFactor = 0.9;
        }
        
        const minDistance = maxRadius * minDistanceFactor;
        const maxDistance = maxRadius * maxDistanceFactor;
        const distance = minDistance + (Math.random() * (maxDistance - minDistance));
        
        // Calculate the position in pixels
        const pixelX = Math.cos(angle) * distance;
        const pixelY = Math.sin(angle) * distance;
        
        // Get current center in pixels
        const centerPixels = map.project(centerPoint);
        
        // Calculate new position in pixels
        const newX = centerPixels.x + pixelX;
        const newY = centerPixels.y + pixelY;
        
        // Convert back to coordinates
        const newPos = map.unproject([newX, newY]);
        
        // Size based on fuel type
        let spotSize;
        let growRate;
        
        switch(fuelType) {
            case 3: // Grass - larger, faster growing
                spotSize = 8 + Math.random() * 7; // 8-15px
                growRate = 1.5;
                break;
            case 5: // Shrub
                spotSize = 7 + Math.random() * 6; // 7-13px
                growRate = 1.2;
                break;
            case 2: // Trees
                spotSize = 6 + Math.random() * 5; // 6-11px
                growRate = 0.8;
                break;
            default:
                spotSize = 5 + Math.random() * 5; // 5-10px
                growRate = 1.0;
        }
        
        // Create fire spot element
        const spot = document.createElement('div');
        spot.className = 'fire-ember';
        spot.style.position = 'absolute';
        spot.style.width = `${spotSize}px`;
        spot.style.height = `${spotSize}px`;
        spot.style.backgroundColor = 'rgba(255, 78, 0, 0.5)';
        spot.style.borderRadius = '50%';
        spot.style.boxShadow = '0 0 10px rgba(255, 50, 0, 0.4)';
        spot.style.transform = 'translate(-50%, -50%)';
        spot.style.zIndex = '94';
        spot.style.left = `${newX}px`;
        spot.style.top = `${newY}px`;
        
        // Add to map
        mapOverlay.appendChild(spot);
        
        // Fade in immediately
        spot.style.opacity = '0.7';
        
        // Update position on map move
        map.on('move', () => {
            const updatedPixels = map.project(newPos);
            spot.style.left = `${updatedPixels.x}px`;
            spot.style.top = `${updatedPixels.y}px`;
        });
        
        // Always grow the spots gradually
        let growth = 0;
        const maxGrowth = 30 + (Math.random() * 20); // 30-50px max
        
        const growInterval = setInterval(() => {
            if (!simulationActive) {
                clearInterval(growInterval);
                return;
            }
            
            growth += growRate;
            spot.style.width = `${spotSize + growth}px`;
            spot.style.height = `${spotSize + growth}px`;
            
            // Stop growing after reaching max size
            if (growth > maxGrowth) {
                clearInterval(growInterval);
            }
        }, 1000); // Grow every second
    }
    
    // Create a new fire cell at the given coordinates
    function createFireCell(coordinates, delay = 0, fuelType = 3) {
        // Create a fire cell element
        const cell = document.createElement('div');
        cell.className = 'fire-cell';
        cell.style.position = 'absolute';
        
        // Base size depending on fuel type - grass fires are larger, forest fires are smaller but more intense
        let baseSize;
        let opacity;
        
        // Adjust size and opacity based on fuel type
        switch(fuelType) {
            case 1: // Water - no fire
                baseSize = 5;
                opacity = 0.1;
                break;
            case 2: // Trees - intense smaller fire
                baseSize = 20;
                opacity = 0.7;
                break;
            case 3: // Grass - large fast fire
                baseSize = 30;
                opacity = 0.5;
                break;
            case 4: // Crops - medium fire
                baseSize = 25;
                opacity = 0.5;
                break;
            case 5: // Shrub - intense medium fire
                baseSize = 25;
                opacity = 0.6;
                break;
            case 6: // Built/Urban - small fire
                baseSize = 15;
                opacity = 0.4;
                break;
            default: // Default medium fire
                baseSize = 20;
                opacity = 0.5;
        }
        
        // Set initial small size that will grow
        cell.style.width = '5px';
        cell.style.height = '5px';
        cell.style.opacity = '0';
        
        // Add to overlay first to start transition
        mapOverlay.appendChild(cell);
        
        // Add delayed growth effect
        setTimeout(() => {
            cell.style.opacity = opacity.toString();
            cell.style.width = `${baseSize}px`;
            cell.style.height = `${baseSize}px`;
        }, delay);
        
        // Position the cell
        const pixels = map.project(coordinates);
        cell.style.left = `${pixels.x}px`;
        cell.style.top = `${pixels.y}px`;
        
        // Update cell position on map move
        map.on('move', () => {
            const updatedPixels = map.project(coordinates);
            cell.style.left = `${updatedPixels.x}px`;
            cell.style.top = `${updatedPixels.y}px`;
        });
        
        // Return cell data
        return {
            element: cell,
            coordinates: coordinates,
            fuelType: fuelType
        };
    }
    
    // Expand the fire based on fuel models and spread patterns
    function expandFire(fireCells, burnedArea, gridSize) {
        // Number of new cells to add in this iteration - reduced for slower spread
        const newCellCount = Math.floor(Math.random() * 3) + 2;
        
        // Directions for spread (8 directions)
        const directions = [
            [1, 0], [1, 1], [0, 1], [-1, 1],
            [-1, 0], [-1, -1], [0, -1], [1, -1]
        ];
        
        // Iterate through each existing cell and potentially spread
        for (let i = 0; i < newCellCount; i++) {
            // Select a random existing fire cell as the source
            if (fireCells.length === 0) break;
            const sourceIndex = Math.floor(Math.random() * fireCells.length);
            const sourceCell = fireCells[sourceIndex];
            
            // Select a random direction
            const dirIndex = Math.floor(Math.random() * directions.length);
            const direction = directions[dirIndex];
            
            // Calculate the new cell coordinates with some variation
            // Reduced distance for slower spread
            const jitter = (Math.random() - 0.5) * gridSize * 0.3;
            const newLng = sourceCell.coordinates[0] + (direction[0] * gridSize / 2000) + (jitter / 2000);
            const newLat = sourceCell.coordinates[1] + (direction[1] * gridSize / 2000) + (jitter / 2000);
            
            // Check if the cell is already burned
            const cellKey = `${newLng.toFixed(6)},${newLat.toFixed(6)}`;
            if (burnedArea.has(cellKey)) continue;
            
            // Determine fuel model at this location
            const fuelType = simulateFuelModelAt(newLng, newLat);
            
            // Skip if water
            if (fuelType === 1) continue;
            
            // Adjust spread probability based on fuel type
            const spreadProbability = getFuelSpreadProbability(fuelType);
            if (Math.random() > spreadProbability) continue;
            
            // Create larger delay for more natural movement
            const delayFactor = Math.random() * 200 + 100;
            
            // Add the new cell with a delay based on position and fuel type
            const newCell = createFireCell([newLng, newLat], i * delayFactor, fuelType);
            fireCells.push(newCell);
            burnedArea.add(cellKey);
        }
    }
    
    // Determine the fuel model at a specific location
    function simulateFuelModelAt(lng, lat) {
        // In a real implementation, this would query the actual raster data from the map
        // For this demo, we'll simulate different land cover types based on location
        
        // Urban areas (approximate major cities in California)
        // Sacramento
        if (lng > -121.55 && lng < -121.40 && lat > 38.50 && lat < 38.65) {
            return 6; // Built/Urban
        }
        
        // Bay Area urban
        if (lng > -122.30 && lng < -122.20 && lat > 37.80 && lat < 37.90) {
            return 6; // Built/Urban
        }
        
        // SF downtown
        if (lng > -122.43 && lng < -122.38 && lat > 37.76 && lat < 37.80) {
            return 6; // Built/Urban
        }
        
        // Forested areas (Sierra Nevada)
        if (lng > -121.0 && lng < -119.5 && lat > 38.0 && lat < 40.0) {
            return 2; // Trees
        }
        
        // Water bodies
        // SF Bay
        if (lng > -122.50 && lng < -122.15 && lat > 37.5 && lat < 38.0) {
            return 1; // Water
        }
        
        // Lake Tahoe
        if (lng > -120.20 && lng < -119.95 && lat > 38.90 && lat < 39.25) {
            return 1; // Water
        }
        
        // Grassland (Central Valley)
        if (lng > -122.0 && lng < -121.0 && lat > 37.0 && lat < 39.0) {
            return 3; // Grass
        }
        
        // Shrubland (coastal ranges)
        if (lng > -122.8 && lng < -122.0 && lat > 37.8 && lat < 39.5) {
            return 5; // Shrub
        }
        
        // Agricultural (Central Valley)
        if (lng > -121.8 && lng < -121.0 && lat > 36.5 && lat < 39.5) {
            return 4; // Crops
        }
        
        // Default to a mix of vegetation types for other areas
        const models = [2, 3, 5, 10]; // Trees, Grass, Shrub, Rangeland
        return models[Math.floor(Math.random() * models.length)];
    }
    
    // Get spread probability based on land cover type
    function getFuelSpreadProbability(fuelType) {
        if (fuelModelData && fuelModelData[fuelType]) {
            return fuelModelData[fuelType].burnRate;
        }
        
        // Default values if land cover data not available
        const defaultRates = {
            0: 0.1,  // No Data
            1: 0,    // Water
            2: 0.4,  // Trees
            3: 0.8,  // Grass
            4: 0.5,  // Crops
            5: 0.7,  // Shrub
            6: 0.1,  // Built/Urban
            7: 0.05, // Bare
            8: 0,    // Snow/Ice
            9: 0,    // Clouds
            10: 0.6  // Rangeland
        };
        
        return defaultRates[fuelType] || 0.5;
    }
    
    // Reset the wildfire simulation
    function resetWildfireSimulation() {
        // Stop active simulation
        simulationActive = false;
        
        // Clear all fire points
        clearFirePoints();
        
        // Clear all fire elements
        const fireElements = mapOverlay.querySelectorAll('.fire-cell, .main-fire, .fire-ember, .fire-point-marker');
        fireElements.forEach(element => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });
        
        // Reset simulation data display
        document.getElementById('simulation-data').innerHTML = '<p>No active simulation</p>';
    }
}); 