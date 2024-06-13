import common
import enum
import traveller
import typing

class SkillFlags(enum.IntFlag):
    ApplyNegativeCharacteristicModifier = enum.auto()
    ApplyPositiveCharacteristicModifier = enum.auto()
SkillFlagsCharacteristicModifierMask = SkillFlags.ApplyPositiveCharacteristicModifier | SkillFlags.ApplyNegativeCharacteristicModifier

class Skill(object):
    _MinTrainedSkillLevel = common.ScalarCalculation(
        value=0,
        name='Min Trained Skill Level')
    _DefaultFlags = SkillFlags.ApplyPositiveCharacteristicModifier | SkillFlags.ApplyNegativeCharacteristicModifier

    def __init__(
            self,
            skillDef: traveller.SkillDefinition
            ) -> None:
        self._skillDef = skillDef
        self._levels: typing.Dict[
            typing.Optional[typing.Union[enum.Enum, str]],
            typing.Tuple[
                common.ScalarCalculation,
                typing.Optional[SkillFlags]]] = {}
        # Set base skill level to default
        self._levels[None] = (
            Skill._MinTrainedSkillLevel,
            None) # Default modifier flags will be used

    def skillDef(self) -> traveller.SkillDefinition:
        return self._skillDef
    
    def name(
            self,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> str:
        return self._skillDef.name(speciality=speciality)
    
    def level(
            self,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
        if speciality not in self._levels:
            # We should only ever get here if an unknown speciality was
            # specified as there should always be an entry in the levels map for
            # None representing the base level. If it's a specialisation we don't
            # have then we know it's skill level 0
            assert(speciality)
            return Skill._MinTrainedSkillLevel
        level, _ = self._levels[speciality]
        return level

    def modifyLevel(
            self,
            levels: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            flags: typing.Optional[SkillFlags] = None,
            stacks: bool = True,
           ) -> bool: # True if skill is still trained otherwise False
        if self._skillDef.isSimple():
            if speciality != None:
                raise AttributeError(
                    f'Unable to set speciality level on simple skill {self._skillDef.name()}')
        elif self._skillDef.isFixedSpeciality():
            if speciality != None and not isinstance(speciality, self._skillDef.fixedSpecialities()):
                raise AttributeError(
                    f'Unable to use speciality type {type(speciality)} to set fixed speciality skill {self._skillDef.name()}')
        elif self._skillDef.isCustomSpeciality():
            if speciality != None and not isinstance(speciality, str):
                raise AttributeError(
                    f'Unable to use speciality type {type(speciality)} to set custom speciality skill {self._skillDef.name()}')
            
        if not speciality and not self._skillDef.isSimple() and levels.value() != 0:
            raise AttributeError(
                f'Unable to set base level of a speciality skill {self._skillDef.name()} to a non-zero value')             

        if speciality and speciality in self._levels:
            currentLevel, _ = self._levels[speciality]
        else:
            currentLevel, _ = self._levels[None]

        if stacks:
            levels = common.Calculator.add(
                lhs=currentLevel,
                rhs=levels,
                name=f'Stacked {self.name(speciality=speciality)} Level')

        if speciality:
            if levels.value() >= 1:
                # Speciality skills have to have a value of 1 or higher
                self._levels[speciality] = (levels, flags)
            elif speciality in self._levels:
                # The speciality skill is 0 (or less) so delete the speciality
                # so the skill reverts to using the base skill level
                del self._levels[speciality]

            # Modifying a speciality can't cause a skill to become untrained
            isTrained = True
        else:
            self._levels[None] = (levels, flags)

            # The skill is no longer trained if the base skill has dropped below 0
            isTrained = levels.value() >= 0

        return isTrained

    def hasSpeciality(
            self,
            speciality: typing.Union[enum.Enum, str]
            ) -> bool:
        return speciality and speciality in self._levels
    
    def specialities(self) -> typing.Iterable[typing.Union[enum.Enum, str]]:
        return [s for s in self._levels.keys() if s != None]
    
    def flags(
            self,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> SkillFlags:
        if speciality in self._levels:
            _, flags = self._levels[speciality]
            if flags != None:
                return flags
        _, flags = self._levels[None]
        return flags if flags != None else Skill._DefaultFlags

class SkillGroup(object):
    _UntrainedSkillLevel = common.ScalarCalculation(
        value=-3,
        name='Untrained Skill Level')

    def __init__(self) -> None:
        self._skills: typing.Dict[
            traveller.SkillDefinition,
            Skill
        ] = {}

    def all(self) -> typing.Iterable[Skill]:
        return list(self._skills.values())

    # NOTE: A skill is only classed as having a speciality if it has the
    # speciality at level 1 or higher
    def hasSkill(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> bool:
        skill = self._skills.get(skillDef)
        if not skill:
            return False
        if not speciality:
            return True
        return skill.hasSpeciality(speciality=speciality)
    
    def skill(
            self,
            skillDef: traveller.SkillDefinition
            ) -> typing.Optional[Skill]:
        return self._skills.get(skillDef)

    def level(
            self,
            skillDef: traveller.SkillDefinition,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> common.ScalarCalculation:
        skill = self._skills.get(skillDef)
        if skill:
            return skill.level(speciality=speciality)
        
        untrainedSkill = SkillGroup._UntrainedSkillLevel
        jackSkill = self._skills.get(traveller.JackOfAllTradesSkillDefinition)
        if jackSkill:
            untrainedSkill = common.Calculator.add(
                lhs=untrainedSkill,
                rhs=jackSkill.level(),
                name='Jack of All Trades Untrained Skill Level')

        return untrainedSkill

    def modifyLevel(
            self,
            skillDef: traveller.SkillDefinition,
            levels: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            flags: typing.Optional[SkillFlags] = None,
            stacks: bool = True
            ) -> None:
        skill = self._skills.get(skillDef)
        if skill:
            isTrained = skill.modifyLevel(
                levels=levels,
                flags=flags,
                speciality=speciality,
                stacks=stacks)
            if not isTrained:
                # Skill is no longer trained so remove it
                del self._skills[skillDef]
        else:
            skill = Skill(skillDef=skillDef)
            isTrained = skill.modifyLevel(
                levels=levels,
                flags=flags,
                speciality=speciality,
                stacks=stacks)
            if not isTrained:
                # Skill isn't trained so don't add it. Really this should never
                # happen as the UI should prevent it
                return 

            # Only add if setting the skill succeeded
            self._skills[skillDef] = skill

    def clear(self) -> None:
        self._skills.clear()            
        