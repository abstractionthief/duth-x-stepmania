-- FlyClock: the default theme's gameplay overlay, plus an invisible actor that
-- tells duth-x-stepmania where the song is.
-- "Save/" is OutFox's preferences folder (~/Library/Preferences/Project OutFox on macOS).
--   Save/flyclock/session.txt   song folder, chart difficulty per player (once per song)
--   Save/flyclock/clock.txt     "<music seconds> <seconds since game start> <beat>", ~20x per second
--   Save/flyclock/judgments.txt one line per judgment: "<music seconds> <player> <score>"
-- Files are rewritten in place (RageFile has no append mode); a reader polls them.

-- LoadFallbackB() gets no metrics group/element for a folder overlay in OutFox,
-- so load the default theme's overlay by path (FlyClock always falls back to it).
local t = Def.ActorFrame {}
t[#t+1] = LoadActor("/Appearance/Themes/default/BGAnimations/ScreenGameplay overlay")
local DIR = "Save/flyclock/"
local last_write = -1
local judgments = {}

local function safe(f, ...)
	local ok, value = pcall(f, ...)
	return ok and value or nil
end

local function write_clock(self)
	local now = GetTimeSinceStart()
	if now - last_write < 0.05 then return end
	last_write = now
	File.Write(DIR .. "clock.txt", string.format("%.4f %.4f %.4f\n",
		GAMESTATE:GetCurMusicSeconds(), now, GAMESTATE:GetSongBeat()))
end

t[#t+1] = Def.ActorFrame {
	OnCommand = function(self)
		judgments = {}
		File.Write(DIR .. "judgments.txt", "")
		local song = GAMESTATE:GetCurrentSong()
		local lines = { "song " .. tostring(song and safe(function() return song:GetSongDir() end) or "?") }
		for _, pn in ipairs(GAMESTATE:GetEnabledPlayers()) do
			local steps = GAMESTATE:GetCurrentSteps(pn)
			lines[#lines + 1] = string.format("%s %s", tostring(pn),
				tostring(steps and safe(function() return steps:GetDifficulty() end) or "?"))
		end
		File.Write(DIR .. "session.txt", table.concat(lines, "\n") .. "\n")
		self:SetUpdateFunction(write_clock)
	end,
	JudgmentMessageCommand = function(self, params)
		judgments[#judgments + 1] = string.format("%.4f %s %s\n", GAMESTATE:GetCurMusicSeconds(),
			tostring(params.Player), tostring(params.TapNoteScore or params.HoldNoteScore))
		File.Write(DIR .. "judgments.txt", table.concat(judgments))
	end,
}

return t
