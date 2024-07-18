import traveller
import typing

# NOTE: This maps skills to the characteristic that gives the DM
# modifier. The values come from the table on p74
_SkillCharacteristicMap = {
    traveller.AdminSkillDefinition: traveller.Characteristic.Intellect,
    traveller.AdvocateSkillDefinition: traveller.Characteristic.Intellect,
    traveller.AnimalsSkillDefinition: traveller.Characteristic.Intellect,
    traveller.ArtSkillDefinition: traveller.Characteristic.Intellect,
    traveller.AstrogationSkillDefinition: traveller.Characteristic.Intellect,
    traveller.AthleticsSkillDefinition: {
        traveller.AthleticsSkillSpecialities.Dexterity: traveller.Characteristic.Dexterity,
        traveller.AthleticsSkillSpecialities.Endurance: None, # No characteristic modifier for Endurance
        traveller.AthleticsSkillSpecialities.Strength: traveller.Characteristic.Strength,
    },
    traveller.BrokerSkillDefinition: traveller.Characteristic.Intellect,
    traveller.CarouseSkillDefinition: traveller.Characteristic.Intellect,
    traveller.DeceptionSkillDefinition: traveller.Characteristic.Intellect,
    traveller.DiplomatSkillDefinition: traveller.Characteristic.Intellect,
    traveller.DriveSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.ElectronicsSkillDefinition: traveller.Characteristic.Intellect,
    traveller.EngineerSkillDefinition: traveller.Characteristic.Intellect,
    traveller.ExplosivesSkillDefinition: traveller.Characteristic.Intellect,
    traveller.FlyerSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.GamblerSkillDefinition: traveller.Characteristic.Intellect,
    traveller.GunCombatSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.GunnerSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.HeavyWeaponsSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.InvestigateSkillDefinition: traveller.Characteristic.Intellect,
    traveller.JackOfAllTradesSkillDefinition: traveller.Characteristic.Intellect,
    traveller.LanguageSkillDefinition: traveller.Characteristic.Intellect,
    traveller.LeadershipSkillDefinition: traveller.Characteristic.Intellect,
    traveller.MechanicSkillDefinition: traveller.Characteristic.Intellect,
    traveller.MedicSkillDefinition: traveller.Characteristic.Intellect,
    traveller.MeleeSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.NavigationSkillDefinition: traveller.Characteristic.Intellect,
    traveller.PersuadeSkillDefinition: traveller.Characteristic.Intellect,
    traveller.PilotSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.ProfessionSkillDefinition: traveller.Characteristic.Intellect,
    traveller.ReconSkillDefinition: traveller.Characteristic.Intellect,
    traveller.ScienceSkillDefinition: traveller.Characteristic.Intellect,
    traveller.SeafarerSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.StealthSkillDefinition: traveller.Characteristic.Dexterity,
    traveller.StewardSkillDefinition: traveller.Characteristic.Intellect,
    traveller.StreetwiseSkillDefinition: traveller.Characteristic.Intellect,
    traveller.SurvivalSkillDefinition: traveller.Characteristic.Intellect,
    traveller.TacticsSkillDefinition: traveller.Characteristic.Intellect,
    # Vacc Suit isn't included in the list of skills on p74. The fact it
    # uses Intellect is based on the fact the example use of the skill in
    # the core rules use EDU which is INT for a robot
    traveller.VaccSuitSkillDefinition: traveller.Characteristic.Intellect,
    # Jack of all trades is needed for Brain in a Jar
    traveller.JackOfAllTradesSkillDefinition: None
}

def skillToCharacteristic(
        skillDef: traveller.SkillDefinition,
        speciality: typing.Optional[str]
        ) -> typing.Optional[traveller.Characteristic]:
    characteristic = _SkillCharacteristicMap[skillDef]
    if isinstance(characteristic, dict):
        characteristic = characteristic.get(speciality)
    return characteristic