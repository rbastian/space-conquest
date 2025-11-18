# Space Conquest - Frontend Interface

A retro-futuristic tactical command interface for the Space Conquest game, inspired by 1980s military command terminals and sci-fi interfaces.

## Design Concept

**Aesthetic**: Retro-futuristic Military Command Terminal
- Monochromatic amber CRT aesthetic with scan lines and glow effects
- Brutalist typography using geometric sans (Orbitron) and monospace (Share Tech Mono)
- Grid-based tactical star map with vector graphics
- Data-dense information panels with a militaristic feel
- Subtle glitch effects and screen flicker for authenticity

## Files

- `index.html` - Main game interface structure
- `styles.css` - Complete styling with CRT effects and animations
- `game.js` - Game controller, rendering, and interaction logic
- `README.md` - This file

## Features

### Current Implementation (Frontend Demo)

1. **Star Map Canvas**
   - Interactive tactical map showing stars and their positions
   - Visual indicators for player ownership (green = Player 1, red = Player 2, gray = Neutral)
   - Home stars shown with distinctive double-circle design
   - Fleet paths shown as animated dashed lines
   - Click stars to view details, hover for highlight effect

2. **Information Panels**
   - **Tactical Data**: Shows selected star details, controlled stars table, and fleets in transit
   - **Command Terminal**: Text-based command input with syntax highlighting
   - **Orders Queue**: Visual list of queued movement orders with remove buttons

3. **Command System**
   Available commands:
   - `MOVE <ships> FROM <star> TO <star>` - Queue fleet movement
   - `LIST` - Show queued orders
   - `STATUS` - Display game status
   - `DONE` - Submit turn
   - `HELP` - Show available commands

4. **Visual Effects**
   - CRT screen overlay with scan lines
   - Animated glowing text effects
   - Pulsing selection indicators
   - Smooth transitions and hover states
   - Tactical grid background

## Quick Start (Demo Mode)

Simply open `index.html` in a modern web browser to see the interface with mock data.

```bash
# From the frontend directory
open index.html  # macOS
xdg-open index.html  # Linux
start index.html  # Windows
```

Or use a simple HTTP server:

```bash
python -m http.server 8000
# Then visit http://localhost:8000
```

## Backend Integration Plan

### API Requirements

The frontend expects the following API endpoints:

#### 1. Get Game State
```
GET /api/game/{game_id}/state
Response: {
  turn: number,
  phase: string,
  currentPlayer: number,
  stars: [
    {
      id: string,
      name: string,
      x: number,
      y: number,
      owner: number | null,
      ships: number,
      baseRU: number,
      isHome: boolean
    }
  ],
  fleets: [
    {
      id: number,
      owner: number,
      ships: number,
      from: string,
      to: string,
      eta: number
    }
  ],
  events: [
    {
      type: string,
      description: string,
      timestamp: number
    }
  ]
}
```

#### 2. Submit Orders
```
POST /api/game/{game_id}/orders
Body: {
  orders: [
    {
      type: "MOVE",
      ships: number,
      from: string,
      to: string
    }
  ]
}
Response: {
  success: boolean,
  errors: string[]
}
```

#### 3. WebSocket Updates (Optional but Recommended)
```
WS /ws/game/{game_id}

Messages:
- TURN_UPDATE: New turn state
- COMBAT_REPORT: Combat events
- GAME_OVER: Victory/defeat notification
```

### Integration Points in game.js

The following methods need to be connected to your backend:

1. **`loadMockGameState()`** (line ~80)
   - Replace with API call to fetch current game state
   - Update `this.gameState` with server response

2. **`submitTurn()`** (line ~435)
   - Add API call to POST orders to backend
   - Handle server validation errors
   - Update game state with response

3. **Add WebSocket listener** for real-time updates
   ```javascript
   connectWebSocket() {
     const ws = new WebSocket('ws://localhost:8000/ws/game/123');
     ws.onmessage = (event) => {
       const data = JSON.parse(event.data);
       if (data.type === 'TURN_UPDATE') {
         this.gameState = data.state;
         this.updateUI();
       }
     };
   }
   ```

### Python Backend Example (FastAPI)

```python
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

class Order(BaseModel):
    type: str
    ships: int
    from_star: str = Field(alias="from")
    to_star: str = Field(alias="to")

@app.get("/api/game/{game_id}/state")
async def get_game_state(game_id: str):
    # Query your game engine
    return {
        "turn": game.current_turn,
        "phase": game.phase,
        "currentPlayer": game.current_player,
        "stars": [star.to_dict() for star in game.stars],
        "fleets": [fleet.to_dict() for fleet in game.fleets],
        "events": game.recent_events
    }

@app.post("/api/game/{game_id}/orders")
async def submit_orders(game_id: str, orders: list[Order]):
    # Validate and process orders
    result = game.process_orders(orders)
    return {"success": result.success, "errors": result.errors}

@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str):
    await websocket.accept()
    # Send updates when game state changes
    while True:
        await websocket.send_json({
            "type": "TURN_UPDATE",
            "state": get_game_state(game_id)
        })
```

## Customization

### Changing Colors

Edit the CSS variables in `styles.css` (lines 8-18):

```css
:root {
    /* Change to green CRT theme */
    --color-primary: #00ff88;
    --color-primary-dim: #00cc66;
    --color-primary-bright: #66ffaa;
}
```

### Adjusting Layout

The main grid layout is defined in `styles.css` (lines 224-240). Modify grid template for different arrangements.

### Adding New Commands

Add command handlers in `game.js` `handleCommand()` method (line ~300):

```javascript
else if (command.startsWith('SCAN')) {
    this.handleScanCommand(command);
}
```

## Browser Compatibility

Tested on:
- Chrome 120+
- Firefox 120+
- Safari 17+
- Edge 120+

Requires ES6+ JavaScript support.

## Performance Notes

- Canvas renders at 60fps using requestAnimationFrame
- Terminal output limited to 100 lines to prevent memory issues
- Tables update only when game state changes
- Animations use CSS transforms for GPU acceleration

## Future Enhancements

- [ ] Minimap overview
- [ ] Fleet waypoint planning (multi-hop routes)
- [ ] Combat animation visualization
- [ ] Sound effects (keyboard typing, alerts)
- [ ] Mobile-responsive layout
- [ ] Dark/Amber/Green theme switcher
- [ ] Replay mode for turn history
- [ ] Player chat/messaging interface
- [ ] Statistics dashboard
- [ ] Tutorial overlay system
