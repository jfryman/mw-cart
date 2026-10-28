import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
f = pcbnew.ZONE_FILLER(b)
print("filled:", f.Fill(b.Zones()))
pcbnew.SaveBoard(sys.argv[2], b)
