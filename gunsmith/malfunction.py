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


_MalfunctionDiceCount = common.ScalarCalculation(
    value=2,
    name='Dice Count For Malfunction Check')
_OverheatMalfunctionTarget = common.ScalarCalculation(
    value=12,
    name='Overheat Malfunction Threshold')
_DangerMalfunctionTarget = common.ScalarCalculation(
    value=9,
    name='Danger Malfunction Threshold')
_DangerMalfunctionModifier = common.ScalarCalculation(
    value=-2,
    name='Danger Malfunction Modifier')
_DisasterMalfunctionTarget = common.ScalarCalculation(
    value=6,
    name='Disaster Malfunction Threshold')
_DisasterMalfunctionModifier = common.ScalarCalculation(
    value=-4,
    name='Disaster Malfunction Modifier')

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
    if not isinstance(weaponSkill, common.ScalarCalculation):
        weaponSkill = common.ScalarCalculation(
            value=weaponSkill,
            name='Weapon Skill')

    if not isinstance(currentHeat, common.ScalarCalculation):
        currentHeat = common.ScalarCalculation(
            value=currentHeat,
            name='Current Heat')

    overheatThreshold = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.OverheatThreshold)
    if not isinstance(overheatThreshold, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have an ScalarCalculation OverheatThreshold attribute')

    dangerThreshold = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.DangerHeatThreshold)
    if not isinstance(dangerThreshold, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have a ScalarCalculation DangerHeatThreshold attribute')

    disasterThreshold = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.DisasterHeatThreshold)
    if not isinstance(disasterThreshold, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have a ScalarCalculation DisasterHeatThreshold attribute')

    if not (overheatThreshold.value() < dangerThreshold.value() < disasterThreshold.value()):
        raise ValueError(f'Invalid heat threshold values {overheatThreshold.value()} {dangerThreshold.value()} {disasterThreshold.value()}')

    malfunctionDm = weapon.attributeValue(
        sequence=sequence,
        attributeId=gunsmith.WeaponAttributeId.MalfunctionDM)
    if not isinstance(malfunctionDm, common.ScalarCalculation):
        raise RuntimeError('Weapon doesn\'t have a ScalarCalculation MalfunctionDM attribute')

    malfunctionModifiers = [weaponSkill, malfunctionDm]

    malfunctionTarget = None
    if currentHeat.value() >= disasterThreshold.value():
        malfunctionTarget = _DisasterMalfunctionTarget
        malfunctionModifiers.append(_DisasterMalfunctionModifier)
    elif currentHeat.value() >= dangerThreshold.value():
        malfunctionTarget = _DangerMalfunctionTarget
        malfunctionModifiers.append(_DangerMalfunctionModifier)
    elif currentHeat.value() >= overheatThreshold.value():
        malfunctionTarget = _OverheatMalfunctionTarget
    else:
        malfunctionTypeProbabilities: typing.Dict[MalfunctionType, common.ScalarCalculation] = {}
        for type in MalfunctionType:
            malfunctionTypeProbabilities[type] = common.ScalarCalculation(
                value=0,
                name=f'Probability Of Type {type.value} Malfunction Occurring')
        return malfunctionTypeProbabilities

    assert(malfunctionTarget)

    malfunctionModifier = common.Calculator.sum(
        values=malfunctionModifiers,
        name='Total Malfunction Modifier')

    # Calculate the probability of a malfunction occurring due to heat
    malfunctionProbability = common.calculateRollProbability(
        dieCount=_MalfunctionDiceCount,
        probability=common.ProbabilityType.GreaterOrEqualTo,
        targetValue=malfunctionTarget)

    # Calculate the probability of different types of malfunction occurring if a malfunction was
    # to occur
    malfunctionTypeProbabilities: typing.Dict[MalfunctionType, common.ScalarCalculation] = {}
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType1] = common.calculateRollProbability(
        dieCount=_MalfunctionDiceCount,
        probability=common.ProbabilityType.LessThanOrEqualTo,
        targetValue=0,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType2] = common.calculateRollRangeProbability(
        dieCount=_MalfunctionDiceCount,
        lowValue=1,
        highValue=3,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType3] = common.calculateRollRangeProbability(
        dieCount=_MalfunctionDiceCount,
        lowValue=4,
        highValue=6,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType4] = common.calculateRollRangeProbability(
        dieCount=_MalfunctionDiceCount,
        lowValue=7,
        highValue=9,
        modifier=malfunctionModifier)
    malfunctionTypeProbabilities[MalfunctionType.MalfunctionType5] = common.calculateRollProbability(
        dieCount=_MalfunctionDiceCount,
        probability=common.ProbabilityType.GreaterOrEqualTo,
        targetValue=10,
        modifier=malfunctionModifier)

    # Calculate the probability of each type of malfunction actually occurring
    for type, probability in malfunctionTypeProbabilities.items():
        malfunctionTypeProbabilities[type] = common.Calculator.multiply(
            lhs=probability,
            rhs=malfunctionProbability,
            name=f'Probability Of Type {type.value} Malfunction Occurring')

    return malfunctionTypeProbabilities
