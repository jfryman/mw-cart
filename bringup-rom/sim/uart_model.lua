-- MAME autoboot script: behavioural model of the MegaWiFi Rev.C UART (TL16C550D,
-- 20 MHz) plus a fake ESP32 speaking LSD/MegaWiFi, mapped at $A130C0-$A130CF.
-- Lets the bring-up ROM's pass paths run in an emulator. Not a hardware model:
-- timing is byte-granular and auto-RTS is approximated.
--
-- Env: SIM_SNAP_AT="6,20" (emulated seconds to snapshot; exits after the last)
--      SIM_FAULT=none|noesp|corrupt   (inject an ESP failure mode)

local CLK = 20000000
local BASE = 0xA130C0
local snap_at = {}
for s in string.gmatch(os.getenv("SIM_SNAP_AT") or "6,20", "[^,]+") do snap_at[#snap_at + 1] = tonumber(s) end
local fault = os.getenv("SIM_FAULT") or "none"

local u = { ier = 0, lcr = 0, mcr = 0, spr = 0, dll = 0, dlm = 0, lsr_err = 0 }
local txq, rxq, espq = {}, {}, {}      -- txq: {b, done}; rxq: bytes; espq: {b, at}
local esp = { ready_at = nil, st = "stx", buf = {}, need = 0, ch = 0 }

local function now() return manager.machine.time:as_double() end
local function div() local d = u.dll + 256 * u.dlm; return d == 0 and 65536 or d end
local function byte_time() return 16 * div() * 10 / CLK end
local function loop() return (u.mcr & 0x10) ~= 0 end

local function rx_push(b)
  if #rxq >= 16 then u.lsr_err = u.lsr_err | 0x02 return end   -- overrun
  rxq[#rxq + 1] = b
end

-- ESP side ---------------------------------------------------------------
local function esp_send(bytes, delay)
  local t = math.max(now() + delay, espq[#espq] and espq[#espq].at or 0)
  local bt = 16 * 1 * 10 / CLK       -- ESP fixed at 1.25 Mbaud
  for _, b in ipairs(bytes) do t = t + bt; espq[#espq + 1] = { b = b, at = t } end
end

local function esp_frame(payload)
  local f = { 0x7E, (#payload >> 8) & 0x0F, #payload & 0xFF }
  for _, b in ipairs(payload) do f[#f + 1] = b end
  f[#f + 1] = 0x7E
  return f
end

local function esp_handle(p)
  if fault == "noesp" then return end
  local cmd = (p[1] << 8) | p[2]
  local reply
  if cmd == 1 then
    reply = { 0, 0, 0, 7, 1, 5, 2 }
    for c in string.gmatch("sim\0", ".") do reply[#reply + 1] = string.byte(c) end
    reply[4] = #reply - 4
  elseif cmd == 2 then
    reply = { 0, 0, p[3], p[4] }
    for i = 5, #p do reply[#reply + 1] = p[i] end
    if fault == "corrupt" and #p > 300 then reply[200] = reply[200] ~ 0x01 end
  else
    reply = { 0, 255, 0, 0 }
  end
  esp_send(esp_frame(reply), 0.0005)
end

local function esp_rx(b)
  if not esp.ready_at or now() < esp.ready_at then return end
  if div() ~= 1 then return end      -- wrong baud: ESP sees garbage
  local s = esp.st
  if s == "stx" then if b == 0x7E then esp.st = "chl" end
  elseif s == "chl" then
    if b ~= 0x7E then esp.ch = b >> 4; esp.need = (b & 0x0F) << 8; esp.st = "len" end
  elseif s == "len" then
    esp.need = esp.need | b; esp.buf = {}; esp.st = esp.need > 0 and "data" or "etx"
  elseif s == "data" then
    esp.buf[#esp.buf + 1] = b; if #esp.buf == esp.need then esp.st = "etx" end
  elseif s == "etx" then
    esp.st = "stx"; if b == 0x7E then esp_handle(esp.buf) end
  end
end

-- UART core ---------------------------------------------------------------
local function advance()
  local t = now()
  while txq[1] and txq[1].done <= t do
    local e = table.remove(txq, 1)
    if loop() then rx_push(e.b) else esp_rx(e.b) end
  end
  -- ESP -> UART, honouring auto-RTS (AFE+RTS): hold off at RX trigger level 14
  local afe = (u.mcr & 0x22) == 0x22
  while espq[1] and espq[1].at <= t and not loop() do
    if afe and #rxq >= 14 then
      local slip = t - espq[1].at
      for _, e in ipairs(espq) do e.at = e.at + slip + 1e-6 end
      break
    end
    rx_push(table.remove(espq, 1).b)
  end
end

local function lsr()
  local t = now()
  local queued = 0
  for _, e in ipairs(txq) do if e.done - byte_time() > t then queued = queued + 1 end end
  local v = (#rxq > 0 and 0x01 or 0) | u.lsr_err
  if queued == 0 then v = v | 0x20 end
  if #txq == 0 then v = v | 0x40 end
  u.lsr_err = 0
  return v
end

local function msr()
  if loop() then
    local m = u.mcr
    return ((m & 1) ~= 0 and 0x20 or 0) | ((m & 2) ~= 0 and 0x10 or 0) |
           ((m & 4) ~= 0 and 0x40 or 0) | ((m & 8) ~= 0 and 0x80 or 0)
  end
  return 0x10 | 0x20                  -- ESP RTS active (our CTS), DSR asserted
end

local function reg_read(r)
  advance()
  local dlab = (u.lcr & 0x80) ~= 0
  if r == 0 then
    if dlab then return u.dll end
    if #rxq > 0 then return table.remove(rxq, 1) end
    return 0
  elseif r == 1 then return dlab and u.dlm or u.ier
  elseif r == 2 then return 0xC1
  elseif r == 3 then return u.lcr
  elseif r == 4 then return u.mcr & 0x3F
  elseif r == 5 then return lsr()
  elseif r == 6 then return msr()
  else return u.spr end
end

local function reg_write(r, v)
  advance()
  local dlab = (u.lcr & 0x80) ~= 0
  if r == 0 then
    if dlab then u.dll = v return end
    if #txq >= 17 then return end   -- FIFO + shifter full: byte lost
    local t = now()
    local start = math.max(t, txq[#txq] and txq[#txq].done or t)
    txq[#txq + 1] = { b = v, done = start + byte_time() }
  elseif r == 1 then if dlab then u.dlm = v else u.ier = v & 0x0F end
  elseif r == 2 then
    if (v & 0x02) ~= 0 then rxq = {} end
    if (v & 0x04) ~= 0 then txq = {} end
  elseif r == 3 then u.lcr = v
  elseif r == 4 then
    local was_reset = (u.mcr & 0x01) ~= 0
    u.mcr = v & 0x3F
    local in_reset = (u.mcr & 0x01) ~= 0
    if in_reset then esp.ready_at = nil; espq = {}
    elseif was_reset then
      esp.ready_at = now() + 0.3; esp.st = "stx"
      -- ROM bootloader chatter at the wrong baud: shows up as framing errors
      for i = 1, 20 do espq[#espq + 1] = { b = 0xA5, at = now() + 0.05 + i * 1e-4 } end
    end
  elseif r == 7 then u.spr = v end
end

local space = manager.machine.devices[":maincpu"].spaces["program"]
uart_rtap = space:install_read_tap(BASE, BASE + 0xF, "mw_uart_r", function(offset, data, mask)
  if (mask & 0x00FF) == 0 then return data end
  local r = ((offset - BASE) >> 1) & 7
  return (data & 0xFF00) | reg_read(r)
end)
uart_wtap = space:install_write_tap(BASE, BASE + 0xF, "mw_uart_w", function(offset, data, mask)
  if (mask & 0x00FF) == 0 then return end
  reg_write(((offset - BASE) >> 1) & 7, data & 0xFF)
end)

-- SIM_HI=<8 MiB image>: model the flat-8MiB hack (R1, ~CART_IN = A22) by serving
-- $400000-$7FFFFF from the image's top half. MAME maps a plain cart at <4 MiB only.
local hi_path = os.getenv("SIM_HI")
if hi_path then
  local fh = assert(io.open(hi_path, "rb"))
  local img = fh:read("a"); fh:close()
  print("SIM_HI: " .. #img .. " bytes, $400000 = " .. string.format("%02x%02x", img:byte(0x400001), img:byte(0x400002)))
  hi_rtap = space:install_read_tap(0x400000, 0x7FFFFF, "mw_hi_r", function(offset, data, mask)
    local i = offset + 1
    return (string.byte(img, i) << 8) | string.byte(img, i + 1)
  end)
end

local idx = 1
emu.register_frame_done(function()
  if snap_at[idx] and now() >= snap_at[idx] then
    local cpu = manager.machine.devices[":maincpu"]
    local fsp = space:read_u32(0xFFFF02)
    local fr = ""
    for i = 0, 13, 2 do fr = fr .. string.format("%04X ", space:read_u16(fsp + i)) end
    print(string.format("t=%.1f PC=%06X faultvec=%d frame@%06X: %s", now(), cpu.state["PC"].value,
      space:read_u16(0xFFFF00), fsp, fr))
    manager.machine.video:snapshot()
    idx = idx + 1
    if not snap_at[idx] then manager.machine:exit() end
  end
end)

-- post-mortem: the ROM's fault stubs record the vector at $FFFF00 and SP at $FFFF02
emu.add_machine_stop_notifier(function()
  local vec = space:read_u16(0xFFFF00)
  if vec ~= 0 then
    local sp = space:read_u32(0xFFFF02)
    local s = ""
    for i = 0, 13, 2 do s = s .. string.format("%04X ", space:read_u16(sp + i)) end
    print(string.format("FAULT vector %d, SP %08X, frame: %s", vec, sp, s))
  end
end)
