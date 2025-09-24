# Custom Sectors
Auto-Jimmy allows you to import custom sector and metadata files so your
sectors can be merged into the stock Traveller universe. Custom sectors
can either be added to an empty region of space or they can replace existing
sectors to allow you to customize the universe for your setting.

## Supported Formats
Auto-Jimmy supports the following sector and metadata file formats:
* [T5 Column Delimited Sector Format](https://travellermap.com/doc/fileformats#t5-column-delimited-format) - aka Second Survey format
* [T5 Tab Delimited Sector Format](https://travellermap.com/doc/fileformats#t5tab)
* [XML Metadata Format](https://travellermap.com/doc/metadata)
* [JSON Metadata Format](https://travellermap.com/doc/api#metadata-retrieve-metadata-for-a-sector)

> [!NOTE]
> The Traveller Map Poster API doesn't support the JSON Metadata format so
> Auto-Jimmy will convert it to XML format when uploading it to Traveller Map.
> This is a completely automatic, however, any errors returned by Traveller Map
> when creating posters or linting may refer to the XML format.

## Metadata
The sector metadata file contains extra information about the sector that is
used in addition to the world information contained in the main sector file. At
a minimum, the metadata file must specify the sector name and its position in
sector coordinates, however, it can also be used to specify things like faction
borders and xboat routes. More information on what can be added can be found
[here](https://travellermap.com/doc/metadata).

> [!NOTE]
> Sector coordinates have their origin at Core, with Rimward & Trailing being
> positive and Coreward & Spinward being negative.

> [!NOTE]
> If there is an existing sector at the position specified it will be replaced
> by the custom sector.

> [!NOTE]
> The sector name must be unique in the universe. The sector can only have the
> same name as an existing sector if it also has the same position as it.

The following gives examples of the minimum XML or JSON metadata you would need
for a custom sector. The positions used by the sectors replace the [Foreven](https://wiki.travellerrpg.com/Foreven_Sector)
sector, which is a sector set aside for referees to customize.

### XML Metadata
```
<?xml version="1.0" encoding="UTF-8"?>
<Sector xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <X>-5</X>
  <Y>-1</Y>
  <Name>Sector Name</Name>
</Sector>
```

### JSON Metadata
```
{
  "Names": [
    {
      "Text": "Sector Name"
    }
  ],
  "X": -5,
  "Y": -1
}
```

## Modifying Existing Sectors
The simplest way to modify an existing sector is to make a copy of the stock
sector and metadata file from the universe snapshot used by Auto-Jimmy, this
copy can then be modified as required, then imported into Auto-Jimmy as a
custom sector.

> [!IMPORTANT]
> You **must** import the modified sector files as custom sectors. If you
> just overwrite the stock sector data, Auto-Jimmy won't generate the poster
> images of your sector so your changes won't be shown in the Traveller Map
> pages it displays.

Where you can find the most recent stock sector files will vary depending on
if you've downloaded a universe update. If you've not downloaded a universe
update, the files can be found in  `./data/map/` under the directory you
cloned/installed Auto-Jimmy to. If you have downloaded an update, they can be
found in `%AppData%\map\` on Windows or `~/.auto-jimmy/map/` on macOS and Linux.

## Linting
Linting is a service provided by Traveller Map where it can analyse your sector
and metadata files to check for errors. For example it will flag worlds that have
a government that is invalid for the population size. The rules Traveller Map uses
when linting are based on the T5 world creation rules.
Auto-Jimmy gives you the option to lint your custom sector files when creating a
new custom sector. If you choose to lint the files, they will be automatically
uploaded to Traveller Map and any errors found will be displayed.

> [!IMPORTANT]
> Linting requires an internet connection.

## Links
* Traveller Map API: https://travellermap.com/doc/api
* Traveller Map Custom Data: https://travellermap.com/doc/custom