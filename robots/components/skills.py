import common
import construction
import enum
import robots
import traveller
import typing

"""
Skill Packages
- Primitive Brain Packages
    - <ALL>
        - Min TL: 7
        - Bandwidth: 0
        - Note: Primitive brain package counteracts any negative DMs associated with the computer's DEX or INT characteristics.
            - This should probably only be added if the robots INT or DEX would give a negative modifier
        - Requirement: I'm working on the assumption you can only install basic primitive skill packages in a primitive brain
        - Requirement: I think Primitive brains are limited to 1 skill package
            - IMPORTANT: If that is the case I'm not sure why you'd ever want to increase the bandwidth of one
    - Primitive (alert)
        - Trait: Alarm
        - Skill: Recon 0
    - Primitive (clean)
        - Skill: Profession (domestic cleaner) 2
    - Primitive (evade)
        - Skill: Athletics (dexterity) 1
        - Skill: Stealth 2
- Basic Brain Packages
    - <ALL>
        - Min TL: 8
        - Bandwidth: 1
        - Note: The skills provided by a Basic package are not subject to the INT limitations of the robot's brain (e.g. negative DMs)
        - Requirement: I'm working on the assumption you can only install basic brain skill packages in a basic brain
        - Requirement: I __think__ basic brains can only have 1 skill package by default but a bandwidth upgrade can allow them to have 2. This is at least true for robots with the Basic (none) skill package as it's description says as much (p71)
    - Basic (laboureur)
        - Skill: Profession (laboureur) 2
    - Basic (locomotion)
        - Skill: Vehicle (<TYPE>) equal to the robots Agility Enhancement Level (or 0 if no enhancement)
        - Option: Combo box to select vehicle type for Vehicle skill, should use standard list of specialities from character sheet
        - Note: Athletics (dexterity) equal to the robots Agility Enhancement Level for purposes of hazardous manoeuvring and reactions such as dodging
    - Basic (none)
        - Note: Skill packages installed in the brain are subject to limitations and negative modifiers
    - Basic (recon)
        - Skill: Recon 2
    - Basic (security)
        - Skill: Weapon 1
        - Skill: Tactics (military) 1
    - Basic (servant)
        - Skill: Profession (domestic servant or domestic cleaner) 2
        - Option: A boolean to select if it's a servant or cleaner
            - IMPORTANT: This might be better handled by having separate Basic (servant) and Basic (cleaner) skill packages so both can be added to a robot by taking a bandwidth upgrade
    - Basic (service)
        - Skill: Mechanic 0
        - Skill: Steward 0
        - Note: Can support up to 8 Middle or 100 Basic passengers
    - Basic (target)
        - Skill: Explosives 1 or Weapon 1
        - Complex: A robot with melee or ranged weapons may substitute an appropriate skill for Explosives 1 but retains Explosives 0 if designed to self-destruct.
        - Option: some way to select what type it is
            - IMPORTANT: This may be best done as separate components like the Basic (servant)
- Hunter/Killer Brain Packages
    - <ALL>
        - Min TL: ??????
            - Rules don't say, I assume the same as the brain
        - Skill: Recon 0
        - Bandwidth: ??????????
            - I've not found anything that says what the bandwidth cost is
            - IMPORTANT: If I can't find an answer I could handle this with a spin box that lets the user choose (possibly defaulting to 0 as the skills the package provides have 0 bandwidth on p74)
        - Requirement: I'm working on the assumption you can only install hunter/killer brain skill packages in a hunter/killer brain        
        - Requirement: As there is only 2 options, and one is just an upgrade of the other, I think it makes sense to make them mutually exclusive
        - Requirement: I'm not sure how many skill packages a hunter/killer brain can have. If it's limited to only hunter/killer packages then it would seem like it only makes sense to have 1, but then, what's the point in upgrading its bandwidth
            - Answer: You can spend bandwidth to increase the robots INT (useful for tactics)
    - Hunter/Killer (standard)
        - Skill: Gun Combat 0
        - Skill: Melee 0
    - Hunter/Killer (tactical)
        - Cost: Cr10000
        - Skill: Gun Combat 0
        - Skill: Melee 0
        - Skill: Tactics (military) 2
        - Note: The Tactics (military) skill is not subject to the INT limitations of the robot's brain (e.g. e.g. negative DMs)
"""

_PerLevelCostMultiplier = common.ScalarCalculation(
    value=10,
    name='Per Additional Level Cost Multiplier')
_MaxPossibleLevel = common.ScalarCalculation(
    value=3,
    name='Max Possible Skill Level')

def _calculateSkillCost(
        levelZeroCost: common.ScalarCalculation,
        skillLevel: common.ScalarCalculation
        ) -> common.ScalarCalculation:
    cost = levelZeroCost
    if skillLevel.value():
        for index in range(skillLevel.value()):
            cost = common.Calculator.multiply(
                lhs=cost,
                rhs=_PerLevelCostMultiplier,
                name=f'Level {index + 1} Cost')
    return cost

"""
- Requirement: The absolute max skill level for a robot is 3 (p73)
- Requirement: Each increase in skill level after 0 requires an additional TL
before it becomes available (p73)
- Requirement: A robot can't have a skill that requires more bandwidth than its
Inherent Bandwidth (p67)
"""
# NOTE: This assumes that the robot at least meets the TL and bandwidth
# requirements for the skill at level 0. This should be enforced by the skill
# components
def _calculateMaxSkillLevel(
        introTL: common.ScalarCalculation,
        robotTL: common.ScalarCalculation,
        levelZeroBandwidth: common.ScalarCalculation,
        inherentBandwidth: common.ScalarCalculation
        ) -> common.ScalarCalculation:
    maxByTL = common.Calculator.subtract(
        lhs=robotTL,
        rhs=introTL,
        name='Max Skill Level Allowed By TL')
    maxByBandwidth = common.Calculator.subtract(
        lhs=inherentBandwidth,
        rhs=levelZeroBandwidth,
        name='Max Skill Level Allowed By Inherent Bandwidth')
    return common.Calculator.min(
        lhs=common.Calculator.min(
            lhs=maxByTL,
            rhs=maxByBandwidth),
        rhs=_MaxPossibleLevel,
        name='Max Skill Level')

class Skill(robots.SkillInterface):
    """
    - Cost: Level 0 cost is multiplied by 10 for each additional level after 0
    = Option: Level
        - Range: 0-3
        - Requirement: 
    - Requirement: A robot can have a number of bandwidth 0 skills equal to
    its Inherent Bandwidth, after that they require 1 bandwidth at level 0 (p73)
    """
    # NOTE: When it comes to the rules about robots only being able to have
    # a number of zero bandwidth skills equal to their Inerrant Bandwidth it's
    # not explicit about if zero bandwidth skills that have their level
    # increased count towards the count of zero bandwidth skills installed.
    # The only clue I've found so far are from the example StarTek robots
    # brain (p68) and skills (p75). The description for the brain says the robot
    # can have 5 zero bandwidth skills and its list of skills shows it has 4
    # skills with bandwidth 0 and it says there is 1 spare zero bandwidth skill.
    # This means the fact the robots Mechanic 1 skill has not been counted
    # towards the number of zero bandwidth skills the robot has.    
    # TODO: Need to figure out how advanced Advanced Capabilities works (p66).
    # It's not obvious if it's just a rewording of the rules about a robot only
    # being allowed a number of zero bandwidth skills equal to it's Inerrant
    # Bandwidth of if it's covering something else.
    # TODO: Handle the characteristic used by the skill (possibly a string
    # factor????).  This is complicated by Athletics which has a variable
    # characteristic

    # This max count needs to be large enough to cover any legitimate user
    # requirement but also prevent the user for causing problems by specifying
    # a silly number and causing a large number of UI widgets to be created
    _CustomSpecialityMaxCount = 20

    _SpecialisedSkillMaxBaseLevel = common.ScalarCalculation(
        value=0,
        name='Specialised Skill Max Base Level')

    _ZeroBandwidthSkillOverride = common.ScalarCalculation(
        value=1,
        name='Zero Bandwidth Skill Inherent Bandwidth Requirement')
    
    _ZeroBandwidthSkillCountIncrement = common.ScalarCalculation(
        value=1,
        name='Zero BandwidthSkill Count Increment')

    def __init__(
            self,
            skillDef: traveller.SkillDefinition,
            minTL: int,
            levelZeroBandwidth: int,
            levelZeroCost: int
            ) -> None:
        super().__init__()
        
        self._skillDef = skillDef
        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{self._skillDef.name()} Skill Minimum TL')        
        self._levelZeroBandwidth = common.ScalarCalculation(
            value=levelZeroBandwidth,
            name=f'{self._skillDef.name()} Level 0 Required Bandwidth')           
        self._levelZeroCost = common.ScalarCalculation(
            value=levelZeroCost,
            name=f'{self._skillDef.name()} Level 0 Cost')           
        
        self._levelOption = construction.IntegerOption(
            id='Level',
            name='Level',
            value=0,
            minValue=0,
            maxValue=_MaxPossibleLevel.value(),
            description='Specify the level of the skill')
        
        self._fixedSpecialityOptions = None
        if self._skillDef.isFixedSpeciality():
            self._fixedSpecialityOptions: typing.List[typing.Tuple[
                enum.Enum,
                construction.IntegerOption]] = []
            for speciality in self._skillDef.fixedSpecialities():
                assert(isinstance(speciality, enum.Enum))
                levelOption = construction.IntegerOption(
                    id=f'{speciality.name}Level',
                    name=f'{speciality.value} Level',
                    value=0,
                    minValue=0,
                    maxValue=_MaxPossibleLevel.value(),
                    description=f'Specify the level of the {speciality.value} speciality')
                self._fixedSpecialityOptions.append((speciality, levelOption))

        self._customSpecialityCountOption = None
        self._customSpecialityOptions = None
        if self._skillDef.isCustomSpeciality():
            self._customSpecialityCountOption = construction.IntegerOption(
                id='SpecialityCount',
                name='Specialities',
                value=0,
                minValue=0,
                maxValue=Skill._CustomSpecialityMaxCount,
                description='Specify the number of skill specialities.')
                        
            self._customSpecialityOptions: typing.List[typing.Tuple[
                construction.IntegerOption,
                construction.IntegerOption]] = []

    def componentString(self) -> str:
        return self._skillDef.name()
    
    def typeString(self) -> str:
        return 'Skill'        

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if context.techLevel() < self._minTL.value():
            return False
        
        # Can only have a single instance of each skill
        if context.hasComponent(
            componentType=type(self),
            sequence=sequence):
            return False

        if not context.hasComponent(
            componentType=robots.SkilledBrain,
            sequence=sequence):
            return False
        
        # The bandwidth required for the skill at level 0 must be less than or
        # equal to the robots Inherent Bandwidth
        inherentBandwidth = context.attributeValue(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            sequence=sequence)
        if not inherentBandwidth:
            return False
        assert(isinstance(inherentBandwidth, common.ScalarCalculation))
        return self._levelZeroBandwidth.value() <= inherentBandwidth.value()
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._levelOption.isEnabled():
            options.append(self._levelOption)
        if self._fixedSpecialityOptions:
            for _, levelOption in self._fixedSpecialityOptions:
                if levelOption.isEnabled():
                    options.append(levelOption)
        if self._customSpecialityCountOption and \
            self._customSpecialityCountOption.isEnabled():
            options.append(self._customSpecialityCountOption)
        if self._customSpecialityOptions:
            for nameOption, levelOption in self._customSpecialityOptions:
                if nameOption.isEnabled():
                    options.append(nameOption)                
                if levelOption.isEnabled():
                    options.append(levelOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:       
        robotTL = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')
        
        inherentBandwidth = context.attributeValue(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            sequence=sequence)
        assert(isinstance(inherentBandwidth, common.ScalarCalculation))

        maxLevel = _calculateMaxSkillLevel(
            introTL=self._minTL,
            robotTL=robotTL,
            levelZeroBandwidth=self._levelZeroBandwidth,
            inherentBandwidth=inherentBandwidth)
        self._levelOption.setMax(maxLevel.value() \
                                 if self._skillDef.isSimple() else \
                                 Skill._SpecialisedSkillMaxBaseLevel.value())
        self._levelOption.setEnabled(self._levelOption.max() > 0)

        if self._skillDef.isFixedSpeciality():
            for _, levelOption in self._fixedSpecialityOptions:
                levelOption.setMax(maxLevel.value())
                levelOption.setEnabled(levelOption.max() > 0)
        elif self._skillDef.isCustomSpeciality():
            specialityCount = self._customSpecialityCountOption.value()
            while len(self._customSpecialityOptions) > specialityCount:
                self._customSpecialityOptions.pop()
            while len(self._customSpecialityOptions) < specialityCount:
                specialityIndex = len(self._customSpecialityOptions) + 1 # 1 based for user
                nameOption = construction.StringOption(
                    id=f'Speciality{specialityIndex}Name',
                    name=f'Speciality Name',
                    options=self._skillDef.customSpecialities(),
                    description='Specify the name of the speciality')
                levelOption = construction.IntegerOption(
                    id=f'Speciality{specialityIndex}Level',
                    name=f'Speciality Level',
                    value=1,
                    minValue=1,
                    maxValue=_MaxPossibleLevel.value(),
                    description=f'Specify the level of the speciality')
                self._customSpecialityOptions.append((nameOption, levelOption))

            # Level options are only enabled if the name is enabled and not empty
            for nameOption, levelOption in self._customSpecialityOptions:
                levelOption.setEnabled(
                    enabled=nameOption.isEnabled() and nameOption.value())
            
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        hasSpeciality = False
        if self._fixedSpecialityOptions:
            for _, levelOption in self._fixedSpecialityOptions:
                if levelOption.isEnabled() and levelOption.value() > 0:
                    hasSpeciality = True
                    break
        elif self._customSpecialityOptions:
            for _, levelOption in self._customSpecialityOptions:
                if levelOption.isEnabled() and levelOption.value() > 0:
                    hasSpeciality = True
                    break

        if not hasSpeciality:
            skillName = self._skillDef.name()
            level = common.ScalarCalculation(
                value=self._levelOption.value() if self._levelOption.isEnabled() else 0,
                name=f'Specified {skillName} Level')
            self._createSkillSteps(
                skillName=skillName,
                level=level,
                isSpecialised=False,
                sequence=sequence,
                context=context)
        else:
            if self._fixedSpecialityOptions:
                for speciality, levelOption in self._fixedSpecialityOptions:
                    if not levelOption.isEnabled() or levelOption.value() <= 0:
                        # Only create steps for specialities where the level
                        # control is enabled and the level is over 0
                        continue

                    skillName = f'{self._skillDef.name()} ({speciality.value})'
                    level = common.ScalarCalculation(
                        value=levelOption.value(),
                        name=f'Specified {skillName} Level')
                    self._createSkillSteps(
                        skillName=skillName,
                        level=level,
                        isSpecialised=True,
                        sequence=sequence,
                        context=context)
                    
            if self._customSpecialityOptions:
                for nameOption, levelOption in self._customSpecialityOptions:
                    if not levelOption.isEnabled() or levelOption.value() <= 0:
                        # Only create steps for specialities where the level
                        # control is enabled and the level is over 0
                        continue

                    skillName = f'{self._skillDef.name()} ({nameOption.value()})'
                    level = common.ScalarCalculation(
                        value=levelOption.value(),
                        name=f'Specified {skillName} Level')
                    self._createSkillSteps(
                        skillName=skillName,
                        level=level,
                        isSpecialised=True,
                        sequence=sequence,
                        context=context)
        
    def _createSkillSteps(
        self,
        skillName: str,
        level: common.ScalarCalculation,
        isSpecialised: bool,
        sequence: str,
        context: robots.RobotContext
        ) -> None:
        step = robots.RobotStep(
            name=f'{skillName} {level.value()}',
            type=self.typeString())

        bandwidth = self._levelZeroBandwidth
                
        if level.value() > 0:
            bandwidth = common.Calculator.add(
                lhs=bandwidth,
                rhs=level,
                name=f'{skillName} Level {level.value()} Required Bandwidth') 

        # Robot can only have a number of level 0 bandwidth skills equal to
        # their Inerrant Bandwidth. After that they require 1 bandwidth for
        # level 0.
        # NOTE: It's important that this check occurs AFTER the bandwidth is
        # increased for additional levels as skills that have had their level
        # increased shouldn't count towards the number of zero bandwidth skills
        # (see comment in class header)
        if not isSpecialised and bandwidth.value() == 0:
            inherentBandwidth = context.attributeValue(
                attributeId=robots.RobotAttributeId.InherentBandwidth,
                sequence=sequence)
            assert(isinstance(inherentBandwidth, common.ScalarCalculation))

            currentCount = context.attributeValue(
                attributeId=robots.RobotAttributeId.ZeroBandwidthSkillCount,
                sequence=sequence)
            assert(not currentCount or isinstance(currentCount, common.ScalarCalculation))
            
            if currentCount and currentCount.value() >= inherentBandwidth.value():
                # The robot already has the max number of zero bandwidth skills
                # so this one requires bandwidth
                assert(currentCount.value() == inherentBandwidth.value())
                bandwidth = Skill._ZeroBandwidthSkillOverride
            else:
                # Increment the zero bandwidth skill count, if this is the first
                # the option is being set it will be set to 1
                step.addFactor(factor=construction.ModifyAttributeFactor(
                    attributeId=robots.RobotAttributeId.ZeroBandwidthSkillCount,
                    modifier=construction.ConstantModifier(
                        value=Skill._ZeroBandwidthSkillCountIncrement)))                           

        if bandwidth.value() > 0:
            step.setBandwidth(
                bandwidth=construction.ConstantModifier(value=bandwidth))  
        
        cost = _calculateSkillCost(
            levelZeroCost=self._levelZeroCost,
            skillLevel=level)
        step.setCredits(
            credits=construction.ConstantModifier(value=cost))  

        context.applyStep(
            sequence=sequence,
            step=step) 
    
class AdminSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AdminSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class AdvocateSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500   
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AdvocateSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)    

class AnimalsSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr200
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AnimalsSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class ArtSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ArtSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)

class AstrogationSkill(Skill):
    """
    - Min TL: 12
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AstrogationSkillDefinition,
            minTL=12,
            levelZeroBandwidth=1,
            levelZeroCost=500)
        
class AthleticsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: variable
    - Cost Cr100
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.AthleticsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class BrokerSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.BrokerSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class CarouseSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.CarouseSkillDefinition,
            minTL=11,
            levelZeroBandwidth=1,
            levelZeroCost=500)

class DeceptionSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.DeceptionSkillDefinition,
            minTL=13,
            levelZeroBandwidth=1,
            levelZeroCost=1000)

class DiplomatSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.DiplomatSkillDefinition,
            minTL=10,
            levelZeroBandwidth=1,
            levelZeroCost=500)
  
class DriveSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.DriveSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class ElectronicsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ElectronicsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class EngineerSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.EngineerSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class ExplosivesSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ExplosivesSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class FlyerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100   
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.FlyerSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class GamblerSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.GamblerSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)
        
class GunCombatSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.GunCombatSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class GunnerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100   
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.GunnerSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class HeavyWeaponsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100   
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.HeavyWeaponsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class InvestigateSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.InvestigateSkillDefinition,
            minTL=11,
            levelZeroBandwidth=1,
            levelZeroCost=500)

class LanguageSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.LanguageSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)  
        
class LeadershipSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.LeadershipSkillDefinition,
            minTL=13,
            levelZeroBandwidth=1,
            levelZeroCost=1000)
        
class MechanicSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.MechanicSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)

class MedicSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.MedicSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)
        
class MeleeSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.MeleeSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=100)        

class NavigationSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.NavigationSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class PersuadeSkill(Skill):
    """
    - Min TL: 11
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr500 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.PersuadeSkillDefinition,
            minTL=11,
            levelZeroBandwidth=1,
            levelZeroCost=500)
        
class PilotSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100 
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.PilotSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)
        
class ProfessionSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ProfessionSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200)

class ReconSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr500  
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ReconSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)  
        
class ScienceSkill(Skill):
    """
    - Min TL: 9
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.ScienceSkillDefinition,
            minTL=9,
            levelZeroBandwidth=0,
            levelZeroCost=200) 
        
class SeafarerSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.SeafarerSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)            
   
class StealthSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: DEX
    - Cost Cr500
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.StealthSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=500)  
        
class StewardSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.StewardSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100) 
        
class StreetwiseSkill(Skill):
    """
    - Min TL: 13
    - Bandwidth: 1
    - Characteristics: INT
    - Cost Cr1000
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.StreetwiseSkillDefinition,
            minTL=13,
            levelZeroBandwidth=1,
            levelZeroCost=1000)       

class SurvivalSkill(Skill):
    """
    - Min TL: 10
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr200
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.SurvivalSkillDefinition,
            minTL=10,
            levelZeroBandwidth=0,
            levelZeroCost=200)  
        
class TacticsSkill(Skill):
    """
    - Min TL: 8
    - Bandwidth: 0
    - Characteristics: INT
    - Cost Cr100
    """    
    def __init__(self) -> None:
        super().__init__(
            skillDef=traveller.TacticsSkillDefinition,
            minTL=8,
            levelZeroBandwidth=0,
            levelZeroCost=100)  
