import common
import construction
import gunsmith
import typing

class _PowerPackImpl(object):
    """
    All Power Packs
    - Min TL: 8
    - Power Per kg: TL8=100, TL9=300, TL10=500, TL11=700, TL12+=1000
    - Trait: A power pack that suffers an excessive energy draw gains the Unreliable trait at a
      level equal to the difference between its normal maximum damage output and the damage
      output of the weapon
    - Requirement: Only compatible with Power Pack Energy Weapon
    - Requirement: When multiple power packs are attached (i.e. internal and external) the ammo
      capacity should be added
    """
    # NOTE The rules (Field Catalogue p63) don't explicitly say what damage the weapon does if it's
    # used with an underpowered power pack. As it doesn't say any different I've gone with the
    # assumption that it will do the normal weapon damage, there's just a good chance that it will
    # fail due to the Unreliable score.
    # NOTE: The fact that the capacities of internal and external packs are cumulative comes from
    # the example of on p116 of the Field Catalogue
    _MinTechLevel = common.ScalarCalculation(
        value=8,
        name='Power Pack Min Tech Level')
    _TL8PowerPerKg = common.ScalarCalculation(
        value=100,
        name='Power Pack (TL8) Power Per kg')
    _TL9PowerPerKg = common.ScalarCalculation(
        value=300,
        name='Power Pack (TL9) Power Per kg')
    _TL10PowerPerKg = common.ScalarCalculation(
        value=500,
        name='Power Pack (TL10) Power Per kg')
    _TL11PowerPerKg = common.ScalarCalculation(
        value=700,
        name='Power Pack (TL11) Power Per kg')
    _TL12PowerPerKg = common.ScalarCalculation(
        value=1000,
        name='Power Pack (TL12+) Power Per kg')

    def __init__(
            self,
            componentString: str,
            costPerKg: typing.Union[int, float, common.ScalarCalculation],
            maxPower: typing.Union[int, float, common.ScalarCalculation],
            ) -> None:
        super().__init__()

        if not isinstance(costPerKg, common.ScalarCalculation):
            costPerKg = common.ScalarCalculation(
                value=costPerKg,
                name=f'{componentString} Power Pack Cost Per kg')

        if not isinstance(maxPower, common.ScalarCalculation):
            maxPower = common.ScalarCalculation(
                value=maxPower,
                name=f'{componentString} Max Power Per Shot Before Overload')

        self._componentString = componentString
        self._costPerKg = costPerKg
        self._maxPower = maxPower

    def componentString(self) -> str:
        return self._componentString

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if  context.techLevel() < self._MinTechLevel.value():
            return False

        return context.hasComponent(
            componentType=gunsmith.PowerPackReceiver,
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
            packWeight: common.ScalarCalculation,
            numberOfPacks: common.ScalarCalculation,
            applyModifiers: bool,
            step:  gunsmith.WeaponStep
            ) -> None:
        totalWeight = common.Calculator.multiply(
            lhs=packWeight,
            rhs=numberOfPacks,
            name='Total Power Pack Weight')
        step.setWeight(weight=construction.ConstantModifier(value=totalWeight))

        totalCost = common.Calculator.multiply(
            lhs=self._costPerKg,
            rhs=totalWeight,
            name=f'{self.componentString()} Power Pack Cost')
        step.setCredits(credits=construction.ConstantModifier(value=totalCost))

        factors = []
        notes = []

        powerPerKg = None
        if context.techLevel() == 8:
            powerPerKg = self._TL8PowerPerKg
        elif context.techLevel() == 9:
            powerPerKg = self._TL9PowerPerKg
        elif context.techLevel() == 10:
            powerPerKg = self._TL10PowerPerKg
        elif context.techLevel() == 11:
            powerPerKg = self._TL11PowerPerKg
        elif context.techLevel() >= 12:
            powerPerKg = self._TL12PowerPerKg
        assert(powerPerKg) # Compatibility check should enforce this

        power = common.Calculator.multiply(
            lhs=powerPerKg,
            rhs=packWeight,
            name=f'{self.componentString()} Power Pack Power')
        # Modify the power rather than setting it to allow the power of internal and external power
        # packs to be cumulative
        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.Power,
            modifier=construction.ConstantModifier(value=power)))

        powerPerShot = context.attributeValue(
            sequence=sequence,
            attributeId=gunsmith.WeaponAttribute.PowerPerShot)
        assert(isinstance(powerPerShot, common.ScalarCalculation)) # Construction logic should enforce this
        shotsPerPack = common.Calculator.divideFloor(
            lhs=power,
            rhs=powerPerShot,
            name=f'{self.componentString()} Power Pack Max Shots')
        # Modify the ammo capacity rather than setting it to allow the ammo capacity of internal and
        # external power packs to be cumulative
        factors.append(construction.ModifyAttributeFactor(
            attributeId=gunsmith.WeaponAttribute.AmmoCapacity,
            modifier=construction.ConstantModifier(value=shotsPerPack)))

        if powerPerShot.value() > self._maxPower.value():
            # The power pack is underpowered for the required shot
            unreliableModifier = common.Calculator.subtract(
                lhs=powerPerShot,
                rhs=self._maxPower,
                name=f'{self.componentString()} Power Pack Unreliable Modifier Due To Excessive Power Draw')
            factors.append(construction.ModifyAttributeFactor(
                attributeId=gunsmith.WeaponAttribute.Unreliable,
                modifier=construction.ConstantModifier(value=unreliableModifier)))

            notes.append(f'Excess power draw from power pack causes Unreliable +{unreliableModifier.value()}')

        for factor in factors:
            if not applyModifiers:
                factor = construction.NonModifyingFactor(factor=factor)
            step.addFactor(factor=factor)

        if applyModifiers:
            for note in notes:
                step.addNote(note=note)

class _WeakPowerPackImpl(_PowerPackImpl):
    """
    - Cost Per kg: Cr500
    - Max Power: 2
    - Power Per kg: TL8=100, TL9=300, TL10=500, TL11=700, TL12+=1000
    - Trait: A power pack that suffers an excessive energy draw gains the Unreliable trait at a
      level equal to the difference between its normal maximum damage output and the damage
      output of the weapon
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Weak',
            costPerKg=500,
            maxPower=2)

class _LightPowerPackImpl(_PowerPackImpl):
    """
    - Cost Per kg: Cr1000
    - Max Power: 3
    - Power Per kg: TL8=100, TL9=300, TL10=500, TL11=700, TL12+=1000
    - Trait: A power pack that suffers an excessive energy draw gains the Unreliable trait at a
      level equal to the difference between its normal maximum damage output and the damage
      output of the weapon
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Light',
            costPerKg=1000,
            maxPower=3)

class _StandardPowerPackImpl(_PowerPackImpl):
    """
    - Cost Per kg: Cr1500
    - Max Power: 5
    - Power Per kg: TL8=100, TL9=300, TL10=500, TL11=700, TL12+=1000
    - Trait: A power pack that suffers an excessive energy draw gains the Unreliable trait at a
      level equal to the difference between its normal maximum damage output and the damage
      output of the weapon
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Standard',
            costPerKg=1500,
            maxPower=5)

class _HeavyPowerPackImpl(_PowerPackImpl):
    """
    - Cost Per kg: Cr2500
    - Max Power: 8
    - Power Per kg: TL8=100, TL9=300, TL10=500, TL11=700, TL12+=1000
    - Trait: A power pack that suffers an excessive energy draw gains the Unreliable trait at a
      level equal to the difference between its normal maximum damage output and the damage
      output of the weapon
    """

    def __init__(self) -> None:
        super().__init__(
            componentString='Heavy',
            costPerKg=2500,
            maxPower=8)

class InternalPowerPackLoaded(gunsmith.InternalPowerPackLoadedInterface):
    def __init__(
            self,
            impl: _PowerPackImpl
            ) -> None:
        super().__init__()
        self._impl = impl

    def componentString(self) -> str:
        return self._impl.componentString()

    def typeString(self) -> str:
        return 'Loaded Internal Power Pack'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not self._impl.isCompatible(sequence=sequence, context=context):
            return False

        # Sequence must have the internal power pack feature
        return context.hasComponent(
            sequence=sequence,
            componentType=gunsmith.InternalPowerPackFeature)

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

        internalPackFeature = context.findFirstComponent(
            sequence=sequence,
            componentType=gunsmith.InternalPowerPackFeature)
        assert(isinstance(internalPackFeature, gunsmith.InternalPowerPackFeature))

        packWeight = common.ScalarCalculation(
            value=internalPackFeature.packWeight(),
            name='Internal Power Pack Weight')

        numberOfPacks = common.ScalarCalculation(
            value=1,
            name='Internal Power Pack Count')

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            packWeight=packWeight,
            numberOfPacks=numberOfPacks,
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class WeakInternalPowerPackLoaded(InternalPowerPackLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_WeakPowerPackImpl())

class LightInternalPowerPackLoaded(InternalPowerPackLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_LightPowerPackImpl())

class StandardInternalPowerPackLoaded(InternalPowerPackLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_StandardPowerPackImpl())

class HeavyInternalPowerPackLoaded(InternalPowerPackLoaded):
    def __init__(self) -> None:
        super().__init__(impl=_HeavyPowerPackImpl())

class ExternalPowerPackLoaded(gunsmith.ExternalPowerPackLoadedInterface):
    def __init__(
            self,
            impl: _PowerPackImpl,
            weight: typing.Optional[float] = None
            ) -> None:
        super().__init__()
        self._impl = impl

        self._weightOption = construction.FloatComponentOption(
            id='Weight',
            name='Weight',
            value=weight if weight != None else 1.0,
            minValue=0.1,
            description='Specify the weight of the power pack.')

    def instanceString(self) -> str:
        return f'{self.componentString()} ({common.formatNumber(number=self._weightOption.value())}kg)'

    def componentString(self) -> str:
        return self._impl.componentString()

    def typeString(self) -> str:
        return 'Loaded External Power Pack'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._weightOption]
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
        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        packWeight = common.ScalarCalculation(
            value=self._weightOption.value(),
            name='Specified Power Pack Weight')

        numberOfPacks = common.ScalarCalculation(
            value=1,
            name='Loaded External Power Pack Count')

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            packWeight=packWeight,
            numberOfPacks=numberOfPacks,
            applyModifiers=True, # Apply factors to weapon when magazine is loaded
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class WeakExternalPowerPackLoaded(ExternalPowerPackLoaded):
    def __init__(
            self,
            weight: typing.Optional[float] = None
            ) -> None:
        super().__init__(impl=_WeakPowerPackImpl(), weight=weight)

class LightExternalPowerPackLoaded(ExternalPowerPackLoaded):
    def __init__(
            self,
            weight: typing.Optional[float] = None
            ) -> None:
        super().__init__(impl=_LightPowerPackImpl(), weight=weight)

class StandardExternalPowerPackLoaded(ExternalPowerPackLoaded):
    def __init__(
            self,
            weight: typing.Optional[float] = None
            ) -> None:
        super().__init__(impl=_StandardPowerPackImpl(), weight=weight)

class HeavyExternalPowerPackLoaded(ExternalPowerPackLoaded):
    def __init__(
            self,
            weight: typing.Optional[float] = None
            ) -> None:
        super().__init__(impl=_HeavyPowerPackImpl(), weight=weight)

class PowerPackQuantity(gunsmith.AmmoQuantityInterface):
    def __init__(
            self,
            impl: _PowerPackImpl
            ) -> None:
        super().__init__()
        self._impl = impl

        self._numberOfPacksOption = construction.IntegerComponentOption(
            id='Quantity',
            name='Packs',
            value=1,
            minValue=1,
            description='Specify the number of power packs.')

    def componentString(self) -> str:
        return self._impl.componentString()

    def typeString(self) -> str:
        return 'Power Pack Quantity'

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        return self._impl.isCompatible(sequence=sequence, context=context)

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._numberOfPacksOption]
        options.extend(self._impl.options())
        return options

    def updateOptions(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        self._impl.updateOptions(sequence=sequence, context=context)

class InternalPowerPackQuantity(PowerPackQuantity):
    def instanceString(self) -> str:
        return f'{self.componentString()} x{self._numberOfPacksOption.value()}'

    def componentString(self) -> str:
        return 'Internal ' + super().componentString()

    def isCompatible(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> bool:
        if not super().isCompatible(sequence, context):
            return False

        return context.hasComponent(
            sequence=sequence,
            componentType=gunsmith.InternalPowerPackFeature)

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        internalPackFeature = context.findFirstComponent(
            sequence=sequence,
            componentType=gunsmith.InternalPowerPackFeature)
        assert(isinstance(internalPackFeature, gunsmith.InternalPowerPackFeature))

        packWeight = common.ScalarCalculation(
            value=internalPackFeature.packWeight(),
            name='Internal Power Pack Weight')

        numberOfPacks = common.ScalarCalculation(
            value=self._numberOfPacksOption.value(),
            name='Specified Number Of Power Packs')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            packWeight=packWeight,
            numberOfPacks=numberOfPacks,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class WeakInternalPowerPackQuantity(InternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_WeakPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return WeakInternalPowerPackLoaded()

class LightInternalPowerPackQuantity(InternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_LightPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return LightInternalPowerPackLoaded()

class StandardInternalPowerPackQuantity(InternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return StandardInternalPowerPackLoaded()

class HeavyInternalPowerPackQuantity(InternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_HeavyPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return HeavyInternalPowerPackLoaded()

class ExternalPowerPackQuantity(PowerPackQuantity):
    def __init__(self, impl: _PowerPackImpl) -> None:
        super().__init__(impl)

        self._weightOption = construction.FloatComponentOption(
            id='Weight',
            name='Weight',
            value=1.0,
            minValue=0.1,
            description='Specify the weight of the power pack.')

    def instanceString(self) -> str:
        return f'{self.componentString()} ({self._weightOption.value()}) x{self._numberOfPacksOption.value()}'

    def componentString(self) -> str:
        return 'External ' + super().componentString()

    def options(self) -> typing.List[construction.ComponentOption]:
        options = [self._weightOption]
        options.extend(super().options())
        return options

    def createSteps(
            self,
            sequence: str,
            context: gunsmith.WeaponContext
            ) -> None:
        packWeight = common.ScalarCalculation(
            value=self._weightOption.value(),
            name='Specified Power Pack Weight')

        numberOfPacks = common.ScalarCalculation(
            value=self._numberOfPacksOption.value(),
            name='Specified Number Of Power Packs')

        step = gunsmith.WeaponStep(
            name=self.instanceString(),
            type=self.typeString())

        self._impl.updateStep(
            sequence=sequence,
            context=context,
            packWeight=packWeight,
            numberOfPacks=numberOfPacks,
            applyModifiers=False, # Don't apply factors to weapon for quantities, just include them for information
            step=step)

        context.applyStep(
            sequence=sequence,
            step=step)

class WeakExternalPowerPackQuantity(ExternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_WeakPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return WeakExternalPowerPackLoaded(weight=self._weightOption.value())

class LightExternalPowerPackQuantity(ExternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_LightPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return LightExternalPowerPackLoaded(weight=self._weightOption.value())

class StandardExternalPowerPackQuantity(ExternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_StandardPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return StandardExternalPowerPackLoaded(weight=self._weightOption.value())

class HeavyExternalPowerPackQuantity(ExternalPowerPackQuantity):
    def __init__(self) -> None:
        super().__init__(impl=_HeavyPowerPackImpl())

    def createLoadedAmmo(self) -> gunsmith.AmmoLoadedInterface:
        return HeavyExternalPowerPackLoaded(weight=self._weightOption.value())
