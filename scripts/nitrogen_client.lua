-- Load required libraries
local socket = require("socket")
local json = require("json") -- Ensure json.lua is in the same directory

-- === CONFIGURATION ===
local HOST = "127.0.0.1"
local PORT = 5556 -- Port for TCP (Simple TCP Server)
local TEMP_IMG_FILE = "nitrogen_temp.bmp"
local TARGET_WIDTH = 256
local TARGET_HEIGHT = 256
local EXPECTED_BYTES = TARGET_WIDTH * TARGET_HEIGHT * 3 + 54 -- Include BMP Header
local CONSOLE_TYPE = "NES" -- "SNES" or "NES"

-- Button order (matches nitrogen/shared.py)
local BUTTON_NAMES = {
    "BACK", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "DPAD_UP", "EAST", "GUIDE", 
    "LEFT_SHOULDER", "LEFT_THUMB", "LEFT_TRIGGER", "NORTH", "RIGHT_BOTTOM", "RIGHT_LEFT", 
    "RIGHT_RIGHT", "RIGHT_SHOULDER", "RIGHT_THUMB", "RIGHT_TRIGGER", "RIGHT_UP", "SOUTH", 
    "START", "WEST"
}

-- === CONTROL MAPPING ===
-- Configure this for your console (example for SNES)
-- NitroGen outputs: SOUTH=A, WEST=X, EAST=B, NORTH=Y (Xbox layout)
local function apply_controls(pred)
    local joy = {}
    local buttons = pred.buttons
    
    -- Send to emulator
    if CONSOLE_TYPE == "SNES" then
        -- Example for SNES (Controller 1)
        joy["P1 B"]      = buttons[6]  > 0.5 -- EAST -> B
        joy["P1 A"]      = buttons[19] > 0.5 -- SOUTH -> A
        joy["P1 Y"]      = buttons[21] > 0.5 -- WEST  -> Y
        joy["P1 X"]      = buttons[11] > 0.5 -- NORTH -> X
        
        joy["P1 Up"]     = buttons[5]  > 0.5 -- DPAD_UP
        joy["P1 Down"]   = buttons[2]  > 0.5 -- DPAD_DOWN
        joy["P1 Left"]   = buttons[3]  > 0.5 -- DPAD_LEFT
        joy["P1 Right"]  = buttons[4]  > 0.5 -- DPAD_RIGHT
        
        joy["P1 Start"]  = buttons[20] > 0.5 -- START
        joy["P1 Select"] = buttons[1]  > 0.5 -- BACK -> Select
        
        joy["P1 L"]      = buttons[8]  > 0.5 -- LEFT_SHOULDER
        joy["P1 R"]      = buttons[15] > 0.5 -- RIGHT_SHOULDER
    elseif CONSOLE_TYPE == "NES" then
        -- Example for NES (Controller 1)
        joy["P1 A"]      = buttons[19] > 0.5 -- SOUTH -> A
        joy["P1 B"]      = buttons[6]  > 0.5 -- EAST -> B
        
        joy["P1 Up"]     = buttons[5]  > 0.5 -- DPAD_UP
        joy["P1 Down"]   = buttons[2]  > 0.5 -- DPAD_DOWN
        joy["P1 Left"]   = buttons[3]  > 0.5 -- DPAD_LEFT
        joy["P1 Right"]  = buttons[4]  > 0.5 -- DPAD_RIGHT
        
        joy["P1 Start"]  = buttons[20] > 0.5 -- START
        joy["P1 Select"] = buttons[1]  > 0.5 -- BACK -> Select
    end
    
    joypad.set(joy)
end

-- === NETWORK FUNCTIONS ===

local tcp = socket.tcp()
tcp:settimeout(2000) -- Timeout 2 sec

console.log("Connecting to Nitrogen Server " .. HOST .. ":" .. PORT .. "...")
local res, err = tcp:connect(HOST, PORT)
if not res then
    console.log("Error connecting: " .. err)
    return
end
tcp:setoption("tcp-nodelay", true)
console.log("Connected!")

-- Main loop
while true do
    -- 1. Take screenshot in BMP (faster than PNG and uncompressed)
    client.screenshot(TEMP_IMG_FILE)
    
    -- 2. Read file as binary
    local f = io.open(TEMP_IMG_FILE, "rb")
    if f then
        local content = f:read("*all")
        f:close()
        
        -- Send the full content (Header + Pixels)
        -- The server will now parse the BMP header to determine orientation and size.
        local raw_pixels = content
        
        local current_len = string.len(raw_pixels)
        
        -- Check size
        if current_len == EXPECTED_BYTES then
            -- 3. Send JSON header
            -- image_source is no longer needed, server detects via BMP header or defaults
            local req = json.encode({
                type = "predict"
            })
            tcp:send(req .. "\n")
            
            -- 4. Send pixels
            tcp:send(raw_pixels)
            
            -- 5. Wait for response (JSON string)
            local line, err = tcp:receive("*l")
            if line then
                local response = json.decode(line)
                if response.status == "ok" then
                    apply_controls(response.pred)
                    
                    -- Visualization (optional)
                    gui.cleartext()
                    gui.text(0, 0, "AI Active")
                else
                    console.log("Server error: " .. (response.message or "unknown"))
                end
            else
                console.log("Connection lost: " .. (err or "unknown"))
                break
            end
        else
            console.log("Error: Screenshot size mismatch!")
            console.log("Expected: " .. EXPECTED_BYTES + 54 .. " bytes (including header)")
            console.log("Got: " .. current_len .. " bytes.")
        end
    end
    
    -- Advance frame
    emu.frameadvance()
end

tcp:close()
