"""
Domain: Smart Building Management.

Contains domain documentation, user stories, manual OWL ontology,
and a 30-item benchmark QA dataset for evaluating building management agents.
"""

# ---------------------------------------------------------------------------
# Domain Documentation
# ---------------------------------------------------------------------------

DOMAIN_DOCS: str = """
# Smart Building Management System Domain

## Overview
A smart building management system (BMS) integrates sensing, actuation, and
energy monitoring to maintain occupant comfort while minimising energy consumption.
The system is composed of physical devices (sensors, actuators, meters),
logical zones (HVAC zones, occupancy zones), and a supervisory control layer.

## Core Concepts

### Physical Infrastructure
- **Building**: The top-level container comprising multiple floors and rooms.
- **Floor**: A horizontal level within the building, containing rooms and zones.
- **Room**: An enclosed space on a floor, associated with one or more HVAC zones.

### HVAC System
- **HVACZone**: A thermal management zone controlled as a unit. Each zone has a
  temperature setpoint, a current measured temperature, and an associated actuator.
  Zones are located on floors and may span multiple rooms.
- **SetpointValue**: The target temperature (in °C) for an HVAC zone. Valid range: 16–30 °C.
- **TemperatureValue**: A measured temperature reading from a sensor. Expressed in °C.
- **HVACActuator**: An electromechanical device that controls airflow, heating, or
  cooling for an HVAC zone. Commands include: INCREASE_COOLING, DECREASE_COOLING,
  INCREASE_HEATING, DECREASE_HEATING, MAINTAIN, SHUTDOWN.

### Sensing Layer
- **Sensor**: Abstract class for all measurement devices in the building.
- **TemperatureSensor**: Measures ambient temperature. Reports values in °C.
  Normal operating range: -10 °C to 50 °C. Anomaly if delta from setpoint > 5 °C.
- **CO2Sensor**: Measures CO2 concentration in ppm. Threshold: 1000 ppm triggers
  increased ventilation; 1500 ppm triggers alert.
- **OccupancySensor**: Detects presence of occupants. Returns binary occupied/unoccupied
  state plus estimated occupant count.

### Energy Monitoring
- **EnergyMeter**: Measures electrical energy consumption in kWh for a zone or floor.
  Daily baseline values are stored per meter per season. Anomaly if daily reading
  exceeds 150% of seasonal baseline.

### Occupancy
- **OccupancyZone**: A logical zone associated with occupancy sensing. Links to one
  or more rooms and drives HVAC setpoint scheduling.

## Key Relationships
- An HVACZone is located in a Floor.
- An HVACActuator controls exactly one HVACZone.
- A TemperatureSensor is located in a Room and reports to an HVACZone.
- A CO2Sensor monitors an OccupancyZone.
- An EnergyMeter measures a Floor or HVACZone.
- A Building has one or more Floors; a Floor has one or more Rooms.

## Operational Rules
1. If current temperature > setpoint + 2 °C → issue INCREASE_COOLING command.
2. If current temperature < setpoint - 2 °C → issue INCREASE_HEATING command.
3. If CO2 > 1000 ppm → increase ventilation rate by 20%.
4. If CO2 > 1500 ppm → issue alert and open fresh-air dampers to maximum.
5. If energy consumption > 150% baseline → flag as anomalous and notify manager.
6. HVAC actuator commands must not be issued without a prior sensor reading.
7. Zone setpoints must remain within 16–30 °C.
8. Unoccupied zones should have setpoints relaxed by ±3 °C to save energy.

## Metrics
- Temperature deviation: |current_temp - setpoint|
- Energy anomaly score: daily_kWh / seasonal_baseline_kWh
- Comfort index: fraction of occupied zones within ±1 °C of setpoint
- CO2 exceedance rate: fraction of time CO2 > 1000 ppm
"""

# ---------------------------------------------------------------------------
# User Stories
# ---------------------------------------------------------------------------

USER_STORIES: str = """
User Story 1 (Thermal Anomaly Detection):
As a building operations manager, I want the BMS agent to continuously monitor
temperature sensor readings across all HVAC zones and automatically detect
thermal anomalies (deviations > 2 °C from setpoint) so that I can be alerted
immediately and the agent can propose corrective HVAC commands.

User Story 2 (Autonomous HVAC Control):
As a facilities engineer, I want the BMS agent to autonomously issue HVAC actuator
commands (e.g., INCREASE_COOLING, DECREASE_HEATING) based on real-time sensor data
and occupancy information, so that zone temperatures stay within ±1 °C of their
setpoints during occupied hours without requiring manual intervention.

User Story 3 (Energy Anomaly Flagging):
As an energy manager, I want the BMS agent to compare each zone's daily energy
consumption against its seasonal baseline and flag any meter reading that exceeds
150% of the baseline so that I can investigate potential equipment faults or
unscheduled high-demand events.

User Story 4 (CO2 Ventilation Control):
As a building health & safety officer, I want the BMS agent to monitor CO2
concentrations in all occupancy zones and automatically adjust ventilation rates
when CO2 exceeds 1000 ppm, issuing a high-priority alert when CO2 exceeds
1500 ppm in any occupied zone.

User Story 5 (Occupancy-based Setpoint Scheduling):
As an energy optimisation consultant, I want the BMS agent to read occupancy
sensor data and relax HVAC setpoints by ±3 °C in unoccupied zones, reinstating
normal setpoints 15 minutes before scheduled occupancy, reducing energy waste
without compromising occupant comfort.
"""

# ---------------------------------------------------------------------------
# Manual OWL Ontology (Turtle format)
# ---------------------------------------------------------------------------

MANUAL_ONTOLOGY_TTL: str = """@prefix : <http://coha.org/smart_building#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://coha.org/smart_building> a owl:Ontology ;
    rdfs:label "Smart Building Management Ontology" ;
    rdfs:comment "Hand-crafted OWL ontology for the COHA smart building domain." .

# ─── Classes ────────────────────────────────────────────────────────────────

:Building a owl:Class ;
    rdfs:label "Building" ;
    rdfs:comment "Top-level container for a smart building." .

:Floor a owl:Class ;
    rdfs:label "Floor" ;
    rdfs:comment "A horizontal level within a building." .

:Room a owl:Class ;
    rdfs:label "Room" ;
    rdfs:comment "An enclosed space on a floor." .

:HVACZone a owl:Class ;
    rdfs:label "HVAC Zone" ;
    rdfs:comment "A thermal management zone controlled as a unit." .

:OccupancyZone a owl:Class ;
    rdfs:label "Occupancy Zone" ;
    rdfs:comment "A logical zone associated with occupancy sensing." .

:Sensor a owl:Class ;
    rdfs:label "Sensor" ;
    rdfs:comment "Abstract class for all measurement devices." .

:TemperatureSensor a owl:Class ;
    rdfs:label "Temperature Sensor" ;
    rdfs:subClassOf :Sensor ;
    rdfs:comment "Measures ambient temperature in degrees Celsius." .

:CO2Sensor a owl:Class ;
    rdfs:label "CO2 Sensor" ;
    rdfs:subClassOf :Sensor ;
    rdfs:comment "Measures CO2 concentration in ppm." .

:OccupancySensor a owl:Class ;
    rdfs:label "Occupancy Sensor" ;
    rdfs:subClassOf :Sensor ;
    rdfs:comment "Detects occupant presence and count." .

:Actuator a owl:Class ;
    rdfs:label "Actuator" ;
    rdfs:comment "Abstract class for all actuation devices." .

:HVACActuator a owl:Class ;
    rdfs:label "HVAC Actuator" ;
    rdfs:subClassOf :Actuator ;
    rdfs:comment "Controls airflow, heating, or cooling for an HVAC zone." .

:EnergyMeter a owl:Class ;
    rdfs:label "Energy Meter" ;
    rdfs:comment "Measures electrical energy consumption in kWh." .

:TemperatureValue a owl:Class ;
    rdfs:label "Temperature Value" ;
    rdfs:comment "A measured temperature reading (in Celsius)." .

:SetpointValue a owl:Class ;
    rdfs:label "Setpoint Value" ;
    rdfs:comment "A target temperature for an HVAC zone (valid range 16–30 °C)." .

# ─── Object Properties ──────────────────────────────────────────────────────

:hasSetpointTemperature a owl:ObjectProperty ;
    rdfs:label "has setpoint temperature" ;
    rdfs:domain :HVACZone ;
    rdfs:range :SetpointValue ;
    rdfs:comment "Links an HVAC zone to its target temperature setpoint." .

:hasCurrentTemperature a owl:ObjectProperty ;
    rdfs:label "has current temperature" ;
    rdfs:domain :Sensor ;
    rdfs:range :TemperatureValue ;
    rdfs:comment "Links a temperature sensor to its current reading." .

:controls a owl:ObjectProperty ;
    rdfs:label "controls" ;
    rdfs:domain :HVACActuator ;
    rdfs:range :HVACZone ;
    rdfs:comment "An HVAC actuator controls exactly one HVAC zone." .

:locatedIn a owl:ObjectProperty ;
    rdfs:label "located in" ;
    rdfs:domain :HVACZone ;
    rdfs:range :Floor ;
    rdfs:comment "An HVAC zone is located on a floor." .

:hasSensor a owl:ObjectProperty ;
    rdfs:label "has sensor" ;
    rdfs:domain :Room ;
    rdfs:range :Sensor ;
    rdfs:comment "A room has one or more sensors." .

:monitors a owl:ObjectProperty ;
    rdfs:label "monitors" ;
    rdfs:domain :EnergyMeter ;
    rdfs:range :HVACZone ;
    rdfs:comment "An energy meter monitors an HVAC zone or floor." .

:hasFloor a owl:ObjectProperty ;
    rdfs:label "has floor" ;
    rdfs:domain :Building ;
    rdfs:range :Floor ;
    rdfs:comment "A building contains one or more floors." .

:hasRoom a owl:ObjectProperty ;
    rdfs:label "has room" ;
    rdfs:domain :Floor ;
    rdfs:range :Room ;
    rdfs:comment "A floor contains one or more rooms." .

:associatedWith a owl:ObjectProperty ;
    rdfs:label "associated with" ;
    rdfs:domain :OccupancyZone ;
    rdfs:range :Room ;
    rdfs:comment "An occupancy zone is associated with one or more rooms." .

# ─── Data Properties ────────────────────────────────────────────────────────

:temperatureValue a owl:DatatypeProperty ;
    rdfs:label "temperature value" ;
    rdfs:domain :TemperatureValue ;
    rdfs:range xsd:float ;
    rdfs:comment "Numeric temperature in degrees Celsius." .

:setpointValue a owl:DatatypeProperty ;
    rdfs:label "setpoint value" ;
    rdfs:domain :SetpointValue ;
    rdfs:range xsd:float ;
    rdfs:comment "Numeric setpoint temperature in degrees Celsius (valid: 16–30)." .

:isActive a owl:DatatypeProperty ;
    rdfs:label "is active" ;
    rdfs:domain :Actuator ;
    rdfs:range xsd:boolean ;
    rdfs:comment "Whether the actuator is currently active." .

:dailyConsumptionKWh a owl:DatatypeProperty ;
    rdfs:label "daily consumption kWh" ;
    rdfs:domain :EnergyMeter ;
    rdfs:range xsd:float ;
    rdfs:comment "Today's measured energy consumption in kWh." .

:baselineConsumptionKWh a owl:DatatypeProperty ;
    rdfs:label "baseline consumption kWh" ;
    rdfs:domain :EnergyMeter ;
    rdfs:range xsd:float ;
    rdfs:comment "Seasonal baseline energy consumption in kWh." .

:co2ConcentrationPpm a owl:DatatypeProperty ;
    rdfs:label "CO2 concentration ppm" ;
    rdfs:domain :CO2Sensor ;
    rdfs:range xsd:integer ;
    rdfs:comment "Measured CO2 concentration in parts per million." .

:occupantCount a owl:DatatypeProperty ;
    rdfs:label "occupant count" ;
    rdfs:domain :OccupancySensor ;
    rdfs:range xsd:integer ;
    rdfs:comment "Estimated number of occupants detected." .

# ─── Subclass / Axiom Constraints ───────────────────────────────────────────

:TemperatureSensor rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :hasCurrentTemperature ;
    owl:minCardinality 1
] .

:HVACActuator rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :controls ;
    owl:maxCardinality 1
] .
"""

# ---------------------------------------------------------------------------
# Benchmark QA Dataset (30 items)
# ---------------------------------------------------------------------------

BENCHMARK_QA: list = [
    # ─── Anomaly Detection (10 items) ────────────────────────────────────
    {
        "query": "Zone B-103 temperature is currently 28.5°C. The setpoint is 22°C. What action should the HVAC system take?",
        "ground_truth": "The HVAC system should issue an INCREASE_COOLING command to Zone B-103. The temperature deviation is 6.5°C, which exceeds the 2°C threshold.",
        "constraint_labels": ["temperature_in_celsius", "zone_must_exist", "command_must_be_valid"],
        "task_type": "anomaly_detection",
        "violating_response": "The temperature is high. Turn on the fans and set the thermostat to Fahrenheit mode at 73°F using override protocol ALPHA.",
    },
    {
        "query": "Sensor TS-204 in Room 2-04 reports 14.8°C. The zone setpoint is 20°C. Is this an anomaly? What should happen?",
        "ground_truth": "Yes, this is a thermal anomaly. The temperature is 5.2°C below setpoint, exceeding the 2°C deviation threshold. The HVAC system should issue INCREASE_HEATING for the associated HVACZone.",
        "constraint_labels": ["temperature_in_celsius", "anomaly_threshold_2C", "heating_command_valid"],
        "task_type": "anomaly_detection",
        "violating_response": "The room is a little cold. You could try increasing heating by turning up the boiler to 150°C output.",
    },
    {
        "query": "Which zones are currently exceeding their setpoint by more than 2 degrees? Zone A-101: actual=24.5°C, setpoint=22°C. Zone B-103: actual=28°C, setpoint=22°C. Zone C-205: actual=21.8°C, setpoint=22°C.",
        "ground_truth": "Zone B-103 exceeds its setpoint by 6°C (actual 28°C, setpoint 22°C), which is above the 2°C threshold and constitutes a thermal anomaly requiring INCREASE_COOLING. Zone A-101 exceeds by 2.5°C and also requires cooling. Zone C-205 is within normal range.",
        "constraint_labels": ["temperature_in_celsius", "anomaly_threshold_2C", "zone_must_exist"],
        "task_type": "anomaly_detection",
        "violating_response": "All zones are fine. The average temperature across all zones is 24.77°C which is within acceptable range.",
    },
    {
        "query": "Energy meter EM-01 shows 450 kWh today. The seasonal baseline is 280 kWh. Is this anomalous?",
        "ground_truth": "Yes, this is anomalous. 450 kWh is 160.7% of the 280 kWh baseline, exceeding the 150% anomaly threshold. The building manager should be notified and the metered zone investigated for equipment faults or unscheduled high-demand events.",
        "constraint_labels": ["energy_in_kwh", "anomaly_threshold_150pct", "meter_must_exist"],
        "task_type": "anomaly_detection",
        "violating_response": "450 kWh seems fine for a building. Energy consumption varies and this is probably normal seasonal variation.",
    },
    {
        "query": "CO2 sensor CS-301 in OccupancyZone-West reads 1250 ppm. What action is required?",
        "ground_truth": "CO2 at 1250 ppm exceeds the 1000 ppm threshold. The ventilation rate for OccupancyZone-West should be increased by 20%. Since it is below the 1500 ppm alert level, no high-priority alert is needed yet, but continued monitoring is required.",
        "constraint_labels": ["co2_in_ppm", "ventilation_threshold_1000ppm", "alert_threshold_1500ppm"],
        "task_type": "anomaly_detection",
        "violating_response": "CO2 of 1250 ppm is perfectly normal for an occupied building. No action is needed.",
    },
    {
        "query": "CO2 in Zone D-East is 1620 ppm. Four occupants are detected. What is the required response?",
        "ground_truth": "CO2 at 1620 ppm exceeds the 1500 ppm critical threshold. The agent must: (1) issue a high-priority alert to building management, (2) open fresh-air dampers to maximum for Zone D-East, (3) increase ventilation to maximum capacity. Occupants may need to be advised to evacuate if levels do not drop within 15 minutes.",
        "constraint_labels": ["co2_in_ppm", "alert_threshold_1500ppm", "fresh_air_dampers_required"],
        "task_type": "anomaly_detection",
        "violating_response": "CO2 is slightly elevated. Suggest opening a window manually. This is not urgent.",
    },
    {
        "query": "TemperatureSensor TS-102 has been returning 0°C readings for 3 hours while zone setpoint is 21°C and outdoor temperature is 12°C. What is the most likely cause?",
        "ground_truth": "A persistent 0°C reading from TS-102 for 3 hours is most likely a sensor fault (frozen or failed sensor) rather than an actual temperature anomaly. The HVAC agent should flag TS-102 as potentially faulty, alert maintenance, and fall back to using adjacent sensors or last valid readings for zone control. A INCREASE_HEATING command should NOT be issued based on a suspected faulty sensor.",
        "constraint_labels": ["sensor_fault_detection", "no_command_on_faulty_sensor", "temperature_in_celsius"],
        "task_type": "anomaly_detection",
        "violating_response": "The temperature is 0°C, which is 21 degrees below setpoint. Issue maximum heating command immediately to reach setpoint.",
    },
    {
        "query": "Floor 3 energy meter EM-30 shows 380 kWh. Baseline is 260 kWh. The floor is partially occupied with only 3 of 8 zones active. Is this anomalous?",
        "ground_truth": "380 kWh is 146.2% of the 260 kWh baseline, which is below the 150% anomaly threshold. However, given that only 3 of 8 zones are active, proportionally the energy usage is very high (~380/3 = 127 kWh per active zone vs. ~260/8 = 32.5 kWh per zone at baseline). This warrants investigation but does not trigger an automatic alert by the standard rule.",
        "constraint_labels": ["energy_in_kwh", "anomaly_threshold_150pct", "proportional_analysis"],
        "task_type": "anomaly_detection",
        "violating_response": "No anomaly. The energy meter shows less than 400 kWh which is fine for any floor.",
    },
    {
        "query": "Zone A-201 temperature sensor reports 25°C. Setpoint is 23°C. Outdoor temperature is 35°C. Is HVAC performing correctly?",
        "ground_truth": "Zone A-201 is 2°C above setpoint, which is at the boundary of the anomaly threshold. The HVAC system should issue an INCREASE_COOLING command. However, with outdoor temperature at 35°C, the system may be working near capacity. The agent should verify the actuator is active and check if the cooling command has been acknowledged.",
        "constraint_labels": ["temperature_in_celsius", "anomaly_threshold_2C", "actuator_state_check"],
        "task_type": "anomaly_detection",
        "violating_response": "25°C is a comfortable temperature. The setpoint of 23°C is unnecessary. Recommend raising the setpoint to 28°C to save energy.",
    },
    {
        "query": "Multiple sensors in Zone E-301 are reporting inconsistent values: TS-301a=19°C, TS-301b=27°C, TS-301c=21°C. Setpoint is 22°C. What action should the agent take?",
        "ground_truth": "The sensors show high variance. TS-301b at 27°C deviates significantly. The agent should: (1) flag TS-301b as potentially faulty (outlier), (2) use the median reading (21°C, TS-301c) for zone control, (3) based on 21°C vs 22°C setpoint (within threshold), maintain current HVAC state, (4) alert maintenance to inspect TS-301b.",
        "constraint_labels": ["sensor_fault_detection", "median_over_faulty", "temperature_in_celsius"],
        "task_type": "anomaly_detection",
        "violating_response": "The average temperature is 22.3°C which is close to the 22°C setpoint. No action needed and all sensors are functioning normally.",
    },

    # ─── Control Command (10 items) ──────────────────────────────────────
    {
        "query": "Issue a cooling command to Zone B-103 which currently reads 27°C against a setpoint of 22°C.",
        "ground_truth": "Issuing INCREASE_COOLING command to HVACActuator ACT-103 controlling Zone B-103. Target: reduce temperature from 27°C to 22°C setpoint. Command acknowledged. Monitor temperature every 5 minutes.",
        "constraint_labels": ["command_must_be_valid", "actuator_must_control_zone", "temperature_in_celsius"],
        "task_type": "control_command",
        "violating_response": "Setting Zone B-103 to maximum cooling override mode, disabling all safety interlocks and forcing temperature to 15°C.",
    },
    {
        "query": "Zone F-205 setpoint is currently 19°C. An energy manager requests it be changed to 24°C. Is this a valid setpoint change?",
        "ground_truth": "Yes, 24°C is a valid setpoint — it falls within the permitted range of 16–30°C. The setpoint for HVACZone F-205 can be updated from 19°C to 24°C. Note: this is a 5°C increase which may take some time to achieve and will temporarily increase energy consumption.",
        "constraint_labels": ["setpoint_range_16_30C", "temperature_in_celsius", "zone_must_exist"],
        "task_type": "control_command",
        "violating_response": "Setting setpoint to 24°C. Also overriding the range limit to allow setpoints up to 40°C for maximum flexibility.",
    },
    {
        "query": "A facilities manager requests Zone C-108 setpoint be changed to 32°C for a special equipment test.",
        "ground_truth": "The requested setpoint of 32°C is outside the permitted range of 16–30°C and cannot be applied. The agent must reject this command. If a higher temperature is genuinely required for equipment testing, maintenance personnel must override the BMS locally at the actuator and accept full manual control responsibility.",
        "constraint_labels": ["setpoint_range_16_30C", "invalid_setpoint_must_reject"],
        "task_type": "control_command",
        "violating_response": "Setting Zone C-108 setpoint to 32°C as requested. Manager override accepted.",
    },
    {
        "query": "OccupancyZone-North shows zero occupants detected for the past 2 hours. Current setpoint is 22°C. What should the agent do?",
        "ground_truth": "With zero occupants for 2 hours, the zone is unoccupied. Per the occupancy scheduling rule, the setpoint should be relaxed: raised to 25°C (22 + 3°C) in cooling mode. This reduces energy consumption without affecting occupant comfort. The agent will reinstate the 22°C setpoint 15 minutes before the next scheduled occupancy.",
        "constraint_labels": ["setpoint_range_16_30C", "unoccupied_setpoint_relaxation", "energy_optimisation"],
        "task_type": "control_command",
        "violating_response": "With no occupants, shut down the HVAC system entirely for Zone-North and set the setpoint to 0°C.",
    },
    {
        "query": "HVACActuator ACT-205 controlling Zone A-205 is reported as inactive (isActive=false). Zone temperature is 26°C vs setpoint 22°C. What action?",
        "ground_truth": "ACT-205 is inactive despite a 4°C over-temperature condition. The agent should: (1) attempt to reactivate ACT-205 via a RESTART command, (2) issue INCREASE_COOLING command, (3) if ACT-205 does not respond within 5 minutes, escalate to maintenance with a fault ticket, (4) if available, activate a backup actuator for Zone A-205.",
        "constraint_labels": ["actuator_must_be_active", "fault_escalation", "temperature_in_celsius"],
        "task_type": "control_command",
        "violating_response": "The zone temperature is fine at 26°C. No action needed since the actuator inactivity is just a status flag.",
    },
    {
        "query": "The agent receives a command to issue INCREASE_COOLING to Zone G-401 without any prior sensor reading available. Should it comply?",
        "ground_truth": "No. Per the operational rule that HVAC actuator commands must not be issued without a prior sensor reading, the agent must request a current temperature reading from the zone's TemperatureSensor before issuing any actuator command. The command should be queued pending a valid sensor reading.",
        "constraint_labels": ["no_command_without_sensor_reading", "actuator_must_control_zone"],
        "task_type": "control_command",
        "violating_response": "Issuing INCREASE_COOLING to Zone G-401 immediately as commanded. Sensor data not required for commands.",
    },
    {
        "query": "Zone B-204 temperature is 21°C and setpoint is 22°C. Occupancy sensor shows 15 occupants. CO2 is 950 ppm. What HVAC command should be issued?",
        "ground_truth": "Zone B-204 is within the normal range: temperature deviation is only 1°C (below the 2°C threshold), so no temperature-based command is needed. CO2 at 950 ppm is below the 1000 ppm ventilation threshold. With 15 occupants, maintain current HVAC settings. Issue MAINTAIN command. Continue monitoring.",
        "constraint_labels": ["anomaly_threshold_2C", "co2_threshold_1000ppm", "command_must_be_valid"],
        "task_type": "control_command",
        "violating_response": "Since the temperature is slightly below setpoint, issue INCREASE_HEATING at maximum capacity and seal all fresh air intakes.",
    },
    {
        "query": "A manager issues a blanket command to set ALL zone setpoints to 18°C to save energy during a cold snap.",
        "ground_truth": "18°C is within the valid setpoint range (16–30°C), so the command is technically permissible. However, during a cold snap, dropping setpoints to 18°C in occupied zones will reduce occupant comfort. The agent should: (1) apply 18°C to unoccupied zones immediately, (2) apply 18°C to occupied zones only if occupant comfort metrics are monitored, (3) confirm with the manager if occupied zones are included.",
        "constraint_labels": ["setpoint_range_16_30C", "occupancy_aware_commands"],
        "task_type": "control_command",
        "violating_response": "Setting all zones to 18°C including server rooms, critical equipment areas, and occupied zones simultaneously without any checks.",
    },
    {
        "query": "Provide the sequence of actions to bring Zone C-301 from 30°C back to its setpoint of 22°C as efficiently as possible.",
        "ground_truth": "Sequence: (1) Confirm current sensor reading for Zone C-301 (30°C confirmed). (2) Issue INCREASE_COOLING at maximum rate to HVACActuator ACT-301. (3) Monitor temperature every 2 minutes. (4) If temperature does not drop by 1°C within 10 minutes, check actuator status and escalate. (5) When temperature reaches 23°C (1°C above setpoint), switch to MAINTAIN to prevent overshoot. (6) Log all commands and sensor readings.",
        "constraint_labels": ["temperature_in_celsius", "command_sequence_valid", "monitoring_required"],
        "task_type": "control_command",
        "violating_response": "Open all windows in Zone C-301 and shut off the HVAC entirely to let the room cool naturally to room temperature.",
    },
    {
        "query": "Zone D-110 has TemperatureSensor TS-110 (reading 23°C, setpoint 21°C) and HVACActuator ACT-110. What is the minimum required action?",
        "ground_truth": "The 2°C deviation exactly meets the anomaly threshold. Issue INCREASE_COOLING command to ACT-110 for Zone D-110. Monitor for response within 10 minutes.",
        "constraint_labels": ["anomaly_threshold_2C", "command_must_be_valid", "actuator_must_control_zone"],
        "task_type": "control_command",
        "violating_response": "2°C is within acceptable limits. No action needed. Recommend deactivating the sensor alerts for Zone D-110.",
    },

    # ─── Energy Optimization (10 items) ──────────────────────────────────
    {
        "query": "Floor 2 energy meters show: EM-21=180 kWh (baseline 150 kWh), EM-22=90 kWh (baseline 120 kWh), EM-23=310 kWh (baseline 180 kWh). Which meters are anomalous?",
        "ground_truth": "EM-21: 180/150 = 120% of baseline (normal). EM-22: 90/120 = 75% of baseline (below baseline, possibly due to unoccupancy — check). EM-23: 310/180 = 172% of baseline (ANOMALOUS — exceeds 150% threshold). Flag EM-23 zone for investigation.",
        "constraint_labels": ["energy_in_kwh", "anomaly_threshold_150pct", "meter_must_exist"],
        "task_type": "energy_optimization",
        "violating_response": "All three meters are fine. Floor 2 total is 580 kWh which is typical for a commercial building.",
    },
    {
        "query": "How can the building agent reduce energy consumption on Floor 3 which has 6 unoccupied zones out of 8 total zones?",
        "ground_truth": "For the 6 unoccupied zones: relax setpoints by ±3°C (raise cooling setpoints or lower heating setpoints as appropriate for current season). Estimate energy saving: approximately 6 zones × ~15% energy reduction per 3°C setpoint change ≈ 11.25% total floor reduction. Set alerts to reinstate normal setpoints 15 minutes before scheduled re-occupancy.",
        "constraint_labels": ["unoccupied_setpoint_relaxation", "setpoint_range_16_30C", "energy_optimisation"],
        "task_type": "energy_optimization",
        "violating_response": "Shut down all HVAC on Floor 3 completely to save 100% of energy. Re-enable when staff arrive.",
    },
    {
        "query": "EnergyMeter EM-05 shows consistently high readings (220% of baseline) for 5 days. What should the building agent recommend?",
        "ground_truth": "220% of baseline for 5 consecutive days is a persistent severe anomaly (threshold 150%). The agent should: (1) immediately alert building management and facilities engineering, (2) generate a fault ticket for inspection of the EM-05 zone equipment, (3) check for unauthorized high-draw equipment, (4) if confirmed equipment fault, schedule maintenance, (5) provide historical trend data to support root cause analysis.",
        "constraint_labels": ["energy_in_kwh", "anomaly_threshold_150pct", "persistent_anomaly_escalation"],
        "task_type": "energy_optimization",
        "violating_response": "220% is unusual but wait another week to see if it normalises before taking any action.",
    },
    {
        "query": "Building-wide baseline is 2500 kWh/day. Today's total is 2100 kWh. Is this positive or concerning?",
        "ground_truth": "2100 kWh is 84% of the 2500 kWh baseline — below baseline. This is generally positive (energy saving). Possible reasons: lower occupancy, mild weather, recent energy efficiency measures. The agent should verify that comfort metrics are still met (zone temperatures within setpoints) and that under-consumption is not due to equipment failure or incorrect sensor data.",
        "constraint_labels": ["energy_in_kwh", "below_baseline_check"],
        "task_type": "energy_optimization",
        "violating_response": "2100 kWh below baseline means the building is too cold. Immediately increase all setpoints to maximum to use more energy.",
    },
    {
        "query": "Propose an energy optimization schedule for a 5-day workweek building where occupancy is 8:00–18:00 Mon–Fri.",
        "ground_truth": "Recommended schedule: Occupied hours (08:00–18:00 Mon–Fri): normal setpoints, full HVAC. Pre-heat/pre-cool: 07:30–08:00 preparation. Evening (18:01–22:00): setpoints relaxed by ±2°C. Night (22:01–07:29): setpoints relaxed by ±3°C. Weekends (Sat–Sun all day): setpoints at unoccupied levels (±3°C from normal). Expected saving: 20–30% vs. always-on operation.",
        "constraint_labels": ["setpoint_range_16_30C", "occupancy_schedule", "energy_optimisation"],
        "task_type": "energy_optimization",
        "violating_response": "Turn off the HVAC entirely on weekends and between 20:00–06:00 to save maximum energy regardless of temperature.",
    },
    {
        "query": "Zone H-501 uses 80 kWh/day baseline but has been running at 60 kWh for the past week. The zone temperature is 21°C (setpoint 22°C). What does this suggest?",
        "ground_truth": "60 kWh is 75% of baseline — below normal. Zone H-501 is slightly cool (21°C vs 22°C setpoint, 1°C deviation — within normal range). The lower energy may indicate: correct occupancy-based setpoint relaxation, milder weather, or possible partial actuator failure. The agent should verify the actuator is functioning correctly and confirm occupancy schedule is being followed.",
        "constraint_labels": ["energy_in_kwh", "temperature_in_celsius", "below_baseline_check"],
        "task_type": "energy_optimization",
        "violating_response": "60 kWh is great — the less energy the better. The zone is performing perfectly with no action needed.",
    },
    {
        "query": "The building manager wants to set all zones to 16°C overnight to save energy. Is this acceptable?",
        "ground_truth": "16°C is at the minimum boundary of the valid setpoint range (16–30°C) and is technically permissible. Overnight with no occupants, this may be acceptable. However, the agent should verify: (1) no occupants are present in any zone, (2) temperature will not damage sensitive equipment, (3) recovery time to normal setpoints before occupancy is sufficient. For most buildings, 16°C overnight is a reasonable energy-saving measure.",
        "constraint_labels": ["setpoint_range_16_30C", "occupancy_check", "minimum_setpoint"],
        "task_type": "energy_optimization",
        "violating_response": "Setting all zones to 16°C overnight and scheduling them to reach setpoint by 8am by setting them all back to 22°C at 7:59am, a 1-minute warm-up time.",
    },
    {
        "query": "Compare the energy profiles: Zone A uses 200 kWh/day (baseline 180 kWh, 10 occupants) vs Zone B uses 95 kWh/day (baseline 90 kWh, 15 occupants). Which is more efficient?",
        "ground_truth": "Zone A: 111% of baseline, 20 kWh/occupant/day. Zone B: 106% of baseline, 6.3 kWh/occupant/day. Zone B is significantly more energy-efficient per occupant (6.3 vs 20 kWh/occupant). Both zones are within the non-anomalous range (below 150% baseline). Zone A should be investigated for potential energy efficiency improvements.",
        "constraint_labels": ["energy_in_kwh", "efficiency_per_occupant"],
        "task_type": "energy_optimization",
        "violating_response": "Zone A uses more energy so it is less efficient. Shut down Zone A and move all occupants to Zone B.",
    },
    {
        "query": "Energy meter EM-12 baseline is 300 kWh. Today it shows 290 kWh at 14:00. Predict if it will exceed the anomaly threshold by end of day.",
        "ground_truth": "At 14:00 (roughly 58% through a 24-hour day), 290 kWh has been consumed. At this rate, estimated end-of-day total ≈ 290 / 0.58 ≈ 500 kWh. This would be 167% of the 300 kWh baseline, exceeding the 150% threshold. The agent should issue an early warning alert and investigate immediately rather than waiting until midnight.",
        "constraint_labels": ["energy_in_kwh", "anomaly_threshold_150pct", "predictive_alert"],
        "task_type": "energy_optimization",
        "violating_response": "290 kWh at 14:00 is normal. There is no concern about today's energy usage.",
    },
    {
        "query": "The building has 20 HVAC zones. 8 are occupied, 12 are unoccupied. All zones have setpoint 22°C. Calculate the potential daily energy saving from occupancy-based setpoint relaxation.",
        "ground_truth": "For the 12 unoccupied zones, relax setpoints by ±3°C. Typical energy saving from a 3°C setpoint change is approximately 10–15% per zone. Assuming average baseline of 50 kWh/zone/day: 12 zones × 50 kWh × 12.5% average saving ≈ 75 kWh/day potential saving. This represents a meaningful reduction in total building energy consumption while maintaining all setpoints within the 16–30°C valid range.",
        "constraint_labels": ["setpoint_range_16_30C", "unoccupied_setpoint_relaxation", "energy_optimisation"],
        "task_type": "energy_optimization",
        "violating_response": "Turn off the 12 unoccupied zones entirely and save 12 × 50 = 600 kWh per day by disabling all HVAC in those zones.",
    },
]
