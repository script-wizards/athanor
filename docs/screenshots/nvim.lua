-- The editor in the staged desktop: nvim with Athanor's colorscheme and
-- nothing else, so the shot doesn't depend on whoever runs the kit.
vim.cmd.colorscheme("athanor")
vim.o.number = true
vim.o.cursorline = false
vim.o.showmode = false
vim.o.laststatus = 2
vim.o.title = true
vim.o.titlestring = "%t"

local modes = { n = "NOR", i = "INS", v = "SEL", V = "SEL" }
function _G.athanor_mode()
    return modes[vim.fn.mode()] or "NOR"
end
vim.o.statusline = "%#TabLineSel# %{v:lua.athanor_mode()} %* %f%=%l:%c "
