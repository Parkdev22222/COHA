"""
Military domain documentation and user stories.

DOMAIN_DOCS: built-in summary of ADP 3-0 / ADP 3-90 / FM 3-0 / ROE materials.

At module load time, if domain/ADP_3-90.pdf is present, its full text replaces
the built-in summary as the authoritative doctrine corpus for DK grounding and
gold standard generation. Place the PDF at:

    <repo_root>/domain/ADP_3-90.pdf

then run: python domain/build_gold_standard.py  (to regenerate gold_standard.ttl)
"""
import logging as _logging
import os as _os

_logger = _logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain Documentation
# ---------------------------------------------------------------------------

DOMAIN_DOCS: str = """
# US Army Tactical Decision Support -- Based on ADP 3-0 (2019), ADP 3-90 (2019), FM 3-0 (2022)

## Source Documents
This domain is derived from the following publicly available US Army doctrine publications:
- ADP 3-0, Operations (July 2019) -- Army Publishing Directorate
- ADP 3-90, Offense and Defense (July 2019) -- Army Publishing Directorate
- FM 3-0, Operations (October 2022) -- Army Publishing Directorate
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
- Terrain and Weather: OAKOC -- Observation/fields of fire, Avenues of approach,
  Key terrain, Obstacles, Cover and concealment
- Troops and support available: unit readiness, attached/OPCON units
- Time available: planning time, movement time, preparation time
- Civil considerations: ASCOPE -- Areas, Structures, Capabilities, Organizations, People, Events

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

## Rules of Engagement (ROE) -- Unclassified Framework
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

### Escalation of Force (EOF) -- Unclassified Training Sequence
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

## Operational Environments and Terrain (OAKOC -- FM 3-0)

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
situation based on reported METT-TC factors -- threat level, unit type, strength,
disposition, and terrain -- and determine whether conditions favor offensive,
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
-- assigning unit types (Infantry, Armor, Aviation, Artillery, SF) to tasks based on
terrain, enemy, and mission requirements -- following combined arms doctrine.
"""

# ---------------------------------------------------------------------------
# Auto-load from PDF if present (overrides built-in summary)
# ---------------------------------------------------------------------------

_PDF_PATH = _os.path.join(_os.path.dirname(__file__), "ADP_3-90.pdf")

if _os.path.exists(_PDF_PATH):
    try:
        from domain.pdf_loader import load_pdf_text as _load_pdf
        _pdf_text = _load_pdf(_PDF_PATH)
        if _pdf_text.strip():
            DOMAIN_DOCS = _pdf_text
            _logger.info(f"DOMAIN_DOCS: loaded from PDF ({len(DOMAIN_DOCS)} chars)")
    except Exception as _e:
        _logger.warning(f"ADP_3-90.pdf found but could not be loaded — using built-in docs: {_e}")
