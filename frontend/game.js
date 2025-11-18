// ============================================
// SPACE CONQUEST - GAME CONTROLLER
// Handles game state, rendering, and interactions
// ============================================

class GameController {
    constructor() {
        // Canvas and rendering
        this.canvas = document.getElementById('starMap');
        this.ctx = this.canvas.getContext('2d');
        this.scale = 1;
        this.offset = { x: 0, y: 0 };
        this.selectedStar = null;
        this.hoveredStar = null;

        // Tooltip for hover
        this.tooltip = document.getElementById('starTooltip');

        // API configuration
        this.apiBase = window.location.origin + '/api';
        this.gameId = null;
        this.websocket = null;

        // Parse URL parameters for debug mode
        const urlParams = new URLSearchParams(window.location.search);
        this.debugMode = urlParams.get('fog') === 'false';

        // Game state (will be populated from backend)
        this.gameState = {
            turn: 1,
            phase: 'ORDERS',
            currentPlayer: 'p1',
            stars: [],
            fleets: [],
            orders: [],
            events: []
        };

        // Event indicators (battles and rebellions)
        this.eventIndicators = [];

        // Initialize
        this.initializeEventListeners();
        this.promptGameCreation();
        this.render();
        this.startAnimationLoop();
    }

    // ============================================
    // INITIALIZATION
    // ============================================

    initializeEventListeners() {
        // Canvas interactions
        this.canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleCanvasHover(e));
        this.canvas.addEventListener('mouseleave', () => this.hideTooltip());

        // Mouse wheel zoom
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
            this.zoom(zoomFactor);
        }, { passive: false });

        // Terminal input
        const terminalInput = document.getElementById('terminalInput');
        if (terminalInput) {
            terminalInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    this.handleCommand(e.target.value);
                    e.target.value = '';
                }
            });
        } else {
            console.error('Terminal input element not found');
        }

        // Control buttons
        document.getElementById('zoomIn').addEventListener('click', () => this.zoom(1.2));
        document.getElementById('zoomOut').addEventListener('click', () => this.zoom(0.8));
        document.getElementById('centerView').addEventListener('click', () => this.centerView());

        // Order management
        document.getElementById('clearOrders').addEventListener('click', () => this.clearOrders());
        document.getElementById('submitTurn').addEventListener('click', () => this.submitTurn());

        // Event log
        document.getElementById('closeEventLog').addEventListener('click', () => {
            document.getElementById('eventLog').classList.add('hidden');
        });

        // Table row clicks
        document.addEventListener('click', (e) => {
            const row = e.target.closest('tbody tr');
            if (row && row.dataset.starId) {
                this.selectStarById(row.dataset.starId);
            }
        });
    }

    // ============================================
    // API INTEGRATION
    // ============================================

    async promptGameCreation() {
        this.addTerminalLine('>> INITIALIZING GAME CREATION INTERFACE', 'system');

        // Check if game ID is in URL
        const urlParams = new URLSearchParams(window.location.search);
        const gameIdFromUrl = urlParams.get('gameId');

        if (gameIdFromUrl) {
            this.addTerminalLine(`>> LOADING EXISTING GAME: ${gameIdFromUrl}`, 'system');
            this.gameId = gameIdFromUrl;
            await this.loadGameState();
            this.connectWebSocket();
        } else {
            this.addTerminalLine('>> CREATING NEW GAME VS AI', 'system');
            await this.createNewGame();
        }
    }

    async createNewGame() {
        try {
            const response = await fetch(`${this.apiBase}/games`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    humanPlayer: 'p1',
                    aiProvider: 'bedrock'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.gameId = data.gameId;
            this.gameState.currentPlayer = data.humanPlayer;

            // Update URL with game ID
            const url = new URL(window.location);
            url.searchParams.set('gameId', this.gameId);
            window.history.pushState({}, '', url);

            this.addTerminalLine(`>> GAME CREATED: ${this.gameId}`, 'success');
            this.addTerminalLine(`>> YOU ARE PLAYER ${data.humanPlayer.toUpperCase()}`, 'success');
            this.addTerminalLine(`>> AI IS PLAYER ${data.aiPlayer.toUpperCase()}`, 'system');

            this.loadStateFromResponse(data.state);
            this.connectWebSocket();

        } catch (error) {
            this.addTerminalLine(`ERROR: Failed to create game - ${error.message}`, 'error');
            console.error('Create game error:', error);
        }
    }

    async loadGameState() {
        try {
            // Add debug parameter if in debug mode
            const url = this.debugMode
                ? `${this.apiBase}/games/${this.gameId}/state?debug=true`
                : `${this.apiBase}/games/${this.gameId}/state`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.loadStateFromResponse(data.state);

            if (data.events) {
                this.displayEvents(data.events);
            }

            this.addTerminalLine('>> GAME STATE LOADED', 'success');

        } catch (error) {
            this.addTerminalLine(`ERROR: Failed to load game - ${error.message}`, 'error');
            console.error('Load game error:', error);
        }
    }

    loadStateFromResponse(state) {
        // Convert API response format to internal format
        this.gameState.turn = state.turn;
        this.gameState.phase = state.phase;

        // Scale star coordinates from game grid (0-11, 0-9) to canvas pixels (800x800)
        // Game uses integer coordinates, we need to map them to pixel positions
        const gridWidth = 12;   // 0-11 inclusive
        const gridHeight = 10;  // 0-9 inclusive
        const canvasWidth = 800;
        const canvasHeight = 800;

        const cellWidth = canvasWidth / gridWidth;   // 66.67 pixels per grid cell
        const cellHeight = canvasHeight / gridHeight; // 80 pixels per grid cell

        this.gameState.stars = state.stars.map(s => ({
            ...s,
            // Store original grid coordinates for display
            gridX: s.x,
            gridY: s.y,
            // Calculate canvas pixel positions (centered in grid cell)
            x: (s.x + 0.5) * cellWidth,
            y: (s.y + 0.5) * cellHeight,
            owner: s.owner === 'p1' ? 1 : s.owner === 'p2' ? 2 : null
        }));

        this.gameState.fleets = state.fleets.map(f => ({
            ...f,
            owner: f.owner === 'p1' ? 1 : 2,
            from: f.origin,
            to: f.dest
        }));

        this.updateUI();
    }

    connectWebSocket() {
        // Add debug parameter if in debug mode
        const debugParam = this.debugMode ? '?debug=true' : '';
        const wsUrl = `ws://${window.location.host}/ws/games/${this.gameId}${debugParam}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            this.addTerminalLine('>> REAL-TIME CONNECTION ESTABLISHED', 'success');
            if (this.debugMode) {
                this.addTerminalLine('>> DEBUG MODE: FOG-OF-WAR DISABLED', 'warning');
            }
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onerror = (error) => {
            this.addTerminalLine('>> WEBSOCKET ERROR', 'error');
            console.error('WebSocket error:', error);
        };

        this.websocket.onclose = () => {
            this.addTerminalLine('>> REAL-TIME CONNECTION CLOSED', 'warning');
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'CONNECTED':
                this.loadStateFromResponse(data.state);
                break;

            case 'AI_THINKING':
                this.gameState.phase = 'AI_THINKING';
                document.getElementById('phaseIndicator').textContent = 'AI THINKING';
                this.updateTelemetryIndicators();
                this.addTerminalLine('>> AI OPPONENT IS CALCULATING STRATEGY...', 'warning');
                break;

            case 'TURN_EXECUTED':
                this.addTerminalLine(`>> TURN ${data.turn} EXECUTED`, 'success');
                this.loadStateFromResponse(data.state);
                this.displayEvents(data.events);

                if (data.winner) {
                    this.handleGameOver(data.winner);
                }
                break;

            case 'GAME_OVER':
                this.handleGameOver(data.winner);
                break;

            case 'PONG':
                // Heartbeat response
                break;
        }
    }

    displayEvents(events) {
        // Clear previous event indicators
        this.eventIndicators = [];

        if (events.combat && events.combat.length > 0) {
            this.addTerminalLine(`>> ${events.combat.length} COMBAT EVENT(S) OCCURRED`, 'warning');
            this.showEventLog(events);

            // Add combat indicators
            events.combat.forEach(combat => {
                const starId = combat.star_id || combat.starId;
                if (starId) {
                    this.eventIndicators.push({
                        starId,
                        type: 'combat',
                        startTime: Date.now(),
                        duration: 5000 // 5 seconds
                    });
                }
            });
        }

        if (events.rebellions && events.rebellions.length > 0) {
            this.addTerminalLine(`>> ${events.rebellions.length} REBELLION(S) OCCURRED`, 'warning');

            // Add rebellion indicators
            events.rebellions.forEach(rebellion => {
                const starId = rebellion.starId || rebellion.star_id;
                if (starId) {
                    this.eventIndicators.push({
                        starId,
                        type: 'rebellion',
                        startTime: Date.now(),
                        duration: 5000 // 5 seconds
                    });
                }
            });
        }

        if (events.hyperspaceLosses && events.hyperspaceLosses.length > 0) {
            this.addTerminalLine(`>> ${events.hyperspaceLosses.length} FLEET(S) LOST IN HYPERSPACE`, 'error');
        }
    }

    handleGameOver(winner) {
        this.gameState.phase = 'COMPLETED';
        const winnerDisplay = winner === 'p1' ? 'PLAYER 1' : winner === 'p2' ? 'PLAYER 2' : winner.toUpperCase();

        this.addTerminalLine('', 'system');
        this.addTerminalLine('='.repeat(50), 'success');
        this.addTerminalLine(`GAME OVER - ${winnerDisplay} WINS!`, 'success');
        this.addTerminalLine('='.repeat(50), 'success');

        document.getElementById('phaseIndicator').textContent = 'GAME OVER';
    }

    // ============================================
    // RENDERING
    // ============================================

    render() {
        const ctx = this.ctx;
        const { width, height } = this.canvas;

        // Clear canvas
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, width, height);

        // Save context and apply transformations
        ctx.save();

        // Apply zoom and pan transformations
        ctx.translate(this.offset.x, this.offset.y);
        ctx.scale(this.scale, this.scale);

        // Draw grid
        this.drawGrid();

        // Draw connections (fleets in transit)
        this.drawFleetPaths();

        // Draw stars
        this.gameState.stars.forEach(star => this.drawStar(star));

        // Draw event indicators (battles and rebellions)
        this.drawEventIndicators();

        // Draw hover indicator
        if (this.hoveredStar) {
            this.drawHoverIndicator(this.hoveredStar);
        }

        // Draw selection indicator
        if (this.selectedStar) {
            this.drawSelectionIndicator(this.selectedStar);
        }

        // Restore context
        ctx.restore();
    }

    drawGrid() {
        const ctx = this.ctx;
        const { width, height } = this.canvas;
        const gridSize = 50;

        ctx.strokeStyle = 'rgba(255, 176, 0, 0.08)';
        ctx.lineWidth = 1;

        // Vertical lines
        for (let x = 0; x < width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }

        // Horizontal lines
        for (let y = 0; y < height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
    }

    drawFleetPaths() {
        const ctx = this.ctx;

        this.gameState.fleets.forEach(fleet => {
            const fromStar = this.gameState.stars.find(s => s.id === fleet.from);
            const toStar = this.gameState.stars.find(s => s.id === fleet.to);

            if (!fromStar || !toStar) return;

            const color = fleet.owner === 1 ? '#00ff88' : '#ff3366';

            // Draw dashed line
            ctx.strokeStyle = color + '44';
            ctx.lineWidth = 2;
            ctx.setLineDash([10, 5]);
            ctx.beginPath();
            ctx.moveTo(fromStar.x, fromStar.y);
            ctx.lineTo(toStar.x, toStar.y);
            ctx.stroke();
            ctx.setLineDash([]);

            // Draw fleet indicator (moving dot)
            const progress = 0.5; // This would be calculated based on eta
            const fleetX = fromStar.x + (toStar.x - fromStar.x) * progress;
            const fleetY = fromStar.y + (toStar.y - fromStar.y) * progress;

            ctx.fillStyle = color;
            ctx.shadowColor = color;
            ctx.shadowBlur = 15;
            ctx.beginPath();
            ctx.arc(fleetX, fleetY, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        });
    }

    drawStar(star) {
        const ctx = this.ctx;
        const { x, y } = star;

        // Determine color based on owner
        let color;
        if (star.owner === 1) color = '#00ff88';
        else if (star.owner === 2) color = '#ff3366';
        else color = '#666666';

        // Draw star glow
        ctx.shadowColor = color;
        ctx.shadowBlur = 20;

        // Draw star circle
        const radius = star.isHome ? 16 : 12;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fill();

        // Reset shadow
        ctx.shadowBlur = 0;

        // Draw inner circle for home stars
        if (star.isHome) {
            ctx.fillStyle = '#0a0a0a';
            ctx.beginPath();
            ctx.arc(x, y, 8, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fill();
        }

        // Draw star name
        ctx.fillStyle = '#ffb000';
        ctx.font = '12px "Share Tech Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(star.id, x, y - radius - 8);

        // Draw ship count
        if (star.ships > 0) {
            ctx.fillStyle = '#ffd966';
            ctx.font = 'bold 11px "Share Tech Mono", monospace';
            ctx.fillText(star.ships.toString(), x, y + radius + 18);
        }
    }

    drawHoverIndicator(star) {
        const ctx = this.ctx;
        const radius = star.isHome ? 20 : 16;

        ctx.strokeStyle = '#ffb000';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(star.x, star.y, radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    drawSelectionIndicator(star) {
        const ctx = this.ctx;
        const radius = star.isHome ? 24 : 20;
        const time = Date.now() / 1000;
        const pulse = Math.sin(time * 3) * 0.5 + 0.5;

        ctx.strokeStyle = `rgba(255, 176, 0, ${0.5 + pulse * 0.5})`;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(star.x, star.y, radius + pulse * 4, 0, Math.PI * 2);
        ctx.stroke();
    }

    drawEventIndicators() {
        const ctx = this.ctx;
        const currentTime = Date.now();

        // Remove expired indicators
        this.eventIndicators = this.eventIndicators.filter(indicator => {
            return (currentTime - indicator.startTime) < indicator.duration;
        });

        // Draw active indicators
        this.eventIndicators.forEach(indicator => {
            const star = this.gameState.stars.find(s => s.id === indicator.starId);
            if (!star) return;

            const elapsed = currentTime - indicator.startTime;
            const progress = elapsed / indicator.duration;
            const alpha = 1 - progress; // Fade out over time

            if (indicator.type === 'combat') {
                // Combat: Flashing red ring
                const time = Date.now() / 200;
                const flash = Math.sin(time * Math.PI) > 0 ? 1 : 0.3;
                const radius = star.isHome ? 30 : 26;

                ctx.strokeStyle = `rgba(255, 51, 102, ${alpha * flash})`;
                ctx.lineWidth = 4;
                ctx.beginPath();
                ctx.arc(star.x, star.y, radius, 0, Math.PI * 2);
                ctx.stroke();

                // Inner pulsing circle
                const pulseRadius = radius - 6;
                ctx.strokeStyle = `rgba(255, 51, 102, ${alpha * 0.5 * flash})`;
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(star.x, star.y, pulseRadius, 0, Math.PI * 2);
                ctx.stroke();

            } else if (indicator.type === 'rebellion') {
                // Rebellion: Pulsing amber ring
                const time = Date.now() / 1000;
                const pulse = Math.sin(time * 4) * 0.5 + 0.5;
                const radius = star.isHome ? 28 : 24;

                ctx.strokeStyle = `rgba(255, 176, 0, ${alpha * (0.6 + pulse * 0.4)})`;
                ctx.lineWidth = 3;
                ctx.setLineDash([8, 4]);
                ctx.beginPath();
                ctx.arc(star.x, star.y, radius + pulse * 3, 0, Math.PI * 2);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        });
    }

    startAnimationLoop() {
        const animate = () => {
            this.render();
            requestAnimationFrame(animate);
        };
        animate();
    }

    // ============================================
    // INTERACTION HANDLERS
    // ============================================

    handleCanvasClick(e) {
        const rect = this.canvas.getBoundingClientRect();

        // Scale mouse coordinates from display size to canvas logical size
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        const canvasX = (e.clientX - rect.left) * scaleX;
        const canvasY = (e.clientY - rect.top) * scaleY;

        // Apply inverse transformations to get world coordinates
        const x = (canvasX - this.offset.x) / this.scale;
        const y = (canvasY - this.offset.y) / this.scale;

        // Find clicked star
        const clickedStar = this.gameState.stars.find(star => {
            const dx = star.x - x;
            const dy = star.y - y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            return distance < (star.isHome ? 20 : 16);
        });

        if (clickedStar) {
            this.selectStar(clickedStar);
        } else {
            this.deselectStar();
        }
    }

    handleCanvasHover(e) {
        const rect = this.canvas.getBoundingClientRect();

        // Scale mouse coordinates from display size to canvas logical size
        const scaleX = this.canvas.width / rect.width;
        const scaleY = this.canvas.height / rect.height;

        const canvasX = (e.clientX - rect.left) * scaleX;
        const canvasY = (e.clientY - rect.top) * scaleY;

        // Apply inverse transformations to get world coordinates
        const x = (canvasX - this.offset.x) / this.scale;
        const y = (canvasY - this.offset.y) / this.scale;

        // Find hovered star
        const hoveredStar = this.gameState.stars.find(star => {
            const dx = star.x - x;
            const dy = star.y - y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            return distance < (star.isHome ? 20 : 16);
        });

        this.hoveredStar = hoveredStar || null;
        this.canvas.style.cursor = hoveredStar ? 'pointer' : 'crosshair';

        // Update tooltip
        if (hoveredStar) {
            this.showTooltip(hoveredStar, e.clientX, e.clientY);
        } else {
            this.hideTooltip();
        }
    }

    showTooltip(star, mouseX, mouseY) {
        const isUnvisited = star.visited === false;

        // Build tooltip content
        let content = `<div class="tooltip-title">${isUnvisited ? 'UNKNOWN SECTOR' : star.name}</div>`;
        content += `<div class="tooltip-row"><span class="tooltip-label">COORDS:</span> ${star.gridX}, ${star.gridY}</div>`;

        if (isUnvisited) {
            // Fog-of-war: limited info
            content += `<div class="tooltip-row"><span class="tooltip-label">STATUS:</span> OUT OF SENSOR RANGE</div>`;
            content += `<div class="tooltip-row"><span class="tooltip-label">INTEL:</span> UNCHARTED</div>`;
        } else {
            // Full intel
            const ownerText = star.owner ? `PLAYER ${star.owner}` : 'NEUTRAL';
            content += `<div class="tooltip-row"><span class="tooltip-label">OWNER:</span> ${ownerText}</div>`;
            content += `<div class="tooltip-row"><span class="tooltip-label">SHIPS:</span> ${star.ships}</div>`;
            content += `<div class="tooltip-row"><span class="tooltip-label">PRODUCTION:</span> ${star.baseRU} RU/TURN</div>`;
            content += `<div class="tooltip-row"><span class="tooltip-label">TYPE:</span> ${star.isHome ? 'HOME STAR' : 'STANDARD'}</div>`;
        }

        this.tooltip.innerHTML = content;
        this.tooltip.classList.remove('hidden');

        // Position tooltip near mouse, but keep it on screen
        const tooltipRect = this.tooltip.getBoundingClientRect();
        let left = mouseX + 15;
        let top = mouseY + 15;

        // Adjust if tooltip would go off-screen
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = mouseX - tooltipRect.width - 15;
        }
        if (top + tooltipRect.height > window.innerHeight - 10) {
            top = mouseY - tooltipRect.height - 15;
        }

        this.tooltip.style.left = `${left}px`;
        this.tooltip.style.top = `${top}px`;
    }

    hideTooltip() {
        this.tooltip.classList.add('hidden');
    }

    selectStar(star) {
        this.selectedStar = star;
        // Star details are now shown via tooltip on hover
        // Selection is used for visual indicator on the map
    }

    selectStarById(starId) {
        const star = this.gameState.stars.find(s => s.id === starId);
        if (star) this.selectStar(star);
    }

    deselectStar() {
        this.selectedStar = null;
    }

    zoom(factor) {
        const oldScale = this.scale;
        this.scale *= factor;
        this.scale = Math.max(0.5, Math.min(3, this.scale));

        // Zoom towards center of canvas
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;

        // Adjust offset to keep center point stable
        const scaleDiff = this.scale - oldScale;
        this.offset.x -= (centerX - this.offset.x) * (scaleDiff / oldScale);
        this.offset.y -= (centerY - this.offset.y) * (scaleDiff / oldScale);
    }

    centerView() {
        // Reset zoom to 1x and center the map
        this.scale = 1;
        this.offset = { x: 0, y: 0 };
    }

    // ============================================
    // COMMAND HANDLING
    // ============================================

    handleCommand(input) {
        const command = input.trim().toUpperCase();

        console.log('handleCommand called with:', input);

        if (!command) return;

        // Add to terminal
        this.addTerminalLine(`> ${command}`, 'user');

        // Parse command
        if (command === 'HELP') {
            this.showHelp();
        } else if (command === 'LIST') {
            this.listOrders();
        } else if (command === 'STATUS') {
            this.showStatus();
        } else if (command === 'DONE') {
            this.submitTurn();
        } else if (command.startsWith('MOVE')) {
            this.parseMovementOrder(command);
        } else {
            this.addTerminalLine('UNKNOWN COMMAND. TYPE "HELP" FOR AVAILABLE COMMANDS.', 'error');
        }
    }

    parseMovementOrder(command) {
        // Example: MOVE 10 FROM A TO B
        const regex = /MOVE\s+(\d+)\s+(?:FROM\s+)?(\w+)\s+(?:TO\s+)?(\w+)/i;
        const match = command.match(regex);

        if (!match) {
            this.addTerminalLine('INVALID SYNTAX. USE: MOVE <ships> FROM <star> TO <star>', 'error');
            return;
        }

        const ships = parseInt(match[1]);
        const fromId = match[2].toUpperCase();
        const toId = match[3].toUpperCase();

        // Validate stars exist
        const fromStar = this.gameState.stars.find(s => s.id === fromId);
        const toStar = this.gameState.stars.find(s => s.id === toId);

        if (!fromStar) {
            this.addTerminalLine(`STAR "${fromId}" NOT FOUND.`, 'error');
            return;
        }

        if (!toStar) {
            this.addTerminalLine(`STAR "${toId}" NOT FOUND.`, 'error');
            return;
        }

        // Validate ownership (convert currentPlayer string to number for comparison)
        const myPlayerNum = this.gameState.currentPlayer === 'p1' ? 1 : 2;
        if (fromStar.owner !== myPlayerNum) {
            this.addTerminalLine(`YOU DO NOT CONTROL STAR "${fromId}".`, 'error');
            return;
        }

        // Validate ship count
        if (ships > fromStar.ships) {
            this.addTerminalLine(`INSUFFICIENT SHIPS AT "${fromId}". AVAILABLE: ${fromStar.ships}`, 'error');
            return;
        }

        // Add order
        this.addOrder({
            type: 'MOVE',
            ships,
            from: fromId,
            to: toId
        });

        this.addTerminalLine(`ORDER QUEUED: ${ships} SHIPS FROM ${fromId} TO ${toId}`, 'success');
    }

    addOrder(order) {
        this.gameState.orders.push(order);
        this.updateOrdersList();
    }

    clearOrders() {
        this.gameState.orders = [];
        this.updateOrdersList();
        this.addTerminalLine('ALL ORDERS CLEARED.', 'warning');
    }

    removeOrder(index) {
        this.gameState.orders.splice(index, 1);
        this.updateOrdersList();
    }

    async submitTurn() {
        console.log('submitTurn called, orders:', this.gameState.orders);

        if (this.gameState.orders.length === 0) {
            this.addTerminalLine('NO ORDERS TO SUBMIT. ORDERS REQUIRED TO END TURN.', 'warning');
            return;
        }

        if (!this.gameId) {
            this.addTerminalLine('ERROR: No active game session', 'error');
            return;
        }

        this.addTerminalLine(`SUBMITTING ${this.gameState.orders.length} ORDER(S)...`, 'system');

        try {
            const response = await fetch(`${this.apiBase}/games/${this.gameId}/orders`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    orders: this.gameState.orders
                })
            });

            const data = await response.json();

            if (!response.ok || !data.accepted) {
                this.addTerminalLine('ORDER SUBMISSION FAILED:', 'error');
                data.errors.forEach(err => {
                    this.addTerminalLine(`  - ${err}`, 'error');
                });
                return;
            }

            this.addTerminalLine('ORDERS ACCEPTED. AWAITING AI RESPONSE...', 'success');

            // Clear local orders queue
            this.gameState.orders = [];
            this.updateOrdersList();

            // Turn execution will be handled via WebSocket

        } catch (error) {
            this.addTerminalLine(`ERROR: ${error.message}`, 'error');
            console.error('Submit orders error:', error);
        }
    }

    showHelp() {
        const helpText = [
            'AVAILABLE COMMANDS:',
            '  MOVE <ships> FROM <star> TO <star> - QUEUE FLEET MOVEMENT',
            '  LIST - SHOW QUEUED ORDERS',
            '  STATUS - DISPLAY GAME STATUS',
            '  DONE - SUBMIT TURN',
            '  HELP - SHOW THIS MESSAGE'
        ];
        helpText.forEach(line => this.addTerminalLine(line, 'system'));
    }

    listOrders() {
        if (this.gameState.orders.length === 0) {
            this.addTerminalLine('NO ORDERS QUEUED.', 'system');
            return;
        }

        this.addTerminalLine('QUEUED ORDERS:', 'system');
        this.gameState.orders.forEach((order, i) => {
            this.addTerminalLine(`  ${i + 1}. MOVE ${order.ships} FROM ${order.from} TO ${order.to}`, 'system');
        });
    }

    showStatus() {
        // Convert currentPlayer (p1/p2) to number (1/2) for comparison
        const myPlayerNum = this.gameState.currentPlayer === 'p1' ? 1 : 2;
        const myStars = this.gameState.stars.filter(s => s.owner === myPlayerNum);
        const totalShips = myStars.reduce((sum, s) => sum + s.ships, 0);

        const statusLines = [
            `TURN: ${this.gameState.turn}`,
            `CONTROLLED STARS: ${myStars.length}`,
            `TOTAL SHIPS: ${totalShips}`,
            `QUEUED ORDERS: ${this.gameState.orders.length}`
        ];

        statusLines.forEach(line => this.addTerminalLine(line, 'system'));
    }

    // ============================================
    // UI UPDATES
    // ============================================

    updateUI() {
        // Update header
        document.getElementById('turnNumber').textContent = this.gameState.turn.toString().padStart(3, '0');
        document.getElementById('phaseIndicator').textContent = this.gameState.phase;

        // Update RX/TX indicators based on phase
        this.updateTelemetryIndicators();

        // Update tables
        this.updateControlledStarsTable();
        this.updateFleetsTable();
        this.updateOrdersList();
    }

    updateTelemetryIndicators() {
        const rxIndicator = document.getElementById('rxIndicator');
        const txIndicator = document.getElementById('txIndicator');

        console.log('Updating telemetry indicators, phase:', this.gameState.phase);

        // RX blinks when receiving (AI thinking)
        // TX blinks when transmitting (awaiting human orders)
        if (this.gameState.phase === 'AI_THINKING') {
            console.log('Setting RX to blink');
            rxIndicator.classList.add('blink');
            txIndicator.classList.remove('blink');
        } else if (this.gameState.phase === 'AWAITING_ORDERS' || this.gameState.phase === 'ORDERS') {
            console.log('Setting TX to blink');
            rxIndicator.classList.remove('blink');
            txIndicator.classList.add('blink');
        } else {
            console.log('Phase is:', this.gameState.phase, '- neither blinks');
            // Game over or other states - neither blinks
            rxIndicator.classList.remove('blink');
            txIndicator.classList.remove('blink');
        }
    }


    updateControlledStarsTable() {
        const tbody = document.querySelector('#controlledStarsTable tbody');
        // Convert currentPlayer (p1/p2) to number (1/2) for comparison
        const myPlayerNum = this.gameState.currentPlayer === 'p1' ? 1 : 2;
        const myStars = this.gameState.stars.filter(s => s.owner === myPlayerNum);

        tbody.innerHTML = myStars.map(star => `
            <tr data-star-id="${star.id}">
                <td>${star.name} (${star.id})</td>
                <td>${star.ships}</td>
                <td>${star.baseRU}</td>
                <td>${star.isHome ? 'HOME' : 'HELD'}</td>
            </tr>
        `).join('');
    }

    updateFleetsTable() {
        const tbody = document.querySelector('#fleetsTable tbody');
        // Convert currentPlayer (p1/p2) to number (1/2) for comparison
        const myPlayerNum = this.gameState.currentPlayer === 'p1' ? 1 : 2;
        const myFleets = this.gameState.fleets.filter(f => f.owner === myPlayerNum);

        if (myFleets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--color-text-dim);">NO FLEETS IN TRANSIT</td></tr>';
            return;
        }

        tbody.innerHTML = myFleets.map(fleet => `
            <tr>
                <td>${fleet.from}</td>
                <td>${fleet.to}</td>
                <td>${fleet.ships}</td>
                <td>${fleet.eta} TURN${fleet.eta !== 1 ? 'S' : ''}</td>
            </tr>
        `).join('');
    }

    updateOrdersList() {
        const container = document.getElementById('ordersList');

        if (this.gameState.orders.length === 0) {
            container.innerHTML = '<div class="no-orders"><p>// NO ORDERS QUEUED</p></div>';
            return;
        }

        container.innerHTML = this.gameState.orders.map((order, i) => `
            <div class="order-item">
                <span class="order-text">
                    ${order.ships} SHIPS: ${order.from} → ${order.to}
                </span>
                <button class="remove-order-btn" onclick="game.removeOrder(${i})">×</button>
            </div>
        `).join('');
    }

    addTerminalLine(text, type = 'system') {
        const output = document.getElementById('terminalOutput');
        const line = document.createElement('div');
        line.className = `terminal-line ${type}`;

        if (type !== 'user') {
            const prompt = document.createElement('span');
            prompt.className = 'prompt';
            prompt.textContent = '>>';
            line.appendChild(prompt);
        }

        const textNode = document.createTextNode(` ${text}`);
        line.appendChild(textNode);

        output.appendChild(line);
        output.scrollTop = output.scrollHeight;

        // Limit terminal history
        while (output.children.length > 100) {
            output.removeChild(output.firstChild);
        }
    }

    showEventLog(events) {
        const eventLog = document.getElementById('eventLog');
        const content = document.getElementById('eventLogContent');

        let html = '';

        // Combat events
        if (events.combat) {
            const myPlayerNum = this.gameState.currentPlayer === 'p1' ? 1 : 2;

            events.combat.forEach(combat => {
                // Determine if this involves the human player
                const isPlayerInvolved = combat.attacker === this.gameState.currentPlayer ||
                                        combat.defender === this.gameState.currentPlayer;

                // Determine display names based on perspective
                let attackerDisplay, defenderDisplay, winnerDisplay;

                if (combat.attacker === 'npc') {
                    attackerDisplay = 'NPC FORCES';
                } else if (combat.attacker === this.gameState.currentPlayer) {
                    attackerDisplay = 'YOUR FORCES';
                } else {
                    attackerDisplay = 'ENEMY FORCES';
                }

                if (combat.defender === 'npc') {
                    defenderDisplay = 'NPC DEFENDERS';
                } else if (combat.defender === this.gameState.currentPlayer) {
                    defenderDisplay = 'YOUR FORCES';
                } else {
                    defenderDisplay = 'ENEMY FORCES';
                }

                // Winner display
                if (combat.winner === 'attacker') {
                    winnerDisplay = attackerDisplay;
                } else if (combat.winner === 'defender') {
                    winnerDisplay = defenderDisplay;
                } else {
                    winnerDisplay = 'MUTUAL DESTRUCTION';
                }

                // Choose color based on outcome for player
                let eventClass = 'combat';
                if (isPlayerInvolved) {
                    // Green if player won, red if player lost
                    const playerWon = (combat.winner === 'attacker' && combat.attacker === this.gameState.currentPlayer) ||
                                     (combat.winner === 'defender' && combat.defender === this.gameState.currentPlayer);
                    eventClass = playerWon ? 'combat-victory' : 'combat-defeat';
                }

                html += `
                    <div class="event-item ${eventClass}">
                        <strong>COMBAT AT ${combat.star_name || combat.starName || 'UNKNOWN'}</strong><br>
                        ${attackerDisplay} (${combat.attacker_ships || 0} SHIPS) VS ${defenderDisplay} (${combat.defender_ships || 0} SHIPS)<br>
                        RESULT: ${winnerDisplay}<br>
                        SURVIVORS: ${combat.winner === 'attacker' ? (combat.attacker_survivors || 0) : (combat.defender_survivors || 0)} SHIPS
                    </div>
                `;
            });
        }

        // Rebellion events
        if (events.rebellions) {
            events.rebellions.forEach(rebellion => {
                html += `
                    <div class="event-item">
                        <strong>REBELLION AT ${rebellion.starName}</strong><br>
                        GARRISON (${rebellion.garrisonBefore}) VS REBELS (${rebellion.rebelShips})<br>
                        RESULT: ${rebellion.outcome.toUpperCase()}<br>
                        GARRISON REMAINING: ${rebellion.garrisonAfter}
                    </div>
                `;
            });
        }

        // Hyperspace losses
        if (events.hyperspaceLosses) {
            events.hyperspaceLosses.forEach(loss => {
                html += `
                    <div class="event-item error">
                        <strong>FLEET LOST IN HYPERSPACE</strong><br>
                        ${loss.ships} SHIPS LOST EN ROUTE FROM ${loss.origin} TO ${loss.dest}
                    </div>
                `;
            });
        }

        content.innerHTML = html || '<p>No events this turn.</p>';
        eventLog.classList.remove('hidden');
    }
}

// Initialize game when page loads
let game;
window.addEventListener('DOMContentLoaded', () => {
    game = new GameController();
});
