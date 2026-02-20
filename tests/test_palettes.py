from config.themes.palettes import ColorPalette

light = ColorPalette.LIGHT
print(f"Primary: {light['blue_600']}")  # #2563EB
print(f"BG: {light['gray_50']}")        # #F9FAFB

dark = ColorPalette.DARK
print(f"Primary: {dark['blue_500']}")   # #3B82F6
print(f"BG: {dark['gray_50']}")         # #1B2430