import traveller

# Define custom skills for the Vehicle and Weapon skills used by some packages.

# I think the only place this skill is mentioned is in entry for the locomotion
# skill package in the table of basic skill packages (top of p70) but I've not
# found any explicit description of exactly what it means. Based on the fact the
# description for the skill package says it's usually installed on robots with
# vehicle speed movement, my best guess is it's effectively the same as giving
# the robot the skill that is relevant to its primary form of locomotion (e.g
# Drive (Wheeled) or Fly (Grav))
RobotVehicleSkillDefinition = traveller.SkillDefinition(
    skillName='Vehicle',
    skillType=traveller.SkillDefinition.SkillType.Simple)

# This skill only appears to be mentioned in the entry for the homing skill
# package in the primitive skill packages table (bottom of p69) and the
# entry for the target skill package (top of p70). I've not been able to
# find an explicit definition but the descriptions for those skill packages
# do imply it's intended to be used with a robot with some form of integrated
# weapon and it's meant to cover the skill for that weapon.
RobotWeaponSkillDefinition = traveller.SkillDefinition(
    skillName='Weapon',
    skillType=traveller.SkillDefinition.SkillType.Simple)
