import common
import construction
import copy
import csv
import gunsmith
import typing

_CsvHeader = ['Component', 'Cost', 'Weight', 'Other Factors']

def exportToCsv(
        weapon: gunsmith.Weapon,
        filePath: str,
        ) -> None:
    with open(filePath, 'w', newline='', encoding='UTF8') as fileHandle:
        writer = csv.writer(fileHandle)

        weapon = _createExportWeapon(originalWeapon=weapon)
        manifest = weapon.manifest()

        writer.writerow(_CsvHeader)
        for section in manifest.sections():
            entries = section.entries()
            if not entries:
                continue # Nothing to do for sections with no entries

            for entry in entries:
                cost = entry.cost(costId=gunsmith.WeaponCost.Credits)
                if cost:
                    costString = cost.displayString(
                        decimalPlaces=gunsmith.ConstructionDecimalPlaces)
                    if isinstance(cost, construction.ConstantModifier):
                        costString = costString.strip('+')
                        costString = 'Cr' + costString
                else:
                    costString = ''

                weight = entry.cost(costId=gunsmith.WeaponCost.Weight)
                if weight:
                    weightString = weight.displayString(
                        decimalPlaces=gunsmith.ConstructionDecimalPlaces)
                    if isinstance(weight, construction.ConstantModifier):
                        weightString = weightString.strip('+')
                        weightString += 'kg'
                else:
                    weightString = ''

                factorList = sorted([factor.displayString() for factor in entry.factors()])
                factorString = ''
                for factor in factorList:
                    if factorString:
                        factorString += '\n'
                    factorString += factor

                writer.writerow([
                    entry.component(),
                    costString,
                    weightString,
                    factorString])

            # Write section total
            writer.writerow([
                f'{section.name()} Total',
                _formatCostTotal(cost=section.totalCost(costId=gunsmith.WeaponCost.Credits)),
                _formatWeightTotal(weight=section.totalCost(costId=gunsmith.WeaponCost.Weight)),
                ''])

        # Write total
        writer.writerow([
            'Total',
            _formatCostTotal(cost=manifest.totalCost(costId=gunsmith.WeaponCost.Credits)),
            _formatWeightTotal(weight=manifest.totalCost(costId=gunsmith.WeaponCost.Weight)),
            ''])

# Create a copy of the weapon for the export process. This has all accessories attached and all
# loaded ammo/magazines removed. This is done in preparation for generating the manifest where
# it should reflect the full (unloaded) weapon weight/cost and all accessory modifiers should be
# show. The final attributes and notes don't mater at this point as they're not displayed in the
# manifest. The weapon will be updated again later for the other tables
def _createExportWeapon(
        originalWeapon: gunsmith.Weapon
        ) -> gunsmith.Weapon:
    weapon = copy.deepcopy(originalWeapon)

    updated = False

    # Remove loaded magazines & ammo from all sequences
    if weapon.unloadWeapon(sequence=None, regenerate=False):
        updated = True

    # Attach detachable accessories for all sequences
    if weapon.setAccessorAttachment(sequence=None, attach=True, regenerate=False):
        updated = True

    if updated:
        weapon.regenerate()

    return weapon

def _formatCostTotal(cost: common.ScalarCalculation) -> str:
    if not cost.value():
        return ''
    return f'Cr{common.formatNumber(cost.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}'

def _formatWeightTotal(weight: common.ScalarCalculation) -> str:
    if not weight.value():
        return ''
    return f'{common.formatNumber(weight.value(), decimalPlaces=gunsmith.ConstructionDecimalPlaces)}kg'
