import common
import enum
import traveller
import typing

class TrainedSkill(object):
    _BaseLevel = common.ScalarCalculation(
        value=0,
        name='Trained Skill Base Level')

    def __init__(
            self,
            skillDef: traveller.SkillDefinition
            ) -> None:
        self._skillDef = skillDef
        self._baseLevel = TrainedSkill._BaseLevel
        self._specialityLevels: typing.Dict[
            typing.Union[enum.Enum, str],
            common.ScalarCalculation] = {}

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
        return self._baseLevel \
            if not speciality else \
            self._specialityLevels.get(speciality, TrainedSkill._BaseLevel)

    def modifyLevel(
            self,
            level: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            stacks: bool = True
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

        if speciality:
            if stacks:
                current = self._specialityLevels.get(speciality)
                if current:
                    level = common.Calculator.add(
                        lhs=current,
                        rhs=level,
                        name=f'Stacked {self.name(speciality=speciality)} Level')
            
            if level.value() >= 1:
                # Speciality skills have to have a value of 1 or higher
                self._specialityLevels[speciality] = level
            elif speciality in self._specialityLevels:
                # The speciality skill is 0 (or less) so delete the speciality
                # so the skill reverts to using the base skill level
                del self._specialityLevels[speciality]
        else:
            if not self._skillDef.isSimple() and level.value() != 0:
                raise AttributeError(
                    f'Unable to set base level of a speciality skill {self._skillDef.name()} to a non-zero value')  
            
            if stacks:
                level = common.Calculator.add(
                    lhs=self._baseLevel,
                    rhs=level,
                    name=f'Stacked {self.name(speciality=speciality)} Level')
          
            self._baseLevel = level

        return self._baseLevel.value() >= 0

    def hasSpeciality(
            self,
            speciality: typing.Union[enum.Enum, str]
            ) -> bool:
        return speciality in self._specialityLevels
    
    def specialities(self) -> typing.Iterable[typing.Union[enum.Enum, str]]:
        return list(self._specialityLevels.keys())

class SkillGroup(object):
    _UntrainedSkillLevel = common.ScalarCalculation(
        value=-3,
        name='Untrained Skill Level')

    def __init__(self) -> None:
        self._skills: typing.Dict[
            traveller.SkillDefinition,
            TrainedSkill
        ] = {}

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
            ) -> typing.Optional[TrainedSkill]:
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
            level: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            stacks: bool = True
            ) -> None:
        skill = self._skills.get(skillDef)
        if skill:
            isTrained = skill.modifyLevel(
                level=level,
                speciality=speciality,
                stacks=stacks)
            if not isTrained:
                # Skill is no longer trained so remove it
                del self._skills[skillDef]
        else:
            skill = TrainedSkill(skillDef=skillDef)
            isTrained = skill.modifyLevel(
                level=level,
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
        