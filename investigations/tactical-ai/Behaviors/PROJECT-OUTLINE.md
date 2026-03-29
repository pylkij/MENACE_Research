Now I have the full picture. Here's the breakdown I'd recommend:

**Stage 1 — Base classes and Move**

Start with `Behavior` and `SkillBehavior` base classes (not in the extraction report, so their shared interface needs to be established from what the subclasses call), then `Move`. `Move` is the highest-priority target: 23 methods, 23 fields, and it's the only `Behavior` subclass that directly interacts with the tile scoring pipeline — `GetHighestTileScore`, `GetTilesSortedByScore`, `GetAddedScoreForPath` etc. are all directly relevant to what's already documented. It also defines the movement execution path that every other behavior ultimately depends on. Establishing `Move` and the base class interface first gives every subsequent stage a foundation to build on.

**Stage 2 — Collect/Evaluate/Execute behaviors: Assist and Attack hierarchies**

`Assist` and `Attack` are the two non-trivial base classes with their own `OnCollect`/`OnEvaluate`/`OnExecute` pipelines. These should be done together because `Buff`, `InflictDamage`, `InflictSuppression`, `Mindray`, `Stun`, `SpawnHovermine`, `SpawnPhantom`, `TargetDesignator`, `CreateLOSBlocker`, and `SupplyAmmo` all inherit from one of them and mostly override only `GetTargetValue`, `GetUtilityFromTileMult`, and `OnScaleBehaviorWeight`. Once `Assist.OnCollect`/`OnEvaluate`/`OnExecute` and `Attack.OnCollect`/`OnEvaluate`/`OnExecute` are reconstructed, the leaf subclasses can be handled as a batch — they're almost certainly thin wrappers differing only in how they score a target.

**Stage 3 — Leaf subclasses of Assist/Attack**

The thin overrides: `Buff`, `InflictDamage`, `InflictSuppression`, `Mindray`, `Stun`, `SpawnHovermine`, `SpawnPhantom`, `TargetDesignator`, `CreateLOSBlocker`, `SupplyAmmo`. Many share RVAs (`OnScaleMovementWeight` at `0x7334E0` is shared by nearly all of them), so decompiling one often resolves several. This stage is likely faster than it looks.

**Stage 4 — Structurally distinct SkillBehaviors**

`Deploy`, `TransportEntity`, `GainBonusTurn`, `MovementSkill`, `TurnArmorTowardsThreat`, `Reload`, `RemoveStatusEffect`, `Scan`. These don't fit the Assist/Attack pattern — they have unique `OnCollect`/`OnEvaluate` logic and in some cases extra lifecycle methods (`OnNewTurn`, `OnBeforeProcessing`, `UpdateArmor`). `TransportEntity` is the most complex here with two `OnEvaluate` overrides and zone-order fields. Group them together but expect more variance than stage 3.

**Stage 5 — Idle and collation**

`Idle` is trivially simple (stub `OnEvaluate`, stub `OnReset`) and can anchor the final stage alongside collation. Use this stage to resolve any cross-cutting questions that emerged — particularly around `FUN_181430ac0` (the per-attack evaluator called from `GetOpportunityLevel`) which is likely to appear inside `Attack.OnEvaluate`.

The key principle throughout is: RVA sharing is your guide. Where two classes share an RVA for a method, that's one decompilation, not two. The extraction report shows enough sharing in stages 2–3 that the actual Ghidra work is significantly less than the class count suggests.