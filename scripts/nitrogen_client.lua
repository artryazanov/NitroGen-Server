-- NitroGen Client for BizHawk (Native .NET Version)
-- FIX: Renamed 'client' variable to 'tcp' to avoid conflict with Emulator API

local luanet = _G.luanet
luanet.load_assembly("System")

-- Imports
local TcpClient = luanet.import_type("System.Net.Sockets.TcpClient")
local File = luanet.import_type("System.IO.File") 
local Encoding = luanet.import_type("System.Text.Encoding")

-- === CONFIGURATION ===
local HOST = "127.0.0.1"
local PORT = 5556
local TEMP_IMG_FILE = "nitrogen_temp.bmp"
local CONSOLE_TYPE = "NES" -- "SNES" or "NES"

-- === CONTROL MAPPING ===
local function apply_controls(button_values)
    local joy = {}
    local buttons = {}
    
    for v in string.gmatch(button_values, "[%d%.]+") do
        table.insert(buttons, tonumber(v))
    end
    
    if #buttons < 21 then return end

    if CONSOLE_TYPE == "SNES" then
        joy["P1 B"]      = buttons[6]  > 0.5 
        joy["P1 A"]      = buttons[19] > 0.5 
        joy["P1 Y"]      = buttons[21] > 0.5 
        joy["P1 X"]      = buttons[11] > 0.5 
        joy["P1 Up"]     = buttons[5]  > 0.5 
        joy["P1 Down"]   = buttons[2]  > 0.5 
        joy["P1 Left"]   = buttons[3]  > 0.5 
        joy["P1 Right"]  = buttons[4]  > 0.5 
        joy["P1 Start"]  = buttons[20] > 0.5 
        joy["P1 Select"] = buttons[1]  > 0.5 
        joy["P1 L"]      = buttons[8]  > 0.5 
        joy["P1 R"]      = buttons[15] > 0.5 
    elseif CONSOLE_TYPE == "NES" then
        joy["P1 A"]      = buttons[19] > 0.5 
        joy["P1 B"]      = buttons[6]  > 0.5 
        joy["P1 Up"]     = buttons[5]  > 0.5 
        joy["P1 Down"]   = buttons[2]  > 0.5 
        joy["P1 Left"]   = buttons[3]  > 0.5 
        joy["P1 Right"]  = buttons[4]  > 0.5 
        joy["P1 Start"]  = buttons[20] > 0.5 
        joy["P1 Select"] = buttons[1]  > 0.5 
    end
    
    joypad.set(joy)
end

-- === MAIN LOGIC ===
console.clear()
console.log("Connecting to " .. HOST .. ":" .. PORT .. "...")

-- FIX: Rename variable to 'tcp' so we don't hide global 'client'
local tcp = TcpClient()
local success, err = pcall(function() 
    tcp:Connect(HOST, PORT) 
end)

if not success then
    console.log("Connection Failed: " .. tostring(err))
    return
end

console.log("Connected!")
local stream = tcp:GetStream()
local resp_buffer = luanet.import_type("System.Byte[]")(4096)

while tcp.Connected do
    -- 1. Screenshot (Now 'client' refers to BizHawk API correctly)
    client.screenshot(TEMP_IMG_FILE)
    
    -- 2. Read Bytes (Fast .NET read)
    local file_bytes = File.ReadAllBytes(TEMP_IMG_FILE)
    
    -- 3. Header
    local json_header = '{"type": "predict"}\n'
    local header_bytes = Encoding.ASCII:GetBytes(json_header)
    
    -- 4. Send
    local send_ok, send_err = pcall(function()
        stream:Write(header_bytes, 0, header_bytes.Length)
        stream:Write(file_bytes, 0, file_bytes.Length)
    end)
    
    if not send_ok then
        console.log("Error sending data.")
        break
    end
    
    -- 5. Receive
    local bytes_read = stream:Read(resp_buffer, 0, resp_buffer.Length)
    if bytes_read > 0 then
        local resp_str = Encoding.ASCII:GetString(resp_buffer, 0, bytes_read)
        
        local s, e = string.find(resp_str, "\"buttons\":%s*%[")
        if e then
            local end_bracket = string.find(resp_str, "%]", e)
            if end_bracket then
                local val_str = string.sub(resp_str, e+1, end_bracket-1)
                apply_controls(val_str)
            end
        end
        
        -- Optional Debug Text
        gui.drawText(0, 0, "AI Active", "green")
    else
        console.log("Server sent empty response.")
        break
    end
    
    emu.frameadvance()
end

tcp:Close()
console.log("Disconnected.")