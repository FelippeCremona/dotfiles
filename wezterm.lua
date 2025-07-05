local wezterm = require 'wezterm'
local mux = wezterm.mux

wezterm.on("gui-startup", function()
  local tab, pane, window = mux.spawn_window{}
  window:gui_window():toggle_fullscreen()
end)

local config = {}
-- config.font = wezterm.font 'Hack NF'
-- config.font = wezterm.font 'JetBrains Mono NL'

config.window_padding = {
  left = 0,
  right = 0,
  top = 0,
  bottom = 0,
}

-- config.color_scheme = 'Mashup Colors (terminal.sexy)'
-- config.color_scheme = 'GruvboxDarkHard'
-- config.color_scheme = 'Gruvbox dark, hard (base16)'
-- config.color_scheme = 'Nucolors (terminal.sexy)'
-- config.color_scheme = 'Catppuccin Mocha'
-- config.color_scheme = "Catppuccin Macchiato"
-- config.color_scheme = 'tokyonight'
config.color_scheme = 'Kanagawa (Gogh)'
-- config.color_scheme = 'Guezwhoz'
-- config.color_scheme = 'Operator Mono Dark'
config.font_size = 16
config.default_domain = 'WSL:Ubuntu-22.04'
config.enable_tab_bar = false
-- config.window_background_opacity = 0.9
-- config.window_background_image = "teste2.jpg"

-- config.window_background_image_hsb = {
--   -- Darken the background image by reducing it to 1/3rd
--   brightness = 0.1,
--
--   -- You can adjust the hue by scaling its value.
--   -- a multiplier of 1.0 leaves the value unchanged.
--   hue = 1.0,
--
--   -- You can adjust the saturation also.
--   saturation = 1.0,
-- }
config.keys = {
  {
    key = 'w',
    mods = 'CTRL|SHIFT',
    action = wezterm.action.CloseCurrentPane { confirm = false },
  },
}
config.window_close_confirmation = 'NeverPrompt'
return config
