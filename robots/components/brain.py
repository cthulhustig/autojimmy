import common
import construction
import enum
import robots
import typing

class Brain(robots.RobotComponentInterface):
    class _BrainType(enum.Enum):
        Primitive = 'Primitive'
        Basic = 'Basic'
        HunterKiller = 'Hunter/Killer'
        Advanced = 'Advanced'
        VeryAdvanced = 'Very Advanced'
        SelfAware = 'Self-Aware'
        Conscious = 'Conscious'
        BrainInAJar = 'Brain in a Jar'

    def __init__(
            self,
            brainType: _BrainType,
            minTL: int
            ) -> None:
        super().__init__()

        self._componentString = f'{brainType.value} TL {minTL}'
        self._brainType = brainType

        self._minTL = common.ScalarCalculation(
            value=minTL,
            name=f'{self._componentString} Brain Minimum TL') 
        
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

class RobotBrain(Brain):
    """
    - Slots: The number of slots taken up by a brain works like this (p66)
        - The brain has no slot requirement If the robot's Size is greater than
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
        - Trait: Hardened
    """
    # NOTE: The Security/X trait that some brains have determine how difficult
    # the are to hack (p106)
    # NOTE: The Expert/X trait that some brains have determines what level of
    # skill the robot can attempt (Difficult (10+), Very Difficult (12+) etc)
    # NOTE: The rules don't explicitly say Brain Hardening gives the Hardened
    # trait but I think it's obvious implied.
    # NOTE: The table in the rules that gives the brain stats (p66) has a Skills
    # column. It's not explicitly stated but as far as I can see it's just
    # giving the INT modifier for the brain. The numbers match up with those
    # used when doing the same for player characteristics (e.g. an INT of 1
    # gives a -2 modifier). If this is not
    # NOTE: The INT upgrade reduces Max Bandwidth rather than having a bandwidth
    # cost. This makes handling some stuff easier (e.g. robot as a player
    # character) and it also makes some conceptual sense as this is being done
    # as a mod to the brain rather than a skill that would require bandwidth to
    # execute

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

    _BandwidthUpgradeCompat = {
        Brain._BrainType.Basic: [
            _BandwidthUpgrade.BasicHunterKillerPlus1
        ],
        Brain._BrainType.HunterKiller: [
            _BandwidthUpgrade.BasicHunterKillerPlus1
        ], 
        Brain._BrainType.Advanced: [
            _BandwidthUpgrade.BasicHunterKillerPlus1,
            _BandwidthUpgrade.AdvancedPlus2,
            _BandwidthUpgrade.AdvancedPlus3,
            _BandwidthUpgrade.AdvancedPlus4
        ],                
        Brain._BrainType.VeryAdvanced: [
            _BandwidthUpgrade.BasicHunterKillerPlus1,
            _BandwidthUpgrade.AdvancedPlus2,
            _BandwidthUpgrade.AdvancedPlus3,
            _BandwidthUpgrade.AdvancedPlus4,            
            _BandwidthUpgrade.VeryAdvancedPlus6,
            _BandwidthUpgrade.VeryAdvancedPlus8
        ], 
        Brain._BrainType.SelfAware: [
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
        Brain._BrainType.Conscious: [
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

    _RetrotechCompatibleBrains = [
        Brain._BrainType.VeryAdvanced,
        Brain._BrainType.SelfAware,
        Brain._BrainType.Conscious
    ]

    _BandwidthUpgradeSlots = common.ScalarCalculation(
        value=1,
        name='Bandwidth Upgrade Required Slots')

    # Data Structure: INT Increase, Required Bandwidth
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
            brainType: Brain._BrainType,
            minTL: int,
            cost: int,
            intelligence: int,
            inherentBandwidth: int,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(brainType=brainType, minTL=minTL)
            
        self._cost = common.ScalarCalculation(
            value=cost,
            name=f'{self._componentString} Brain Cost') 
            
        self._intelligence = common.ScalarCalculation(
            value=intelligence,
            name=f'{self._componentString} Brain INT Characteristic')             
            
        self._inherentBandwidth = common.ScalarCalculation(
            value=inherentBandwidth,
            name=f'{self._componentString} Brain Inherent Bandwidth')

        self._notes = notes

        self._hardenedOption = construction.BooleanOption(
            id='Hardened',
            name='Hardened',
            value=False,
            description='Specify if the brain is protected from radiation and ion weapons')

        self._bandwidthUpgradeOption = construction.EnumOption(
            id='BandwidthUpgrade',
            name='Bandwidth Upgrade',
            type=RobotBrain._BandwidthUpgrade,
            isOptional=True,
            description='Optionally upgrade the Bandwidth of the Brain.')
        
        self._intellectUpgradeOption = construction.EnumOption(
            id='IntellectUpgrade',
            name='Intellect Upgrade',
            type=RobotBrain._IntellectUpgrade,
            isOptional=True,
            description='Optionally upgrade the Brains INT characteristic.')        

    def instanceString(self) -> str:
        if self._isHardened():
            return 'Hardened ' + self._componentString
        return self._componentString
    
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
            enabled=context.techLevel() >= RobotBrain._HardenedMinTL.value())

        bandwidthUpgrades = self._allowedBandwidthUpgrades(
            sequence=sequence,
            context=context)
        self._bandwidthUpgradeOption.setEnabled(
            enabled=len(bandwidthUpgrades) > 0)
        self._bandwidthUpgradeOption.setChoices(
            choices=bandwidthUpgrades)
        
        intellectUpgrades = self._allowedIntellectUpgrades(
            sequence=sequence,
            context=context)
        self._intellectUpgradeOption.setEnabled(
            enabled=len(intellectUpgrades) > 0)
        self._intellectUpgradeOption.setChoices(
            choices=intellectUpgrades)
        
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
        possible = RobotBrain._BandwidthUpgradeCompat.get(self._brainType)
        if not possible:
            return []

        robotTL = context.techLevel()
        allowed = []
        for upgrade in possible:
            minTL, _, _ = RobotBrain._BandwidthUpgradeData[upgrade]
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
            _, _, bandwidthIncrease = RobotBrain._BandwidthUpgradeData[bandwidthUpgrade]
            maxBandwidth += bandwidthIncrease
            
        allowed = []
        for upgrade in RobotBrain._IntellectUpgrade:
            _, requiredBandwidth = RobotBrain._IntellectUpgradeBandwidthUsage[upgrade]
            if requiredBandwidth <= maxBandwidth:
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
                value=RobotBrain._HighRelativeBrainSizeSlotCost))
        
        # The cost of brains of Very Advanced construction or later drops by
        # 50% for every TL after it was introduced
        cost = self._cost
        if self._brainType in RobotBrain._RetrotechCompatibleBrains:
            for index in range(deltaTL.value()):
                iterTL = self._minTL.value() + index + 1
                cost = common.Calculator.multiply(
                    lhs=cost,
                    rhs=RobotBrain._RetrotechPerTLCostScale,
                    name=f'Retrotech {self.componentString()} Cost at TL{iterTL}')
        if self._isHardened():
            cost = common.Calculator.applyPercentage(
                value=cost,
                percentage=RobotBrain._HardenedCostPercent,
                name=f'Hardened {cost.name()}')
            step.addFactor(factor=construction.SetAttributeFactor(
                attributeId=robots.RobotAttributeId.Hardened))         
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.INT,
            value=self._intelligence))
        
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.InherentBandwidth,
            value=self._inherentBandwidth))
        
        # NOTE: Initialise current max bandwidth to the inherent bandwidth
        step.addFactor(factor=construction.SetAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            value=self._inherentBandwidth))
        
        if self._notes:
            for note in self._notes:
                step.addNote(note=note)
        
        return step
    
    def _createBandwidthUpgradeStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        upgrade = self._selectedBandwidthUpgrade()
        if not upgrade:
            return None# Nothing to do
        assert(isinstance(upgrade, RobotBrain._BandwidthUpgrade))
        
        _, cost, bandwidthIncrease = RobotBrain._BandwidthUpgradeData[upgrade]
        cost = common.ScalarCalculation(
            value=cost,
            name=f'{upgrade.value} Bandwidth Upgrade Cost')
        bandwidthIncrease = common.ScalarCalculation(
            value=bandwidthIncrease,
            name=f'{upgrade.value} Bandwidth Increase')
        
        stepName = f'Bandwidth Upgrade ({upgrade.value})'
        if self._isHardened():
            stepName = 'Hardened ' + stepName
            cost = common.Calculator.applyPercentage(
                value=cost,
                percentage=RobotBrain._HardenedCostPercent,
                name=f'Hardened {cost.name()}')

        step = robots.RobotStep(
            name=stepName,
            type=self.typeString())
        
        step.setCredits(credits=construction.ConstantModifier(value=cost))
        step.setSlots(slots=construction.ConstantModifier(
            value=RobotBrain._BandwidthUpgradeSlots))

        # NOTE: Update max bandwidth NOT inherent bandwidth
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            modifier=construction.ConstantModifier(value=bandwidthIncrease)))

        return step   

    def _createIntellectUpgradeStep(
            self,
            sequence: str,
            context: robots.RobotContext
            ) -> typing.Optional[robots.RobotStep]:
        upgrade = self._selectedIntellectUpgrade()
        if not upgrade:
            return None# Nothing to do
        assert(isinstance(upgrade, RobotBrain._IntellectUpgrade))

        step = robots.RobotStep(
            name=f'Intellect Upgrade ({upgrade.value})',
            type=self.typeString())        

        intelligenceIncrease, requiredBandwidth = RobotBrain._IntellectUpgradeBandwidthUsage[upgrade]
        intelligenceIncrease = common.ScalarCalculation(
            value=intelligenceIncrease,
            name=f'{upgrade.value} Intellect Upgrade INT Increase')
        requiredBandwidth = common.ScalarCalculation(
            value=requiredBandwidth,
            name=f'{upgrade.value} Intellect Upgrade Required Bandwidth')
        maxBandwidthModifier = common.Calculator.negate(
            value=requiredBandwidth,
            name=f'{upgrade.value} Intellect Upgrade Max Bandwidth Modifier')

        oldIntelligence = context.attributeValue(
            attributeId=robots.RobotAttributeId.INT,
            sequence=sequence)
        assert(isinstance(oldIntelligence, common.ScalarCalculation))

        multiplier = common.Calculator.add(
            lhs=oldIntelligence,
            rhs=common.ScalarCalculation(value=1))
        if upgrade != RobotBrain._IntellectUpgrade.IntelligencePlus1:
            multiplier = common.Calculator.multiply(
                lhs=multiplier,
                rhs=common.Calculator.add(
                    lhs=oldIntelligence,
                    rhs=common.ScalarCalculation(value=2)))
            if upgrade != RobotBrain._IntellectUpgrade.IntelligencePlus2:
                multiplier = common.Calculator.multiply(
                    lhs=multiplier,
                    rhs=common.Calculator.add(
                        lhs=oldIntelligence,
                        rhs=common.ScalarCalculation(value=3)))
        
        newIntelligence = common.Calculator.add(
            lhs=oldIntelligence,
            rhs=intelligenceIncrease,
            name='New INT Characteristic')
        if newIntelligence.value() >= RobotBrain._IntellectUpgradeHighIntThreshold.value():
            multiplier = common.Calculator.multiply(
                lhs=multiplier,
                rhs=RobotBrain._IntellectUpgradeHighIntMultiplier)
            
        multiplier = common.Calculator.rename(
            value=multiplier,
            name=f'{upgrade.value} Intellect Upgrade Cost Multiplier')

        cost = common.Calculator.multiply(
            lhs=RobotBrain._IntellectUpgradeBaseCost,
            rhs=multiplier,
            name=f'{upgrade.value} Intellect Upgrade Cost')
        step.setCredits(credits=construction.ConstantModifier(value=cost))

        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.INT,
            modifier=construction.ConstantModifier(value=intelligenceIncrease)))
        
        # NOTE: Update max bandwidth NOT inherent bandwidth
        step.addFactor(factor=construction.ModifyAttributeFactor(
            attributeId=robots.RobotAttributeId.MaxBandwidth,
            modifier=construction.ConstantModifier(value=maxBandwidthModifier)))        

        return step      
    
class PrimitiveBrain(RobotBrain):
    """
    - Trait: INT 1
    - Trait: Computer/0
    - Trait: Inherent Bandwidth 0    
    - Note: Programmable
    - Requirement: I don't think this is compatible with additional skills  
    """
      
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
            notes=['Programmable, Computer/0. (p66)'])
        
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
 
class BasicBrain(RobotBrain):
    """
    - Trait: Computer/1
    - Trait: Inherent Bandwidth 1
    - Note: Limited Language, Security/0
    - Requirement: I don't think this is compatible with additional skills  
    """
      
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
            notes=['Limited Language, Security/0, Computer/1. (p66)'])
                
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
        
class HunterKillerBrain(RobotBrain):
    """
    - Trait: Computer/1
    - Skill: Recon 0
    - Trait: Inherent Bandwidth 1
    - Note: Limited Fried or Foe, Security/1    
    """
    # NOTE: The Recon 0 mentioned in the description of the brain (p65) is
    # handled by the Hunter/Killer Skill Package. As far as I can tell you
    # have to take a skill package and both variants give Recon 0.
      
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
            notes=['Limited Fried or Foe, Security/1, Computer/1. (p66)'])
                
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

# This class only exists so other components can easily check if a robot has
# a brain that can skills (rather than a skill package) 
class SkilledRobotBrain(RobotBrain):
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
        
class AdvancedBrain(SkilledRobotBrain):
    """
    - Trait: Computer/2
    - Trait: Inherent Bandwidth 2
    - Note: Intelligent Interface, Expert/1, Security/1
    - Note: Advanced brains can only attempt tasks up to Difficult (10+)
    """
      
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
            notes=['Intelligent Interface, Expert/1, Security/1, Computer/2. (p66)',
                   'The robot can only attempt tasks up to Difficult (10+). (p65)'])
                
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

class VeryAdvancedBrain(SkilledRobotBrain):
    """
    - Note: Intellect Interface, Expert/2, Security/2
    - Note: Advanced brains can only attempt tasks up to Very Difficult (12+)
    """
      
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
            notes=[f'Intellect Interface, Expert/2, Security/2, Computer/{inherentBandwidth}. (p66)',
                   'The robot can only attempt tasks up to Very Difficult (12+). (p65)'])
                
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

class SelfAwareBrain(SkilledRobotBrain):
    """
    - Note: Near sentient, Expert/3, Security/3
    - Note: Advanced brains can only attempt tasks up to Formidable (14+)
    """
      
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
            notes=[f'Near sentient, Expert/3, Security/3, Computer/{inherentBandwidth}. (p66)',
                   'The robot can only attempt tasks up to Formidable (14+). (p65/66)'])
                
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

class ConsciousBrain(SkilledRobotBrain):
    """
    - Note: Conscious Intelligence, Security/3   
    """
      
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
            notes=[f'Conscious Intelligence, Security/3, Computer/{inherentBandwidth}. (p66)'])
                
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
        
# NOTE: This is inherits from Brain not RobotBrain
class BrainInAJarBrain(Brain):
    """
    - Requirement: Must be size 2 or greater
    - Requirement: Skills have no cost or bandwidth requirement there is also no limitation on the number of skills
    - Option: Optionally specify INT, EDU, SOC, PSI, LCK, WLT (Wealth), MRL (Morale), STY (Sanity)
   """
    # NOTE: This is based on the 'Brain in a Jar' concept from the Full-body
    # Cybernetics rules (p92)
    # NOTE: The fact that there is no costs or number cap on skills is based on
    # my logic that the skills come from the living brain that is being installed
    # NOTE: Adding a note for the Degradation check is handled by the derived
    # classes as some have a check every month and some annually

    _ConfigurableCharacteristics = robots.MentalCharacteristicAttributeIds + \
        robots.OptionalCharacteristicAttributeIds

    _MinChassisSize = 2

    def __init__(
            self,
            minTL: int,
            cost: int,
            slots: int,
            notes: typing.Optional[typing.Iterable[str]] = None
            ) -> None:
        super().__init__(
            brainType=Brain._BrainType.BrainInAJar,
            minTL=minTL)
        
        self._cost = common.ScalarCalculation(
            value=cost,
            name=f'{self._componentString} Cost')
        
        self._slots = common.ScalarCalculation(
            value=slots,
            name=f'{self._componentString} Required Slots')
        
        self._notes = notes

        self._characteristicOptions: typing.Dict[robots.RobotAttributeId, construction.IntegerOption] = {}
        for characteristic in BrainInAJarBrain._ConfigurableCharacteristics:
            isOptional = characteristic in robots.OptionalCharacteristicAttributeIds
            option = construction.IntegerOption(
                id=characteristic.value,
                name=characteristic.value,
                isOptional=isOptional,
                minValue=0,
                maxValue=99, # This is pretty arbitrary but having a max makes the UI scale the control better
                value=None if isOptional else 0,
                description=f'Specify the {characteristic.value} characteristics of the brain.')
            self._characteristicOptions[characteristic] = option

    def isCompatible(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> bool:
        if not super().isCompatible(sequence, context):
            return False
        
        chassisSize = context.attributeValue(
            attributeId=robots.RobotAttributeId.Size,
            sequence=sequence)
        return chassisSize and chassisSize.value() >= BrainInAJarBrain._MinChassisSize
        
    def options(self) -> typing.List[construction.ComponentOption]:
        options = []
        for option in self._characteristicOptions.values():
            if option.isEnabled():
                options.append(option)
        return options

    def createSteps(
            self,
            sequence: str,
            context: construction.ConstructionContext
            ) -> None:
        step = robots.RobotStep(
            name=self.instanceString(),
            type=self.typeString())
        
        step.setCredits(
            credits=construction.ConstantModifier(value=self._cost))
        step.setSlots(
            slots=construction.ConstantModifier(value=self._slots))
        
        characteristicNotes = []
        for characteristic, option in self._characteristicOptions.items():
            if option.isEnabled() and option.value() != None:
                step.addFactor(factor=construction.SetAttributeFactor(
                    attributeId=characteristic,
                    value=common.ScalarCalculation(
                        value=option.value(),
                        name=f'Specified {characteristic.value} characteristic value')))

                characteristicNotes.append(f'{characteristic.value} {option.value()}')

        if characteristicNotes:
            step.addNote(note=', '.join(characteristicNotes))

        if self._notes:
            for note in self._notes:
                step.addNote(note=note)

        context.applyStep(
            sequence=sequence,
            step=step) 
        
class BrainInAJarTL12Brain(BrainInAJarBrain):
    """
    - Min TL: 12
    - Slots: 3
    - Cost: 1000000
    - Note: Monthly INT 4+ Degradation Checks (p93)    
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=12,
            cost=1000000,
            slots=3,
            notes=['INT 4+ Degradation Checks must be made monthly. (p93)'])
        
class BrainInAJarTL14Brain(BrainInAJarBrain):
    """
    - Min TL: 14
    - Slots: 2
    - Cost: 2000000
    - Note: Annual INT 5+ Degradation Checks (p93)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=14,
            cost=2000000,
            slots=2,
            notes=['INT 5+ Degradation Checks must be made annually. (p93)'])     

class BrainInAJarTL16Brain(BrainInAJarBrain):
    """
    - Min TL: 16
    - Slots: 2
    - Cost: 5000000
    - Note: Annual INT 3+ Degradation Checks (p93)
    """
    def __init__(self) -> None:
        super().__init__(
            minTL=16,
            cost=5000000,
            slots=2,
            notes=['INT 3+ Degradation Checks must be made annually. (p93)'])