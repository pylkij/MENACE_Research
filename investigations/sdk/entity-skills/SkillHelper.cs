// Helper Classes - Mostly just rebuilding SDK functionality down here

public static class SkillHelper
{
    // Offsets verified against dump.cs
    private const int OFFSET_COOLDOWN_HANDLER_TEMPLATE  = 0x18; // CooldownEffectHandler.m_Template
    private const int OFFSET_COOLDOWN_HANDLER_VALUE     = 0x20; // CooldownEffectHandler.m_Cooldown
    private const int OFFSET_COOLDOWN_TEMPLATE_AIONLY   = 0x5C; // Cooldown.AIOnly

    public static MelonLogger.Instance Log { get; set; }

    public static bool AddSkill(Actor actor, string templateName)
    {
        var container = actor.GetSkills();
        if (container == null) return false;

        var templates = UnityEngine.Resources.FindObjectsOfTypeAll<SkillTemplate>();
        SkillTemplate template = null;
        foreach (var t in templates)
        {
            if (t.name.Equals(templateName, StringComparison.OrdinalIgnoreCase))
            {
                template = t;
                break;
            }
        }
        if (template == null) return false;

        var skill = template.CreateSkill();
        if (skill == null) return false;

        return container.Add(skill);
    }

    public static bool RemoveSkill(Actor actor, string skillID)
    {
        var container = actor.GetSkills();
        if (container == null) return false;

        return container.RemoveByID(skillID);
    }

    public static bool SetCooldown(Actor actor, string skillID, int turns)
    {
        var handler = GetCooldownHandler(actor, skillID);
        if (handler == null) return false;

        Marshal.WriteInt32(handler.Pointer + OFFSET_COOLDOWN_HANDLER_VALUE, turns);
        return true;
    }

    public static bool ResetCooldown(Actor actor, string skillID)
    {
        var handler = GetCooldownHandler(actor, skillID);
        if (handler == null) return false;

        var templatePtr = Marshal.ReadIntPtr(handler.Pointer + OFFSET_COOLDOWN_HANDLER_TEMPLATE);
        var defaultTurns = templatePtr != IntPtr.Zero
            ? new Cooldown(templatePtr).RoundsToCoolDown
            : 0;

        Marshal.WriteInt32(handler.Pointer + OFFSET_COOLDOWN_HANDLER_VALUE, defaultTurns);
        return true;
    }

    public static bool ModifyCooldown(Actor actor, string skillID, int delta)
    {
        var handler = GetCooldownHandler(actor, skillID);
        if (handler == null) return false;

        var current = Marshal.ReadInt32(handler.Pointer + OFFSET_COOLDOWN_HANDLER_VALUE);
        Marshal.WriteInt32(handler.Pointer + OFFSET_COOLDOWN_HANDLER_VALUE, Math.Max(0, current + delta));
        return true;
    }

    public static bool DisableAIOnlyCooldown(Actor actor, string skillID)
    {
        var handler = GetCooldownHandler(actor, skillID);
        if (handler == null) return false;

        var templatePtr = Marshal.ReadIntPtr(handler.Pointer + OFFSET_COOLDOWN_HANDLER_TEMPLATE);
        if (templatePtr == IntPtr.Zero) return false;

        Marshal.WriteByte(templatePtr + OFFSET_COOLDOWN_TEMPLATE_AIONLY, 0);
        return true;
    }

    // --- Private Helpers ---

    private static CooldownEffectHandler GetCooldownHandler(Actor actor, string skillID, MelonLogger.Instance log = null)
    {
        var container = actor.GetSkills();
        if (container == null)
        {
            Log.Msg($"[GetCooldownHandler] container is null for actor {actor}");
            return null;
        }

        var skill = container.GetSkillByID(skillID, null)?.TryCast<Skill>();
        if (skill == null)
        {
            Log.Msg($"[GetCooldownHandler] skill '{skillID}' not found in container");
            return null;
        }

        skill.GetEventHandlerOfType<CooldownEffectHandler>(out var handler);
        Log.Msg($"[GetCooldownHandler] handler is {(handler == null ? "null" : "found")}");
        return handler;
    }
}