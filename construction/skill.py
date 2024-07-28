import common
import construction
import enum
import traveller
import typing

class SkillFlags(enum.IntFlag):
    NoNegativeCharacteristicModifier = enum.auto()
    NoPositiveCharacteristicModifier = enum.auto()
    SpecialityOnly = enum.auto()

class Skill(object):
    _MinTrainedSkillLevel = common.ScalarCalculation(
        value=0,
        name='Min Trained Skill Level')
    _DefaultFlags = SkillFlags(0)

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

    def skillDef(self) -> traveller.SkillDefinition:
        return self._skillDef

    def name(
            self,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None
            ) -> str:
        return self._skillDef.name(speciality=speciality)

    def level(
            self,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            modifier: typing.Optional[common.ScalarCalculation] = None
            ) -> typing.Optional[common.ScalarCalculation]:
        if not self._levels:
            # If there are no levels set then this is either a simple skill
            # at level 0 or skill that has specialities but none have been
            # taken. Either way it means the skill is 0
            return Skill._MinTrainedSkillLevel

        if self._skillDef.isSimple():
            level, flags = self._levels.get(None, (Skill._MinTrainedSkillLevel, Skill._DefaultFlags))
        elif speciality in self._levels:
            level, flags = self._levels[speciality]
        elif (not speciality) or (None not in self._levels):
            # Either the default skill level was requested _or_ the specified
            # speciality doesn't have an explicit level, however, all the
            # specialities that have been taken have the SpecialityOnly flag
            # so there is no default skill level.
            return None
        else:
            # The skill level for a speciality was requested, however, it
            # doesn't have an explicit level. Use the default skill level
            # instead
            level, flags = self._levels[None]

        level = common.Calculator.equals(
            value=level,
            name='{skill} Skill Level'.format(
                skill=self.name(speciality=speciality)))
        if modifier:
            if modifier.value() < 0:
                if (flags & SkillFlags.NoNegativeCharacteristicModifier) != 0:
                    return level
            elif modifier.value() > 0:
                if (flags & SkillFlags.NoPositiveCharacteristicModifier) != 0:
                    return level
            level = common.Calculator.add(
                lhs=level,
                rhs=modifier,
                name=f'Modified ' + level.name())

        return level

    def modifyLevel(
            self,
            modifier: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            flags: SkillFlags = SkillFlags(0),
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

        if not speciality and not self._skillDef.isSimple() and modifier.value() != 0:
            raise AttributeError(
                f'Unable to set base level of a speciality skill {self._skillDef.name()} to a non-zero value')

        level = self.level(speciality=speciality)
        if level and stacks:
            level = common.Calculator.add(
                lhs=level,
                rhs=modifier,
                name=f'Stacked {self.name(speciality=speciality)} Skill Level')
        else:
            level = common.Calculator.equals(
                value=modifier,
                name=f'{self.name(speciality=speciality)} Skill Level')

        if self._skillDef.isSimple():
            if level.value() < 0:
                return False # No longer trained
            self._levels[None] = (level, flags)
            return True # Still trained

        if not speciality:
            self._levels[None] = (level, flags)
            # Due to previous checks we know the new level must be 0 so the
            # skill can't have become untrained
            return True

        if level.value() >= 1:
            # Speciality skills have to have a value of 1 or higher
            self._levels[speciality] = (level, flags)

            # Create a None level for defaulting if the flags allow it
            notSpecialityOnly = (flags & SkillFlags.SpecialityOnly) == 0
            if notSpecialityOnly and (None not in self._levels):
                self._levels[None] = (Skill._MinTrainedSkillLevel, flags)
        elif speciality in self._levels:
            # The speciality skill is 0 (or less) so delete the speciality
            # so the skill reverts to using the base skill level
            del self._levels[speciality]

        # As long as there is at least one level still specified then the skill
        # is still trained. This could be a level for a specialisation or for
        # the None entry that was created either because it was explicitly set
        # or because it was automatically created when a specialisation was set
        # without the SpecialityOnly flag
        return len(self._levels) > 0

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
            ) -> typing.Optional[SkillFlags]:
        if not self._levels:
            return Skill._DefaultFlags

        if self._skillDef.isSimple():
            _, flags = self._levels.get(None, (None, Skill._DefaultFlags))
            return flags

        if speciality not in self._levels:
            speciality = None
        _, flags = self._levels.get(speciality, (None, None))
        return flags

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
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            modifier: typing.Optional[common.ScalarCalculation] = None
            ) -> common.ScalarCalculation:
        skill = self._skills.get(skillDef)
        if skill:
            level = skill.level(speciality=speciality, modifier=modifier)
            if level:
                return level

        untrainedSkill = common.Calculator.equals(
            value=SkillGroup._UntrainedSkillLevel,
            name='Untrained {skill} Skill Level'.format(
                skill=skillDef.name(speciality=speciality)))
        jackSkill = self._skills.get(traveller.JackOfAllTradesSkillDefinition)
        if jackSkill:
            untrainedSkill = common.Calculator.add(
                lhs=untrainedSkill,
                rhs=jackSkill.level(),
                name='Jack of All Trades ' + untrainedSkill.name())
        if modifier:
            untrainedSkill = common.Calculator.add(
                lhs=untrainedSkill,
                rhs=modifier,
                name='Modified ' + untrainedSkill.name())

        return untrainedSkill

    def modifyLevel(
            self,
            skillDef: traveller.SkillDefinition,
            modifier: common.ScalarCalculation,
            speciality: typing.Optional[typing.Union[enum.Enum, str]] = None,
            flags: SkillFlags = SkillFlags(0),
            stacks: bool = True
            ) -> None:
        skill = self._skills.get(skillDef)
        if skill:
            isTrained = skill.modifyLevel(
                modifier=modifier,
                flags=flags,
                speciality=speciality,
                stacks=stacks)
            if not isTrained:
                # Skill is no longer trained so remove it
                del self._skills[skillDef]
        else:
            skill = Skill(skillDef=skillDef)
            isTrained = skill.modifyLevel(
                modifier=modifier,
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
