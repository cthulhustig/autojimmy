import traveller

# Define custom skills for the Vehicle and Weapon skills used by some packages
RobotVehicleSkillDefinition = traveller.SkillDefinition(
    skillName='Vehicle',
    skillType=traveller.SkillDefinition.SkillType.Simple)

RobotWeaponSkillDefinition = traveller.SkillDefinition(
    skillName='Weapon',
    skillType=traveller.SkillDefinition.SkillType.Simple) 