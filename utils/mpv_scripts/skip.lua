-- Importing mpv module
local mp = require('mp')
local mp_options = require("mp.options")
local msg = require('mp.msg')

local options = { -- setting default options
    op_start = 0, op_end = 0, ed_start = 0, ed_end = 0,
}
mp_options.read_options(options, "skip") --reading script-opts data

-- Log loaded configuration
msg.info("========== ANI-SKIP LOADED ==========")
msg.info(string.format("OP: %.2f - %.2f", options.op_start, options.op_end))
msg.info(string.format("ED: %.2f - %.2f", options.ed_start, options.ed_end))
msg.info("====================================")

-- Main function to check and skip if within the defined section
local function skip()
    local current_time = mp.get_property_number("time-pos")

    if not current_time then
        return
    end

    -- Check for opening sequence
    if options.op_start > 0 and current_time >= options.op_start and current_time < options.op_end then
        msg.info(string.format("⏩ SKIPPING OP: %.2f -> %.2f", current_time, options.op_end))
        mp.set_property_number("time-pos", options.op_end)
    end

    -- Check for ending sequence
    if options.ed_start > 0 and current_time >= options.ed_start and current_time < options.ed_end then
        msg.info(string.format("⏩ SKIPPING ED: %.2f -> %.2f", current_time, options.ed_end))
        mp.set_property_number("time-pos", options.ed_end)
    end
end

-- Bind the function to be called whenever the time position is changed
mp.observe_property("time-pos", "number", skip)
msg.info("Skip observer registered")
