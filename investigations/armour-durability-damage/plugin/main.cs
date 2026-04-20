using System;
using MelonLoader;
using Menace.ModpackLoader;
using HarmonyLib;
using Menace.SDK;

namespace RendAmmoDebug;

public class Plugin : IModpackPlugin
{
    private static MelonLogger.Instance _log;
    private static HarmonyLib.Harmony _harmony;

    public void OnInitialize(MelonLogger.Instance logger, HarmonyLib.Harmony harmony)
    {
        _log = logger;
        _harmony = harmony;
        _log.Msg("RendAmmoDebug loaded.");

        try
        {
            Patch_UpdateProperty();
        }
        catch (Exception ex)
        {
            _log.Error($"Patch failed: {ex}");
        }
    }

    private static void Patch_UpdateProperty()
    {
        var targetType = GameState.FindManagedType("Il2CppMenace.Tactical.EntityProperties");
        if (targetType == null) { _log.Error("EntityProperties not found."); return; }

        var updateProp = targetType.GetMethod("UpdateProperty",
            System.Reflection.BindingFlags.Instance |
            System.Reflection.BindingFlags.Public);

        var updateMultProp = targetType.GetMethod("UpdateMultProperty",
            System.Reflection.BindingFlags.Instance |
            System.Reflection.BindingFlags.Public);

        var flatPostfix = typeof(Plugin).GetMethod(nameof(UpdateProperty_Postfix),
            System.Reflection.BindingFlags.Static |
            System.Reflection.BindingFlags.NonPublic);

        var multPostfix = typeof(Plugin).GetMethod(nameof(UpdateMultProperty_Postfix),
            System.Reflection.BindingFlags.Static |
            System.Reflection.BindingFlags.NonPublic);

        if (updateProp != null)
            _harmony.Patch(updateProp, postfix: new HarmonyMethod(flatPostfix));

        if (updateMultProp != null)
            _harmony.Patch(updateMultProp, postfix: new HarmonyMethod(multPostfix));

        _log.Msg("Patched EntityProperties.UpdateProperty and UpdateMultProperty.");
    }

    private static void UpdateProperty_Postfix(
        Il2CppMenace.Tactical.EntityPropertyType _propertyType, int _amount)
    {
        _log.Msg($"  UpdateProperty — PropertyType: {_propertyType} ({(int)_propertyType}), Amount: {_amount}");
    }

    private static void UpdateMultProperty_Postfix(
        Il2CppMenace.Tactical.EntityPropertyType _propertyType, float _amountMult)
    {
        _log.Msg($"  UpdateMultProperty — PropertyType: {_propertyType} ({(int)_propertyType}), AmountMult: {_amountMult}");
    }

    public void OnSceneLoaded(int buildIndex, string sceneName) { }
    public void OnUpdate() { }
    public void OnGUI() { }
    public void OnUnload() { }
}