import enum

class RuleId(enum.Enum):
    # Attempt to make generated weapon more compatible with rules and example weapons from Core Rule
    # Book (and other source books). This is done by changing some base values and dropping some rules
    # that meant some weapon types generated using the core rules are massively nerfed compared to
    # example weapons from other rule books.
    # - Energy Weapons have a base penetration of 0 rather than -1
    # - Handgun Barrels don't apply a -1 penetration modifier. Minimal and short barrels do still apply
    # a modifier.
    # - Smoothbore calibres have a base penetration of 0 rather than -1
    CoreRulesCompatible = 'Core Rules Compatible'


_CoreRulesCompatibleDescription = \
    '<p>When the Core Rules Compatible option is enabled, the weapon construction logic will ' \
    'tweak some values in order to generate weapons that can be more easily used in games ' \
    'where weapons from the Core Rules or other supplements are also being used.</p>' \
    '<p>The fact the Field Catalogue gives some common weapon types like shotguns and pistols a ' \
    'base Penetration of -1 (or lower) can complicate mixing weapons from the Field Catalogue ' \
    'and Core Rule.</p>' \
    '<p>If you want to use the Field Catalogue rules as-is, you need to calculate updated stats ' \
    'for the Core Rule weapons in your game. As well as taking time, this could also result in ' \
    'players finding their favourite boomstick is now doing significantly less damage than it ' \
    'used to due to it now having the LowPen trait. If you want to use this approach, leave Core ' \
    'Rules Compatibility disabled.</p>' \
    'An alternative approach is to tweak the Field Catalogue rules slightly so that the most ' \
    'common weapon types no longer have a base Penetration below 0. Weapon modifications and ' \
    'more exotic ammo types can still reduce a weapons Penetration value, but things like a ' \
    'basic unmodified Autopistol firing ball ammo will act as it did under the Core Rules. If ' \
    'you want to use this approach, enable Core Rules Compatibility for all weapons you ' \
    'generate.</p>' \
    '<p>When Core Rules Compatibility is enabled, the following changes are made to the Field ' \
    'Catalogue Rules:' \
    '<ul style="margin-left:15px; -qt-list-indent:0;">' \
    '<li>Energy weapons have a Base Penetration of 0 rather than -1</li>' \
    '<li>Smoothbore Calibre weapons have a Base Penetration of 0 rather than -1</li>' \
    '<li>Handgun Barrels don\'t apply a Penetration -1 modifier</li>' \
    '</ul></p>' \
    '<p>When creating handguns and other similar short range weapons that wouldn\'t normally have ' \
    'a stock, you might also want to disable the DM-2 attack modifier that the Field Catalogue ' \
    'applies to stockless weapons at ranges > 25m. This can be done on a case by case basis when ' \
    'selecting the stockless component.</p>'

RuleDescriptions = {
    RuleId.CoreRulesCompatible: _CoreRulesCompatibleDescription
}
