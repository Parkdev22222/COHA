"""
Military domain CQ benchmark: 60 Competency Questions across 3 sub-domains.
Based on FM 3-0, JP 3-0, ADP 3-0, ADP 3-90.
"""
from typing import List, Dict

# == Sub-domain 1: Tactical Ground Operations (CQ1-20) ========================

TACTICAL_GROUND_CQS: List[Dict] = [
    {
        "id": "TG01", "subdomain": "tactical_ground",
        "question": "Which units hold engagement rules permitted under threat level RED?",
        "key_entities": ["Unit", "EngagementRule", "ThreatLevel"],
    },
    {
        "id": "TG02", "subdomain": "tactical_ground",
        "question": "What terrain types are suitable for armored unit operations?",
        "key_entities": ["ArmorUnit", "TerrainType", "operatesIn"],
    },
    {
        "id": "TG03", "subdomain": "tactical_ground",
        "question": "Which missions require a minimum readiness percentage of 80%?",
        "key_entities": ["Mission", "Unit", "readinessPct"],
    },
    {
        "id": "TG04", "subdomain": "tactical_ground",
        "question": "What fire support assets are assigned to support an infantry battalion conducting a deliberate attack?",
        "key_entities": ["FireSupportAsset", "InfantryUnit", "Mission", "supportedBy"],
    },
    {
        "id": "TG05", "subdomain": "tactical_ground",
        "question": "Which engagement rules apply when weapons state is WEAPONS TIGHT and a hostile act has been committed?",
        "key_entities": ["EngagementRule", "WeaponsState", "hostileAct"],
    },
    {
        "id": "TG06", "subdomain": "tactical_ground",
        "question": "What is the doctrinal sequence of escalation of force steps before lethal engagement?",
        "key_entities": ["EscalationOfForce", "EngagementRule", "WeaponsState"],
    },
    {
        "id": "TG07", "subdomain": "tactical_ground",
        "question": "Which unit types require infantry support when operating in urban terrain?",
        "key_entities": ["ArmorUnit", "InfantryUnit", "UrbanTerrain", "requiresSupport"],
    },
    {
        "id": "TG08", "subdomain": "tactical_ground",
        "question": "What forms of maneuver are available for an attack against a fortified position?",
        "key_entities": ["FormOfManeuver", "Attack", "DefensivePosition"],
    },
    {
        "id": "TG09", "subdomain": "tactical_ground",
        "question": "Which units are assigned to conduct search-and-attack operations in forested terrain?",
        "key_entities": ["Unit", "MovementToContact", "ForestTerrain"],
    },
    {
        "id": "TG10", "subdomain": "tactical_ground",
        "question": "What are the preconditions for transitioning from attack to exploitation operations?",
        "key_entities": ["Attack", "Exploitation", "Mission", "precondition"],
    },
    {
        "id": "TG11", "subdomain": "tactical_ground",
        "question": "Which unit echelons have authority to modify engagement rules within their area of operations?",
        "key_entities": ["CommandEchelon", "EngagementRule", "BCT", "Division"],
    },
    {
        "id": "TG12", "subdomain": "tactical_ground",
        "question": "What logistics classes are consumed by an armored BCT during a 72-hour offensive operation?",
        "key_entities": ["LogisticsClass", "ArmorUnit", "OffensiveMission", "sustainmentRequires"],
    },
    {
        "id": "TG13", "subdomain": "tactical_ground",
        "question": "Which terrain types degrade aviation unit effectiveness?",
        "key_entities": ["AviationUnit", "TerrainType", "ForestTerrain", "MountainTerrain"],
    },
    {
        "id": "TG14", "subdomain": "tactical_ground",
        "question": "What are the key terrain features identified during OAKOC terrain analysis?",
        "key_entities": ["TerrainAnalysis", "KeyTerrain", "ObservationField", "AvenueOfApproach"],
    },
    {
        "id": "TG15", "subdomain": "tactical_ground",
        "question": "Which defensive operation type is appropriate when the mission is to hold terrain for 48 hours?",
        "key_entities": ["AreaDefense", "MobileDefense", "DefensiveMission", "terrainRetention"],
    },
    {
        "id": "TG16", "subdomain": "tactical_ground",
        "question": "What weapons systems are organic to an infantry platoon for anti-armor defense?",
        "key_entities": ["InfantryUnit", "Platoon", "WeaponSystem", "antiArmor"],
    },
    {
        "id": "TG17", "subdomain": "tactical_ground",
        "question": "Which unit types lead the breach of a mined obstacle belt?",
        "key_entities": ["EngineerUnit", "ObstacleBelt", "BreachOperation", "leadsBreaching"],
    },
    {
        "id": "TG18", "subdomain": "tactical_ground",
        "question": "What threat level triggers maximum force protection posture with armed escort requirements?",
        "key_entities": ["ThreatLevel", "ThreatLevel_RED", "ForceProtection", "armedEscort"],
    },
    {
        "id": "TG19", "subdomain": "tactical_ground",
        "question": "Which missions conducted by Special Forces units require indigenous force integration?",
        "key_entities": ["SpecialForcesUnit", "Mission", "UnconventionalWarfare", "indigenousForce"],
    },
    {
        "id": "TG20", "subdomain": "tactical_ground",
        "question": "What is the doctrinal force ratio required for a deliberate attack against prepared defensive positions?",
        "key_entities": ["Attack", "DefensivePosition", "forceRatio", "deliberateAttack"],
    },
]

# == Sub-domain 2: Command and Control (CQ21-40) ==============================

C2_CQS: List[Dict] = [
    {
        "id": "C201", "subdomain": "command_and_control",
        "question": "Which command post is responsible for coordinating fires and maneuver at brigade level?",
        "key_entities": ["CommandPost", "BCT", "FireSupportCoordination", "ManeuverCoordination"],
    },
    {
        "id": "C202", "subdomain": "command_and_control",
        "question": "What order type is issued for immediate tactical changes without full deliberate planning?",
        "key_entities": ["OrderType", "FragmentaryOrder", "FRAGO", "hastyAttack"],
    },
    {
        "id": "C203", "subdomain": "command_and_control",
        "question": "Which reporting chain is used to escalate ROE modification requests from battalion to theater?",
        "key_entities": ["ReportingChain", "EngagementRule", "Battalion", "BCT", "Corps"],
    },
    {
        "id": "C204", "subdomain": "command_and_control",
        "question": "What intelligence summary products does the S2 produce to support the commander's decision cycle?",
        "key_entities": ["IntelSummary", "S2", "DecisionPoint", "Intelligence"],
    },
    {
        "id": "C205", "subdomain": "command_and_control",
        "question": "At which decision point does the brigade commander commit the reserve force?",
        "key_entities": ["DecisionPoint", "Reserve", "Brigade", "CommandPost"],
    },
    {
        "id": "C206", "subdomain": "command_and_control",
        "question": "Which command echelon has authority to approve a WEAPONS FREE declaration?",
        "key_entities": ["CommandEchelon", "WeaponsState_FREE", "BCT", "Division", "approvalAuthority"],
    },
    {
        "id": "C207", "subdomain": "command_and_control",
        "question": "What is the standard format for an operations order (OPORD) issued at battalion level?",
        "key_entities": ["OrderType", "OPORD", "Battalion", "situation", "mission", "execution"],
    },
    {
        "id": "C208", "subdomain": "command_and_control",
        "question": "Which staff section is responsible for coordinating CSS and sustainment planning?",
        "key_entities": ["StaffSection", "S4", "Sustainment", "LogisticsUnit", "CSSCoordination"],
    },
    {
        "id": "C209", "subdomain": "command_and_control",
        "question": "How does the commander's intent flow from corps to battalion level?",
        "key_entities": ["CommandersIntent", "Corps", "Division", "BCT", "Battalion", "orderHierarchy"],
    },
    {
        "id": "C210", "subdomain": "command_and_control",
        "question": "What are the required elements of a warning order (WARNO) issued before an OPORD?",
        "key_entities": ["OrderType", "WARNO", "situation", "missionTasks", "movementTime"],
    },
    {
        "id": "C211", "subdomain": "command_and_control",
        "question": "Which command relationships authorize a unit to receive tactical direction from another unit?",
        "key_entities": ["CommandRelationship", "OPCON", "TACON", "ADCON", "Unit"],
    },
    {
        "id": "C212", "subdomain": "command_and_control",
        "question": "What triggers a battle handover during a retrograde operation?",
        "key_entities": ["BattleHandover", "Retrograde", "TriggerLine", "CommandPost"],
    },
    {
        "id": "C213", "subdomain": "command_and_control",
        "question": "Which fire support coordination measures (FSCMs) are established to protect friendly forces during offensive operations?",
        "key_entities": ["FSCM", "FireSupportCoordination", "CoordinatedFireLine", "NoFireArea"],
    },
    {
        "id": "C214", "subdomain": "command_and_control",
        "question": "What communication architecture is used by the BCT main command post during large-scale combat operations?",
        "key_entities": ["CommunicationArchitecture", "CommandPost", "BCT", "RadioNet", "C2Network"],
    },
    {
        "id": "C215", "subdomain": "command_and_control",
        "question": "Which staff sections participate in the military decision-making process (MDMP)?",
        "key_entities": ["MDMP", "StaffSection", "S2", "S3", "S4", "CommandPost"],
    },
    {
        "id": "C216", "subdomain": "command_and_control",
        "question": "What is the relationship between the main command post and the tactical command post during an attack?",
        "key_entities": ["MainCommandPost", "TacticalCommandPost", "Attack", "commanderLocation"],
    },
    {
        "id": "C217", "subdomain": "command_and_control",
        "question": "How are priority intelligence requirements (PIRs) tasked to collection assets at brigade level?",
        "key_entities": ["PIR", "CollectionAsset", "Brigade", "S2", "IntelligenceTask"],
    },
    {
        "id": "C218", "subdomain": "command_and_control",
        "question": "What order type authorizes a subordinate unit to conduct a raid with time-sensitive intelligence?",
        "key_entities": ["OrderType", "FRAGO", "Raid", "timeSensitiveIntelligence"],
    },
    {
        "id": "C219", "subdomain": "command_and_control",
        "question": "Which echelon maintains the common operational picture (COP) for the corps area of operations?",
        "key_entities": ["CommonOperationalPicture", "Corps", "CommandPost", "situationalAwareness"],
    },
    {
        "id": "C220", "subdomain": "command_and_control",
        "question": "What sustainment reporting cycle is required for Class III and V resupply during combat operations?",
        "key_entities": ["SustainmentReport", "LogisticsClass", "ClassIII", "ClassV", "resupplyCycle"],
    },
]

# == Sub-domain 3: ISR/Intelligence (CQ41-60) =================================

ISR_CQS: List[Dict] = [
    {
        "id": "ISR01", "subdomain": "isr_intelligence",
        "question": "Which sensor platforms are tasked to collect on high-priority targets in contested airspace?",
        "key_entities": ["SensorPlatform", "TargetEntity", "contesetdAirspace", "ISRTask"],
    },
    {
        "id": "ISR02", "subdomain": "isr_intelligence",
        "question": "What observation events trigger an update to the threat assessment for a named area of interest?",
        "key_entities": ["ObservationEvent", "ThreatAssessment", "NamedAreaOfInterest", "trigger"],
    },
    {
        "id": "ISR03", "subdomain": "isr_intelligence",
        "question": "Which target entities are classified as high-value targets requiring division-level engagement authority?",
        "key_entities": ["TargetEntity", "HighValueTarget", "Division", "engagementAuthority"],
    },
    {
        "id": "ISR04", "subdomain": "isr_intelligence",
        "question": "What are the priority intelligence requirements that drive collection planning for an armored BCT?",
        "key_entities": ["PriorityIntelRequirement", "CollectionPlanning", "ArmorUnit", "BCT"],
    },
    {
        "id": "ISR05", "subdomain": "isr_intelligence",
        "question": "Which ISR assets are organic to a brigade combat team for tactical-level collection?",
        "key_entities": ["SensorPlatform", "BCT", "organicISR", "UAV", "SIGINT"],
    },
    {
        "id": "ISR06", "subdomain": "isr_intelligence",
        "question": "How does a threat assessment change when a target entity transitions from suspected to confirmed hostile?",
        "key_entities": ["ThreatAssessment", "TargetEntity", "suspectedHostile", "confirmedHostile"],
    },
    {
        "id": "ISR07", "subdomain": "isr_intelligence",
        "question": "What minimum observation events are required to confirm enemy artillery position for counter-fire?",
        "key_entities": ["ObservationEvent", "EnemyArtillery", "CounterFireTarget", "confirmationThreshold"],
    },
    {
        "id": "ISR08", "subdomain": "isr_intelligence",
        "question": "Which sensor platform types provide ground moving target indication (GMTI) data?",
        "key_entities": ["SensorPlatform", "GMTI", "GroundSurveillance", "RadarPlatform"],
    },
    {
        "id": "ISR09", "subdomain": "isr_intelligence",
        "question": "What is the relationship between a named area of interest and a targeted area of interest in ISR planning?",
        "key_entities": ["NamedAreaOfInterest", "TargetedAreaOfInterest", "ISRPlanning", "collectionZone"],
    },
    {
        "id": "ISR10", "subdomain": "isr_intelligence",
        "question": "Which intelligence disciplines are represented in an all-source intelligence fusion cell?",
        "key_entities": ["IntelligenceDiscipline", "SIGINT", "HUMINT", "IMINT", "FusionCell"],
    },
    {
        "id": "ISR11", "subdomain": "isr_intelligence",
        "question": "What threat assessment level triggers a request for theater-level ISR asset support?",
        "key_entities": ["ThreatAssessment", "ThreatLevel", "ISRAsset", "theaterISR", "requestAuthority"],
    },
    {
        "id": "ISR12", "subdomain": "isr_intelligence",
        "question": "Which target entities require special handling instructions due to protected status under LOAC?",
        "key_entities": ["TargetEntity", "ProtectedStatus", "LOAC", "CivilianObject", "MedicalFacility"],
    },
    {
        "id": "ISR13", "subdomain": "isr_intelligence",
        "question": "What observation events from HUMINT sources are required to update the enemy order of battle?",
        "key_entities": ["ObservationEvent", "HUMINT", "OrderOfBattle", "EnemyUnit", "S2"],
    },
    {
        "id": "ISR14", "subdomain": "isr_intelligence",
        "question": "Which sensor platforms are degraded in their collection capability by adverse weather conditions?",
        "key_entities": ["SensorPlatform", "WeatherCondition", "IMINT", "UAV", "degradedCapability"],
    },
    {
        "id": "ISR15", "subdomain": "isr_intelligence",
        "question": "How are priority intelligence requirements linked to decision points in the commander's decision cycle?",
        "key_entities": ["PriorityIntelRequirement", "DecisionPoint", "CommandersDecision", "S2"],
    },
    {
        "id": "ISR16", "subdomain": "isr_intelligence",
        "question": "What target entity attributes must be confirmed before a time-sensitive target is approved for engagement?",
        "key_entities": ["TargetEntity", "TimeSensitiveTarget", "PID", "engagementApproval", "ThreatAssessment"],
    },
    {
        "id": "ISR17", "subdomain": "isr_intelligence",
        "question": "Which collection assets have persistent surveillance capability for a 24-hour period over a target area?",
        "key_entities": ["SensorPlatform", "PersistentSurveillance", "UAV", "MQ1C", "TargetArea"],
    },
    {
        "id": "ISR18", "subdomain": "isr_intelligence",
        "question": "What is the required reporting timeline for an observation event involving enemy indirect fire activity?",
        "key_entities": ["ObservationEvent", "IndirectFire", "ReportingTimeline", "SALUTE", "ISOPREP"],
    },
    {
        "id": "ISR19", "subdomain": "isr_intelligence",
        "question": "Which ISR synchronization matrix products are produced to deconflict collection asset employment?",
        "key_entities": ["ISRSynchronizationMatrix", "CollectionAsset", "deconfliction", "S2", "S3"],
    },
    {
        "id": "ISR20", "subdomain": "isr_intelligence",
        "question": "What threat assessment products does the S2 provide to support targeting at brigade and above?",
        "key_entities": ["ThreatAssessment", "TargetingProduct", "S2", "Brigade", "HVT", "HPT"],
    },
]

ALL_CQS: List[Dict] = TACTICAL_GROUND_CQS + C2_CQS + ISR_CQS

# == Gold Standard Ontology (LLM-assisted, reviewed against FM 3-0 / FM 6-0) ==
# Construction: Claude 3.5 Sonnet generated initial schema covering all 60 CQs;
# reviewed for structural correctness and domain validity against U.S. Army doctrine.
# Used as relative upper-bound reference for SC metric only — not absolute ground truth.
# Generator model (EXAONE-4.0-32B) differs from gold constructor (Claude 3.5 Sonnet)
# to reduce circular evaluation bias.

GOLD_STANDARD_TTL: str = """
@prefix : <http://coha.org/military#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/military> a owl:Ontology ;
    rdfs:label "Military Tactical Ontology Gold Standard" ;
    rdfs:comment "Upper-bound reference ontology covering all 60 CQs across 3 sub-domains." .

# --- Tactical Ground: Unit Hierarchy ---

:Unit a owl:Class ; rdfs:label "Unit" .
:ManeuverUnit a owl:Class ; rdfs:label "Maneuver Unit" ; rdfs:subClassOf :Unit .
:InfantryUnit a owl:Class ; rdfs:label "Infantry Unit" ; rdfs:subClassOf :ManeuverUnit .
:ArmorUnit a owl:Class ; rdfs:label "Armor Unit" ; rdfs:subClassOf :ManeuverUnit .
:MechInfUnit a owl:Class ; rdfs:label "Mechanized Infantry Unit" ; rdfs:subClassOf :ManeuverUnit .
:AviationUnit a owl:Class ; rdfs:label "Aviation Unit" ; rdfs:subClassOf :Unit .
:SpecialForcesUnit a owl:Class ; rdfs:label "Special Forces Unit" ; rdfs:subClassOf :Unit .
:RangerUnit a owl:Class ; rdfs:label "Ranger Unit" ; rdfs:subClassOf :Unit .
:FieldArtilleryUnit a owl:Class ; rdfs:label "Field Artillery Unit" ; rdfs:subClassOf :Unit .
:AirDefenseUnit a owl:Class ; rdfs:label "Air Defense Unit" ; rdfs:subClassOf :Unit .
:EngineerUnit a owl:Class ; rdfs:label "Engineer Unit" ; rdfs:subClassOf :Unit .
:LogisticsUnit a owl:Class ; rdfs:label "Logistics Unit" ; rdfs:subClassOf :Unit .
:MilitaryIntelligenceUnit a owl:Class ; rdfs:label "Military Intelligence Unit" ; rdfs:subClassOf :Unit .

# --- Command Echelons ---

:CommandEchelon a owl:Class ; rdfs:label "Command Echelon" .
:Squad a owl:Class ; rdfs:label "Squad" ; rdfs:subClassOf :CommandEchelon .
:Platoon a owl:Class ; rdfs:label "Platoon" ; rdfs:subClassOf :CommandEchelon .
:Company a owl:Class ; rdfs:label "Company" ; rdfs:subClassOf :CommandEchelon .
:Battalion a owl:Class ; rdfs:label "Battalion" ; rdfs:subClassOf :CommandEchelon .
:BCT a owl:Class ; rdfs:label "Brigade Combat Team" ; rdfs:subClassOf :CommandEchelon .
:Division a owl:Class ; rdfs:label "Division" ; rdfs:subClassOf :CommandEchelon .
:Corps a owl:Class ; rdfs:label "Corps" ; rdfs:subClassOf :CommandEchelon .

# --- Missions ---

:Mission a owl:Class ; rdfs:label "Mission" .
:OffensiveMission a owl:Class ; rdfs:label "Offensive Mission" ; rdfs:subClassOf :Mission .
:MovementToContact a owl:Class ; rdfs:label "Movement to Contact" ; rdfs:subClassOf :OffensiveMission .
:Attack a owl:Class ; rdfs:label "Attack" ; rdfs:subClassOf :OffensiveMission .
:DeliberateAttack a owl:Class ; rdfs:label "Deliberate Attack" ; rdfs:subClassOf :Attack .
:HastyAttack a owl:Class ; rdfs:label "Hasty Attack" ; rdfs:subClassOf :Attack .
:Exploitation a owl:Class ; rdfs:label "Exploitation" ; rdfs:subClassOf :OffensiveMission .
:Pursuit a owl:Class ; rdfs:label "Pursuit" ; rdfs:subClassOf :OffensiveMission .
:Raid a owl:Class ; rdfs:label "Raid" ; rdfs:subClassOf :OffensiveMission .
:DefensiveMission a owl:Class ; rdfs:label "Defensive Mission" ; rdfs:subClassOf :Mission .
:AreaDefense a owl:Class ; rdfs:label "Area Defense" ; rdfs:subClassOf :DefensiveMission .
:MobileDefense a owl:Class ; rdfs:label "Mobile Defense" ; rdfs:subClassOf :DefensiveMission .
:Retrograde a owl:Class ; rdfs:label "Retrograde" ; rdfs:subClassOf :DefensiveMission .
:Delay a owl:Class ; rdfs:label "Delay" ; rdfs:subClassOf :Retrograde .
:Withdrawal a owl:Class ; rdfs:label "Withdrawal" ; rdfs:subClassOf :Retrograde .
:BreachOperation a owl:Class ; rdfs:label "Breach Operation" ; rdfs:subClassOf :OffensiveMission .

# --- Terrain ---

:TerrainType a owl:Class ; rdfs:label "Terrain Type" .
:OpenTerrain a owl:Class ; rdfs:label "Open Terrain" ; rdfs:subClassOf :TerrainType .
:UrbanTerrain a owl:Class ; rdfs:label "Urban Terrain" ; rdfs:subClassOf :TerrainType .
:ForestTerrain a owl:Class ; rdfs:label "Forest Terrain" ; rdfs:subClassOf :TerrainType .
:MountainTerrain a owl:Class ; rdfs:label "Mountain Terrain" ; rdfs:subClassOf :TerrainType .
:DesertTerrain a owl:Class ; rdfs:label "Desert Terrain" ; rdfs:subClassOf :TerrainType .
:LittoralTerrain a owl:Class ; rdfs:label "Littoral Terrain" ; rdfs:subClassOf :TerrainType .

# --- Threat and ROE ---

:ThreatLevel a owl:Class ; rdfs:label "Threat Level" .
:ThreatLevel_GREEN a owl:Class ; rdfs:label "Threat Level GREEN" ; rdfs:subClassOf :ThreatLevel .
:ThreatLevel_YELLOW a owl:Class ; rdfs:label "Threat Level YELLOW" ; rdfs:subClassOf :ThreatLevel .
:ThreatLevel_AMBER a owl:Class ; rdfs:label "Threat Level AMBER" ; rdfs:subClassOf :ThreatLevel .
:ThreatLevel_RED a owl:Class ; rdfs:label "Threat Level RED" ; rdfs:subClassOf :ThreatLevel .
:ThreatLevel_BLACK a owl:Class ; rdfs:label "Threat Level BLACK" ; rdfs:subClassOf :ThreatLevel .

:WeaponsState a owl:Class ; rdfs:label "Weapons State" .
:WeaponsState_FREE a owl:Class ; rdfs:label "Weapons Free" ; rdfs:subClassOf :WeaponsState .
:WeaponsState_TIGHT a owl:Class ; rdfs:label "Weapons Tight" ; rdfs:subClassOf :WeaponsState .
:WeaponsState_HOLD a owl:Class ; rdfs:label "Weapons Hold" ; rdfs:subClassOf :WeaponsState .

:EngagementRule a owl:Class ; rdfs:label "Engagement Rule" .
:SelfDefenseRule a owl:Class ; rdfs:label "Self-Defense Rule" ; rdfs:subClassOf :EngagementRule .
:ReturnFireRule a owl:Class ; rdfs:label "Return Fire Rule" ; rdfs:subClassOf :EngagementRule .
:DefensiveFiresRule a owl:Class ; rdfs:label "Defensive Fires Rule" ; rdfs:subClassOf :EngagementRule .
:OffensiveRule a owl:Class ; rdfs:label "Offensive Rule" ; rdfs:subClassOf :EngagementRule .
:WeaponsFreeRule a owl:Class ; rdfs:label "Weapons Free Rule" ; rdfs:subClassOf :EngagementRule .

:EscalationOfForce a owl:Class ; rdfs:label "Escalation of Force" .
:ForceProtectionMeasure a owl:Class ; rdfs:label "Force Protection Measure" .
:FireSupportAsset a owl:Class ; rdfs:label "Fire Support Asset" .
:ObstacleBelt a owl:Class ; rdfs:label "Obstacle Belt" .
:FormOfManeuver a owl:Class ; rdfs:label "Form of Maneuver" .
:WeaponSystem a owl:Class ; rdfs:label "Weapon System" .

# --- Command and Control ---

:CommandPost a owl:Class ; rdfs:label "Command Post" .
:MainCommandPost a owl:Class ; rdfs:label "Main Command Post" ; rdfs:subClassOf :CommandPost .
:TacticalCommandPost a owl:Class ; rdfs:label "Tactical Command Post" ; rdfs:subClassOf :CommandPost .

:OrderType a owl:Class ; rdfs:label "Order Type" .
:OPORD a owl:Class ; rdfs:label "Operations Order" ; rdfs:subClassOf :OrderType .
:FRAGO a owl:Class ; rdfs:label "Fragmentary Order" ; rdfs:subClassOf :OrderType .
:WARNO a owl:Class ; rdfs:label "Warning Order" ; rdfs:subClassOf :OrderType .

:ReportingChain a owl:Class ; rdfs:label "Reporting Chain" .
:StaffSection a owl:Class ; rdfs:label "Staff Section" .
:S2 a owl:Class ; rdfs:label "S2 Intelligence Section" ; rdfs:subClassOf :StaffSection .
:S3 a owl:Class ; rdfs:label "S3 Operations Section" ; rdfs:subClassOf :StaffSection .
:S4 a owl:Class ; rdfs:label "S4 Logistics Section" ; rdfs:subClassOf :StaffSection .

:IntelSummary a owl:Class ; rdfs:label "Intelligence Summary" .
:DecisionPoint a owl:Class ; rdfs:label "Decision Point" .
:CommandRelationship a owl:Class ; rdfs:label "Command Relationship" .
:MDMP a owl:Class ; rdfs:label "Military Decision-Making Process" .
:CommandersIntent a owl:Class ; rdfs:label "Commander's Intent" .
:FSCM a owl:Class ; rdfs:label "Fire Support Coordination Measure" .
:BattleHandover a owl:Class ; rdfs:label "Battle Handover" .
:CommonOperationalPicture a owl:Class ; rdfs:label "Common Operational Picture" .

# --- ISR/Intelligence ---

:SensorPlatform a owl:Class ; rdfs:label "Sensor Platform" .
:UAV a owl:Class ; rdfs:label "UAV" ; rdfs:subClassOf :SensorPlatform .
:GroundSurveillanceSensor a owl:Class ; rdfs:label "Ground Surveillance Sensor" ; rdfs:subClassOf :SensorPlatform .
:SignalIntelligenceAsset a owl:Class ; rdfs:label "SIGINT Asset" ; rdfs:subClassOf :SensorPlatform .
:ImageryAsset a owl:Class ; rdfs:label "Imagery Asset" ; rdfs:subClassOf :SensorPlatform .

:TargetEntity a owl:Class ; rdfs:label "Target Entity" .
:HighValueTarget a owl:Class ; rdfs:label "High-Value Target" ; rdfs:subClassOf :TargetEntity .
:HighPayoffTarget a owl:Class ; rdfs:label "High-Payoff Target" ; rdfs:subClassOf :TargetEntity .
:TimeSensitiveTarget a owl:Class ; rdfs:label "Time-Sensitive Target" ; rdfs:subClassOf :TargetEntity .

:ObservationEvent a owl:Class ; rdfs:label "Observation Event" .
:ThreatAssessment a owl:Class ; rdfs:label "Threat Assessment" .
:PriorityIntelRequirement a owl:Class ; rdfs:label "Priority Intelligence Requirement" .
:NamedAreaOfInterest a owl:Class ; rdfs:label "Named Area of Interest" .
:TargetedAreaOfInterest a owl:Class ; rdfs:label "Targeted Area of Interest" .
:ISRSynchronizationMatrix a owl:Class ; rdfs:label "ISR Synchronization Matrix" .
:IntelligenceDiscipline a owl:Class ; rdfs:label "Intelligence Discipline" .
:FusionCell a owl:Class ; rdfs:label "All-Source Intelligence Fusion Cell" .
:LogisticsClass a owl:Class ; rdfs:label "Logistics Class" .

# --- Object Properties ---

:hasCurrentThreatLevel a owl:ObjectProperty ;
    rdfs:label "has current threat level" ;
    rdfs:domain :Unit ;
    rdfs:range :ThreatLevel .

:hasEngagementRule a owl:ObjectProperty ;
    rdfs:label "has engagement rule" ;
    rdfs:domain :Mission ;
    rdfs:range :EngagementRule .

:hasWeaponsState a owl:ObjectProperty ;
    rdfs:label "has weapons state" ;
    rdfs:domain :Unit ;
    rdfs:range :WeaponsState .

:operatesIn a owl:ObjectProperty ;
    rdfs:label "operates in" ;
    rdfs:domain :Unit ;
    rdfs:range :TerrainType .

:conductsMission a owl:ObjectProperty ;
    rdfs:label "conducts mission" ;
    rdfs:domain :Unit ;
    rdfs:range :Mission .

:commandAuthorityLevel a owl:ObjectProperty ;
    rdfs:label "command authority level" ;
    rdfs:domain :Mission ;
    rdfs:range :CommandEchelon .

:supportedBy a owl:ObjectProperty ;
    rdfs:label "supported by" ;
    rdfs:domain :Unit ;
    rdfs:range :LogisticsUnit .

:requiresSupport a owl:ObjectProperty ;
    rdfs:label "requires support" ;
    rdfs:domain :ArmorUnit ;
    rdfs:range :InfantryUnit .

:issuesOrder a owl:ObjectProperty ;
    rdfs:label "issues order" ;
    rdfs:domain :CommandPost ;
    rdfs:range :OrderType .

:tasksCollection a owl:ObjectProperty ;
    rdfs:label "tasks collection" ;
    rdfs:domain :S2 ;
    rdfs:range :SensorPlatform .

:producesAssessment a owl:ObjectProperty ;
    rdfs:label "produces assessment" ;
    rdfs:domain :S2 ;
    rdfs:range :ThreatAssessment .

:observes a owl:ObjectProperty ;
    rdfs:label "observes" ;
    rdfs:domain :SensorPlatform ;
    rdfs:range :TargetEntity .

:triggers a owl:ObjectProperty ;
    rdfs:label "triggers" ;
    rdfs:domain :ObservationEvent ;
    rdfs:range :ThreatAssessment .

:linkedToDecisionPoint a owl:ObjectProperty ;
    rdfs:label "linked to decision point" ;
    rdfs:domain :PriorityIntelRequirement ;
    rdfs:range :DecisionPoint .

:approvalAuthority a owl:ObjectProperty ;
    rdfs:label "approval authority" ;
    rdfs:domain :WeaponsState_FREE ;
    rdfs:range :CommandEchelon .

:leadsBreaching a owl:ObjectProperty ;
    rdfs:label "leads breaching" ;
    rdfs:domain :EngineerUnit ;
    rdfs:range :BreachOperation .

:hasReportingChain a owl:ObjectProperty ;
    rdfs:label "has reporting chain" ;
    rdfs:domain :CommandEchelon ;
    rdfs:range :ReportingChain .

:isOrganicTo a owl:ObjectProperty ;
    rdfs:label "is organic to" ;
    rdfs:domain :SensorPlatform ;
    rdfs:range :CommandEchelon .

:sustainmentRequires a owl:ObjectProperty ;
    rdfs:label "sustainment requires" ;
    rdfs:domain :Mission ;
    rdfs:range :LogisticsClass .

:covers a owl:ObjectProperty ;
    rdfs:label "covers" ;
    rdfs:domain :NamedAreaOfInterest ;
    rdfs:range :TargetEntity .

:deconflictsWith a owl:ObjectProperty ;
    rdfs:label "deconflicts with" ;
    rdfs:domain :ISRSynchronizationMatrix ;
    rdfs:range :SensorPlatform .

# --- Datatype Properties ---

:readinessPct a owl:DatatypeProperty ;
    rdfs:label "readiness percentage" ;
    rdfs:domain :Unit ;
    rdfs:range xsd:float .

:personnelStrength a owl:DatatypeProperty ;
    rdfs:label "personnel strength" ;
    rdfs:domain :Unit ;
    rdfs:range xsd:integer .

:hasPID a owl:DatatypeProperty ;
    rdfs:label "has positive identification" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean .

:isHostileAct a owl:DatatypeProperty ;
    rdfs:label "is hostile act" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean .

:demonstratesHostileIntent a owl:DatatypeProperty ;
    rdfs:label "demonstrates hostile intent" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean .

:isProportional a owl:DatatypeProperty ;
    rdfs:label "is proportional" ;
    rdfs:domain :Mission ;
    rdfs:range xsd:boolean .

:confirmationCount a owl:DatatypeProperty ;
    rdfs:label "confirmation count" ;
    rdfs:domain :TargetEntity ;
    rdfs:range xsd:integer .

:isPersistent a owl:DatatypeProperty ;
    rdfs:label "is persistent surveillance" ;
    rdfs:domain :SensorPlatform ;
    rdfs:range xsd:boolean .

:forceRatio a owl:DatatypeProperty ;
    rdfs:label "force ratio" ;
    rdfs:domain :Attack ;
    rdfs:range xsd:float .
"""

USER_STORY: str = (
    "As a military intelligence officer, I want an ontology that can answer tactical "
    "decision-support queries about units, missions, engagement rules, threat levels, "
    "command relationships, and ISR asset assignments."
)
