import common
import construction
import enum
import gunsmith
import typing

class MagazineLoaded(gunsmith.WeaponComponentInterface):
    pass

class MagazineQuantity(gunsmith.WeaponComponentInterface):
    def createLoadedMagazine(self) -> MagazineLoaded:
        raise RuntimeError(f'{type(self)} is derived from MagazineQuantity so must implement createLoadedMagazine') 


# ███████████                          ███                     █████     ███  ████
#░░███░░░░░███                        ░░░                     ░░███     ░░░  ░░███
# ░███    ░███ ████████   ██████      █████  ██████   ██████  ███████   ████  ░███   ██████
# ░██████████ ░░███░░███ ███░░███    ░░███  ███░░███ ███░░███░░░███░   ░░███  ░███  ███░░███
# ░███░░░░░░   ░███ ░░░ ░███ ░███     ░███ ░███████ ░███ ░░░   ░███     ░███  ░███ ░███████
# ░███         ░███     ░███ ░███     ░███ ░███░░░  ░███  ███  ░███ ███ ░███  ░███ ░███░░░
# █████        █████    ░░██████      ░███ ░░██████ ░░██████   ░░█████  █████ █████░░██████
#░░░░░        ░░░░░      ░░░░░░       ░███  ░░░░░░   ░░░░░░     ░░░░░  ░░░░░ ░░░░░  ░░░░░░
#                                 ███ ░███
#                                ░░██████
#                                 ░░░░░░

# NOTE: These are the per grenade weight multiplier for a removable magazine (Field Catalogue p58).
# The wording doesn't explicitly state that it doesn't apply to fixed magazines but it does say
# that the weight causes them to be difficult to handle, the fact that it's talking about handling
# the magazine separately from the weapon would suggest it's talking about removable magazines.
# It's even less clear if the rules consider a belt a magazine in this context. I've chosen to treat
# it as one as it's consistent with what is done elsewhere.
_StandardGrenadeMagazinePerGrenadeWeight = common.ScalarCalculation(
    value=0.5,
    name='Standard Launcher Magazine Per Grenade Weight')
_LightGrenadeMagazinePerGrenadeWeight = common.ScalarCalculation(
    value=0.3,
    name='Light Launcher Magazine Per Grenade Weight')
def _calculateLauncherMagazinePerGrenadeWeight(
        sequence: str,
        context: gunsmith.WeaponContext
        ) -> common.ScalarCalculation:
    isLightLauncher = \
        context.hasComponent(
            componentType=gunsmith.LightSingleShotLauncherReceiver,
            sequence=sequence) \
        or context.hasComponent(
            componentType=gunsmith.LightSemiAutomaticLauncherReceiver,
            sequence=sequence) \
        or context.hasComponent(
            componentType=gunsmith.LightSupportLauncherReceiver,
            sequence=sequence)
    return _LightGrenadeMagazinePerGrenadeWeight if isLightLauncher else _StandardGrenadeMagazinePerGrenadeWeight

class _ProjectileMagazineImpl(object):
    """
    - Requirement: Only compatible with weapons that hae a removable magazine feed
    """
    # NOTE: When it comes to calculating the magazine cost it's not clear if the weapon cost
    # it's based on should include the cost of a secondary weapon or accessories. The wording
    # in the rules (Field Catalogue p45) says it's a percentage of the weapons purchase price.
    # It seems odd that the cost of the secondary weapon would affect the cost of a magazine
    # for the primary (or vice versa). To be as close to the wording of the rules as I can
    # I've chosen to include the cost of the secondary weapon. However I'm NOT including the
    # cost of accessories as having something that can be added to the weapon after construction
    # affect the cost of a magazine would make no logical sense

    def __init__(
            self,
            componentString: str,
            weaponPercentageCost: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            quickdrawModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            ) -> None:
        super().__init__()

        if weaponPercentageCost != None and not isinstance(weaponPercentageCost, common.ScalarCalculation):
            weaponPercentageCost = common.ScalarCalculation(
                value=weaponPercentageCost,
                name=f'{componentString} Weapon Cost Percentage')

        if quickdrawModifier != None and not isinstance(quickdrawModifier, common.ScalarCalculation):
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name=f'{componentString} Quickdraw Modifier')

        self._componentString = componentString
        self._weaponPercentageCost = weaponPercentageCost
        self._quickdrawModifier = quickdrawModifier

    def componentString(self) -> str:
        return self._componentString

    def instanceString(self) -> str:
        return self.componentString()

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        # Only compatible with weapons that have a receiver.
        if not context.hasComponent(
                componentType=gunsmith.Receiver,
                sequence=sequence):
            return False

        return context.hasComponent(
            componentType=gunsmith.RemovableMagazineFeed,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return []

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        pass

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        if self._weaponPercentageCost:
            itemCost = common.Calculator.takePercentage(
                value=context.baseCredits(sequence=sequence), # Only include cost of this weapon sequence
                percentage=self._weaponPercentageCost,
                name=f'{self.componentString()} Cost')
            assert(itemCost)
            totalCost = common.Calculator.multiply(
                lhs=itemCost,
                rhs=numberOfMagazines,
                name=f'{self.componentString()} Cost')
            step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        if self._quickdrawModifier:
            factor = construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(
                    value=self._quickdrawModifier))
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _StandardProjectileMagazineImpl(_ProjectileMagazineImpl):
    """
    - Cost: 1% of Weapon Purchase Price
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules say the magazine cost is a percentage of the weapon purchase price (Field
    # Catalogue p45). It's not entirely clear if that's the purchase cost of the base weapon or the
    # cost with accessories. I've chosen to take a percentage of the base cost for a couple of
    # reasons. Firstly, implementing it would be tricky as there would be a logical loop as the
    # magazine its self is included in the final cost. Secondly, I don't think it makes logical
    # sense as accessories can be added/removed after purchase so why would they affect the cost of
    # a magazine.

    def __init__(self) -> None:
        super().__init__(
            componentString='Standard Capacity',
            weaponPercentageCost=1)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step: gunsmith.WeaponStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence):
            ammoCapacity = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
            assert(isinstance(ammoCapacity, common.ScalarCalculation)) # Construction logic should enforce this
            magazineWeight = common.Calculator.multiply(
                lhs=ammoCapacity,
                rhs=_calculateLauncherMagazinePerGrenadeWeight(
                    sequence=sequence,
                    context=context),
                name=f'{self.componentString()} Weight')
            step.setWeight(weight=construction.ConstantModifier(value=magazineWeight))

class _ExtendedProjectileMagazineImpl(_ProjectileMagazineImpl):
    """
    - Cost: 2% of Weapon Purchase Price
    - Ammo Capacity: Up to +50%
    - Quickdraw: -2
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules say the magazine cost is a percentage of the weapon purchase price (Field
    # Catalogue p45). It's not entirely clear if that's the purchase cost of the base weapon or the
    # cost with accessories. I've chosen to take a percentage of the base cost for a couple of
    # reasons. Firstly, implementing it would be tricky as there would be a logical loop as the
    # magazine its self is included in the final cost. Secondly, I don't think it makes logical
    # sense as accessories can be added/removed after purchase so why would they affect the cost of
    # a magazine.

    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None
            ) -> None:
        super().__init__(
            componentString='Extended Capacity',
            weaponPercentageCost=2,
            quickdrawModifier=-2)

        self._capacityIncreaseOption = construction.FloatOption(
            id='CapacityIncrease',
            name='Capacity Increase (%)',
            value=capacityIncrease if capacityIncrease != None else 50,
            minValue=0,
            maxValue=50,
            description='Specify the percentage increase in ammunition capacity given by the extended magazine.')

    def capacityIncrease(self) -> int:
        return self._capacityIncreaseOption.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityIncreaseOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step: gunsmith.WeaponStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence):
            ammoCapacity = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
            assert(isinstance(ammoCapacity, common.ScalarCalculation)) # Construction logic should enforce this
            capacityIncrease = common.ScalarCalculation(
                value=self._capacityIncreaseOption.value(),
                name='Specified Extended Magazine Capacity Percentage Modifier')
            ammoCapacity = common.Calculator.floor(
                value=common.Calculator.applyPercentage(
                    value=ammoCapacity,
                    percentage=capacityIncrease),
                name='Modified Ammo Capacity')
            magazineWeight = common.Calculator.multiply(
                lhs=ammoCapacity,
                rhs=_calculateLauncherMagazinePerGrenadeWeight(
                    sequence=sequence,
                    context=context),
                name=f'{self.componentString()} Weight')
            step.setWeight(weight=construction.ConstantModifier(value=magazineWeight))

        capacityIncrease = common.ScalarCalculation(
            value=self._capacityIncreaseOption.value(),
            name='Specified Extended Magazine Capacity Percentage Modifier')
        factor = construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=capacityIncrease,
                roundDown=True))
        if not applyModifiers:
            factor = construction.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

class _RemovableDrumProjectileMagazineImpl(_ProjectileMagazineImpl):
    """
    - Cost: x5 Standard Magazine Cost == 5% Weapon Cost
    - Ammo Capacity: Up to x2.5
    - Quickdraw: -6
    - Trait: Inaccurate (-1)
    - Trait: Hazardous (-1)
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules say the magazine cost is a percentage of the weapon purchase price (Field
    # Catalogue p45). It's not entirely clear if that's the purchase cost of the base weapon or the
    # cost with accessories. I've chosen to take a percentage of the base cost for a couple of
    # reasons. Firstly, implementing it would be tricky as there would be a logical loop as the
    # magazine its self is included in the final cost. Secondly, I don't think it makes logical
    # sense as accessories can be added/removed after purchase so why would they affect the cost of
    # a magazine.
    _InaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Removable Drum Magazine Inaccurate Modifier')
    _HazardousModifier = common.ScalarCalculation(
        value=-1,
        name='Removable Drum Magazine Hazardous Modifier')

    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None
            ) -> None:
        super().__init__(
            componentString='Removable Drum',
            weaponPercentageCost=5,
            quickdrawModifier=-6)

        self._capacityIncreaseOption = construction.FloatOption(
            id='CapacityIncrease',
            name='Capacity Increase (%)',
            value=capacityIncrease if capacityIncrease != None else 150,
            minValue=0,
            maxValue=150,
            description='Specify the percentage increase in ammunition capacity given by the removable drum magazine.')

    def capacityIncrease(self) -> int:
        return self._capacityIncreaseOption.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityIncreaseOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step: gunsmith.WeaponStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence):
            ammoCapacity = context.attributeValue(
                sequence=sequence,
                attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
            assert(isinstance(ammoCapacity, common.ScalarCalculation)) # Construction logic should enforce this
            capacityIncrease = common.ScalarCalculation(
                value=self._capacityIncreaseOption.value(),
                name='Specified Drum Magazine Capacity Percentage Modifier')
            ammoCapacity = common.Calculator.floor(
                value=common.Calculator.applyPercentage(
                    value=ammoCapacity,
                    percentage=capacityIncrease),
                name='Modified Ammo Capacity')
            magazineWeight = common.Calculator.multiply(
                lhs=ammoCapacity,
                rhs=_calculateLauncherMagazinePerGrenadeWeight(
                    sequence=sequence,
                    context=context),
                name=f'{self.componentString()} Weight')
            step.setWeight(weight=construction.ConstantModifier(value=magazineWeight))

        factors = []

        capacityIncrease = common.ScalarCalculation(
            value=self._capacityIncreaseOption.value(),
            name='Specified Drum Magazine Capacity Percentage Modifier')
        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=capacityIncrease,
                roundDown=True)))

        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._InaccurateModifier)))

        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Hazardous,
            modifier=construction.ConstantModifier(
                value=self._HazardousModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _BeltProjectileMagazineImpl(_ProjectileMagazineImpl):
    """
    - Quickdraw: -8
    - Trait: Inaccurate (-1)
    - Note: DM-2 applies when firing on the move unless a suitable belt-holder is in place
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules don't have a cost for an unloaded ammo belt so I've chosen to allow the user to
    # enter one.
    _InaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Belt Magazine Inaccurate Modifier')
    _Note = 'DM-2 to attack rolls when firing on the move unless a suitable belt-holder is in place'

    _UnloadedCostOptionDescription = \
        '<p>Specify the cost of a single <b>unloaded</b> belt of the specified capacity.</p>' \
        '<p>The description of ammunition belts on p45 of the Field Catalogue doesn\'t give a cost of ' \
        'an unloaded belt. This allows you to specify a value you agree with your Referee.</p>'

    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None
            ) -> None:
        super().__init__(
            componentString='Belt',
            quickdrawModifier=-8)

        self._capacityOption = construction.IntegerOption(
            id='Capacity',
            name='Capacity',
            value=capacity if capacity != None else 100,
            minValue=1,
            description='Specify the number of rounds of ammunition held by the belt.')

        self._unloadedCostOption = construction.FloatOption(
            id='UnloadedCost',
            name='Unloaded Cost',
            value=unloadedCost if unloadedCost != None else 0,
            minValue=0,
            description=_BeltProjectileMagazineImpl._UnloadedCostOptionDescription)

    def capacity(self) -> int:
        return self._capacityOption.value()

    def unloadedCost(self) -> float:
        return self._unloadedCostOption.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityOption)
        options.append(self._unloadedCostOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        super().updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        unloadedCost = common.ScalarCalculation(
            value=self._unloadedCostOption.value(),
            name='Specified Unloaded Belt Cost')
        totalCost = common.Calculator.multiply(
            lhs=unloadedCost,
            rhs=numberOfMagazines,
            name=f'{self.componentString()} Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        if context.hasComponent(
                componentType=gunsmith.LauncherReceiver,
                sequence=sequence):
            ammoCapacity = common.ScalarCalculation(
                value=self._capacityOption.value(),
                name='Specified Belt Capacity')
            magazineWeight = common.Calculator.multiply(
                lhs=ammoCapacity,
                rhs=_calculateLauncherMagazinePerGrenadeWeight(
                    sequence=sequence,
                    context=context),
                name=f'{self.componentString()} Weight')
            step.setWeight(weight=construction.ConstantModifier(value=magazineWeight))

        factors = []

        ammoCapacity = common.ScalarCalculation(
            value=self._capacityOption.value(),
            name='Specified Belt Capacity')
        factors.append(construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            value=ammoCapacity))

        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._InaccurateModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

        if applyModifiers:
            step.addNote(note=self._Note)


#   █████████                                                       █████     ███                                ████
#  ███░░░░░███                                                     ░░███     ░░░                                ░░███
# ███     ░░░   ██████  ████████   █████ █████  ██████  ████████   ███████   ████   ██████  ████████    ██████   ░███
#░███          ███░░███░░███░░███ ░░███ ░░███  ███░░███░░███░░███ ░░░███░   ░░███  ███░░███░░███░░███  ░░░░░███  ░███
#░███         ░███ ░███ ░███ ░███  ░███  ░███ ░███████  ░███ ░███   ░███     ░███ ░███ ░███ ░███ ░███   ███████  ░███
#░░███     ███░███ ░███ ░███ ░███  ░░███ ███  ░███░░░   ░███ ░███   ░███ ███ ░███ ░███ ░███ ░███ ░███  ███░░███  ░███
# ░░█████████ ░░██████  ████ █████  ░░█████   ░░██████  ████ █████  ░░█████  █████░░██████  ████ █████░░████████ █████
#  ░░░░░░░░░   ░░░░░░  ░░░░ ░░░░░    ░░░░░     ░░░░░░  ░░░░ ░░░░░    ░░░░░  ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░ ░░░░░
_LoadedBeltWeightOptionDescription = \
    '<p>Specify the cost of the <b>loaded</b> belt.</p>' \
    '<p>The Field Catalogue gives very little information on how to calculate the weight of ' \
    'a loaded belt of ammunition. The only example it gives is a 50 round belt of Battle Rifle ' \
    'calibre ammunition typically weighing 1.5kg. This allows you to specify a weight that you ' \
    'agree with your Referee.</p>'

class ConventionalMagazineLoaded(MagazineLoaded):
    """
    - Requirement: Only compatible with conventional weapons
    """

    def __init__(
            self,
            impl: _ProjectileMagazineImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def typeString(self) -> str:
        return 'Loaded Magazine'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        context.applyStep(
            sequence=sequence,
            step=self._createStep(sequence=sequence, context=context))

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=common.ScalarCalculation(value=1),
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        return step

class StandardConventionalMagazineLoaded(ConventionalMagazineLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_StandardProjectileMagazineImpl())

class ExtendedConventionalMagazineLoaded(ConventionalMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None
            ) -> None:
        super().__init__(impl=_ExtendedProjectileMagazineImpl(
            capacityIncrease=capacityIncrease))

class RemovableDrumConventionalMagazineLoaded(ConventionalMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None
            ) -> None:
        super().__init__(impl=_RemovableDrumProjectileMagazineImpl(
            capacityIncrease=capacityIncrease))

class BeltConventionalMagazineLoaded(ConventionalMagazineLoaded):
    # NOTE: I've added an option so the user can specify the loaded weight of the belt for conventional
    # weapons. All the rules have is a a single example of a 50 round belt of Battle Rifle ammo weighting
    # ~1.5kg (Field Catalogue p45).

    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None,
            loadedWeight: typing.Optional[float] = None
            ) -> None:
        super().__init__(impl=_BeltProjectileMagazineImpl(
            capacity=capacity,
            unloadedCost=unloadedCost))

        self._loadedWeightOption = construction.FloatOption(
            id='LoadedWeight',
            name='Loaded Weight',
            value=loadedWeight if loadedWeight != None else 0,
            minValue=0,
            description=_LoadedBeltWeightOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._loadedWeightOption)
        return options

    def _createStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> gunsmith.WeaponStep:
        step = super()._createStep(sequence=sequence, context=context)

        loadedWeight = common.ScalarCalculation(
            value=self._loadedWeightOption.value(),
            name='Specified Loaded Belt Weight')
        step.setWeight(weight=construction.ConstantModifier(value=loadedWeight))

        return step

class ConventionalMagazineQuantity(MagazineQuantity):
    """
    - Requirement: Only compatible with conventional weapons
    """

    def __init__(
            self,
            impl: _ProjectileMagazineImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfMagazinesOption = construction.IntegerOption(
            id='Quantity',
            name='Quantity',
            value=1,
            minValue=1,
            description='Specify the number of magazines.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} x{self._numberOfMagazinesOption.value()}'

    def typeString(self) -> str:
        return 'Magazine Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.ConventionalReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._numberOfMagazinesOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        numberOfMagazines = common.ScalarCalculation(
            value=self._numberOfMagazinesOption.value(),
            name='Specified Number Of Magazines')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class StandardConventionalMagazineQuantity(ConventionalMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardProjectileMagazineImpl())

    def createLoadedMagazine(self) -> StandardConventionalMagazineLoaded:
        return StandardConventionalMagazineLoaded()

class ExtendedConventionalMagazineQuantity(ConventionalMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExtendedProjectileMagazineImpl())

    def createLoadedMagazine(self) -> ExtendedConventionalMagazineLoaded:
        assert(isinstance(self._impl, _ExtendedProjectileMagazineImpl))
        return ExtendedConventionalMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease())

class RemovableDrumConventionalMagazineQuantity(ConventionalMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_RemovableDrumProjectileMagazineImpl())

    def createLoadedMagazine(self) -> RemovableDrumConventionalMagazineLoaded:
        assert(isinstance(self._impl, _RemovableDrumProjectileMagazineImpl))
        return RemovableDrumConventionalMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease())

class BeltConventionalMagazineQuantity(ConventionalMagazineQuantity):
    # NOTE: I've added an option so the user can specify the loaded weight of the belt for conventional
    # weapons. All the rules have is a a single example of a 50 round belt of Battle Rifle ammo weighting
    # ~1.5kg (Field Catalogue p45). It's important to note that this option is available for magazine
    # quantities and loaded magazines even though it's only actually used for loaded magazines. This is
    # necessary to allow magazine quantities to generate the loaded version of that component
    def __init__(self) -> None:
        super().__init__(impl=_BeltProjectileMagazineImpl())

        self._loadedWeightOption = construction.FloatOption(
            id='LoadedWeight',
            name='Loaded Weight',
            value=0,
            minValue=0,
            description=_LoadedBeltWeightOptionDescription)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._loadedWeightOption)
        return options

    def createLoadedMagazine(self) -> BeltConventionalMagazineLoaded:
        assert(isinstance(self._impl, _BeltProjectileMagazineImpl))
        return BeltConventionalMagazineLoaded(
            capacity=self._impl.capacity(),
            unloadedCost=self._impl.unloadedCost(),
            loadedWeight=self._loadedWeightOption.value())


# █████                                                █████
#░░███                                                ░░███
# ░███         ██████   █████ ████ ████████    ██████  ░███████    ██████  ████████
# ░███        ░░░░░███ ░░███ ░███ ░░███░░███  ███░░███ ░███░░███  ███░░███░░███░░███
# ░███         ███████  ░███ ░███  ░███ ░███ ░███ ░░░  ░███ ░███ ░███████  ░███ ░░░
# ░███      █ ███░░███  ░███ ░███  ░███ ░███ ░███  ███ ░███ ░███ ░███░░░   ░███
# ███████████░░████████ ░░████████ ████ █████░░██████  ████ █████░░██████  █████
#░░░░░░░░░░░  ░░░░░░░░   ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░  ░░░░ ░░░░░  ░░░░░░  ░░░░░

class LauncherMagazineLoaded(MagazineLoaded):
    """
    - Weight: (Field Catalogue p45)
        - Standard Grenades: 0.5kg per grenade
        - Mini Grenades: 0.3kg per grenade
    - Requirement: Only compatible with Launcher Weapons
    """

    def __init__(
            self,
            impl: _ProjectileMagazineImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def typeString(self) -> str:
        return 'Loaded Magazine'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=common.ScalarCalculation(value=1),
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class StandardLauncherMagazineLoaded(LauncherMagazineLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_StandardProjectileMagazineImpl())

class ExtendedLauncherMagazineLoaded(LauncherMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None
            ) -> None:
        super().__init__(impl=_ExtendedProjectileMagazineImpl(
            capacityIncrease=capacityIncrease))

class RemovableDrumLauncherMagazineLoaded(LauncherMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None
            ) -> None:
        super().__init__(impl=_RemovableDrumProjectileMagazineImpl(
            capacityIncrease=capacityIncrease))

class BeltLauncherMagazineLoaded(LauncherMagazineLoaded):
    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None
            ) -> None:
        super().__init__(impl=_BeltProjectileMagazineImpl(
            capacity=capacity,
            unloadedCost=unloadedCost))

class LauncherMagazineQuantity(MagazineQuantity):
    """
    - Requirement: Only compatible with Launcher Weapons
    """

    def __init__(
            self,
            impl: _ProjectileMagazineImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfMagazinesOption = construction.IntegerOption(
            id='Quantity',
            name='Quantity',
            value=1,
            minValue=1,
            description='Specify the number of magazines.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} x{self._numberOfMagazinesOption.value()}'

    def typeString(self) -> str:
        return 'Magazine Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        return context.hasComponent(
            componentType=gunsmith.LauncherReceiver,
            sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._numberOfMagazinesOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        numberOfMagazines = common.ScalarCalculation(
            value=self._numberOfMagazinesOption.value(),
            name='Specified Number Of Magazines')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class StandardLauncherMagazineQuantity(LauncherMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardProjectileMagazineImpl())

    def createLoadedMagazine(self) -> StandardLauncherMagazineLoaded:
        assert(isinstance(self._impl, _StandardProjectileMagazineImpl))
        return StandardLauncherMagazineLoaded()

class ExtendedLauncherMagazineQuantity(LauncherMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExtendedProjectileMagazineImpl())

    def createLoadedMagazine(self) -> ExtendedLauncherMagazineLoaded:
        assert(isinstance(self._impl, _ExtendedProjectileMagazineImpl))
        return ExtendedLauncherMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease())

class RemovableDrumLauncherMagazineQuantity(LauncherMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_RemovableDrumProjectileMagazineImpl())

    def createLoadedMagazine(self) -> RemovableDrumLauncherMagazineLoaded:
        assert(isinstance(self._impl, _RemovableDrumProjectileMagazineImpl))
        return RemovableDrumLauncherMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease())

class BeltLauncherMagazineQuantity(LauncherMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BeltProjectileMagazineImpl())

    def createLoadedMagazine(self) -> BeltLauncherMagazineLoaded:
        assert(isinstance(self._impl, _BeltProjectileMagazineImpl))
        return BeltLauncherMagazineLoaded(
            capacity=self._impl.capacity(),
            unloadedCost=self._impl.unloadedCost())


#   █████████                       █████               ███      █████
#  ███░░░░░███                     ░░███               ░░░      ░░███
# ███     ░░░   ██████   ████████  ███████   ████████  ████   ███████   ███████  ██████
#░███          ░░░░░███ ░░███░░███░░░███░   ░░███░░███░░███  ███░░███  ███░░███ ███░░███
#░███           ███████  ░███ ░░░   ░███     ░███ ░░░  ░███ ░███ ░███ ░███ ░███░███████
#░░███     ███ ███░░███  ░███       ░███ ███ ░███      ░███ ░███ ░███ ░███ ░███░███░░░
# ░░█████████ ░░████████ █████      ░░█████  █████     █████░░████████░░███████░░██████
#  ░░░░░░░░░   ░░░░░░░░ ░░░░░        ░░░░░  ░░░░░     ░░░░░  ░░░░░░░░  ░░░░░███ ░░░░░░
#                                                                      ███ ░███
#                                                                     ░░██████
#                                                                      ░░░░░░

class EnergyCartridgeType(enum.Enum):
    Weak = 'Weak'
    Light = 'Light'
    Standard = 'Standard'
    Heavy = 'Heavy'

class _EnergyCartridgeMagazineImpl(object):
    """
    All Energy Cartridge Magazines
    - Weight: 20% of the weight of the cartridges it contains
    - Cost
        - Disposable: Cost of 1 cartridge
        - Reusable: Cost of 2 cartridges
    - Requirement: Only compatible with Cartridge Energy Weapon
    - Requirement: Only compatible with weapons with a Removable Magazine Feed
    """
    # NOTE: The wording around the weight of a magazine is a little ambiguous (Field Catalogue p64).
    # It says "The weight of a disposable magazine or holder is equal to the weight of the
    # cartridges within it plus 20%". I've taken this to mean an empty magazine would weight 20% of
    # the weight of the cartridges it can contain rather than the it describing the weight of an
    # empty magazine

    _WeightPercentage = common.ScalarCalculation(
        value=+20,
        name='Energy Cartridge Magazine Cartridge Weight Percentage')
    _DisposableCostMultiplier = common.ScalarCalculation(
        value=1,
        name='Disposable Energy Cartridge Magazine Cartridge Cost Multiplier')
    _ReusableCostMultiplier = common.ScalarCalculation(
        value=2,
        name='Reusable Energy Cartridge Magazine Cartridge Cost Multiplier')

    _CartridgeMinTechLevelMap = {
        EnergyCartridgeType.Weak: 9,
        EnergyCartridgeType.Light: 10,
        EnergyCartridgeType.Standard: 11,
        EnergyCartridgeType.Heavy: 12
    }
    _CartridgeWeightMap = {
        EnergyCartridgeType.Weak: common.ScalarCalculation(value=0.01, name='Weak Energy Cartridge Weight'),
        EnergyCartridgeType.Light: common.ScalarCalculation(value=0.01, name='Light Energy Cartridge Weight'),
        EnergyCartridgeType.Standard: common.ScalarCalculation(value=0.02, name='Standard Energy Cartridge Weight'),
        EnergyCartridgeType.Heavy: common.ScalarCalculation(value=0.025, name='Heavy Energy Cartridge Weight')
    }
    _CartridgeCostMap = {
        EnergyCartridgeType.Weak: common.ScalarCalculation(value=5, name='Weak Energy Cartridge Cost'),
        EnergyCartridgeType.Light: common.ScalarCalculation(value=8, name='Light Energy Cartridge Cost'),
        EnergyCartridgeType.Standard: common.ScalarCalculation(value=10, name='Standard Energy Cartridge Cost'),
        EnergyCartridgeType.Heavy: common.ScalarCalculation(value=15, name='Heavy Energy Cartridge Cost')
    }

    def __init__(
            self,
            componentString: str,
            cartridgeType: EnergyCartridgeType,
            costMultiplier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            quickdrawModifier: typing.Optional[typing.Union[int, common.ScalarCalculation]] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__()

        if costMultiplier != None and not isinstance(costMultiplier, common.ScalarCalculation):
            costMultiplier = common.ScalarCalculation(
                value=costMultiplier,
                name=f'{componentString} Energy Cartridge Magazine Cost Multiplier')

        if quickdrawModifier != None and not isinstance(quickdrawModifier, common.ScalarCalculation):
            quickdrawModifier = common.ScalarCalculation(
                value=quickdrawModifier,
                name=f'{componentString} Energy Cartridge Magazine Quickdraw Modifier')

        self._componentString = componentString
        self._cartridgeType = cartridgeType
        self._costMultiplier = costMultiplier
        self._quickdrawModifier = quickdrawModifier

        self._reusableOption = construction.BooleanOption(
            id='Reusable',
            name='Reusable',
            value=isReusable if isReusable != None else True, # Environmentally friendly by default :)
            description='Specify if the magazine is reusable or disposable')

    def cartridgeType(self) -> EnergyCartridgeType:
        return self._cartridgeType

    def isReusable(self) -> bool:
        return self._reusableOption.value()

    def componentString(self) -> str:
        return f'{self._componentString} ({self._cartridgeType.value} Cartridge)'

    def instanceString(self) -> str:
        isReusable = self._reusableOption.value()
        return "{0} ({1} Cartridge, {2})".format(
            self._componentString,
            self._cartridgeType.value,
            'Reusable' if isReusable else 'Disposable')

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if context.techLevel() < _EnergyCartridgeMagazineImpl._CartridgeMinTechLevelMap[self._cartridgeType]:
            return False

        # Only compatible with weapons that have a receiver.
        if not context.hasComponent(
                componentType=gunsmith.Receiver,
                sequence=sequence):
            return False

        # Only compatible with cartridge energy weapons that have a removable magazine feed
        return context.hasComponent(
            componentType=gunsmith.EnergyCartridgeReceiver,
            sequence=sequence) \
            and context.hasComponent(
                componentType=gunsmith.RemovableMagazineFeed,
                sequence=sequence)

    def options(self) -> typing.List[construction.ComponentOption]:
        return [self._reusableOption]

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        pass

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            ammoCapacity: common.ScalarCalculation,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        cartridgeWeight = _EnergyCartridgeMagazineImpl._CartridgeWeightMap[self._cartridgeType]
        cartridgeCost = _EnergyCartridgeMagazineImpl._CartridgeCostMap[self._cartridgeType]

        isReusable = self._reusableOption.value()

        magazineWeight = common.Calculator.takePercentage(
            value=common.Calculator.multiply(
                lhs=cartridgeWeight,
                rhs=ammoCapacity),
            percentage=self._WeightPercentage,
            name=f'{self.componentString()} Weight')
        totalWeight = common.Calculator.multiply(
            lhs=magazineWeight,
            rhs=numberOfMagazines,
            name=f'Total {self.componentString()} Weight')
        step.setWeight(weight=construction.ConstantModifier(value=totalWeight))

        magazineCost = common.Calculator.multiply(
            lhs=cartridgeCost,
            rhs=self._ReusableCostMultiplier if isReusable else self._DisposableCostMultiplier)
        if self._costMultiplier:
            magazineCost = common.Calculator.multiply(
                lhs=magazineCost,
                rhs=self._costMultiplier)
        magazineCost = common.Calculator.rename(
            value=magazineCost,
            name=f'{self.componentString()} Cost')

        totalCost = common.Calculator.multiply(
            lhs=magazineCost,
            rhs=numberOfMagazines,
            name=f'Total {self.componentString()} Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        if self._quickdrawModifier:
            factor = construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttributeId.Quickdraw,
                modifier=construction.ConstantModifier(
                    value=self._quickdrawModifier))
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _StandardEnergyCartridgeMagazineImpl(_EnergyCartridgeMagazineImpl):
    """
    - Cost: 1% of Weapon Purchase Price
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules say the magazine cost is a percentage of the weapon purchase price (Field
    # Catalogue p45). It's not entirely clear if that's the purchase cost of the base weapon or the
    # cost with accessories. I've chosen to take a percentage of the base cost for a couple of
    # reasons. Firstly, implementing it would be tricky as there would be a logical loop as the
    # magazine its self is included in the final cost. Secondly, I don't think it makes logical
    # sense as accessories can be added/removed after purchase so why would they affect the cost of
    # a magazine.

    def __init__(
            self,
            cartridgeType: EnergyCartridgeType,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Standard Capacity',
            cartridgeType=cartridgeType,
            isReusable=isReusable)

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
        assert(isinstance(ammoCapacity, common.ScalarCalculation))

        super().updateStep(
            sequence=sequence,
            context=context,
            ammoCapacity=ammoCapacity,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

class _ExtendedEnergyCartridgeMagazineImpl(_EnergyCartridgeMagazineImpl):
    """
    - Cost: x2 standard magazine cost
    - Ammo Capacity: Up to +50%
    - Quickdraw: -2
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules don't explicitly say that you can get extended energy cartridge magazines but it seems
    # reasonable that you could.

    def __init__(
            self,
            cartridgeType: EnergyCartridgeType,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Extended Capacity',
            costMultiplier=2,
            quickdrawModifier=-2,
            cartridgeType=cartridgeType,
            isReusable=isReusable)

        self._capacityIncreaseOption = construction.FloatOption(
            id='CapacityIncrease',
            name='Capacity Increase (%)',
            value=capacityIncrease if capacityIncrease != None else 50,
            minValue=0,
            maxValue=50,
            description='Specify the percentage increase in ammunition capacity given by the extended magazine.')

    def capacityIncrease(self) -> int:
        return self._capacityIncreaseOption.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityIncreaseOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step: gunsmith.WeaponStep
            ) -> None:
        capacityIncrease = common.ScalarCalculation(
            value=self._capacityIncreaseOption.value(),
            name='Specified Extended Magazine Capacity Percentage Modifier')
        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
        assert(isinstance(ammoCapacity, common.ScalarCalculation))
        ammoCapacity = common.Calculator.applyPercentage(
            value=ammoCapacity,
            percentage=capacityIncrease,
            name='Extended Magazine Ammo Capacity')

        super().updateStep(
            sequence=sequence,
            context=context,
            ammoCapacity=ammoCapacity,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        factor = construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=capacityIncrease,
                roundDown=True))
        if not applyModifiers:
            factor = construction.NonModifyingFactor(factor=factor)
        step.addFactor(factor=factor)

class _RemovableDrumEnergyCartridgeMagazineImpl(_EnergyCartridgeMagazineImpl):
    """
    - Cost: x5 Standard Magazine Cost == 5% Weapon Cost
    - Ammo Capacity: Up to x2.5
    - Quickdraw: -6
    - Trait: Inaccurate (-1)
    - Trait: Hazardous (-1)
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules don't explicitly say that you can get removable drum energy cartridge magazines
    # but it seems reasonable that you could.

    _InaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Removable Drum Magazine Inaccurate Modifier')
    _HazardousModifier = common.ScalarCalculation(
        value=-1,
        name='Removable Drum Magazine Hazardous Modifier')

    def __init__(
            self,
            cartridgeType: EnergyCartridgeType,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Removable Drum',
            costMultiplier=5,
            quickdrawModifier=-6,
            cartridgeType=cartridgeType,
            isReusable=isReusable)

        self._capacityIncreaseOption = construction.FloatOption(
            id='CapacityIncrease',
            name='Capacity Increase (%)',
            value=capacityIncrease if capacityIncrease != None else 150,
            minValue=0,
            maxValue=150,
            description='Specify the percentage increase in ammunition capacity given by the removable drum magazine.')

    def capacityIncrease(self) -> int:
        return self._capacityIncreaseOption.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityIncreaseOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step: gunsmith.WeaponStep
            ) -> None:
        capacityIncrease = common.ScalarCalculation(
            value=self._capacityIncreaseOption.value(),
            name='Specified Drum Magazine Capacity Percentage Modifier')
        ammoCapacity = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity)
        assert(isinstance(ammoCapacity, common.ScalarCalculation))
        ammoCapacity = common.Calculator.applyPercentage(
            value=ammoCapacity,
            percentage=capacityIncrease,
            name='Drum Magazine Ammo Capacity')

        super().updateStep(
            sequence=sequence,
            context=context,
            ammoCapacity=ammoCapacity,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        factors = []

        capacityIncrease = common.ScalarCalculation(
            value=self._capacityIncreaseOption.value(),
            name='Specified Drum Magazine Capacity Percentage Modifier')
        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            modifier=construction.PercentageModifier(
                value=capacityIncrease,
                roundDown=True)))

        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._InaccurateModifier)))

        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Hazardous,
            modifier=construction.ConstantModifier(
                value=self._HazardousModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

class _BeltEnergyCartridgeMagazineImpl(_EnergyCartridgeMagazineImpl):
    """
    - Quickdraw: -8
    - Trait: Inaccurate (-1)
    - Note: DM-2 applies when firing on the move unless a suitable belt-holder is in place
    - Requirement: Only compatible with Removable Magazine Feed
    """
    # NOTE: The rules don't explicitly say that you can get belt energy cartridge magazines but it seems
    # reasonable that you could.

    _InaccurateModifier = common.ScalarCalculation(
        value=-1,
        name='Belt Magazine Inaccurate Modifier')
    _Note = 'DM-2 to attack rolls when firing on the move unless a suitable belt-holder is in place'

    _UnloadedCostOptionDescription = \
        '<p>Specify the cost of a single <b>unloaded</b> belt of the specified capacity.</p>' \
        '<p>The description of ammunition belts on p45 of the Field Catalogue doesn\'t give a cost of ' \
        'an unloaded belt. This allows you to specify a value you agree with your Referee.</p>'

    def __init__(
            self,
            cartridgeType: EnergyCartridgeType,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(
            componentString='Belt',
            quickdrawModifier=-8,
            cartridgeType=cartridgeType,
            isReusable=isReusable)

        self._capacityOption = construction.IntegerOption(
            id='Capacity',
            name='Capacity',
            value=capacity if capacity != None else 100,
            minValue=1,
            description='Specify the number of rounds of ammunition held by the belt.')

        self._unloadedCostOption = construction.FloatOption(
            id='UnloadedCost',
            name='Unloaded Cost',
            value=unloadedCost if unloadedCost != None else 0,
            minValue=0,
            description=_BeltProjectileMagazineImpl._UnloadedCostOptionDescription)

    def capacity(self) -> int:
        return self._capacityOption.value()

    def unloadedCost(self) -> float:
        return self._unloadedCostOption.value()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = super().options()
        options.append(self._capacityOption)
        options.append(self._unloadedCostOption)
        return options

    def updateStep(
            self,
            sequence: str,
            context: gunsmith.WeaponContext,
            numberOfMagazines: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        ammoCapacity = common.ScalarCalculation(
            value=self._capacityOption.value(),
            name='Specified Belt Capacity')

        super().updateStep(
            sequence=sequence,
            context=context,
            ammoCapacity=ammoCapacity,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=applyModifiers,
            step=step)

        unloadedCost = common.ScalarCalculation(
            value=self._unloadedCostOption.value(),
            name='Specified Unloaded Belt Cost')
        totalCost = common.Calculator.multiply(
            lhs=unloadedCost,
            rhs=numberOfMagazines,
            name=f'{self.componentString()} Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        factors = []

        ammoCapacity = common.ScalarCalculation(
            value=self._capacityOption.value(),
            name='Specified Belt Capacity')
        factors.append(construction.SetAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.AmmoCapacity,
            value=ammoCapacity))

        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttributeId.Inaccurate,
            modifier=construction.ConstantModifier(
                value=self._InaccurateModifier)))

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

        if applyModifiers:
            step.addNote(note=self._Note)

class EnergyCartridgeMagazineLoaded(MagazineLoaded):
    def __init__(
            self,
            impl: _EnergyCartridgeMagazineImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def cartridgeType(self) -> EnergyCartridgeType:
        return self._impl.cartridgeType()

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return self._impl.instanceString()

    def typeString(self) -> str:
        return 'Loaded Magazine'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        return self._impl.options()

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=common.ScalarCalculation(value=1),
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class StandardWeakEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak,
            isReusable=isReusable))

class StandardLightEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light,
            isReusable=isReusable))

class StandardStandardEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard,
            isReusable=isReusable))

class StandardHeavyEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy,
            isReusable=isReusable))

class ExtendedWeakEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class ExtendedLightEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class ExtendedStandardEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class ExtendedHeavyEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class RemovableDrumWeakEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class RemovableDrumLightEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class RemovableDrumStandardEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class RemovableDrumHeavyEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacityIncrease: typing.Optional[int] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy,
            capacityIncrease=capacityIncrease,
            isReusable=isReusable))

class BeltWeakEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak,
            capacity=capacity,
            unloadedCost=unloadedCost,
            isReusable=isReusable))

class BeltLightEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light,
            capacity=capacity,
            unloadedCost=unloadedCost,
            isReusable=isReusable))

class BeltStandardEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard,
            capacity=capacity,
            unloadedCost=unloadedCost,
            isReusable=isReusable))

class BeltHeavyEnergyCartridgeMagazineLoaded(EnergyCartridgeMagazineLoaded):
    def __init__(
            self,
            capacity: typing.Optional[int] = None,
            unloadedCost: typing.Optional[float] = None,
            isReusable: typing.Optional[bool] = None
            ) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy,
            capacity=capacity,
            unloadedCost=unloadedCost,
            isReusable=isReusable))

class EnergyCartridgeMagazineQuantity(MagazineQuantity):
    """
    - Requirement: Only compatible with energy weapons
    """

    def __init__(
            self,
            impl: _EnergyCartridgeMagazineImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfMagazinesOption = construction.IntegerOption(
            id='Quantity',
            name='Quantity',
            value=1,
            minValue=1,
            description='Specify the number of magazines.')

    def cartridgeType(self) -> EnergyCartridgeType:
        return self._impl.cartridgeType()

    def componentString(self) -> str:
        return self._impl.componentString()

    def instanceString(self) -> str:
        return f'{self._impl.instanceString()} x{self._numberOfMagazinesOption.value()}'

    def typeString(self) -> str:
        return 'Magazine Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._numberOfMagazinesOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        numberOfMagazines = common.ScalarCalculation(
            value=self._numberOfMagazinesOption.value(),
            name='Specified Number Of Magazines')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            numberOfMagazines=numberOfMagazines,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class StandardWeakEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak
        ))

    def createLoadedMagazine(self) -> StandardWeakEnergyCartridgeMagazineLoaded:
        return StandardWeakEnergyCartridgeMagazineLoaded(
            isReusable=self._impl.isReusable())

class StandardLightEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light
        ))

    def createLoadedMagazine(self) -> StandardLightEnergyCartridgeMagazineLoaded:
        return StandardLightEnergyCartridgeMagazineLoaded(
            isReusable=self._impl.isReusable())

class StandardStandardEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard
        ))

    def createLoadedMagazine(self) -> StandardStandardEnergyCartridgeMagazineLoaded:
        return StandardStandardEnergyCartridgeMagazineLoaded(
            isReusable=self._impl.isReusable())

class StandardHeavyEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy
        ))

    def createLoadedMagazine(self) -> StandardHeavyEnergyCartridgeMagazineLoaded:
        return StandardHeavyEnergyCartridgeMagazineLoaded(
            isReusable=self._impl.isReusable())

class ExtendedWeakEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak
        ))

    def createLoadedMagazine(self) -> ExtendedWeakEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _ExtendedEnergyCartridgeMagazineImpl))
        return ExtendedWeakEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class ExtendedLightEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light
        ))

    def createLoadedMagazine(self) -> ExtendedLightEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _ExtendedEnergyCartridgeMagazineImpl))
        return ExtendedLightEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class ExtendedStandardEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard
        ))

    def createLoadedMagazine(self) -> ExtendedStandardEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _ExtendedEnergyCartridgeMagazineImpl))
        return ExtendedStandardEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class ExtendedHeavyEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_ExtendedEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy
        ))

    def createLoadedMagazine(self) -> ExtendedHeavyEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _ExtendedEnergyCartridgeMagazineImpl))
        return ExtendedHeavyEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class RemovableDrumWeakEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak
        ))

    def createLoadedMagazine(self) -> RemovableDrumWeakEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _RemovableDrumEnergyCartridgeMagazineImpl))
        return RemovableDrumWeakEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class RemovableDrumLightEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light
        ))

    def createLoadedMagazine(self) -> RemovableDrumLightEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _RemovableDrumEnergyCartridgeMagazineImpl))
        return RemovableDrumLightEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class RemovableDrumStandardEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard
        ))

    def createLoadedMagazine(self) -> RemovableDrumStandardEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _RemovableDrumEnergyCartridgeMagazineImpl))
        return RemovableDrumStandardEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class RemovableDrumHeavyEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_RemovableDrumEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy
        ))

    def createLoadedMagazine(self) -> RemovableDrumHeavyEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _RemovableDrumEnergyCartridgeMagazineImpl))
        return RemovableDrumHeavyEnergyCartridgeMagazineLoaded(
            capacityIncrease=self._impl.capacityIncrease(),
            isReusable=self._impl.isReusable())

class BeltWeakEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Weak
        ))

    def createLoadedMagazine(self) -> BeltWeakEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _BeltEnergyCartridgeMagazineImpl))
        return BeltWeakEnergyCartridgeMagazineLoaded(
            capacity=self._impl.capacity(),
            unloadedCost=self._impl.unloadedCost(),
            isReusable=self._impl.isReusable())

class BeltLightEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Light
        ))

    def createLoadedMagazine(self) -> BeltLightEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _BeltEnergyCartridgeMagazineImpl))
        return BeltLightEnergyCartridgeMagazineLoaded(
            capacity=self._impl.capacity(),
            unloadedCost=self._impl.unloadedCost(),
            isReusable=self._impl.isReusable())

class BeltStandardEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Standard
        ))

    def createLoadedMagazine(self) -> BeltStandardEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _BeltEnergyCartridgeMagazineImpl))
        return BeltStandardEnergyCartridgeMagazineLoaded(
            capacity=self._impl.capacity(),
            unloadedCost=self._impl.unloadedCost(),
            isReusable=self._impl.isReusable())

class BeltHeavyEnergyCartridgeMagazineQuantity(EnergyCartridgeMagazineQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_BeltEnergyCartridgeMagazineImpl(
            cartridgeType=EnergyCartridgeType.Heavy
        ))

    def createLoadedMagazine(self) -> BeltHeavyEnergyCartridgeMagazineLoaded:
        assert(isinstance(self._impl, _BeltEnergyCartridgeMagazineImpl))
        return BeltHeavyEnergyCartridgeMagazineLoaded(
            capacity=self._impl.capacity(),
            unloadedCost=self._impl.unloadedCost(),
            isReusable=self._impl.isReusable())
