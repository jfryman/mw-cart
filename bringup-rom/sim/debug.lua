local space = manager.machine.devices[":maincpu"].spaces["program"]
local n = 0
dbg_r = space:install_read_tap(0xA130C0, 0xA130CF, "dbg_r", function(offset, data, mask)
  n = n + 1
  if n < 12 then print(string.format("R off=%06X data=%04X mask=%04X", offset, data, mask)) end
  return data
end)
dbg_w = space:install_write_tap(0xA130C0, 0xA130CF, "dbg_w", function(offset, data, mask)
  n = n + 1
  if n < 12 then print(string.format("W off=%06X data=%04X mask=%04X", offset, data, mask)) end
end)
local done = false
emu.register_frame_done(function()
  if not done and manager.machine.time:as_double() > 8 then
    done = true
    local cpu = manager.machine.devices[":maincpu"]
    local sp = cpu.state["SP"].value
    print(string.format("PC=%06X SP=%08X", cpu.state["PC"].value, sp))
    local s = ""
    for i = 0, 15, 2 do s = s .. string.format("%04X ", space:read_u16(sp + i)) end
    print("stack: " .. s)
    manager.machine:exit()
  end
end)
