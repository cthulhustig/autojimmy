import common
import construction
import enum
import robots
import typing

class Brain(robots.BrainInterface):
    """
    - Slots: The number of slots taken up by a brain works like this (p66)
        - The brain has no slot requirement If the robots Size is greater than
        or equal to:
        (Computer/X - (RobotTL - BrainMinTL))
        - Otherwise the brain costs 1 slot
    - Cost: The Retrotech rules (p67) says the cost of a brain drops by 50%
    for every TL after its min TL.
    - Brain Bandwidth Upgrade
        - <ALL>
            - Slots: 1
            - Requirement: A brain can have an upgrade for a more primitive
            brain installed to save cost
        - Basic or Hunter/Killer +1
            - Min TL: 8
            - Cost: Cr5000
            - Trait: Bandwidth +1
        - Advanced +2
            - Min TL: 10
            - Cost: Cr5000
            - Trait: Bandwidth +2
        - Advanced +3
            - Min TL: 11
            - Cost: Cr10000
            - Trait: Bandwidth +3
        - Advanced +4
            - Min TL: 12
            - Cost: Cr20000
            - Trait: Bandwidth +4
        - Very Advanced +6
            - Min TL: 12
            - Cost: Cr50000
            - Trait: Bandwidth +6
        - Very Advanced +8
            - Min TL: 12
            - Cost: Cr100000
            - Trait: Bandwidth +8
        - Self-Aware +10
            - Min TL: 15
            - Cost: Cr500000
            - Trait: Bandwidth +10
        - Self-Aware +15
            - Min TL: 15
            - Cost: Cr1000000
            - Trait: Bandwidth +15
        - Self-Aware +20
            - Min TL: 15
            - Cost: Cr2500000
            - Trait: Bandwidth +20
        - Self-Aware +25
            - Min TL: 15
            - Cost: Cr5000000
            - Trait: Bandwidth +25
        - Conscious +30
            - Min TL: 17
            - Cost: Cr5000000
            - Trait: Bandwidth +30
        - Conscious +40
            - Min TL: 17
            - Cost: Cr10000000
            - Trait: Bandwidth +40
        - Conscious +50
            - Min TL: 19
            - Cost: Cr5000000
            - Trait: Bandwidth +50 
    - Brain Intellect Upgrade
        - <ALL>
            - Cost: Multiplied by 2 if INT is 12+
        - INT+1
            - Cost: (Current INT + 1) x Cr1000
                - Multiplied by 2 if final INT is 12+
            - Trait: Bandwidth -1
        - INT+2
            - Cost: (Current INT+1) x (Current INT+2) x Cr1000
                - Multiplied by 2 if final INT is 12+    
            - Trait: Bandwidth -3
        - INT+3
            - Cost: (Current INT+1) x (Current INT+2) x (Current INT+3) x Cr1000
                - Multiplied by 2 if final INT is 12+          
            - Trait: Bandwidth -6
    - Brain Hardening
        - Min TL: 8
        - Cost: +50% Brain Cost, if a Bandwidth Upgrade is installed its cost is
        also increased by 50%
        - Note: Protects brain from ion and radiation weapons            
    """
    # NOTE: The Security/X trait that some brains have determine how difficult
    # the are to hack (p106)
    # NOTE: The Expert/X trait that some brains have determines what level of
    # skill the robot can attempt (Difficult (10+), Very Difficult (12+) etc)
    # TODO: The table in the rules that gives the brain stats (p66) has a Skills
    # column. I __think__ this is just giving the INT modifier for the brain.
    # The numbers match up with those used when doing the same for player
    # characteristics (e.g. an INT of 1 gives a -2 modifier). If this is not
    # what the column is showing then I don't know what it is as there doesn't
    # seem to be anything that explains it.
    # This could be a good question for Geir
    # TODO: Do something with Computer/X rating. Could be a note, could be
    # an attribute. Note I don't __think__ this is a skill

    class _BrainType(enum.Enum):
        Primitive = 'Primitive'
        Basic = 'Basic'
        HunterKiller = 'Hunter/Killer'
        Advanced = 'Advanced'
        VeryAdvanced = 'Very Advanced'
        SelfAware = 'Self-Aware'
        Conscious = 'Conscious'

    class _BandwidthUpgrade(enum.Enum):
        BasicHunterKillerPlus1 = 'Basic or Hunter/Killer +1'
        AdvancedPlus2 = 'Advanced +2'
        AdvancedPlus3 = 'Advanced +3'
        AdvancedPlus4 = 'Advanced +4'
        VeryAdvancedPlus6 = 'Very Advanced +6'
        VeryAdvancedPlus8 = 'Very Advanced +8'
        SelfAwarePlus10 = 'Self-Aware +10'
        SelfAwarePlus15 = 'Self-Aware +15'
        SelfAwarePlus20 = 'Self-Aware +20'
        SelfAwarePlus25 = 'Self-Aware +25'
        ConsciousPlus30 = 'Conscious +30'
        ConsciousPlus40 = 'Conscious +40'
        ConsciousPlus50 = 'Conscious +50'

    class _IntellectUpgrade(enum.Enum):
        IntelligencePlus1 = 'INT+1'
        IntelligencePlus2 = 'INT+2'
        IntelligencePlus3 = 'INT+3'

    _HighRelativeBrainSizeSlotCost = common.ScalarCalculation(
        value=1,
        name='High Relative Brain Size Required Slots')
    
    _RetrotechPerTLCostScale = common.ScalarCalculation(
        value=0.5,
        name='Retrotech Per TL Cost Scale')
    
    _HardenedMinTL = common.ScalarCalculation(
        value=8,
        name='Brain Hardening Min TL')
    _HardenedCostPercent = common.ScalarCalculation(
        value=50,
        name='Brain Hardening Cost Percentage')
    
    # Data Structure: Min TL, Cost, Bandwidth Modifier, Compatible Brain Types
    _BandwidthUpgradeData = {
        _BandwidthUpgrade.BasicHunterKillerPlus1: (8, 5000, +1),
        _BandwidthUpgrade.AdvancedPlus2: (10, 5000, +2),
        _BandwidthUpgrade.AdvancedPlus3: (11, 10000, +3),
        _BandwidthUpgrade.AdvancedPlus4: (12, 20000, +4),
        _BandwidthUpgrade.VeryAdvancedPlus6: (12, 50000, +6),
        _BandwidthUpgrade.VeryAdvancedPlus8: (12, 100000, +8),
        _BandwidthUpgrade.SelfAwarePlus10: (15, 500000, +10),
        _BandwidthUpgrade.SelfAwarePlus15: (15, 1000000, +15),
        _BandwidthUpgrade.SelfAwarePlus20: (15, 2500000, +20),
        _BandwidthUpgrade.SelfAwarePlus25: (15, 5000000, +25),
        _BandwidthUpgrade.ConsciousPlus30: (17, 5000000, +30),
        _BandwidthUpgrade.ConsciousPlus40: (17, 10000000, +40),
        _BandwidthUpgrade.ConsciousPlus50: (18, 5000000, +50),
    }

    # TODO: This is ugly as hell but I can't see a better way that isn't just
    # ugly in a different way
    _BandwidthUpgradeCompat = {
        _BrainType.Basic: [
            _BandwidthUpgrade.BasicHunterKillerPlus1
        ],
        _BrainType.HunterKiller: [
            _BandwidthUpgrade.BasicHunterKillerPlus1
        ], 
        _BrainType.Advanced: [
            _BandwidthUpgrade.BasicHunterKillerPlus1,
            _BandwidthUpgrade.AdvancedPlus2,
            _BandwidthUpgrade.AdvancedPlus3,
            _BandwidthUpgrade.AdvancedPlus4
        ],                
        _BrainType.VeryAdvanced: [
            _BandwidthUpgrade.BasicHunterKillerPlus1,
            _BandwidthUpgrade.AdvancedPlus2,
            _BandwidthUpgrade.AdvancedPlus3,
            _BandwidthUpgrade.AdvancedPlus4,            
            _BandwidthUpgrade.VeryAdvancedPlus6,
            _BandwidthUpgrade.VeryAdvancedPlus8
        ], 
        _BrainType.SelfAware: [
            _BandwidthUpgrade.BasicHunterKillerPlus1,
            _BandwidthUpgrade.AdvancedPlus2,
            _BandwidthUpgrade.AdvancedPlus3,
            _BandwidthUpgrade.AdvancedPlus4,            
            _BandwidthUpgrade.VeryAdvancedPlus6,
            _BandwidthUpgrade.VeryAdvancedPlus8,            
            _BandwidthUpgrade.SelfAwarePlus10,
            _BandwidthUpgrade.SelfAwarePlus15,
            _BandwidthUpgrade.SelfAwarePlus20,
            _BandwidthUpgrade.SelfAwarePlus25
        ],       
        _BrainType.Conscious: [
            _BandwidthUpgrade.BasicHunterKillerPlus1,
            _BandwidthUpgrade.AdvancedPlus2,
            _BandwidthUpgrade.AdvancedPlus3,
            _BandwidthUpgrade.AdvancedPlus4,            
            _BandwidthUpgrade.VeryAdvancedPlus6,
            _BandwidthUpgrade.VeryAdvancedPlus8,            
            _BandwidthUpgrade.SelfAwarePlus10,
            _BandwidthUpgrade.SelfAwarePlus15,
            _BandwidthUpgrade.SelfAwarePlus20,
            _BandwidthUpgrade.SelfAwarePlus25,            
            _BandwidthUpgrade.ConsciousPlus30,
            _BandwidthUpgrade.ConsciousPlus40,
            _BandwidthUpgrade.ConsciousPlus50
        ]
    }

    _BandwidthUpgradeSlots = common.ScalarCalculation(
        value=1,
        name='Bandwidth Upgrade Required Slots')

    # Data Structure: INT Increase, Bandwidth Cost
    _IntellectUpgradeBandwidthUsage = {
        _IntellectUpgrade.IntelligencePlus1: (1, 1),
        _IntellectUpgrade.IntelligencePlus2: (2, 3),
        _IntellectUpgrade.IntelligencePlus3: (3, 6)
    }

    _IntellectUpgradeBaseCost = common.ScalarCalculation(
        value=1000,
        name='Intellect Upgrade Base Cost')
    _IntellectUpgradeHighIntThreshold = common.ScalarCalculation(
        value=12,
        name='Intellect Upgrade High INT Threshold')
    _IntellectUpgradeHighIntMultiplier = common.ScalarCalculation(
        value=2,
        name='Intellect Upgrade High INT Multiplier')    

    def __init__(
            self,
            brainType: _BrainType,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__()

        self._brainType = brainType
        self._componentString = f'{brainType.value} TL {minTL}'

        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{self._componentString} Brain Minimum TL') 
            
        self._cost = common.ScalarCalculation(
            value=cost,
            name=f'{self._componentString} Brain Cost') 
            
        self._intelligence = common.ScalarCalculation(
            value=intelligence,
            name=f'{self._componentString} Brain INT Characteristic')             
            
        self._inherentBandwidth = common.ScalarCalculation(
            value=inherentBandwidth,
            name=f'{self._componentString} Brain Inherent Bandwidth')

        self._notes = list(notes)

        self._hardenedOption = construction.BooleanOption(
            id='Hardened',
            name='Hardened',
            value=False,
            description='Specify if the brain is protected from radiation and ion weapons')

        self._bandwidthUpgradeOption = construction.EnumOption(
            id='BandwidthUpgrade',
            name='Bandwidth Upgrade',
            type=Brain._BandwidthUpgrade,
            isOptional=True,
            description='Optionally upgrade the Bandwidth of the Brain.')
        
        self._intellectUpgradeOption = construction.EnumOption(
            id='IntellectUpgrade',
            name='Intellect Upgrade',
            type=Brain._IntellectUpgrade,
            isOptional=True,
            description='Optionally upgrade the Brains INT characteristic.')        

    def instanceString(self) -> str:
        if self._isHardened():
            return 'Hardened ' + self._componentString
        return self._componentString

    def componentString(self) -> str:
        return self._componentString
    
    def typeString(self) -> str:
        return 'Brain'        

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if context.techLevel() < self._minTL.value():
            return False

        return context.hasComponent(
            componentType=robots.Chassis,
            sequence=sequence)
    
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        if self._hardenedOption.isEnabled():
            options.append(self._hardenedOption)
        if self._bandwidthUpgradeOption.isEnabled():
            options.append(self._bandwidthUpgradeOption)
        if self._intellectUpgradeOption.isEnabled():
            options.append(self._intellectUpgradeOption)
        return options

    def updateOptions(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        self._hardenedOption.setEnabled(
            enabled=context.techLevel() >= Brain._HardenedMinTL.value())

        bandwidthUpgrades = self._allowedBandwidthUpgrades(
            sequence=sequence,
            context=context)
        self._bandwidthUpgradeOption.setEnabled(
            enabled=len(bandwidthUpgrades) > 0)
        self._bandwidthUpgradeOption.setOptions(
            options=bandwidthUpgrades)
        
        intellectUpgrades = self._allowedIntellectUpgrades(
            sequence=sequence,
            context=context)
        self._intellectUpgradeOption.setEnabled(
            enabled=len(intellectUpgrades) > 0)
        self._intellectUpgradeOption.setOptions(
            options=intellectUpgrades)
        
    def createSteps(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createPrimaryStep(
                sequence=sequence,
                context=context))
        
        bandwidthStep = self._createBandwidthUpgradeStep(
            sequence=sequence,
            context=context)
        if bandwidthStep:
            context.applyStep(
                sequence=sequence,
                step=bandwidthStep)
            
        intellectStep = self._createIntellectUpgradeStep(
            sequence=sequence,
            context=context)
        if intellectStep:
            context.applyStep(
                sequence=sequence,
                step=intellectStep) 

    def _isHardened(self) -> bool:
        return self._hardenedOption.value() if self._hardenedOption.isEnabled() else False
        
    def _allowedBandwidthUpgrades(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.List[_BandwidthUpgrade]:
        possible = Brain._BandwidthUpgradeCompat.get(self._brainType)
        if not possible:
            return []

        robotTL = context.techLevel()
        allowed = []
        for upgrade in possible:
            minTL, _, _ = Brain._BandwidthUpgradeData[upgrade]
            if robotTL >= minTL:
                allowed.append(upgrade)
        return allowed
    
    def _selectedBandwidthUpgrade(self) -> typing.Optional[_BandwidthUpgrade]:
        return self._bandwidthUpgradeOption.value() \
            if self._bandwidthUpgradeOption.isEnabled() else \
            None
    
    def _allowedIntellectUpgrades(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.List[_IntellectUpgrade]:
        maxBandwidth = self._inherentBandwidth.value()
        bandwidthUpgrade = self._selectedBandwidthUpgrade()
        if bandwidthUpgrade:
            _, _, bandwidthUsed = Brain._BandwidthUpgradeData[bandwidthUpgrade]
            maxBandwidth += bandwidthUsed
            
        allowed = []
        for upgrade in Brain._IntellectUpgrade:
            _, bandwidthUsed = Brain._IntellectUpgradeBandwidthUsage[upgrade]
            if bandwidthUsed <= maxBandwidth:
                allowed.append(upgrade)
        return allowed

    def _selectedIntellectUpgrade(self) -> typing.Optional[_IntellectUpgrade]:
        return self._intellectUpgradeOption.value() \
            if self._intellectUpgradeOption.isEnabled() else \
            None

    def _createPrimaryStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> robots.RobotStep:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        robotTL = common.ScalarCalculation(
            value=context.techLevel(),
            name='Robot TL')
        
        robotSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        assert(isinstance(robotSize, common.ScalarCalculation))

        deltaTL = common.Calculator.subtract(
            lhs=robotTL,
            rhs=self._minTL,
            name=f'Tech Levels Since {self.componentString()} Introduction')
        assert(deltaTL.value() >= 0)
        
        # A brain requires no slots if it's Size is greater than or equal the
        # threshold below, otherwise it requires 1 slot
        # (Computer/X - (RobotTL - BrainMinTL))
        brainSizeThreshold = common.Calculator.subtract(
            lhs=self._inherentBandwidth,
            rhs=deltaTL,
            name='Brain Size Threshold')
        if robotSize.value() < brainSizeThreshold.value():
            step.setSlots(slots=construction.ConstantModifier(
                value=Brain._HighRelativeBrainSizeSlotCost))
        
        # A brains cost drops by 50% for every TL after it was introduced
        cost = self._cost
        for index in range(deltaTL.value()):
            iterTL = self._minTL.value() + index + 1
            cost = common.Calculator.multiply(
                lhs=cost,
                rhs=Brain._RetrotechPerTLCostScale,
                name=f'{self.componentString()} Cost For TL{iterTL} Robot')
        if self._isHardened():
            cost = common.Calculator.applyPercentage(
                value=cost,
                percentage=Brain._HardenedCostPercent,
                name=f'Hardened {cost.name()}')            
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.Intelligence,
            value=self._intelligence))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            value=self._inherentBandwidth))
        
        # NOTE: Initialise current max bandwidth to the inherent bandwidth
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            value=self._inherentBandwidth))
        
        return step
    
    def _createBandwidthUpgradeStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        upgrade = self._selectedBandwidthUpgrade()
        if not upgrade:
            return None# Nothing to do
        assert(isinstance(upgrade, Brain._BandwidthUpgrade))
        
        _, cost, bandwidth = Brain._BandwidthUpgradeData[upgrade]
        cost = common.ScalarCalculation(
            value=cost,
            name=f'{upgrade.value} Bandwidth Upgrade Cost')
        bandwidth = common.ScalarCalculation(
            value=bandwidth,
            name=f'{upgrade.value} Bandwidth Increase')
        
        stepName = f'Bandwidth Upgrade ({upgrade.value})'
        if self._isHardened():
            stepName = 'Hardened ' + stepName
            cost = common.Calculator.applyPercentage(
                value=cost,
                percentage=Brain._HardenedCostPercent,
                name=f'Hardened {cost.name()}')

        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
        
        step.setCredits(credits=construction.ConstantModifier(value=cost))
        step.setSlots(slots=construction.ConstantModifier(
            value=Brain._BandwidthUpgradeSlots))

        # NOTE: Update max bandwidth NOT inherent bandwidth
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            modifier=construction.ConstantModifier(value=bandwidth)))

        return step   

    def _createIntellectUpgradeStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        upgrade = self._selectedIntellectUpgrade()
        if not upgrade:
            return None# Nothing to do
        assert(isinstance(upgrade, Brain._IntellectUpgrade))

        step = robots.RobotStep(
            name=f'Intellect Upgrade ({upgrade.value})',
            type=self.typeString())        

        intelligenceIncrease, bandwidthUsed = Brain._IntellectUpgradeBandwidthUsage[upgrade]
        intelligenceIncrease = common.ScalarCalculation(
            value=intelligenceIncrease,
            name=f'{upgrade.value} Intellect Upgrade INT Increase')
        bandwidthUsed = common.ScalarCalculation(
            value=bandwidthUsed,
            name=f'{upgrade.value} Intellect Upgrade Required Bandwidth')        

        oldIntelligence = context.attributeValue(
            attributeId=robots.RobotAttributeId.Intelligence,
            sequence=sequence)
        assert(isinstance(oldIntelligence, common.ScalarCalculation))

        multiplier = common.Calculator.add(
            lhs=oldIntelligence,
            rhs=common.ScalarCalculation(value=1))
        if upgrade != Brain._IntellectUpgrade.IntelligencePlus1:
            multiplier = common.Calculator.multiply(
                lhs=multiplier,
                rhs=common.Calculator.add(
                    lhs=oldIntelligence,
                    rhs=common.ScalarCalculation(value=2)))
            if upgrade != Brain._IntellectUpgrade.IntelligencePlus2:
                multiplier = common.Calculator.multiply(
                    lhs=multiplier,
                    rhs=common.Calculator.add(
                        lhs=oldIntelligence,
                        rhs=common.ScalarCalculation(value=3)))
        
        newIntelligence = common.Calculator.add(
            lhs=oldIntelligence,
            rhs=intelligenceIncrease,
            name='New INT Characteristic')
        if newIntelligence.value() >= Brain._IntellectUpgradeHighIntThreshold.value():
            multiplier = common.Calculator.multiply(
                lhs=multiplier,
                rhs=Brain._IntellectUpgradeHighIntMultiplier)
            
        multiplier = common.Calculator.rename(
            value=multiplier,
            name=f'{upgrade.value} Intellect Upgrade Cost Multiplier')

        cost = common.Calculator.multiply(
            lhs=Brain._IntellectUpgradeBaseCost,
            rhs=multiplier,
            name=f'{upgrade.value} Intellect Upgrade Cost')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.Intelligence,
            modifier=construction.ConstantModifier(value=intelligenceIncrease)))        
        
        # NOTE: As this is still technically part of the brain I think it makes
        # sense to update the max available bandwidth rather than having a
        # bandwidth cost. This means the required bandwidth value needs to be
        # negated as the positive value needs to be converted to a negative
        # modifier
        # NOTE: Update max bandwidth NOT inherent bandwidth
        assert(bandwidthUsed.value() > 0)
        bandwidthUsed = common.Calculator.negate(
            value=bandwidthUsed,
            name=f'{upgrade.value} Intellect Upgrade Max Bandwidth Modifier')    
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            modifier=construction.ConstantModifier(value=bandwidthUsed)))

        return step      
    
class PrimitiveBrain(Brain):
    """
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Inherent Bandwidth 0    
    - Note: Programmable
    - Requirement: I don't think this is compatible with additional skills  
    """
    # TODO: Handle incompatible with additional skills if that is how it
    # actually works. It seems odd that it would have a skill count (even
    # if it is a negative one, if it isn't compatible with additional skills)
      
    def __init__(
            self,
            minTL: int,
            cost: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.Primitive,
            minTL=minTL,
            cost=cost,
            intelligence=1,
            inherentBandwidth=0,
            notes=['Programmable']) # TODO: This is a crap note, needs more context#
        
class PrimitiveTL7Brain(PrimitiveBrain):
    """
    - Min TL: 7
    - Cost: Cr10000
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Inherent Bandwidth 0
    - Note: Programmable
    """
      
    def __init__(self) -> None:
        super().__init__(
            minTL=7,
            cost=10000)
        
class PrimitiveTL8Brain(PrimitiveBrain):
    """
    - Min TL: 8
    - Cost: Cr100
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Inherent Bandwidth 0
    - Note: Programmable
    """
      
    def __init__(self) -> None:
        super().__init__(
            minTL=8,
            cost=100)
 
class BasicBrain(Brain):
    """
    - Trait: Computer/1
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    - Requirement: I don't think this is compatible with additional skills  
    """
    # TODO: Handle incompatible with additional skills if that is how it
    # actually works. It seems odd that it would have a skill count (even
    # if it is a negative one, if it isn't compatible with additional skills)
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.Basic,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=1,
            notes=['Limited Language, Security/0']) # TODO: This is a crap note
                
class BasicTL8Brain(BasicBrain):
    """
    - Min TL: 8
    - Cost: Cr20000
    - Trait: INT 3
    - Trait: Computer/1
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=8,
            cost=20000,
            intelligence=3)
        
class BasicTL10Brain(BasicBrain):
    """
    - Min TL: 10
    - Cost: Cr4000
    - Trait: Computer/1
    - Trait: INT 4
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=10,
            cost=4000,
            intelligence=4) 
        
class HunterKillerBrain(Brain):
    """
    - Trait: Computer/1
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1    
    """
    # TODO: Handle incompatible with additional skills if that is how it
    # actually works. It seems odd that it would have a skill count (even
    # if it is a negative one, if it isn't compatible with additional skills)
    # TODO: Handle Recon skill
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.HunterKiller,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=1,
            notes=['Limited Fried or Foe, Security/1']) # TODO: This is a crap note
                
class HunterKillerTL8Brain(HunterKillerBrain):
    """
    - Min TL: 8
    - Cost: Cr30000
    - Trait: INT 3
    - Trait: Computer/1
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=8,
            cost=30000,
            intelligence=3)
        
class HunterKillerTL10Brain(HunterKillerBrain):
    """
    - Min TL: 10
    - Cost: Cr6000
    - Trait: INT 4
    - Trait: Computer/1
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=10,
            cost=6000,
            intelligence=4)
        
class SkilledBrain(Brain):
    """
    - Skill Count: The robot can have an additional number of zero-level skills
    equal to the Computer/X inherent Bandwidth of the brain
    """
    # TODO: Handle additional skills

    def __init__(
            self,
            brainType: Brain._BrainType,
            minTL: typing.Union[int, common.ScalarCalculation],
            cost: typing.Union[int, common.ScalarCalculation],
            intelligence: typing.Union[int, common.ScalarCalculation],
            inherentBandwidth: typing.Union[int, common.ScalarCalculation],
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            brainType=brainType,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            notes=notes)     
        
class AdvancedBrain(SkilledBrain):
    """
    - Trait: Computer/2
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.Advanced,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=2,
            notes=['Limited Fried or Foe, Security/1', # TODO: This is a crap note
                   'Can only attempt tasks up to Difficult (10+)'])
                
class AdvancedTL10Brain(AdvancedBrain):
    """
    - Min TL: 10
    - Cost: Cr100000
    - Trait: INT 6
    - Trait: Computer/2
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)  
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=10,
            cost=100000,
            intelligence=6)
        
class AdvancedTL11Brain(AdvancedBrain):
    """
    - Min TL: 11
    - Cost: Cr50000
    - Trait: INT 7
    - Trait: Computer/2
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+) 
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=11,
            cost=50000,
            intelligence=7) 
        
class AdvancedTL12Brain(AdvancedBrain):
    """
    - Min TL: 12
    - Cost: Cr10000
    - Trait: INT 8
    - Trait: Computer/2
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=12,
            cost=10000,
            intelligence=8) 

class VeryAdvancedBrain(SkilledBrain):
    """
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.VeryAdvanced,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            notes=['Intellect Interface, Expert/2, Security/2', # TODO: This is a crap note
                   'Can only attempt tasks up to Very Difficult (12+)'])
                
class VeryAdvancedTL12Brain(VeryAdvancedBrain):
    """
    - Min TL: 12
    - Cost: Cr500000
    - Trait: INT 9
    - Trait: Computer/3
    - Trait: Inherent Bandwidth 3
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=12,
            cost=500000,
            intelligence=9,
            inherentBandwidth=3)
        
class VeryAdvancedTL13Brain(VeryAdvancedBrain):
    """
    - Min TL: 13
    - Cost: Cr500000
    - Trait: INT 10
    - Trait: Computer/4
    - Trait: Inherent Bandwidth 4
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+) 
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=13,
            cost=500000,
            intelligence=10,
            inherentBandwidth=4)
        
class VeryAdvancedTL14Brain(VeryAdvancedBrain):
    """
    - Min TL: 14
    - Cost: Cr500000
    - Trait: INT 11
    - Trait: Computer/5
    - Trait: Inherent Bandwidth 5
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=14,
            cost=500000,
            intelligence=11,
            inherentBandwidth=5)

class SelfAwareBrain(SkilledBrain):
    """
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.SelfAware,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            notes=['Near sentient, Expert/3, Security/3', # TODO: This is a crap note
                   'Can only attempt tasks up to Formidable (14+)'])
                
class SelfAwareTL15Brain(SelfAwareBrain):
    """
    - Min TL: 15
    - Cost: Cr1000000
    - Trait: INT 12
    - Trait: Computer/10
    - Trait: Inherent Bandwidth 10
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=15,
            cost=1000000,
            intelligence=12,
            inherentBandwidth=10)
        
class SelfAwareTL16Brain(SelfAwareBrain):
    """
    - Min TL: 16
    - Cost: Cr1000000
    - Trait: INT 13
    - Trait: Computer/15
    - Trait: Inherent Bandwidth 15
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=16,
            cost=1000000,
            intelligence=13,
            inherentBandwidth=15)

class ConsciousBrain(SkilledBrain):
    """
    - Note: Conscious Intelligence, Security/3   
    """
    # TODO: Handle additional zero level skills
      
    def __init__(
            self,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.Conscious,
            minTL=minTL,
            cost=cost,
            intelligence=intelligence,
            inherentBandwidth=inherentBandwidth,
            notes=['Conscious Intelligence, Security/3']) # TODO: This is a crap note
                
class ConsciousTL17Brain(ConsciousBrain):
    """
    - Min TL: 17
    - Cost: Cr5000000
    - Trait: INT 15
    - Trait: Computer/20
    - Trait: Inherent Bandwidth 20
    - Note: Conscious Intelligence, Security/3
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=17,
            cost=5000000,
            intelligence=15,
            inherentBandwidth=20)
        
class ConsciousTL18Brain(ConsciousBrain):
    """
    - Min TL: 18
    - Cost: Cr1000000
    - Trait: INT 15
    - Trait: Computer/30
    - Trait: Inherent Bandwidth 30
    - Note: Conscious Intelligence, Security/3
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=18,
            cost=1000000,
            intelligence=15,
            inherentBandwidth=30)