import common
import enum
import gunsmith
import typing

"""
- If heat at the point of firing is > overheat threshold
    - Roll 2D, target number comes from table on p14
        - >= Overheat & < Danger = 12
        - >= Danger & < Disaster = 9
        - >= Disaster = 6
    - If roll is >= target number a malfunction has occurred
        - Roll 2D with the following modifiers
            - Plus players gun skill
            - Plus any modifiers for Bulwarked and Rugged
            - Minus weapons damage
            - Minus any hazardous and ramshackle scores the weapon has
        - Effect of malfunction comes from table on p8
            - <= 0 = Breech explosion or similar disaster. The weapon is ruined and the user receives its normal damage
            - 1-3 = A critical component breaks. The weapon is out of action until repaired in a workshop
            - 4-6 = A component breaks or ammunition jams in the mechanism. The weapon is out of action but can be
            fixed in a few minutes without the need for a workshop.
            - 7-9 = An ammunition misfeed or similar minor technical issue occurs. One significant action is required to
            clear it or ready the weapon
            - >= 10 = A minor technical fault wastes this shot but does not put the weapon out of commission. For example,
            a grenade launches but fails to detonate, or a bit of dirt on the end of the emitter tunnel blocks a laser
            pulse but is vapourised by it clearing the weapon to shoot normally
"""
# NOTE: The description of what modifiers apply when rolling against the Malfunction table (Field
# Catalogue p8) say that the Hazardous score but doesn't mention Ramshackle. However the description
# for Ramshackle (Field Catalogue p7) does say the DM is applied to the result of rolls on the
# Malfunction table.

class MalfunctionType(enum.Enum):
    # <= 0 = Breech explosion or similar disaster. The weapon is ruined and the user receives its normal damage
    MalfunctionType1 = 1

    # 1-3 = A critical component breaks. The weapon is out of action until repaired in a workshop
    MalfunctionType2 = 2

    # 4-6 = A component breaks or ammunition jams in the mechanism. The weapon is out of action but can be
    # fixed in a few minutes without the need for a workshop.
    MalfunctionType3 = 3

    # 7-9 = An ammunition misfeed or similar minor technical issue occurs. One significant action is required to
    # clear it or ready the weapon
    MalfunctionType4 = 4

    # >= 10 = A minor technical fault wastes this shot but does not put the weapon out of commission. For example,
    # a grenade launches but fails to detonate, or a bit of dirt on the end of the emitter tunnel blocks a laser
    # pulse but is vaporised by it clearing the weapon to shoot normally
    MalfunctionType5 = 5


_MalfunctionDiceCount = 2
_OverheatMalfunctionTarget = 12
_DangerMalfunctionTarget = 9
_DangerMalfunctionModifier = -2
_DisasterMalfunctionTarget = 6
_DisasterMalfunctionModifier = -4

_MalfunctionTypeDescriptionMap = {
    MalfunctionType.MalfunctionType1: 'Breech explosion or similar disaster. The weapon is ruined and the user receives its normal damage',
    MalfunctionType.MalfunctionType2: 'A critical component breaks. The weapon is out of action until repaired in a workshop',
    MalfunctionType.MalfunctionType3: 'A component breaks or ammunition jams in the mechanism. The weapon is out of action but can be fixed in a few minutes without the need for a workshop',
    MalfunctionType.MalfunctionType4: 'An ammunition misfeed or similar minor technical issue occurs. One significant action is required to clear it or ready the weapon',
    MalfunctionType.MalfunctionType5: 'A minor technical fault wastes this shot but does not put the weapon out of commission. For example, a grenade launches but fails to detonate, or a bit of dirt on the end of the emitter tunnel blocks a laser pulse but is vapourised by it clearing the weapon to shoot normally',
}

def malfunctionDescription(
        malfunctionType: MalfunctionType
        ) -> str:
    return _MalfunctionTypeDescriptionMap[malfunctionType]

# NOTE: This function returns a normalised percentage in the range (0->1.0)
def calculateMalfunctionProbability(
        weapon: gunsmith.Weapon,
        sequence: str,
        weaponSkill: typing.Union[int, common.ScalarCalculation],
        currentHeat: typing.Union[int, common.ScalarCalculation]
        ) -> typing.Optional[typing.Mapping[MalfunctionType, common.ScalarCalculation]]:
    if isinstance(weaponSkill, common.ScalarCalculation):
        weaponSkill = weaponSkill.value()

    if isinstance(currentHeat, common.ScalarCalculation):
        currentHeat = currentHeat.value()

    overheatThreshold = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.OverheatThreshold)
    if not isinstance(overheatThreshold, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have an ScalarCalculation OverheatThreshold attribute')
    overheatThreshold = overheatThreshold.value()

    dangerThreshold = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold)
    if not isinstance(dangerThreshold, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have a ScalarCalculation DangerHeatThreshold attribute')
    dangerThreshold = dangerThreshold.value()

    disasterThreshold = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold)
    if not isinstance(disasterThreshold, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have a ScalarCalculation DisasterHeatThreshold attribute')
    disasterThreshold = disasterThreshold.value()

    if not (overheatThreshold < dangerThreshold < disasterThreshold):
        raise ValueError(f'Invalid heat threshold values {overheatThreshold} {dangerThreshold} {disasterThreshold}')

    malfunctionDm = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.MalfunctionDM)
    if not isinstance(malfunctionDm, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have a ScalarCalculation MalfunctionDM attribute')
    malfunctionDm = malfunctionDm.value()

    malfunctionModifier = weaponSkill + malfunctionDm
    malfunctionTarget = None
    if currentHeat >= disasterThreshold:
        malfunctionTarget = _DisasterMalfunctionTarget
        malfunctionModifier += _DisasterMalfunctionModifier
    elif currentHeat >= dangerThreshold:
        malfunctionTarget = _DangerMalfunctionTarget
        malfunctionModifier += _DangerMalfunctionModifier
    elif currentHeat >= overheatThreshold:
        malfunctionTarget = _OverheatMalfunctionTarget
    else:
        malfunctionTypeProbabilities: typing.Dict[MalfunctionType, common.ScalarCalculation] = {}
        for type in MalfunctionType:
            malfunctionTypeProbabilities[type] = common.ScalarCalculation(
                value=0,
                name=f'Probability Of Type {type.value} Malfunction Occurring')
        return malfunctionTypeProbabilities

    assert(malfunctionTarget)

    # Calculate the probability of a malfunction occurring due to heat
    malfunctionProbability = _calculateGreaterOrEqualProbability(
        targetValue=malfunctionTarget)

    # Calculate the probability of different types of malfunction occurring if a malfunction was
    # to occur
    malfunctionTypeProbabilities: typing.Dict[MalfunctionType, common.ScalarCalculation] = {}
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType1] = _calculateLessOrEqualProbability(
        targetValue=0,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType2] = _calculateRangeProbability(
        lowValue=1,
        highValue=3,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType3] = _calculateRangeProbability(
        lowValue=4,
        highValue=6,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType4] = _calculateRangeProbability(
        lowValue=7,
        highValue=9,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType5] = _calculateGreaterOrEqualProbability(
        targetValue=10,
        modifier=malfunctionModifier)

    # Calculate the probability of each type of malfunction actually occurring
    for type, probability in malfunctionTypeProbabilities.items():
        malfunctionTypeProbabilities[type] = common.Calculator.multiply(
            lhs=probability,
            rhs=malfunctionProbability,
            name=f'Probability Of Type {type.value} Malfunction Occurring')

    return malfunctionTypeProbabilities

def _calculateLessOrEqualProbability(
        targetValue: int,
        modifier: int = 0,
        ) -> common.ScalarCalculation:
    resultName = 'Probability Of Rolling Less Than Or Equal To {value} Inclusive With {dice}D'.format(
        value=targetValue,
        dice=_MalfunctionDiceCount)
    if modifier:
        resultName += f'{modifier:+}'

    return common.ScalarCalculation(
        value=common.calculateRollProbability(
            targetValue=targetValue,
            dieCount=_MalfunctionDiceCount,
            dieType=common.DieType.D6,
            modifier=modifier,
            probability=common.ComparisonType.LessThanOrEqualTo),
        name=resultName)

def _calculateGreaterOrEqualProbability(
        targetValue: int,
        modifier: int = 0
        ) -> common.ScalarCalculation:
    resultName = 'Probability Of Rolling Greater Than Or Equal To {value} With {dice}D'.format(
        value=targetValue,
        dice=_MalfunctionDiceCount)
    if modifier:
        resultName += f'{modifier:+}'

    return common.ScalarCalculation(
        value=common.calculateRollProbability(
            targetValue=targetValue,
            dieCount=_MalfunctionDiceCount,
            dieType=common.DieType.D6,
            modifier=modifier,
            probability=common.ComparisonType.GreaterOrEqualTo),
        name=resultName)

def _calculateRangeProbability(
        lowValue: int,
        highValue: int,
        modifier: int = 0
        ) -> common.ScalarCalculation:
    resultName = 'Probability Of Rolling Between {low} And {high} Inclusive With {dice}D'.format(
        low=lowValue,
        high=highValue,
        dice=_MalfunctionDiceCount)
    if modifier:
        resultName += f'{modifier:+}'

    return common.ScalarCalculation(
        value=common.calculateRollRangeProbability(
            lowValue=lowValue,
            highValue=highValue,
            dieCount=_MalfunctionDiceCount,
            dieType=common.DieType.D6,
            modifier=modifier),
        name=resultName)
