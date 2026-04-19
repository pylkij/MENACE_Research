using System;
using System.Collections.Generic;
using System.Linq;

using MelonLoader;
using Menace.ModpackLoader;
using Menace.SDK;

using Il2CppMenace.States;
using Il2CppMenace.Strategy;
using Il2CppMenace.Items;
using Il2CppMenace.Tactical;
using Il2CppMenace.Tactical.Skills;

namespace OCIRebalance;

public class Plugin : IModpackPlugin
{
    private static MelonLogger.Instance _log;

    private class UpgradeEntry
    {
        internal string Name { get; set; }
        internal string Skill { get; set; }
        internal bool IsInstalled { get; set; }
    }

    private static List<UpgradeEntry> _upgradeEntries = new List<UpgradeEntry>()
    {
        new UpgradeEntry { Name = "oci.dice_airdropped_minefield", Skill = "ocirebalance.airdropped_minefield", IsInstalled = false },
        new UpgradeEntry { Name = "oci.dice_electronic_warfare_system", Skill = "ocirebalance.electronic_warfare", IsInstalled = false },
        new UpgradeEntry { Name = "oci.dice_hacker_attack", Skill = "ocirebalance.remote_hacker", IsInstalled = false },
        new UpgradeEntry { Name = "oci.dice_sensor_decoys", Skill = "ocirebalance.sensor_ghosts", IsInstalled = false },
        new UpgradeEntry { Name = "oci.dice_smoke_curtain", Skill = "ocirebalance.smoke_curtain", IsInstalled = false },
        new UpgradeEntry { Name = "oci.zayn_auto_laser_sentry_turret", Skill = "ocirebalance.laser_turret", IsInstalled = false },
        new UpgradeEntry { Name = "oci.zayn_gravity_manipulator", Skill = "ocirebalance.gravity_pulse", IsInstalled = false },
        new UpgradeEntry { Name = "oci.zayn_ion_cannon", Skill = "ocirebalance.ion_cannon", IsInstalled = false },
        new UpgradeEntry { Name = "oci.standard_dropship_minigun_strafing", Skill = "ocirebalance.dropship_minigun_run", IsInstalled = false },
        new UpgradeEntry { Name = "oci.standard_unguided_missile_strike", Skill = "ocirebalance.orbital_missile_strike", IsInstalled = false },
        new UpgradeEntry { Name = "oci.unbent_dropship_rocket_run", Skill = "ocirebalance.dropship_rocket_run", IsInstalled = false },
        new UpgradeEntry { Name = "oci.unbent_medevac", Skill = "ocirebalance.cas_evac", IsInstalled = false },
        new UpgradeEntry { Name = "oci.unbent_supply_drop", Skill = "ocirebalance.resupply", IsInstalled = false }
    };

    public void OnInitialize(MelonLogger.Instance logger, HarmonyLib.Harmony harmony)
    {
        _log = logger;
        _log.Msg("OCIRebalance loaded.");

        GameState.TacticalReady += OnTacticalReady;
    }

    // MissionPreparation is a scene that is called but never actually loads,
    // making it a reliable flag to snapshot OCI state after all ship upgrades
    // are finalized but before the Tactical scene begins.
    public void OnSceneLoaded(int buildIndex, string sceneName)
    {
        if (!GameState.IsScene("MissionPreparation")) return;

        // Reset all to false before checking current state
        foreach (var upgrade in _upgradeEntries)
        {
            upgrade.IsInstalled = false;
        }

        // Check installed OCIs and set matches true
        var installed = GetInstalledUpgrades();
        foreach (var name in installed)
        {
            var upgrade = _upgradeEntries.FirstOrDefault(u => u.Name == name);
            if (upgrade != null)
            {
                upgrade.IsInstalled = true;
            }
        }
    }

    // Check inventory of all active player squads looking for the radio.
    private static void OnTacticalReady()
    {
        var actors = EntitySpawner.ListEntities(factionFilter: 1);
        if (actors == null || actors.Length == 0) return;

        foreach (var actor in actors)
        {
            var container = new Actor(actor.Pointer).GetItems();
            if (container == null) continue;

            var items = container.GetAllItems();
            if (items == null) continue;

            foreach (var item in items)
            {
                var template = item?.GetTemplate();
                if (template == null) continue;
                if (template.name == "ocirebalance.specialweapon.rmc_tac_radio")
                {
                    AssignTACSkills(new Actor(actor.Pointer));
                    _log.Msg($"TAC Skills assigned.");
                    continue;
                }
            }
        }
    }

    // If a squad is carrying the TAC Radio Special Weapon, assign skills 
    // for each Tactical OCI installed on the ship
    private static void AssignTACSkills(Actor actor)
    {
        foreach (var upgrade in _upgradeEntries)
        {
            if (upgrade.IsInstalled)
            {
                AddSkill(actor, upgrade.Skill);
                _log.Msg($"Added {upgrade.Skill} to {actor}");
            }
        }
    }

    // Menace.SDK Inventory.GetContainer() + Inventory.GetAllItems() 
    // are non-functional; reimplemented directly.
    private static List<(string SlotName, string TemplateName)> GetActorItems(GameObj actor)
    {
        var result = new List<(string, string)>();

        try
        {
            var entity = new Actor(actor.Pointer);
            var container = entity.GetItems();
            if (container == null) return result;

            var items = container.GetAllItems();
            if (items == null) return result;

            foreach (var item in items)
            {
                if (item == null) continue;
                var template = item.GetTemplate();
                if (template == null) continue;
                result.Add((GetSlotTypeName((int)template.SlotType), template.name));
            }
        }
        catch (Exception ex)
        {
            _log.Error($"GetActorItems failed: {ex.Message}");
        }

        return result;
    }

    // Slot names matching ItemSlot enum constants
    private static string GetSlotTypeName(int slotType) => slotType switch
    {
        -1  => "None",
        0   => "InfantryWeapon",
        1   => "InfantrySpecial",
        2   => "InfantryArmor",
        3   => "InfantryAccessory",
        4   => "Vehicle",
        5   => "VehicleAccessory",
        6   => "VehicleLightTurret",
        7   => "VehicleHeavyTurret",
        8   => "ModularVehicleLight",
        9   => "ModularVehicleMedium",
        10  => "ModularVehicleHeavy",
        255 => "All",
        _   => $"Unknown({slotType})"
    };

    // Menace.SDK OCI.GetInstalledUpgrades() is non-functional; 
    // reimplemented directly.
    private static List<string> GetInstalledUpgrades()
    {
        var result = new List<string>();

        var state = StrategyState.Get();
        if (state == null) return result;

        var shipUpgrades = state.ShipUpgrades;
        if (shipUpgrades == null) return result;

        for (int i = 0; i < ShipUpgrades.TOTAL_SLOTS; i++)
        {
            var equipped = shipUpgrades.GetEquippedUpgrade(i);
            if (equipped == null) continue;

            var templateObj = Templates.Find("ShipUpgradeTemplate", equipped.name);
            if (templateObj == null) continue;

            var name = Templates.ReadField(templateObj, "name")?.ToString() ?? string.Empty;
            result.Add(name);
        }

        return result;
    }

    // Menace.SDK EntitySkills.AddSkill() is non-functional; 
    // reimplemented directly.
    private static bool AddSkill(Actor actor, string templateName)
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

    public void OnUpdate() { }
    public void OnGUI() { }

    public void OnUnload()
    {
        GameState.TacticalReady -= OnTacticalReady;
    }
}