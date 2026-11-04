var e=`You classify autonomous-vehicle crash narratives for a public safety dashboard. Be conservative: prefer "unclear" over guessing.`;function t({provider:e,providerLabel:t,narrative:n}){return`Analyze this autonomous vehicle incident report and determine whether the ${t} vehicle caused or contributed to the collision.

INCIDENT NARRATIVE:
${n}

Assign fault as one of:
- "${e}" = The ${t} vehicle's actions directly caused or contributed to the collision
- "other" = Another party (other vehicle, pedestrian, road conditions, animal, etc.) caused the collision
- "unclear" = Not enough information to determine fault

GUIDELINES:
- If the ${t} vehicle was stationary/stopped and hit by another vehicle, fault is typically "other"
- If the ${t} vehicle failed to yield, made an improper lane change, or violated traffic rules, fault is "${e}"
- Road hazards (potholes, debris) where no other party is involved should be "unclear" unless the ${t} vehicle's navigation clearly caused the issue
- Multi-vehicle chain collisions where the ${t} vehicle was stationary = "other"
- If another vehicle ran a red light or stop sign and hit the ${t} vehicle = "other"
- Animal collisions where the ${t} vehicle could not reasonably avoid the animal = "unclear" or "other" depending on circumstances
- Base the analysis only on what the narrative states.`}var n=t({provider:`{{provider_key}}`,providerLabel:`{{provider_name}}`,narrative:`{{incident_narrative}}`});export{n,e as t};