# Units

Baby Buddy can work in metric or US customary units. The choice is under
_Site Settings_ (the user menu, staff only) as **Unit system**:

| Measurement                       | Metric | US customary |
| --------------------------------- | ------ | ------------ |
| Weight                            | kg     | lb           |
| Height, head circumference        | cm     | in           |
| Feeding and pumping amounts       | ml     | fl oz        |
| Temperature                       | °C     | °F           |

## How it works

**Values are always stored in metric.** Conversion happens only where a value is
entered or displayed:

- Entry forms label the field with the active unit ("Weight (lb)") and convert
  what you type into metric before saving.
- Lists, dashboard cards, the timeline and report charts convert back for display.
- The REST API always reads and writes metric, so an integration never has to
  know how the interface is configured.

Switching the setting therefore changes what you see, not the data. A weight
entered as 8 lb is stored as 3.6287 kg and shows as 8 lb again, or as 3.629 kg
if the site is switched to metric.

The setting is site-wide rather than per user, so a value entered by one parent
reads the same to the other.

## What is not converted

Two values have no inherent unit and are left alone:

- **BMI** is an index, not a measurement.
- **Diaper change amount** has no agreed meaning in Baby Buddy - some people
  record a volume, others a nappy weight - so it is shown exactly as entered.

Medication dosage keeps its own per-entry unit field, chosen when the entry is
created, and is unaffected by this setting.

## Existing data

If you have been recording measurements before setting this, the values already
in the database are treated as metric, because that is the storage unit. Anyone
who had been typing pounds into the weight field will find those entries
reinterpreted as kilograms. Correct them by editing the entries, or convert them
in bulk through the API before switching the display to US units.
