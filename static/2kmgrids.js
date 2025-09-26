/* global L */

(function () {
  // Initialize map with standard WGS84 coordinates
  const map = L.map("map", {
    center: [61.0, 25.0], // Center of Finland
    zoom: 6,
    maxZoom: 12,
    minZoom: 4
  });

  // Add base layer
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let gridLayer = null;
  let currentDataset = null;
  let db = null;

  // Grid configuration - 2km rigid grid system
  // Use a reference latitude for consistent grid calculations
  const REFERENCE_LATITUDE = 61.0; // Finland's approximate center latitude
  
  // Calculate fixed grid sizes based on reference latitude
  const GRID_SIZE_LAT_DEGREES = 0.018; // 2km in latitude degrees (constant)
  const GRID_SIZE_LON_DEGREES = (() => {
    // Calculate longitude grid size at reference latitude
    const longitudeKmPerDegree = 111 * Math.cos(REFERENCE_LATITUDE * Math.PI / 180);
    return 2 / longitudeKmPerDegree; // 2km in longitude degrees at reference latitude
  })();
  
  // Grid origin - define a reference point for the grid
  const GRID_ORIGIN_LAT = 60.0; // Grid starts at this latitude
  const GRID_ORIGIN_LON = 20.0; // Grid starts at this longitude

  const els = {
    status: document.getElementById("status"),
  };

  // Initialize IndexedDB (reuse from heatmap)
  function initDB() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('BioToolsDatasets', 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        db = request.result;
        resolve();
      };
      
      request.onupgradeneeded = (event) => {
        const database = event.target.result;
        if (!database.objectStoreNames.contains('datasets')) {
          const store = database.createObjectStore('datasets', { keyPath: 'id' });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('url', 'url', { unique: false });
          store.createIndex('hash', 'hash', { unique: false });
        }
      };
    });
  }

  // Get dataset ID from URL parameters
  function getDatasetId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('id');
  }

  // Load dataset from IndexedDB
  async function loadDataset(datasetId) {
    try {
      const transaction = db.transaction(['datasets'], 'readonly');
      const store = transaction.objectStore('datasets');
      const request = store.get(datasetId);
      
      return new Promise((resolve) => {
        request.onsuccess = () => {
          resolve(request.result || null);
        };
        request.onerror = () => {
          resolve(null);
        };
      });
    } catch (error) {
      console.error('Error loading dataset:', error);
      return null;
    }
  }

  // Extract WGS84 coordinates from dataset results
  function extractWGS84Coordinates(dataset) {
    const points = [];
    
    if (!dataset || !dataset.data || !dataset.data.results) {
      return points;
    }
    
    console.log(`Processing ${dataset.data.results.length} results for WGS84 coordinates`);
    
    dataset.data.results.forEach((result, index) => {
      try {
        // Check if the result has WGS84 coordinates
        const gathering = result.gathering;
        if (gathering && gathering.conversions && gathering.conversions.wgs84CenterPoint) {
          const lat = gathering.conversions.wgs84CenterPoint.lat;
          const lon = gathering.conversions.wgs84CenterPoint.lon;
          
          if (lat && lon && !isNaN(lat) && !isNaN(lon)) {
            const point = {
              lat: parseFloat(lat),
              lon: parseFloat(lon),
              weight: result.gathering?.interpretations?.individualCount || 1
            };
            
            // Log first few points for debugging
            if (index < 5) {
              console.log(`Point ${index}:`, point);
            }
            
            points.push(point);
          }
        }
      } catch (error) {
        // Skip problematic records
        console.warn('Skipping record due to error:', error);
      }
    });
    
    console.log(`Extracted ${points.length} valid WGS84 coordinates`);
    return points;
  }

  // Calculate which 2km grid squares contain points
  function calculateGridSquares(points) {
    const gridSquares = new Map();
    
    console.log(`Processing ${points.length} points for rigid 2km grid calculation`);
    console.log(`Grid size: ${GRID_SIZE_LAT_DEGREES}° lat × ${GRID_SIZE_LON_DEGREES.toFixed(6)}° lon`);
    
    points.forEach((point, index) => {
      // Validate point coordinates
      if (!point.lat || !point.lon || isNaN(point.lat) || isNaN(point.lon)) {
        console.warn(`Invalid point at index ${index}:`, point);
        return;
      }
      
      // Calculate which grid square this point belongs to using rigid grid
      // Calculate grid indices relative to the grid origin
      const latIndex = Math.floor((point.lat - GRID_ORIGIN_LAT) / GRID_SIZE_LAT_DEGREES);
      const lonIndex = Math.floor((point.lon - GRID_ORIGIN_LON) / GRID_SIZE_LON_DEGREES);
      
      // Calculate actual grid square coordinates
      const gridLat = GRID_ORIGIN_LAT + latIndex * GRID_SIZE_LAT_DEGREES;
      const gridLon = GRID_ORIGIN_LON + lonIndex * GRID_SIZE_LON_DEGREES;
      
      // Create grid square bounds
      const bounds = [
        [gridLat, gridLon], // Southwest corner
        [gridLat + GRID_SIZE_LAT_DEGREES, gridLon + GRID_SIZE_LON_DEGREES] // Northeast corner
      ];
      
      const key = `${latIndex},${lonIndex}`; // Use indices as key for consistency
      
      if (!gridSquares.has(key)) {
        gridSquares.set(key, {
          bounds: bounds,
          count: 0,
          totalWeight: 0,
          gridLat: gridLat,
          gridLon: gridLon,
          latIndex: latIndex,
          lonIndex: lonIndex
        });
      }
      
      const square = gridSquares.get(key);
      square.count++;
      square.totalWeight += point.weight;
    });
    
    const result = Array.from(gridSquares.values());
    console.log(`Created ${result.length} rigid grid squares with data`);
    return result;
  }

  // Create or update grid visualization
  function createOrUpdateGrid(gridSquares) {
    // Remove existing grid layer
    if (gridLayer) {
      map.removeLayer(gridLayer);
    }
    
    if (gridSquares.length === 0) {
      console.log('No grid squares to display');
      return;
    }

    console.log(`Creating ${gridSquares.length} grid squares`);
    
    // Create new layer group for grid squares
    gridLayer = L.layerGroup();
    
    // Calculate color scale based on record count
    const maxCount = Math.max(...gridSquares.map(sq => sq.count));
    const minCount = Math.min(...gridSquares.map(sq => sq.count));
    
    console.log(`Record count range: ${minCount} - ${maxCount}`);
    
    gridSquares.forEach((square, index) => {
      // Log first few squares for debugging
      if (index < 3) {
        const latSizeKm = GRID_SIZE_LAT_DEGREES * 111;
        const lonSizeKm = GRID_SIZE_LON_DEGREES * 111 * Math.cos(REFERENCE_LATITUDE * Math.PI / 180);
        console.log(`Square ${index}:`, {
          bounds: square.bounds,
          count: square.count,
          gridLat: square.gridLat,
          gridLon: square.gridLon,
          latIndex: square.latIndex,
          lonIndex: square.lonIndex,
          actualSizeKm: `${latSizeKm.toFixed(2)}km × ${lonSizeKm.toFixed(2)}km`
        });
      }
      
      // Calculate color intensity based on record count
      const intensity = maxCount > minCount ? 
        (square.count - minCount) / (maxCount - minCount) : 0.5;
      
      // Create color from blue (low) to red (high)
      const red = Math.floor(intensity * 255);
      const blue = Math.floor((1 - intensity) * 255);
      const color = `rgb(${red}, 0, ${blue})`;
      
      // Create rectangle for this grid square
      const rectangle = L.rectangle(square.bounds, {
        color: '#000000',  // Black border for visibility
        weight: 1,         // Border weight
        fillColor: color,
        fillOpacity: 0.6   // Semi-transparent
      });
      
      // Add popup with information
      rectangle.bindPopup(`
        <strong>2km Grid Square</strong><br>
        Records: ${square.count}<br>
        Total Weight: ${square.totalWeight.toFixed(1)}<br>
        Grid Index: (${square.latIndex}, ${square.lonIndex})<br>
        Grid Center: ${(square.gridLat + GRID_SIZE_LAT_DEGREES/2).toFixed(6)}, ${(square.gridLon + GRID_SIZE_LON_DEGREES/2).toFixed(6)}<br>
        Grid Size: ${(GRID_SIZE_LAT_DEGREES * 111).toFixed(1)}km × ${(GRID_SIZE_LON_DEGREES * 111 * Math.cos(REFERENCE_LATITUDE * Math.PI / 180)).toFixed(1)}km
      `);
      
      gridLayer.addLayer(rectangle);
    });
    
    // Add grid layer to map
    gridLayer.addTo(map);
    
    // Fit map to show all grid squares
    try {
      const group = new L.featureGroup(gridLayer.getLayers());
      const bounds = group.getBounds();
      
      if (bounds && bounds.isValid()) {
        const paddedBounds = bounds.pad(0.1);
        map.fitBounds(paddedBounds, { maxZoom: 10 });
      } else {
        // Fallback: set a reasonable view of Finland
        map.setView([61.0, 25.0], 6);
      }
    } catch (error) {
      console.warn('Error fitting bounds:', error);
      map.setView([61.0, 25.0], 6);
    }
  }

  function setStatus(message, type) {
    els.status.textContent = message;
    els.status.className = "stats" + (type ? " " + type : "");
  }

  // Load dataset and initialize grid visualization
  async function loadDatasetAndInitialize() {
    try {
      const datasetId = getDatasetId();
      if (!datasetId) {
        setStatus('No dataset ID provided. Please select a dataset from the Simple Parser page.', 'error');
        return;
      }

      setStatus('Loading dataset...', 'loading');

      const dataset = await loadDataset(datasetId);
      if (!dataset) {
        setStatus('Dataset not found.', 'error');
        return;
      }

      currentDataset = dataset;
      const points = extractWGS84Coordinates(dataset);
      
      if (points.length === 0) {
        setStatus('No WGS84 coordinates found in this dataset.', 'error');
        return;
      }

      setStatus(`Loaded ${points.length} points from dataset.`, 'ok');
      
      const gridSquares = calculateGridSquares(points);
      setStatus(`Found ${gridSquares.length} grid squares with data.`, 'ok');
      
      createOrUpdateGrid(gridSquares);

    } catch (error) {
      console.error('Error loading dataset:', error);
      setStatus(`Error: ${error.message}`, 'error');
    }
  }

  // Initialize the app
  document.addEventListener('DOMContentLoaded', async function() {
    try {
      await initDB();
      await loadDatasetAndInitialize();
    } catch (error) {
      console.error('Failed to initialize app:', error);
      setStatus('Failed to initialize database', 'error');
    }
  });
})();
