-- Importing mpv module
local mp = require('mp')
local mp_options = require("mp.options")
local msg = require('mp.msg')

local options = { -- setting default options
    op_start = 0, op_end = 0, ed_start = 0, ed_end = 0,
}
mp_options.read_options(options, "skip") --reading script-opts data

-- Track which segments have been skipped to avoid multiple skips
local skipped_op = false
local skipped_ed = false

-- Log loaded configuration
msg.info("========== ANI-SKIP LOADED ==========")
msg.info(string.format("OP: %.2f - %.2f", options.op_start, options.op_end))
msg.info(string.format("ED: %.2f - %.2f", options.ed_start, options.ed_end))
msg.info("====================================")

-- Main function to check and skip if within the defined section
local function skip()
    local current_time = mp.get_property_number("time-pos")
    local paused = mp.get_property_bool("pause")

    if not current_time or paused then
        return
    end

    -- Check for opening sequence (with 0.5 second buffer before actual start)
    if options.op_start > 0 and not skipped_op then
        if current_time >= options.op_start - 0.5 and current_time < options.op_end then
            msg.info(string.format("⏩ SKIPPING OP: %.2f -> %.2f (was at %.2f)", options.op_start, options.op_end, current_time))
            mp.set_property_number("time-pos", options.op_end)
            skipped_op = true
        end
    end

    -- Reset OP skip flag if we've passed the end
    if options.op_end > 0 and current_time >= options.op_end then
        skipped_op = false
    end

    -- Check for ending sequence (with 0.5 second buffer before actual start)
    if options.ed_start > 0 and not skipped_ed then
        if current_time >= options.ed_start - 0.5 and current_time < options.ed_end then
            msg.info(string.format("⏩ SKIPPING ED: %.2f -> %.2f (was at %.2f)", options.ed_start, options.ed_end, current_time))
            mp.set_property_number("time-pos", options.ed_end)
            skipped_ed = true
        end
    end

    -- Reset ED skip flag if we've passed the end
    if options.ed_end > 0 and current_time >= options.ed_end then
        skipped_ed = false
    end
end

-- Use a periodic timer (100ms) for more reliable skip detection
-- This ensures we catch the skip moment even with fast playback speed
local timer = mp.add_periodic_timer(0.1, skip)
msg.info("Skip timer registered (100ms periodic check)")
