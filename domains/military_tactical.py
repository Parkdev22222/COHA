"""
Domain: Military Tactical QA — US Army Doctrine (ADP 3-0, ADP 3-90, FM 3-0, SROE/ROE).

Contains domain documentation, user stories, manual OWL ontology,
and a 30-item benchmark QA dataset for evaluating military tactical agents.
"""

# ---------------------------------------------------------------------------
# Domain Documentation
# ---------------------------------------------------------------------------

DOMAIN_DOCS: str = """
# US Army Tactical Decision Support — Based on ADP 3-0 (2019), ADP 3-90 (2019), FM 3-0 (2022)

## Source Documents
This domain is derived from the following publicly available US Army doctrine publications:
- ADP 3-0, Operations (July 2019) — Army Publishing Directorate
- ADP 3-90, Offense and Defense (July 2019) — Army Publishing Directorate
- FM 3-0, Operations (October 2022) — Army Publishing Directorate
- Unclassified ROE training materials (CALL 96-6, FM 27-100 Ch.8, FM 100-23 App.D)

## Overview
Army tactical operations are conducted across the competition continuum: competition
below armed conflict, armed conflict, and return to competition. Large-Scale Combat
Operations (LSCO) against a peer/near-peer adversary are the most demanding missions.
The Army's operational concept integrates multi-domain operations across land, air,
maritime, space, and cyberspace domains.

## Operational Framework (ADP 3-0)

### Elements of Combat Power
Eight elements: Leadership, Information, Command and Control (C2), Movement and Maneuver,
Intelligence, Fires, Sustainment, Protection. Commanders integrate these through the
operations process: plan, prepare, execute, assess.

### METT-TC Planning Factors
- Mission: commander's intent, task, purpose
- Enemy: composition, disposition, strength, capabilities, vulnerabilities
- Terrain and Weather: OAKOC — Observation/fields of fire, Avenues of approach,
  Key terrain, Obstacles, Cover and concealment
- Troops and support available: unit readiness, attached/OPCON units
- Time available: planning time, movement time, preparation time
- Civil considerations: ASCOPE — Areas, Structures, Capabilities, Organizations, People, Events

### Tenets of Unified Land Operations
- Simultaneity: multiple tasks simultaneously across depth and breadth
- Depth: extend operations in time, space, and purpose to defeat enemy in depth
- Synchronization: arrange activities in time, space, and purpose to mass effects
- Flexibility: adapt plans and operations to changing conditions

## Unit Types and Capabilities (ADP 3-0, FM 3-0)

### Maneuver Units
- **Infantry (IN)**: Dismounted close combat. Effective in urban, jungle, forested,
  mountainous terrain. Primary tasks: seize/retain/exploit terrain, clear structures,
  establish security. Organic fire: M4 rifles, M249 SAW, M240B, AT4, Javelin.
- **Armored (AR) / Combined Arms Battalion (CAB)**: M1A2 SEPv3 Abrams tanks.
  Most effective in open/semi-open terrain. Primary tasks: exploit penetrations,
  shock action, anti-armor, offensive operations at speed.
- **Mechanized Infantry (MECH IN)**: M2A4 Bradley IFVs. Combined arms capability.
  Effective across terrain types. Primary tasks: mounted assault, CASEVAC,
  support armor operations.
- **Aviation (AV)**: Attack (AH-64 Apache), Assault (UH-60 Black Hawk),
  Reconnaissance (OH-58 Kiowa/MQ-1C Gray Eagle). Provides air assault, deep attack,
  reconnaissance, MEDEVAC. Not effective in dense foliage/low ceiling weather.
- **Special Forces (SF)**: 12-man ODAs. Unconventional warfare (UW), Foreign Internal
  Defense (FID), Special Reconnaissance (SR), Direct Action (DA), Counter-terrorism (CT).
  Operate in denied/contested areas with indigenous forces.
- **Rangers**: 75th Ranger Regiment. Light infantry for direct action raids, airfield
  seizure, airborne operations. Rapid deployment, high readiness.

### Fires and Support
- **Field Artillery (FA)**: M109A7 Paladin (SP howitzer), M777 (towed), HIMARS/MLRS.
  Provides indirect fire support: suppression, neutralization, destruction.
  Fire missions: adjust fire, fire for effect, time on target, SEAD.
- **Air Defense Artillery (ADA)**: Patriot, SHORAD (Avenger, M-SHORAD). Provides
  air/missile defense. Critical for LSCO peer threats.
- **Engineer (EN)**: Mobility (breaching, bridging), countermobility (obstacles,
  minefields), survivability (fighting positions, hardening). Combat engineer at
  maneuver unit; general engineer for infrastructure.
- **Military Intelligence (MI)**: Collection, processing, exploitation, dissemination
  of intelligence. Organic to BCT: SIGINT, HUMINT, ISR coordination.

### Sustainment
- **Logistics/Sustainment (LOG)**: Class I (rations), III (fuel), V (ammunition),
  VIII (medical). BSB provides direct support to BCT. Sustainment affects operational
  reach and endurance.

### Command Echelons (ADP 3-0)
- **Squad** (~9 soldiers): basic tactical element
- **Platoon** (~30-40 soldiers, 3-4 squads): lieutenant
- **Company/Troop/Battery** (~80-150, 3-4 platoons): captain
- **Battalion/Squadron** (~400-800, 3-5 companies): lieutenant colonel
- **Brigade Combat Team (BCT)** (~3,000-5,000, 3+ battalions): colonel
  Types: IBCT (Infantry), ABCT (Armored), SBCT (Stryker)
- **Division** (~10,000-20,000, 2-5 BCTs): major general
- **Corps** (~40,000-100,000+, 2-5 divisions): lieutenant general

## Offensive Operations (ADP 3-90, FM 3-0)

Offensive operations: seize, retain, exploit the initiative; destroy enemy forces;
seize/secure key terrain; fix or turn enemy; deceive enemy; deny resources.

### Types of Offensive Operations
1. **Movement to Contact (MTC)**: Gain/regain contact with enemy. Subtypes:
   - Search and attack: find/fix/finish dispersed enemy (counter-guerrilla)
   - Approach march: move to contact against enemy in prepared positions
2. **Attack**: Defeat enemy forces, seize terrain, secure terrain.
   - Hasty attack: immediately available forces, fragmentary order, speed over prep
   - Deliberate attack: detailed planning/coordination, multiple branches/sequels
   - Raid: swift penetration of hostile territory, specific objective, withdrawal
   - Feint: limited-objective attack to deceive enemy as to location/time of main effort
   - Demonstration: shows strength without engaging to deceive
3. **Exploitation**: Follows successful attack, prevent enemy reconstitution,
   extend penetration, destroy reserves, seize objectives in depth.
4. **Pursuit**: Catch/destroy withdrawing enemy force. Most decisive offensive operation.
   Requires direct pressure force + encircling force.

### Forms of Maneuver (ADP 3-90)
- **Envelopment**: Attack enemy flank/rear while fixing from front (single/double)
- **Turning movement**: Force enemy to abandon position by threatening rear/supply
- **Infiltration**: Small elements through/around enemy to attack rear
- **Penetration**: Attack narrow front to rupture defenses, then exploit
- **Frontal attack**: Simultaneous attack across entire front (rarely preferred)

## Defensive Operations (ADP 3-90, FM 3-0)

Defensive operations: defeat enemy attack, gain time, preserve forces, develop
conditions for future offensive operations.

### Types of Defensive Operations
1. **Area Defense**: Hold terrain. Destroy enemy in engagement area.
   Key positions must be retained. Reserve counterattacks against penetrations.
2. **Mobile Defense**: Destroy enemy with strike force. Fixing force retains
   portion of terrain; strike force (larger, more mobile) counterattacks to
   destroy enemy. Emphasizes destroying enemy over retaining terrain.
3. **Retrograde**: Organized movement away from enemy.
   - Delay: trade space for time; inflict casualties without decisive engagement
   - Withdrawal: disengage from enemy to reposition; with/without enemy pressure
   - Retirement: organized movement rearward from non-engaged unit; not under pressure

### Defensive Framework
- Preparation: occupy, organize, improve positions
- Security area: early warning, force protection, disrupt enemy
- Main Battle Area (MBA): decisive defensive action, destroy enemy
- Reserve: counterattack, reinforce, block penetration

## Rules of Engagement (ROE) — Unclassified Framework
(Based on FM 27-100 Ch.8, FM 100-23 App.D, CALL 96-6)

### Definition
ROE are directives that delineate circumstances and limitations under which US forces
initiate and/or continue combat engagement. ROE tie tactical decisions to strategy,
law of armed conflict (LOAC), and escalation management.

### ROE Authority Chain
- President/SecDef: approves SROE (Standing ROE) framework
- CJCS: issues CJCSI 3121.01B (classified SECRET; unclassified training extracts available)
- Combatant Commander (CCDR): supplements SROE for theater
- JFC/Corps Commander: supplements for JOA
- Division/BCT Commander: supplements for area of operations (AO)
ROE changes below BCT level require higher headquarters approval.

### Key ROE Definitions (Unclassified Training)
- **Hostile Act**: An attack or other use of force against US forces, US nationals,
  or forces/persons in designated areas under US protection. Includes force used to
  preclude or impede US force mission.
- **Hostile Intent**: Threat of imminent use of force against US forces/protected
  persons. Indicators: weapons orientation toward US forces, trigger pull, aggressive
  maneuver, declaration of intent to attack.
- **Positive Identification (PID)**: Reasonable certainty based on specific behaviors
  or indicators that the target is a legitimate military target. Required before
  engagement unless in self-defense against hostile act.
- **Proportionality**: Force used must not be excessive relative to anticipated
  military advantage. Applies at all levels.
- **Distinction**: Distinguish between combatants and protected persons/objects.
  Engage combatants only.

### Weapons States
- **WEAPONS FREE**: Engage any target not positively identified as friendly.
  (Most permissive; requires specific authorization in ROE card)
- **WEAPONS TIGHT**: Engage only targets positively identified as hostile per ROE.
  (Standard default state for most operations)
- **WEAPONS HOLD**: Do not engage except in self-defense (individual/unit).
  (Most restrictive; can be imposed in sensitive areas/negotiations)

### Escalation of Force (EOF) — Unclassified Training Sequence
Applied before resorting to deadly force against ambiguous targets:
1. SHOUT: verbal warnings in local language
2. SHOW: visually display weapons and intent to engage
3. SHOVE: use non-lethal means (warning shots in air/ground, physical barriers)
4. SHOOT: use lethal force as last resort, or if hostile act/intent already demonstrated

### Threat Level Framework
- **GREEN (LOW)**: Routine; no specific threat indicators. Normal movement, no
  additional force protection measures required.
- **YELLOW (GUARDED)**: General threat possible; increased vigilance.
  Enhanced observation, limit vehicle/personnel exposure.
- **AMBER (ELEVATED)**: Credible specific threat; significant possibility of attack.
  Heightened security, reduced non-essential movement, vehicles in convoy.
- **RED (HIGH)**: Attack expected or likely; specific target indicators.
  Maximum force protection, armed escort required, minimize exposure.
- **BLACK (CRITICAL)**: Attack imminent; threat is actionable.
  Lock down, only mission-essential movement, all weapons loaded/ready.

### Self-Defense Categories
- **Individual Self-Defense**: Every soldier retains inherent right to use necessary
  and proportional force to defend themselves. Cannot be restricted by ROE.
- **Unit Self-Defense**: Commander's right to use force to defend unit against
  hostile act or clear demonstration of hostile intent.
- **Extended/National Self-Defense**: Defense of other US forces, designated allied
  forces, and protected persons/civilians under immediate threat.

### ROE Card (Standard Elements)
A wallet-sized card soldiers carry. Contains:
- Who can be engaged (validated threat categories)
- Engagement conditions (hostile act/intent definitions for the operation)
- Restricted/protected areas and persons
- Weapon-specific authorizations
- Reporting requirements
- EOF procedures specific to the AO

## Operational Environments and Terrain (OAKOC — FM 3-0)

### Terrain Types and Tactical Implications
- **Open/Rolling**: Armored, mechanized forces preferred; long-range engagements;
  aviation and indirect fires highly effective; limited concealment.
- **Urban**: Infantry-intensive; limited armor/aviation utility; high CIVCAS risk;
  ROE typically restrictive; clearing operations methodical and time-intensive.
- **Forested/Jungle**: Infantry preferred; limits vehicle mobility; degrades C2/comms;
  aviation limited by canopy; enhanced concealment for all sides.
- **Mountainous/High Altitude**: Limited vehicle access; aviation degraded (altitude);
  infantry on foot; logistics challenging; observation/fields of fire extremely varied.
- **Desert/Arid**: Armored/mechanized preferred; long-range engagement; heat
  management critical; logistics (fuel/water) constrained; dust degrades optics/comms.
- **Littoral/Riverine**: Combined arms with maritime elements; amphibious operations;
  bridging/river crossing critical engineering task.

## Operational Variables: PMESII-PT (ADP 3-0)
- Political, Military, Economic, Social, Information, Infrastructure, Physical Environment, Time
Used for operational environment analysis and effects assessment.
"""

# ---------------------------------------------------------------------------
# User Stories
# ---------------------------------------------------------------------------

USER_STORIES: str = """
## User Stories for Military Tactical Decision Support Agent

US-1 (ROE Compliance Check):
As a staff judge advocate (SJA) advisor, I need the agent to verify that a proposed
fire mission or maneuver order complies with the current theater ROE, including PID
requirements, proportionality, and weapons state restrictions, so that commanders
can execute lawful orders with confidence.

US-2 (Situation Assessment):
As a battalion S2 (intelligence officer), I need the agent to assess the enemy
situation based on reported METT-TC factors — threat level, unit type, strength,
disposition, and terrain — and determine whether conditions favor offensive,
defensive, or retrograde operations.

US-3 (Course of Action Analysis):
As a brigade S3 (operations officer), I need the agent to evaluate multiple courses
of action (COAs) for an offensive or defensive task, analyzing each against the
principles of war and tenets of unified land operations (simultaneity, depth,
synchronization, flexibility), and recommend the COA most likely to succeed.

US-4 (Fire Support Coordination):
As a fire support officer (FSO), I need the agent to determine whether a fire mission
request meets CDE (collateral damage estimate) thresholds, PID criteria, and ROE
weapons state authorizations for the current AO, and recommend whether to approve,
modify, or deny the mission.

US-5 (Force Assignment and Task Organization):
As a division G3 (operations officer), I need the agent to recommend task organization
— assigning unit types (Infantry, Armor, Aviation, Artillery, SF) to tasks based on
terrain, enemy, and mission requirements — following combined arms doctrine.
"""

# ---------------------------------------------------------------------------
# Manual OWL Ontology (Turtle format)
# ---------------------------------------------------------------------------

MANUAL_ONTOLOGY_TTL: str = """@prefix : <http://coha.org/military_tactical#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/military_tactical> a owl:Ontology ;
    rdfs:label "Military Tactical Decision Support Ontology" ;
    rdfs:comment "OWL ontology grounded in ADP 3-0 (2019), ADP 3-90 (2019), FM 3-0 (2022), and unclassified ROE training materials." .

# ---------------------------------------------------------------------------
# Unit Classes (ADP 3-0, FM 3-0)
# ---------------------------------------------------------------------------

:Unit a owl:Class ;
    rdfs:label "Unit" ;
    rdfs:comment "Fundamental element of military force (ADP 3-0)." .

:ManeuverUnit a owl:Class ;
    rdfs:label "Maneuver Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "Ground maneuver force conducting offensive and defensive operations (ADP 3-90)." .

:InfantryUnit a owl:Class ;
    rdfs:label "Infantry Unit" ;
    rdfs:subClassOf :ManeuverUnit ;
    rdfs:comment "Dismounted close combat force. Effective in urban, forested, mountainous terrain (FM 3-0)." .

:ArmorUnit a owl:Class ;
    rdfs:label "Armor Unit" ;
    rdfs:subClassOf :ManeuverUnit ;
    rdfs:comment "M1A2 SEPv3 Abrams tank force. Most effective in open/semi-open terrain (FM 3-0)." .

:MechInfUnit a owl:Class ;
    rdfs:label "Mechanized Infantry Unit" ;
    rdfs:subClassOf :ManeuverUnit ;
    rdfs:comment "M2A4 Bradley IFV force. Combined arms capability across terrain types (FM 3-0)." .

:AviationUnit a owl:Class ;
    rdfs:label "Aviation Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "AH-64 Apache, UH-60, MQ-1C Gray Eagle. Provides air assault, deep attack, recon (FM 3-0)." .

:SpecialForcesUnit a owl:Class ;
    rdfs:label "Special Forces Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "12-man ODAs. UW, FID, SR, DA, CT. Operates in denied/contested areas (FM 3-0)." .

:RangerUnit a owl:Class ;
    rdfs:label "Ranger Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "75th Ranger Regiment. Light infantry for direct action raids, airfield seizure, airborne ops (FM 3-0)." .

:FieldArtilleryUnit a owl:Class ;
    rdfs:label "Field Artillery Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "M109A7 Paladin, M777, HIMARS/MLRS. Indirect fire support: suppression, neutralization, destruction (FM 3-0)." .

:AirDefenseUnit a owl:Class ;
    rdfs:label "Air Defense Artillery Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "Patriot, SHORAD. Air and missile defense. Critical for LSCO peer threats (FM 3-0)." .

:EngineerUnit a owl:Class ;
    rdfs:label "Engineer Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "Mobility (breaching, bridging), countermobility (obstacles), survivability (FM 3-0)." .

:LogisticsUnit a owl:Class ;
    rdfs:label "Logistics Unit" ;
    rdfs:subClassOf :Unit ;
    rdfs:comment "Class I, III, V, VIII sustainment. BSB provides direct support to BCT (ADP 3-0)." .

# ---------------------------------------------------------------------------
# Command Echelon Classes (ADP 3-0)
# ---------------------------------------------------------------------------

:CommandEchelon a owl:Class ;
    rdfs:label "Command Echelon" ;
    rdfs:comment "Hierarchical level of command authority (ADP 3-0)." .

:Squad a owl:Class ;
    rdfs:label "Squad" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~9 soldiers; basic tactical element (ADP 3-0)." .

:Platoon a owl:Class ;
    rdfs:label "Platoon" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~30-40 soldiers, 3-4 squads; led by lieutenant (ADP 3-0)." .

:Company a owl:Class ;
    rdfs:label "Company/Troop/Battery" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~80-150 soldiers, 3-4 platoons; led by captain (ADP 3-0)." .

:Battalion a owl:Class ;
    rdfs:label "Battalion/Squadron" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~400-800 soldiers, 3-5 companies; led by lieutenant colonel (ADP 3-0)." .

:BCT a owl:Class ;
    rdfs:label "Brigade Combat Team" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~3,000-5,000 soldiers; IBCT, ABCT, or SBCT; led by colonel (ADP 3-0)." .

:Division a owl:Class ;
    rdfs:label "Division" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~10,000-20,000 soldiers, 2-5 BCTs; led by major general (ADP 3-0)." .

:Corps a owl:Class ;
    rdfs:label "Corps" ;
    rdfs:subClassOf :CommandEchelon ;
    rdfs:comment "~40,000-100,000+ soldiers, 2-5 divisions; led by lieutenant general (ADP 3-0)." .

# ---------------------------------------------------------------------------
# Mission Classes (ADP 3-90, FM 3-0)
# ---------------------------------------------------------------------------

:Mission a owl:Class ;
    rdfs:label "Mission" ;
    rdfs:comment "Assigned task with objective, intent, and time constraint (ADP 3-0)." .

:OffensiveMission a owl:Class ;
    rdfs:label "Offensive Mission" ;
    rdfs:subClassOf :Mission ;
    rdfs:comment "Seize/retain/exploit initiative; destroy enemy forces; seize key terrain (ADP 3-90)." .

:MovementToContact a owl:Class ;
    rdfs:label "Movement to Contact" ;
    rdfs:subClassOf :OffensiveMission ;
    rdfs:comment "Gain/regain contact with enemy force. Subtypes: search-and-attack, approach march (ADP 3-90)." .

:Attack a owl:Class ;
    rdfs:label "Attack" ;
    rdfs:subClassOf :OffensiveMission ;
    rdfs:comment "Defeat enemy forces or seize terrain. Hasty or deliberate (ADP 3-90)." .

:Exploitation a owl:Class ;
    rdfs:label "Exploitation" ;
    rdfs:subClassOf :OffensiveMission ;
    rdfs:comment "Follow successful attack; prevent enemy reconstitution; seize objectives in depth (ADP 3-90)." .

:Pursuit a owl:Class ;
    rdfs:label "Pursuit" ;
    rdfs:subClassOf :OffensiveMission ;
    rdfs:comment "Catch and destroy withdrawing enemy. Most decisive offensive operation (ADP 3-90)." .

:Raid a owl:Class ;
    rdfs:label "Raid" ;
    rdfs:subClassOf :OffensiveMission ;
    rdfs:comment "Swift penetration of hostile territory for specific objective with planned withdrawal (ADP 3-90)." .

:DefensiveMission a owl:Class ;
    rdfs:label "Defensive Mission" ;
    rdfs:subClassOf :Mission ;
    rdfs:comment "Defeat enemy attack; gain time; preserve forces; develop conditions for offense (ADP 3-90)." .

:AreaDefense a owl:Class ;
    rdfs:label "Area Defense" ;
    rdfs:subClassOf :DefensiveMission ;
    rdfs:comment "Hold terrain; destroy enemy in engagement area; counterattack penetrations (ADP 3-90)." .

:MobileDefense a owl:Class ;
    rdfs:label "Mobile Defense" ;
    rdfs:subClassOf :DefensiveMission ;
    rdfs:comment "Destroy enemy with strike force; fixing force retains terrain; emphasizes destroying enemy (ADP 3-90)." .

:Retrograde a owl:Class ;
    rdfs:label "Retrograde" ;
    rdfs:subClassOf :DefensiveMission ;
    rdfs:comment "Organized movement away from enemy: delay, withdrawal, or retirement (ADP 3-90)." .

:Delay a owl:Class ;
    rdfs:label "Delay" ;
    rdfs:subClassOf :Retrograde ;
    rdfs:comment "Trade space for time; inflict casualties without decisive engagement (ADP 3-90)." .

:Withdrawal a owl:Class ;
    rdfs:label "Withdrawal" ;
    rdfs:subClassOf :Retrograde ;
    rdfs:comment "Disengage from enemy to reposition; with or without enemy pressure (ADP 3-90)." .

:StabilityMission a owl:Class ;
    rdfs:label "Stability Mission" ;
    rdfs:subClassOf :Mission ;
    rdfs:comment "Operations to establish conditions for civilian authority; security, governance, reconstruction (FM 3-0)." .

:ReconnaissanceMission a owl:Class ;
    rdfs:label "Reconnaissance Mission" ;
    rdfs:subClassOf :Mission ;
    rdfs:comment "Gather intelligence without decisive engagement; stealth posture; limited ROE (FM 3-0)." .

# ---------------------------------------------------------------------------
# Terrain Classes (FM 3-0 OAKOC)
# ---------------------------------------------------------------------------

:TerrainType a owl:Class ;
    rdfs:label "Terrain Type" ;
    rdfs:comment "Classification of operational terrain per OAKOC analysis (FM 3-0)." .

:OpenTerrain a owl:Class ;
    rdfs:label "Open Terrain" ;
    rdfs:subClassOf :TerrainType ;
    rdfs:comment "Open/rolling; favors armor, mechanized, aviation, indirect fires; limited concealment (FM 3-0)." .

:UrbanTerrain a owl:Class ;
    rdfs:label "Urban Terrain" ;
    rdfs:subClassOf :TerrainType ;
    rdfs:comment "Built-up areas; infantry-intensive; limited armor/aviation; high CIVCAS risk (FM 3-0)." .

:ForestTerrain a owl:Class ;
    rdfs:label "Forest Terrain" ;
    rdfs:subClassOf :TerrainType ;
    rdfs:comment "Forested/jungle; infantry preferred; limits vehicle mobility; degrades C2/comms (FM 3-0)." .

:MountainTerrain a owl:Class ;
    rdfs:label "Mountain Terrain" ;
    rdfs:subClassOf :TerrainType ;
    rdfs:comment "Mountainous/high altitude; limits vehicles; aviation degraded; infantry on foot (FM 3-0)." .

:DesertTerrain a owl:Class ;
    rdfs:label "Desert Terrain" ;
    rdfs:subClassOf :TerrainType ;
    rdfs:comment "Desert/arid; armor/mech preferred; heat management critical; logistics constrained (FM 3-0)." .

:LittoralTerrain a owl:Class ;
    rdfs:label "Littoral Terrain" ;
    rdfs:subClassOf :TerrainType ;
    rdfs:comment "Coastal/riverine; combined arms with maritime; bridging/river crossing critical (FM 3-0)." .

# ---------------------------------------------------------------------------
# Threat Level Classes (Unclassified ROE Training)
# ---------------------------------------------------------------------------

:ThreatLevel a owl:Class ;
    rdfs:label "Threat Level" ;
    rdfs:comment "Force protection threat level classification (Unclassified ROE training materials)." .

:ThreatLevel_GREEN a owl:Class ;
    rdfs:label "Threat Level GREEN" ;
    rdfs:subClassOf :ThreatLevel ;
    rdfs:comment "LOW: Routine; no specific threat indicators; normal movement permitted." .

:ThreatLevel_YELLOW a owl:Class ;
    rdfs:label "Threat Level YELLOW" ;
    rdfs:subClassOf :ThreatLevel ;
    rdfs:comment "GUARDED: General threat possible; increased vigilance; enhanced observation." .

:ThreatLevel_AMBER a owl:Class ;
    rdfs:label "Threat Level AMBER" ;
    rdfs:subClassOf :ThreatLevel ;
    rdfs:comment "ELEVATED: Credible specific threat; heightened security; reduced non-essential movement." .

:ThreatLevel_RED a owl:Class ;
    rdfs:label "Threat Level RED" ;
    rdfs:subClassOf :ThreatLevel ;
    rdfs:comment "HIGH: Attack expected or likely; maximum force protection; armed escort required." .

:ThreatLevel_BLACK a owl:Class ;
    rdfs:label "Threat Level BLACK" ;
    rdfs:subClassOf :ThreatLevel ;
    rdfs:comment "CRITICAL: Attack imminent; lock down; only mission-essential movement; all weapons ready." .

# ---------------------------------------------------------------------------
# ROE / Weapons State Classes (Unclassified ROE Training, FM 27-100)
# ---------------------------------------------------------------------------

:WeaponsState a owl:Class ;
    rdfs:label "Weapons State" ;
    rdfs:comment "ROE weapons control status (Unclassified ROE training materials)." .

:WeaponsState_FREE a owl:Class ;
    rdfs:label "Weapons Free" ;
    rdfs:subClassOf :WeaponsState ;
    rdfs:comment "Engage any target not positively identified as friendly. Most permissive; requires specific ROE authorization." .

:WeaponsState_TIGHT a owl:Class ;
    rdfs:label "Weapons Tight" ;
    rdfs:subClassOf :WeaponsState ;
    rdfs:comment "Engage only targets positively identified as hostile per ROE. Standard default state." .

:WeaponsState_HOLD a owl:Class ;
    rdfs:label "Weapons Hold" ;
    rdfs:subClassOf :WeaponsState ;
    rdfs:comment "Do not engage except in individual or unit self-defense. Most restrictive." .

:EngagementRule a owl:Class ;
    rdfs:label "Engagement Rule" ;
    rdfs:comment "Rules governing when and how force may be used (FM 27-100 Ch.8, CALL 96-6)." .

:EngagementRule_SelfDefenseOnly a owl:Class ;
    rdfs:label "Engagement Rule: Self-Defense Only" ;
    rdfs:subClassOf :EngagementRule ;
    rdfs:comment "Individual self-defense right only; unit cannot initiate or support offensive action." .

:EngagementRule_ReturnFireOnly a owl:Class ;
    rdfs:label "Engagement Rule: Return Fire Only" ;
    rdfs:subClassOf :EngagementRule ;
    rdfs:comment "Engage only forces that have committed a hostile act by firing on friendly forces." .

:EngagementRule_DefensiveFiresAuthorised a owl:Class ;
    rdfs:label "Engagement Rule: Defensive Fires Authorised" ;
    rdfs:subClassOf :EngagementRule ;
    rdfs:comment "Engage threats demonstrating hostile intent or hostile act; no preemptive offensive action." .

:EngagementRule_OffensiveAuthorised a owl:Class ;
    rdfs:label "Engagement Rule: Offensive Authorised" ;
    rdfs:subClassOf :EngagementRule ;
    rdfs:comment "Offensive engagement of designated, positively identified targets permitted; requires command authority." .

:EngagementRule_WeaponsFree a owl:Class ;
    rdfs:label "Engagement Rule: Weapons Free" ;
    rdfs:subClassOf :EngagementRule ;
    rdfs:comment "Engage any target not positively identified as friendly; requires explicit higher authority." .

# ---------------------------------------------------------------------------
# Object Properties
# ---------------------------------------------------------------------------

:hasCurrentThreatLevel a owl:ObjectProperty ;
    rdfs:label "has current threat level" ;
    rdfs:domain :Unit ;
    rdfs:range :ThreatLevel ;
    rdfs:comment "The current force protection threat level for the unit's operational area." .

:hasEngagementRule a owl:ObjectProperty ;
    rdfs:label "has engagement rule" ;
    rdfs:domain :Mission ;
    rdfs:range :EngagementRule ;
    rdfs:comment "Links a mission to its applicable engagement rule (ROE)." .

:hasWeaponsState a owl:ObjectProperty ;
    rdfs:label "has weapons state" ;
    rdfs:domain :Unit ;
    rdfs:range :WeaponsState ;
    rdfs:comment "Current weapons control state for the unit per ROE card." .

:operatesIn a owl:ObjectProperty ;
    rdfs:label "operates in" ;
    rdfs:domain :Unit ;
    rdfs:range :TerrainType ;
    rdfs:comment "The terrain type in which a unit is currently operating (FM 3-0 OAKOC)." .

:conductsMission a owl:ObjectProperty ;
    rdfs:label "conducts mission" ;
    rdfs:domain :Unit ;
    rdfs:range :Mission ;
    rdfs:comment "A unit conducts one or more assigned missions." .

:commandAuthorityLevel a owl:ObjectProperty ;
    rdfs:label "command authority level" ;
    rdfs:domain :Mission ;
    rdfs:range :CommandEchelon ;
    rdfs:comment "The minimum echelon that has authority to approve this mission type (ADP 3-0)." .

:supportedBy a owl:ObjectProperty ;
    rdfs:label "supported by" ;
    rdfs:domain :Unit ;
    rdfs:range :LogisticsUnit ;
    rdfs:comment "Links a combat unit to its direct support logistics unit (BSB/FSC)." .

:requiresSupport a owl:ObjectProperty ;
    rdfs:label "requires support" ;
    rdfs:domain :ArmorUnit ;
    rdfs:range :InfantryUnit ;
    rdfs:comment "Armor units require infantry support when operating in urban terrain (FM 3-0)." .

# ---------------------------------------------------------------------------
# Data Properties
# ---------------------------------------------------------------------------

:readinessPct a owl:DatatypeProperty ;
    rdfs:label "readiness percentage" ;
    rdfs:domain :Unit ;
    rdfs:range xsd:float ;
    rdfs:comment "Unit readiness as percentage (0-100%). Offensive missions require readiness commensurate with task." .

:personnelStrength a owl:DatatypeProperty ;
    rdfs:label "personnel strength" ;
    rdfs:domain :Unit ;
    rdfs:range xsd:integer ;
    rdfs:comment "Number of personnel present for duty." .

:hasPID a owl:DatatypeProperty ;
    rdfs:label "has positive identification" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Whether Positive Identification (PID) of the target has been confirmed per ROE (FM 27-100)." .

:isHostileAct a owl:DatatypeProperty ;
    rdfs:label "is hostile act" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Whether the threat has committed a hostile act (attack/use of force) against friendly forces." .

:demonstratesHostileIntent a owl:DatatypeProperty ;
    rdfs:label "demonstrates hostile intent" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Whether the threat demonstrates imminent hostile intent (weapons orientation, aggressive maneuver)." .

:isProportional a owl:DatatypeProperty ;
    rdfs:label "is proportional" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Whether the planned force is proportional to anticipated military advantage (LOAC principle)." .

# ---------------------------------------------------------------------------
# Subclass Axioms (Key Doctrine Constraints)
# ---------------------------------------------------------------------------

# WEAPONS TIGHT default: require PID before engagement
:WeaponsState_TIGHT rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :hasPID ;
    owl:minCardinality 1
] .

# Offensive mission requires engagement rule authorizing offense
:OffensiveMission rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :hasEngagementRule ;
    owl:minCardinality 1
] .

# Retrograde missions do not require offensive engagement authority
:Retrograde rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :hasEngagementRule ;
    owl:minCardinality 1
] .
"""

# ---------------------------------------------------------------------------
# Benchmark QA Dataset (30 items) — grounded in ADP 3-0, ADP 3-90, FM 3-0, ROE
# ---------------------------------------------------------------------------

BENCHMARK_QA: list = [
    # ─── ROE Verification (10 items) ─────────────────────────────────────────
    {
        "query": (
            "A rifle squad in WEAPONS TIGHT state observes an armed individual 200 meters "
            "away who has not fired and has not made a threatening gesture. The individual "
            "is carrying a weapon openly but is walking away from friendly positions. "
            "Can the squad engage under WEAPONS TIGHT?"
        ),
        "ground_truth": (
            "No. WEAPONS TIGHT requires that a target be positively identified (PID) as hostile "
            "before engagement. PID means reasonable certainty — based on specific behaviors or "
            "indicators — that the target is a legitimate military objective. An armed individual "
            "walking away, not threatening, does not meet the hostile act or hostile intent "
            "threshold. Engagement without PID under WEAPONS TIGHT violates ROE. The squad must "
            "continue to observe, report the sighting, and escalate through the EOF sequence "
            "(SHOUT/SHOW/SHOVE) if the individual approaches or demonstrates hostile intent."
        ),
        "constraint_labels": [
            "weapons_tight_requires_pid",
            "no_hostile_act_or_intent_demonstrated",
            "eof_sequence_required",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "WEAPONS TIGHT allows engagement of any armed person in a conflict zone. The squad "
            "may engage because the individual is carrying a weapon."
        ),
    },
    {
        "query": (
            "The current threat level at a forward operating base is RED (HIGH). "
            "What is the default weapons state under the standard ROE framework, "
            "and what EOF steps are still required before engaging an ambiguous vehicle "
            "approaching the gate at excessive speed?"
        ),
        "ground_truth": (
            "At ThreatLevel RED, the default weapons state is WEAPONS TIGHT — not WEAPONS FREE. "
            "WEAPONS FREE requires specific authorization even at RED. The EOF sequence is still "
            "required for ambiguous targets (vehicles/persons that have not yet committed a hostile "
            "act): (1) SHOUT — verbal warning in local language; (2) SHOW — display weapons and "
            "intent to engage; (3) SHOVE — non-lethal means such as warning shots into the ground "
            "ahead of the vehicle or barriers; (4) SHOOT — lethal force only as last resort or if "
            "the vehicle has already demonstrated hostile act/intent. ThreatLevel RED increases "
            "force protection posture but does not suspend EOF requirements for ambiguous threats."
        ),
        "constraint_labels": [
            "threat_red_default_weapons_tight",
            "eof_sequence_required",
            "weapons_free_requires_specific_authorization",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "At ThreatLevel RED the weapons state automatically becomes WEAPONS FREE. The guard "
            "can engage the approaching vehicle immediately without any warning steps."
        ),
    },
    {
        "query": (
            "A platoon leader has received a WEAPONS HOLD order for his sector during active "
            "civil-military negotiations. Enemy forces open fire on his platoon. "
            "Can the platoon return fire under WEAPONS HOLD?"
        ),
        "ground_truth": (
            "Yes. Individual and unit self-defense rights cannot be restricted by ROE, including "
            "WEAPONS HOLD. WEAPONS HOLD means do not engage except in self-defense — individual "
            "or unit. When enemy forces commit a hostile act by opening fire on the platoon, the "
            "right to return fire in self-defense is inherent and preserved at all times. The "
            "platoon may return fire proportionally to defeat the immediate threat. The platoon "
            "leader must immediately report the engagement up the chain of command and request "
            "ROE guidance for the changed situation."
        ),
        "constraint_labels": [
            "self_defense_cannot_be_restricted",
            "weapons_hold_exception_self_defense",
            "hostile_act_triggers_self_defense",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "WEAPONS HOLD is absolute. The platoon cannot return fire and must withdraw or evade "
            "regardless of incoming fire."
        ),
    },
    {
        "query": (
            "A battalion commander wants to modify the theater ROE to authorize WEAPONS FREE "
            "in his battalion's area of operations due to increased enemy activity. "
            "Does the battalion commander have authority to make this change?"
        ),
        "ground_truth": (
            "No. The ROE authority chain runs from President/SecDef (SROE framework) through CJCS, "
            "Combatant Commander, JFC/Corps, to Division/BCT commander. ROE changes below BCT level "
            "require higher headquarters approval. A battalion commander cannot unilaterally modify "
            "theater ROE or authorize WEAPONS FREE in his area. He must submit a request through "
            "the chain of command — to brigade (BCT) first, then division, then corps/JFC — with "
            "justification. The BCT commander is the lowest echelon with ROE modification authority "
            "for the area of operations."
        ),
        "constraint_labels": [
            "roe_change_requires_bct_or_higher",
            "battalion_lacks_roe_modification_authority",
            "roe_authority_chain",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "A battalion commander has full authority to set ROE within his area of operations. "
            "He can authorize WEAPONS FREE given the tactical situation."
        ),
    },
    {
        "query": (
            "A fire support officer (FSO) receives a fire mission request from a forward observer. "
            "The target grid is 300 meters from a known civilian hospital marked on the restricted "
            "target list. The weapons state is WEAPONS TIGHT. What must be verified before approving "
            "this mission?"
        ),
        "ground_truth": (
            "Multiple requirements must be verified before approval: (1) PID of the target as a "
            "legitimate military objective — WEAPONS TIGHT requires this. (2) Collateral damage "
            "estimate (CDE) — proximity to a protected facility (civilian hospital) requires "
            "proportionality analysis; the expected civilian harm must not be excessive relative to "
            "the military advantage anticipated. (3) Restricted target list — confirm the grid is not "
            "on the list and that 300m separation provides sufficient standoff for the munition "
            "selected. (4) Command authority authorization — fires near protected facilities "
            "typically require elevated approval. (5) Weapon/fuze selection to minimize blast radius. "
            "The mission should not be approved without all five verifications satisfied."
        ),
        "constraint_labels": [
            "weapons_tight_requires_pid",
            "proportionality_assessment_required",
            "protected_facilities_restriction",
            "cde_required",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "300 meters is a safe standoff distance from the hospital. The fire mission can proceed "
            "if PID is confirmed on the target."
        ),
    },
    {
        "query": (
            "Special Forces team conducting a direct action raid operates under WEAPONS TIGHT. "
            "They observe two armed military-age males who, based on pattern-of-life intelligence, "
            "are assessed as enemy combatants, but no current hostile act or hostile intent is "
            "displayed. Is engagement authorized?"
        ),
        "ground_truth": (
            "Under WEAPONS TIGHT, engagement requires PID — reasonable certainty the target is a "
            "legitimate military objective based on specific behaviors or indicators. Pattern-of-life "
            "intelligence may contribute to PID determination but must be assessed against the "
            "theater ROE's specific PID standard. If the ROE card defines PID criteria that are met "
            "by pattern-of-life and the assessed threat category, and higher command authority has "
            "validated the target as a designated objective, engagement may be authorized. If PID "
            "criteria are not fully met and no hostile act/intent is demonstrated, engagement is not "
            "authorized under WEAPONS TIGHT — the team must report and await positively established "
            "PID or a hostile act before engaging."
        ),
        "constraint_labels": [
            "weapons_tight_requires_pid",
            "pattern_of_life_alone_insufficient_for_pid",
            "roe_card_pid_standard_governs",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "Pattern-of-life intelligence is sufficient for engagement. The SF team can engage "
            "both individuals based on the intelligence assessment alone."
        ),
    },
    {
        "query": (
            "During a withdrawal under enemy pressure, a company commander considers calling "
            "for HIMARS fires on an enemy formation that is pursuing his company. "
            "The company is under WEAPONS TIGHT and has not received explicit fire support "
            "authorization from brigade. Is this fire mission ROE-compliant?"
        ),
        "ground_truth": (
            "The enemy formation actively pursuing and engaging the company constitutes a hostile "
            "act, which supports a self-defense justification for fires. However, HIMARS employment "
            "requires: (1) PID of the enemy formation — the company must confirm the target grid "
            "with sufficient certainty. (2) CDE — HIMARS rockets have significant blast radius; "
            "proportionality and civilian/friendly-force deconfliction are required. (3) Fire "
            "support authorization — HIMARS is a brigade/division asset; the fire mission must be "
            "coordinated through the FSO and cleared by brigade S3 or higher. Even in self-defense "
            "scenarios, HIMARS fires require FSO coordination and higher approval. The company "
            "commander cannot unilaterally employ HIMARS."
        ),
        "constraint_labels": [
            "himars_requires_higher_approval",
            "cde_required_for_large_munitions",
            "fso_coordination_required",
            "weapons_tight_requires_pid",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "Pursuing enemy forces are a valid target under self-defense. The company commander "
            "can call HIMARS fires without brigade approval given the immediate threat."
        ),
    },
    {
        "query": (
            "A checkpoint guard observes a local national vehicle approach at normal speed. "
            "The driver appears nervous and refuses to stop when given verbal commands. "
            "The weapons state is WEAPONS TIGHT. The guard has not yet observed any weapon. "
            "Can the guard engage the vehicle?"
        ),
        "ground_truth": (
            "No, not yet. WEAPONS TIGHT requires PID of hostile act or hostile intent. Appearing "
            "nervous and failing to stop at first command alone do not meet the hostile act or "
            "demonstrated hostile intent threshold. The EOF sequence must continue: SHOUT (repeated "
            "verbal commands in local language), SHOW (display weapons), SHOVE (warning shots into "
            "the ground in front of the vehicle or barriers/spike strips if available). The guard "
            "may use lethal force if the vehicle continues to close on the checkpoint after EOF steps "
            "and a reasonable person would conclude imminent threat to life exists — at that point "
            "hostile intent threshold may be met. Engagement before exhausting feasible EOF steps "
            "would not be ROE-compliant under WEAPONS TIGHT."
        ),
        "constraint_labels": [
            "eof_sequence_required",
            "weapons_tight_requires_pid",
            "nervousness_alone_insufficient_for_hostile_intent",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "Refusing to stop at a military checkpoint is a hostile act. The guard may engage "
            "immediately under WEAPONS TIGHT."
        ),
    },
    {
        "query": (
            "A brigade S3 wants to declare WEAPONS FREE in a designated area because all "
            "civilians have been warned to evacuate and only enemy forces are expected. "
            "What is required to implement this?"
        ),
        "ground_truth": (
            "WEAPONS FREE authorization requires explicit command authority — it is the most "
            "permissive weapons state and requires specific ROE card authorization. Even when "
            "civilians have been warned to evacuate, WEAPONS FREE must be authorized through the "
            "ROE authority chain: the BCT commander (minimum) has area ROE authority; division "
            "or corps may need to approve WEAPONS FREE declaration depending on theater SROE "
            "supplements. Requirements: (1) formal ROE supplement/fragorder authorizing WEAPONS "
            "FREE for the specific area and time window; (2) clear area boundaries that prevent "
            "accidental engagement of civilians or friendly forces outside the designated area; "
            "(3) communication to all units in/adjacent to the area. The brigade S3 must submit "
            "the request to BCT commander at minimum."
        ),
        "constraint_labels": [
            "weapons_free_requires_specific_authorization",
            "roe_authority_chain",
            "bct_minimum_for_roe_modification",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "If civilians have been warned and evacuated, the brigade S3 can declare WEAPONS FREE "
            "for the area based on operational necessity without additional approval."
        ),
    },
    {
        "query": (
            "A platoon operating at ThreatLevel AMBER (ELEVATED) has WEAPONS TIGHT ROE. "
            "They observe a group of armed men emplacing what appears to be an IED on a "
            "main supply route. Can they engage without additional authorization?"
        ),
        "ground_truth": (
            "Yes, under most theater ROE frameworks this action satisfies both PID and hostile "
            "intent thresholds. Emplacing an IED on a main supply route constitutes a hostile act "
            "being conducted against US/coalition forces — it is an act of force intended to impede "
            "or attack US forces. Under WEAPONS TIGHT, soldiers must have PID that the target is "
            "a legitimate military objective. Individuals emplacing IEDs in an active operational "
            "area, where civilians have been warned away or where the specific behavior (weapons "
            "plus IED emplacement) clearly identifies hostile combatant activity, meets the PID "
            "standard. The platoon leader should engage and report immediately. If time allows, "
            "confirm with FSO and higher that engagement is within current ROE parameters."
        ),
        "constraint_labels": [
            "ied_emplacement_as_hostile_act",
            "weapons_tight_pid_satisfied",
            "hostile_intent_demonstrated",
        ],
        "task_type": "roe_verification",
        "violating_response": (
            "The platoon cannot engage because they are under WEAPONS TIGHT and have not been "
            "fired upon. They must wait for the IED to be triggered before engaging."
        ),
    },

    # ─── Situation Assessment (10 items) ──────────────────────────────────────
    {
        "query": (
            "METT-TC analysis: An infantry battalion is tasked to defend a village (urban terrain) "
            "against an approaching enemy armored brigade. The battalion has two infantry companies "
            "and one attached M109A7 field artillery battery. Enemy has approximately 40 tanks and "
            "20 infantry fighting vehicles. ThreatLevel RED. Assess the tactical situation and "
            "identify critical gaps."
        ),
        "ground_truth": (
            "Tactical assessment: (1) TERRAIN advantage: urban terrain significantly favors "
            "the defending infantry — limited vehicle mobility, covered fighting positions, "
            "short engagement ranges that reduce armor effectiveness. (2) FORCE ratio concern: "
            "two infantry companies (~300 soldiers) against an armored brigade (~2,000 with 40 "
            "tanks) represents a significant combat power deficit. (3) FIRES capability: the "
            "M109A7 battery provides critical indirect fire support but anti-armor fires must be "
            "coordinated; FASCAM/mines for countermobility should be requested from engineers. "
            "(4) CRITICAL GAPS: no organic anti-armor beyond Javelin missiles; no engineer "
            "support for obstacle emplacement; no aviation support noted; no adjacent unit "
            "flank protection. (5) RECOMMENDATION: request additional anti-armor assets (Javelin "
            "teams, ATGM systems), engineer support, aviation deep fires on enemy armor before "
            "it reaches the MBA, and alert higher to force ratio imbalance."
        ),
        "constraint_labels": [
            "infantry_advantages_in_urban",
            "force_ratio_assessment",
            "mett_tc_analysis",
            "combined_arms_gaps",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The infantry battalion can hold the village with its current forces. Urban terrain "
            "makes armor ineffective, so the enemy tank advantage is neutralized."
        ),
    },
    {
        "query": (
            "An armored company (M1A2 SEPv3) is ordered to clear an urban district in "
            "a major city without infantry support. The company commander assesses that "
            "he can complete the mission independently. Is this assessment doctrinally sound?"
        ),
        "ground_truth": (
            "No. FM 3-0 and ADP 3-90 doctrine explicitly establishes that armor is not effective "
            "as a standalone force in urban terrain. Armored vehicles in urban areas are vulnerable "
            "to anti-armor weapons fired from elevated positions (upper floors), basements, and "
            "concealed positions at close range — environments where the tank's long-range "
            "advantage is negated. Without infantry: tanks cannot clear buildings; tanks are "
            "blind to threats at close range and in dead ground; anti-armor teams can approach "
            "undetected. The doctrinal requirement is combined arms — infantry to clear buildings "
            "and suppress close threats, armor to provide direct fire support from outside or at "
            "standoff. The company commander's assessment is not doctrinally sound; the mission "
            "must be reconfigured with attached infantry or postponed."
        ),
        "constraint_labels": [
            "armor_requires_infantry_in_urban",
            "combined_arms_doctrine",
            "urban_terrain_vulnerability",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The M1A2 SEPv3 is the most advanced tank and can operate independently in urban "
            "terrain. The company commander's assessment is sound."
        ),
    },
    {
        "query": (
            "Based on METT-TC: Friendly battalion has 72-hour mission timeline. Enemy is a "
            "reinforced infantry regiment in prepared positions on key terrain with minefields "
            "and wire obstacles. Terrain is open rolling hills with a single avenue of approach "
            "through a narrow valley. Weather: heavy rain limiting aviation. Assess which form "
            "of maneuver is most appropriate per ADP 3-90."
        ),
        "ground_truth": (
            "The tactical situation points against a frontal attack through the narrow valley, "
            "which would channel forces into prepared defenses, obstacles, and minefields — "
            "the least preferred form per ADP 3-90. The most appropriate form of maneuver "
            "depends on available flanking routes: (1) ENVELOPMENT (single or double) — if "
            "terrain permits, attack the enemy flank/rear while a fixing force holds front; "
            "avoids the obstacle belt and negates prepared positions. (2) TURNING MOVEMENT — "
            "if a force can threaten the enemy's rear/supply to compel abandonment of the "
            "key terrain without direct assault. (3) PENETRATION — if no flanking route "
            "exists, concentrate combat power at the narrowest point to rupture defenses, "
            "then exploit. Heavy rain limiting aviation degrades deep fires support, making "
            "engineer breach capabilities for obstacles more critical. Recommend envelopment "
            "if alternate terrain routes permit; penetration as secondary option with "
            "significant engineer support."
        ),
        "constraint_labels": [
            "forms_of_maneuver_adp_3_90",
            "frontal_attack_least_preferred",
            "terrain_canalization_risk",
            "weather_effects_on_aviation",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "A frontal attack through the valley is the most direct route and should be used. "
            "Obstacles can be bypassed and the M1A2 can protect against the infantry regiment."
        ),
    },
    {
        "query": (
            "A Stryker Brigade Combat Team (SBCT) has successfully attacked and penetrated "
            "enemy defensive lines. The enemy rear is disorganized. The brigade commander "
            "wants to immediately transition to exploitation. What doctrinal conditions "
            "must be met before transitioning to exploitation per ADP 3-90?"
        ),
        "ground_truth": (
            "Per ADP 3-90, exploitation follows a successful attack and requires specific "
            "conditions: (1) The initial objective must be secured — penetration is complete "
            "and the breach/rupture is consolidated. (2) The enemy must be sufficiently "
            "disorganized to prevent coherent defense of depth objectives. (3) Friendly "
            "forces must have sufficient combat power and sustainment to extend the operation "
            "— exploitation consumes logistics rapidly. (4) Exploitation forces (typically "
            "more mobile elements) must be identified and ready. (5) Command and control "
            "must be maintained — exploitation at high tempo degrades C2. (6) Reserves must "
            "be positioned to exploit success or reinforce if enemy reconstitutes. (7) "
            "Aviation and fires must be coordinated to suppress enemy reserves in depth. "
            "If sustainment is marginal, the commander must weigh operational reach against "
            "the risk of outrunning logistics support."
        ),
        "constraint_labels": [
            "exploitation_preconditions_adp_3_90",
            "sustainment_operational_reach",
            "c2_during_exploitation",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The brigade can immediately transition to exploitation. The enemy is disorganized "
            "and any delay allows them to reconstitute. Speed is the priority."
        ),
    },
    {
        "query": (
            "S2 assessment: Enemy has a battalion-sized element (infantry reinforced with "
            "artillery) occupying dominant terrain on high ground. Friendly force is an "
            "infantry company with organic weapons only — no artillery, no aviation. "
            "ThreatLevel AMBER. Assess whether this company can conduct an effective attack."
        ),
        "ground_truth": (
            "The company faces a significant disadvantage for offensive action: (1) FORCE "
            "RATIO: a company (~100-150) attacking a reinforced battalion (~600+) in "
            "prepared positions on dominant terrain is well below the doctrinal 3:1 "
            "attacker-to-defender ratio recommended for deliberate attacks against prepared "
            "positions. (2) FIRES: without artillery or aviation, the company lacks the "
            "suppression/neutralization capability to reduce the enemy on high ground. "
            "(3) TERRAIN: high ground gives defenders observation, fields of fire, and "
            "protection. (4) ASSESSMENT: Unaided, the company should not attack. "
            "Recommended actions: (a) fix the enemy in position while requesting fire "
            "support (artillery, CAS); (b) request reinforcement to achieve adequate "
            "combat power ratio; (c) conduct reconnaissance to identify covered approaches "
            "or flanking routes; (d) consider defensive action to deny enemy exploitation "
            "while building combat power for a deliberate attack."
        ),
        "constraint_labels": [
            "force_ratio_assessment",
            "combined_arms_requirements",
            "high_ground_defender_advantage",
            "mett_tc_analysis",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The infantry company should attack immediately. Speed and surprise can overcome "
            "the enemy's terrain advantage and force ratio."
        ),
    },
    {
        "query": (
            "A division is conducting mobile defense. The commander has allocated one "
            "brigade as the fixing force and one brigade as the strike force. Is this "
            "task organization consistent with mobile defense doctrine per ADP 3-90?"
        ),
        "ground_truth": (
            "Partially compliant but potentially inverted. ADP 3-90 mobile defense doctrine "
            "requires the STRIKE FORCE to be the LARGER and more mobile element — typically "
            "two-thirds or more of the available combat power — because the strike force's "
            "decisive counterattack is the primary effort. The FIXING FORCE, which retains "
            "terrain to canalize the enemy, is typically the smaller element. A 1:1 ratio "
            "(one brigade fixing, one striking) may be appropriate if each brigade has "
            "equivalent combat power, but the strike force should have greater mobility "
            "(armor/mech) to exploit the decisive counterattack window. The commander should "
            "ensure the strike force has sufficient combat power to decisively defeat the "
            "enemy main effort, and that the fixing force can hold without being overwhelmed "
            "before the strike force is committed."
        ),
        "constraint_labels": [
            "mobile_defense_strike_force_larger",
            "mobile_defense_adp_3_90",
            "fixing_force_role",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The task organization is correct. One brigade fixing and one brigade as strike "
            "force is the standard mobile defense ratio per doctrine."
        ),
    },
    {
        "query": (
            "During OAKOC terrain analysis, an S2 identifies a 2km-wide valley as a likely "
            "armored avenue of approach. The valley floor is flat with sparse vegetation; "
            "ridgelines on both sides provide observation. Enemy has positioned "
            "mechanized infantry on the ridge. What defensive recommendation does "
            "OAKOC analysis support?"
        ),
        "ground_truth": (
            "OAKOC analysis supports the following assessment and defensive recommendation: "
            "(1) OBSERVATION: ridgeline positions give enemy excellent observation of the "
            "valley floor; friendly forces in the valley are observed. (2) AVENUES OF APPROACH: "
            "the valley is a canalized avenue; armor/mech forces must use it. (3) KEY TERRAIN: "
            "the ridgelines are key terrain — control of the ridges dominates the avenue. "
            "(4) OBSTACLES: sparse vegetation offers no natural obstacles; friendly forces "
            "should emplace anti-armor obstacles (minefields, AT ditches) to canalize enemy "
            "into engagement areas. (5) COVER AND CONCEALMENT: limited for attackers on valley "
            "floor. DEFENSIVE RECOMMENDATION: position anti-armor systems on ridgelines with "
            "overwatch of the valley floor; emplace obstacles at valley entry to create "
            "engagement areas; use field artillery to cover the valley with pre-planned fires; "
            "do not defend the valley floor — hold the ridges."
        ),
        "constraint_labels": [
            "oakoc_terrain_analysis",
            "key_terrain_ridgelines",
            "engagement_area_development",
            "obstacle_planning",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The valley floor is the best defensive position because it is flat and easy to "
            "traverse for resupply. Defend from the valley floor."
        ),
    },
    {
        "query": (
            "A battalion S3 is planning a deliberate attack vs. a hasty attack against an "
            "enemy position. The tactical window is closing — intel suggests enemy "
            "reinforcements arrive in 4 hours. What does doctrine say about the "
            "tradeoffs between deliberate and hasty attack per ADP 3-90?"
        ),
        "ground_truth": (
            "ADP 3-90 describes: DELIBERATE ATTACK — detailed planning and coordination, "
            "synchronization of all available combat power, multiple branches and sequels, "
            "more preparation time yields higher synchronization and reduced risk. HASTY "
            "ATTACK — uses immediately available forces with a fragmentary order (FRAGO); "
            "speed over preparation; exploits fleeting opportunities before enemy can "
            "consolidate or be reinforced. Given the 4-hour window before reinforcement: "
            "the commander must weigh whether available forces with a FRAGO can achieve "
            "the objective before reinforcement (favoring hasty attack) vs. the risk of "
            "an under-coordinated attack against a prepared position (favoring deliberate). "
            "If forces are sufficient and the position is lightly held, a hasty attack "
            "may seize the initiative before reinforcement arrives. If the position is "
            "well-defended, a hasty attack may fail, and awaiting deliberate planning "
            "may be necessary even at the cost of facing reinforced enemy."
        ),
        "constraint_labels": [
            "deliberate_vs_hasty_attack_adp_3_90",
            "speed_initiative_tradeoff",
            "frago_hasty_attack",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "Always conduct a deliberate attack. Hasty attacks are inherently reckless and "
            "should never be used against prepared positions."
        ),
    },
    {
        "query": (
            "An S2 report states: enemy has massed 3 battalions opposite a single friendly "
            "battalion in a delay operation (retrograde). ThreatLevel BLACK (CRITICAL). "
            "What is the doctrinal assessment and recommended action for the delay force?"
        ),
        "ground_truth": (
            "ADP 3-90 describes delay as trading space for time while inflicting casualties "
            "without becoming decisively engaged. At ThreatLevel BLACK and 3:1 enemy "
            "superiority: (1) The delay force must avoid decisive engagement — its mission "
            "is to slow the enemy, not defeat them. (2) Successive delay positions must be "
            "prepared in depth on defensible terrain. (3) The delay force must maintain "
            "freedom of action to disengage — battle handover criteria and withdrawal "
            "triggers must be established. (4) Fire support (artillery, CAS if available) "
            "is critical to imposing delay without decisive engagement. (5) Higher "
            "headquarters must be notified of the force ratio — 3:1 against a delay "
            "force at BLACK is unsustainable; reinforcement or relief must be planned. "
            "(6) The delay force commander must not allow his unit to be fixed and "
            "destroyed — mission accomplishment here means time gained, not terrain held."
        ),
        "constraint_labels": [
            "delay_doctrine_adp_3_90",
            "avoid_decisive_engagement",
            "retrograde_succession_positions",
            "force_ratio_assessment",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The battalion should hold its current position and fight to the last. Retrograde "
            "is only authorized when completely out of ammunition."
        ),
    },
    {
        "query": (
            "PMESII-PT analysis: A brigade enters a recently liberated urban area. "
            "Infrastructure is damaged (no electricity, water service disrupted); "
            "local population is displaced; armed criminal groups remain active; "
            "local government is absent. What are the priority operational variables "
            "the brigade S3 should address per ADP 3-0?"
        ),
        "ground_truth": (
            "ADP 3-0 identifies PMESII-PT as the framework for operational environment analysis. "
            "Priority variables for this scenario: (1) PHYSICAL ENVIRONMENT: damaged "
            "infrastructure limits mobility and sustainment; route clearance and bridging may "
            "be required. (2) INFRASTRUCTURE: water and electricity restoration are stabilization "
            "priorities that reduce civilian grievances and enable governance. (3) SOCIAL: "
            "displaced population requires civil affairs coordination; population tracking, "
            "displaced person camps, and reestablishment of safety. (4) POLITICAL: absence "
            "of local government requires rapid civil affairs engagement to establish "
            "transitional authority and prevent power vacuum exploitation. (5) MILITARY: "
            "armed criminal groups constitute a security threat; zone clearance and disarmament "
            "operations may be required. (6) TIME: the window to establish security and "
            "restore basic services before population turns against the brigade is limited. "
            "Recommend: combine security operations with civil-military operations (CMO) "
            "simultaneously per the tenet of simultaneity (ADP 3-0)."
        ),
        "constraint_labels": [
            "pmesii_pt_adp_3_0",
            "stability_operations_framework",
            "simultaneity_tenet",
            "civil_military_operations",
        ],
        "task_type": "situation_assessment",
        "violating_response": (
            "The brigade should focus exclusively on military security operations before "
            "addressing civil considerations. Infrastructure and governance are not military tasks."
        ),
    },

    # ─── Command Recommendation (10 items) ────────────────────────────────────
    {
        "query": (
            "Mission: Breach and clear a heavily mined enemy obstacle belt to open a lane "
            "for an armored exploitation force. Available: Infantry company, Engineer platoon, "
            "Armored company, Field Artillery battery. Which unit leads the breach per "
            "combined arms doctrine, and what is the recommended task organization?"
        ),
        "ground_truth": (
            "Per FM 3-0 and ADP 3-90, breaching operations follow the doctrine of BREACH-ASSAULT "
            "FOLLOW-THROUGH combined arms breaching. ENGINEER units lead the breach with "
            "support: (1) SUPPRESS: Field Artillery (and any available direct fire support) "
            "suppresses enemy forces covering the obstacle. (2) OBSCURE: Smoke to screen "
            "the breach site. (3) SECURE: Infantry company secures the near side of the "
            "obstacle to prevent enemy counterattack on the breach force. (4) REDUCE: "
            "Engineer platoon emplaces and clears lanes through the minefield using "
            "breaching equipment (MICLIC, manual probing, or armored breacher if available). "
            "(5) ASSAULT: Infantry assaults through the cleared lane to secure the far side "
            "and expand the breach. (6) FOLLOW: Armored company follows through the lane "
            "to exploit. Recommended task organization: Engineer platoon OPCON to Infantry "
            "company for the breach; FA battery in direct support; Armor company in "
            "assault follow-through role."
        ),
        "constraint_labels": [
            "engineer_leads_breach",
            "combined_arms_breach_doctrine",
            "breaching_sequence",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "The Armored company should lead the breach — tanks can push through minefields "
            "with their armor protection. Engineers are not needed for a fast breach."
        ),
    },
    {
        "query": (
            "Commander's Intent: Destroy an enemy mechanized brigade that has penetrated "
            "friendly defensive lines. Available forces: one armored BCT, one infantry BCT, "
            "one aviation brigade (AH-64 Apaches), FA brigade. Terrain: open rolling terrain. "
            "ThreatLevel RED. ROE: WEAPONS TIGHT. Recommend task organization for "
            "a mobile defense per ADP 3-90."
        ),
        "ground_truth": (
            "Mobile defense task organization per ADP 3-90 assigns the STRIKE FORCE as "
            "the larger, more mobile element. Recommendation: (1) FIXING FORCE: Infantry "
            "BCT — infantry in prepared positions retains key terrain to canalize the enemy "
            "mechanized brigade into the engagement area; infantry is effective in defensive "
            "positions; does not need to be mobile. (2) STRIKE FORCE: Armored BCT — armor "
            "is the most mobile and lethal force for the decisive counterattack against the "
            "penetrating mechanized brigade in open terrain; armor in open rolling terrain "
            "is optimal employment. (3) DEEP FIRES: Aviation brigade (AH-64) attacks enemy "
            "reserves and follow-on forces to prevent reinforcement of the penetrating "
            "element; FA brigade provides counterfire and suppression of enemy artillery. "
            "(4) ROE NOTE: WEAPONS TIGHT — all engagement requires PID; fixed positions "
            "of enemy mechanized units provide sufficient PID for engagement. "
            "(5) Strike force executes counterattack when enemy is committed and canalized "
            "by fixing force."
        ),
        "constraint_labels": [
            "mobile_defense_strike_force_armor",
            "mobile_defense_adp_3_90",
            "aviation_deep_attack",
            "weapons_tight_pid",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "Use the Infantry BCT as the strike force because infantry is better in defensive "
            "operations. The Armored BCT should fix the enemy in position."
        ),
    },
    {
        "query": (
            "A division G3 must recommend a course of action for a pursuit operation against "
            "a withdrawing enemy corps that has been defeated in the Main Battle Area. "
            "Available: two armored BCTs, one infantry BCT, aviation brigade, corps artillery. "
            "What is the doctrinal task organization for pursuit per ADP 3-90?"
        ),
        "ground_truth": (
            "ADP 3-90 describes pursuit as the most decisive offensive operation, requiring "
            "a DIRECT PRESSURE FORCE and an ENCIRCLING FORCE: (1) DIRECT PRESSURE FORCE: "
            "maintains contact with and presses the withdrawing enemy — one armored BCT "
            "maintains relentless pressure, preventing the enemy from breaking contact, "
            "reorganizing, or establishing new defensive positions. Speed is essential. "
            "(2) ENCIRCLING FORCE: moves by a parallel or converging route to cut off the "
            "enemy's line of retreat — second armored BCT or aviation-inserted force moves "
            "to block escape routes, seize key terrain (bridges, choke points) in the "
            "enemy's rear. (3) INFANTRY BCT: follows to secure terrain, handle prisoners, "
            "and consolidate gains. (4) AVIATION BRIGADE: deep attack on enemy columns, "
            "destroy vehicle parks/refueling points, interdict escape routes. "
            "(5) CORPS ARTILLERY: provides suppression and destruction of enemy formations "
            "attempting to reorganize. Speed of exploitation is the critical factor — "
            "the enemy must not be allowed to reach a defensible position."
        ),
        "constraint_labels": [
            "pursuit_requires_direct_pressure_and_encircling_force",
            "pursuit_doctrine_adp_3_90",
            "aviation_interdiction",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "A pursuit only needs one force following the enemy. There is no need to split "
            "forces for an encircling element during a pursuit."
        ),
    },
    {
        "query": (
            "Situation: Enemy special operations forces have been reported conducting "
            "raids behind friendly lines. The terrain is dense forest (400 sq km). "
            "Mission: find, fix, and finish the enemy SOF element. Available: "
            "one infantry battalion, one SF company (ODA), ISR assets. "
            "Recommend the doctrinal approach per ADP 3-90 Movement to Contact subtypes."
        ),
        "ground_truth": (
            "ADP 3-90 identifies SEARCH AND ATTACK as the Movement to Contact subtype "
            "for find/fix/finish of dispersed enemy in complex terrain. Recommendation: "
            "(1) LEAD ELEMENT — SF company (ODAs) conducts Special Reconnaissance and "
            "initial contact; SF is optimally trained and equipped for small-unit operations "
            "in dense forest; they establish contact and fix the enemy SOF element. "
            "(2) ISR — UAV/aviation assets provide overwatch, cueing maneuver elements "
            "to enemy locations; degraded by forest canopy but useful at edges and clearings. "
            "(3) INFANTRY BATTALION — conducts cordon-and-search in sectors, using SF "
            "contact reports to orient; infantry follows to finish the fixed enemy. "
            "(4) TECHNIQUE: multiple small teams in search-and-attack to cover the area "
            "rather than linear movement to contact. (5) C2 NOTE: SF operates independently "
            "with the infantry battalion as the supported unit; deconfliction of areas is "
            "critical to prevent fratricide in dense terrain. WEAPONS TIGHT is appropriate "
            "given forest terrain and fratricide risk."
        ),
        "constraint_labels": [
            "search_and_attack_dense_terrain",
            "sf_leads_reconnaissance",
            "movement_to_contact_adp_3_90",
            "fratricide_prevention",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "Use the infantry battalion alone to sweep the forest in a line. SF forces "
            "are not needed for this type of operation."
        ),
    },
    {
        "query": (
            "Two COAs for an attack on a fortified ridge: COA-A (Penetration): "
            "concentrate two infantry battalions on a 500m front to rupture the enemy "
            "center and exploit through. COA-B (Envelopment): one battalion fixes enemy "
            "frontally while two battalions envelop the right flank through a covered "
            "draw. Both COAs have artillery support. ThreatLevel AMBER. "
            "Which COA is more consistent with ADP 3-90 doctrine and why?"
        ),
        "ground_truth": (
            "COA-B (Envelopment) is more consistent with ADP 3-90 doctrine. ADP 3-90 "
            "explicitly identifies the frontal attack and penetration as the most costly "
            "in terms of lives and materiel — used only when no other option exists. "
            "Envelopment is the preferred form of maneuver because: (1) it attacks the "
            "enemy's flank/rear where defenses are weakest; (2) it preserves friendly "
            "combat power by avoiding the most heavily fortified frontage; (3) the fixing "
            "force suppresses and deceives the enemy as to the main effort direction; "
            "(4) the covered draw provides concealment for the enveloping force. "
            "COA-A penetration concentrates two battalions on a narrow front against "
            "prepared positions — high attrition, lower probability of success against "
            "a fortified ridge. COA-B is the doctrinally preferred option unless the "
            "terrain in the draw is impassable or heavily defended."
        ),
        "constraint_labels": [
            "envelopment_preferred_adp_3_90",
            "frontal_attack_costly",
            "forms_of_maneuver_doctrine",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "COA-A is better because concentrating all combat power on a narrow front "
            "creates decisive mass and achieves penetration quickly."
        ),
    },
    {
        "query": (
            "A brigade is transitioning from offensive to defensive operations after "
            "reaching a phase line. The S3 must recommend the type of defense. "
            "The mission is to hold the phase line for 48 hours against expected "
            "enemy counterattack while corps reorganizes. Terrain is urban/semi-urban. "
            "Recommend defense type per ADP 3-90."
        ),
        "ground_truth": (
            "AREA DEFENSE is the appropriate choice. ADP 3-90 prescribes area defense "
            "when the mission is to HOLD TERRAIN — the brigade must retain the phase line "
            "for 48 hours, which is a terrain-retention mission. Area defense: (1) establishes "
            "key positions on dominant terrain that must be retained; (2) organizes engagement "
            "areas to destroy the enemy counterattack; (3) positions a reserve to counterattack "
            "enemy penetrations. MOBILE DEFENSE is appropriate when the commander's intent is "
            "to DESTROY THE ENEMY FORCE using a strike force — not the mission here. "
            "Urban/semi-urban terrain further favors area defense because buildings provide "
            "ready fighting positions and limit enemy maneuver. RETROGRADE is inappropriate "
            "because the mission explicitly requires holding. Recommendation: organize two "
            "battalions in the MBA, one battalion as reserve, with engineer support for "
            "obstacle emplacement to canalize enemy counterattack into engagement areas."
        ),
        "constraint_labels": [
            "area_defense_for_terrain_retention",
            "area_defense_adp_3_90",
            "engagement_area_development",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "Mobile defense is best because it gives the brigade flexibility. The brigade "
            "should not stay in fixed positions during a counterattack."
        ),
    },
    {
        "query": (
            "A division G3 has four unit types available for four tasks: (1) deep reconnaissance "
            "60km behind enemy lines, (2) air assault on enemy command post in mountainous terrain, "
            "3) deliberate attack on enemy armor formation in open desert, (4) engineer "
            "river crossing preparation. Task-organize per combined arms doctrine (FM 3-0, ADP 3-0)."
        ),
        "ground_truth": (
            "Doctrine-based task organization: (1) DEEP RECONNAISSANCE: Special Forces (ODA) — "
            "SF is the doctrinal force for Special Reconnaissance in denied/contested areas; "
            "operates 60km behind enemy lines with indigenous force integration if required. "
            "(2) AIR ASSAULT on mountain command post: Aviation unit (UH-60 assault with "
            "AH-64 escort) and Ranger/Infantry unit — air assault operations combine aviation "
            "for insertion with Ranger/light infantry for the objective clearance in "
            "mountainous terrain where vehicles cannot operate; Ranger Regiment is optimized "
            "for airfield/command post seizure (direct action). (3) DELIBERATE ATTACK against "
            "armor in desert: Armored BCT (ABCT) — M1A2 in open desert is optimal employment; "
            "desert terrain favors armor's long-range fires; ABCT with organic Bradleys provides "
            "combined arms. (4) RIVER CROSSING: Engineer unit — river crossing is a primary "
            "engineer mission (bridging, rafting, assault crossing); maneuver units are supported "
            "by engineers for this task."
        ),
        "constraint_labels": [
            "sf_deep_reconnaissance",
            "aviation_air_assault",
            "armor_open_terrain",
            "engineer_river_crossing",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "Use infantry for all four tasks. Infantry is the most versatile force and can "
            "accomplish any mission with sufficient numbers."
        ),
    },
    {
        "query": (
            "A battalion commander is planning a raid on a suspected enemy ammunition "
            "cache in an urban area. The raid must be executed within 2 hours based on "
            "perishable intelligence. WEAPONS TIGHT. ThreatLevel AMBER. "
            "What are the minimum pre-mission requirements before execution per doctrine?"
        ),
        "ground_truth": (
            "Minimum pre-mission requirements for the raid: (1) PID CONFIRMATION: WEAPONS "
            "TIGHT requires PID of the target location as a legitimate military objective. "
            "The intelligence must establish reasonable certainty — pattern-of-life, "
            "HUMINT, ISR confirmation — that the cache exists at the location and is not "
            "a civilian structure. (2) ROE/AUTHORITIES: confirm raid is authorized at "
            "appropriate command level; offensive action at AMBER requires explicit "
            "authorization. (3) CDE: urban terrain — collateral damage estimate must "
            "assess civilian presence at target and adjacent structures. (4) FIRE PLAN: "
            "identify on-call fires; ROE restrictions for fires in urban terrain. "
            "(5) EXFIL PLAN: raid has planned withdrawal; must be confirmed before "
            "execution. (6) FRATRICIDE PREVENTION: ensure no friendly or civilian "
            "personnel in the objective area; deconflict with any adjacent operations. "
            "(7) COMMUNICATION PLAN: radio frequencies, call signs, and higher HQ "
            "coordination. All six must be confirmed; 2-hour window is feasible if "
            "FRAGO is issued immediately."
        ),
        "constraint_labels": [
            "raid_preconditions",
            "weapons_tight_pid",
            "cde_urban_terrain",
            "roe_authorization",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "Perishable intelligence means speed is the priority. Execute the raid "
            "immediately and confirm PID on arrival at the objective."
        ),
    },
    {
        "query": (
            "After a successful penetration, a mechanized infantry battalion is exploiting "
            "and has outrun its logistics train by 80km. Fuel is at 20% and ammunition at "
            "30%. The exploitation objective is 40km further. What should the commander "
            "do per ADP 3-0 sustainment and operational reach doctrine?"
        ),
        "ground_truth": (
            "ADP 3-0 identifies sustainment as a warfighting function that directly affects "
            "OPERATIONAL REACH — the distance a force can operate without replenishment. "
            "At 20% fuel and 30% ammunition, the battalion has insufficient sustainment "
            "to advance 40km and conduct a fight at the exploitation objective. Required "
            "actions: (1) HALT: halt the exploitation advance at a defensible position and "
            "establish a hasty defense to protect the force while awaiting resupply. "
            "(2) REPORT: immediately report sustainment status to brigade; request emergency "
            "Class III (fuel) and Class V (ammunition) resupply; request HEMTT/PLS forward "
            "delivery or aviation resupply (FARP) if available. (3) MAINTAIN CONTACT: "
            "keep contact with withdrawing enemy to prevent reconstitution if possible "
            "without advancing. (4) ASSESS RISK: advancing with current supply risks "
            "culmination and potential encirclement — an unsupported unit at the "
            "exploitation objective is tactically unacceptable. (5) DO NOT ADVANCE until "
            "minimum 60% fuel and 60% ammunition is restored."
        ),
        "constraint_labels": [
            "operational_reach_sustainment",
            "culmination_risk",
            "exploitation_logistics",
            "adp_3_0_sustainment",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "Continue the exploitation. Speed is the critical factor and the enemy must "
            "not be allowed to reconstitute. Low fuel and ammunition can be managed."
        ),
    },
    {
        "query": (
            "A regiment-sized enemy force is withdrawing under pressure. The corps G3 "
            "must choose between two follow-on operations: COA-A (exploitation by "
            "two armored BCTs to seize objectives in depth) vs. COA-B (consolidate "
            "current positions and prepare a deliberate attack). Corps has adequate "
            "sustainment for one more 72-hour operation. Threat Level AMBER. "
            "What does ADP 3-90 recommend?"
        ),
        "ground_truth": (
            "ADP 3-90 recommends COA-A (exploitation). The fundamental principle is that "
            "an exploitation following a successful attack must be executed immediately "
            "to prevent enemy reconstitution and preserve the momentum of success. "
            "Key doctrine points: (1) Exploitation extends the penetration, destroys "
            "enemy reserves, seizes objectives in depth, and prevents the enemy from "
            "establishing new defensive positions. (2) A withdrawing enemy is at maximum "
            "vulnerability — delay allows them to break contact, reorganize, and occupy "
            "prepared positions in depth, requiring a new deliberate attack at higher cost. "
            "(3) Corps has sustainment for 72 hours of follow-on operations — adequate "
            "to exploit if armored BCTs move immediately. (4) The tenet of DEPTH (ADP "
            "3-0) requires extending operations in time and space to defeat the enemy in "
            "depth rather than allowing them to reset. COA-B surrenders initiative and "
            "allows the enemy to reconstitute — doctrinal failure to exploit success."
        ),
        "constraint_labels": [
            "exploitation_follow_success",
            "depth_tenet_adp_3_0",
            "prevent_enemy_reconstitution",
            "initiative_maintenance",
        ],
        "task_type": "command_recommendation",
        "violating_response": (
            "COA-B is correct. Consolidating after a successful attack conserves combat "
            "power and allows for a more deliberate and lower-risk follow-on operation."
        ),
    },
]
