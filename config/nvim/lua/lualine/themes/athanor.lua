-- The terminal's 16 colors. The mode is ochre in normal, green in insert and
-- magenta in visual, as in Helix, reversed so the terminal's own background is
-- the text in every scheme.
local function mode(color)
    return {
        a = { fg = color, bg = "NONE", gui = "reverse,bold" },
        b = { fg = "NONE", bg = "NONE" },
        c = { fg = 8, bg = "NONE" },
    }
end

return {
    normal = mode(3),
    insert = mode(2),
    visual = mode(5),
    replace = mode(1),
    command = mode(3),
    terminal = mode(2),
    inactive = {
        a = { fg = 8, bg = "NONE" },
        b = { fg = 8, bg = "NONE" },
        c = { fg = 8, bg = "NONE" },
    },
}
