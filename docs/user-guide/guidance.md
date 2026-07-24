# Guidance

Guidance turns a child's age into a short list of things to do, things to watch for and
what is typical right now. It starts a month before the birth and continues day by day
through the newborn period, then month by month.

!!! warning "Not medical advice"

    The bundled content is general information to help with planning and orientation. It
    does not replace a midwife, health visitor, paediatrician or doctor. Anything that
    worries you is worth a call to your own care team.

## How the timeline works

Every entry is placed on the timeline by a scale and a period:

| Scale      | Period means                | Example                        |
| ---------- | --------------------------- | ------------------------------ |
| `prenatal` | days before the due date    | `30` is a month before the due date |
| `day`      | days since the birth date   | `0` is the day of birth        |
| `month`    | month of life, from 1       | `1` is birth up to one month old |

Periods do not have to be contiguous. When nothing is written for the exact day, the most
recent earlier period applies. This is why daily content can stop at day 30 and the
monthly content simply takes over from there.

Prenatal entries work the other way around, counting down: fourteen days before the due
date, the nearest checkpoint that has been reached is the one shown.

## Prenatal guidance

Baby Buddy's children require a birth date, so guidance for the weeks before the birth
needs its own anchor. Add a **pregnancy** with a due date under
_Guidance > Manage pregnancies_.

Once the baby arrives, edit the pregnancy and set **Arrived as** to the new child. That
retires its prenatal guidance while keeping the record.

## Marking actions as done

Actions can be ticked off, and progress is tracked per child (or per pregnancy) rather
than per user, so both parents see the same list. Recaps and "watch for" entries are
informational and have no checkbox.

Read-only users can see guidance but cannot change progress.

## Monthly recaps

Each month has a recap page combining the guidance for that month with totals drawn from
what has actually been logged: feedings, diaper changes, sleep, tummy time, weight change
and notes. A month still in progress is labelled as such.

## Customising the content

The bundled content lives in `guidance/data/guidance.json` and is loaded automatically
whenever migrations run. Entries are matched on their `slug`, so reloading updates them in
place instead of creating duplicates.

To load content manually:

```shell
python manage.py loadguidance
```

To load your own file:

```shell
python manage.py loadguidance --file /path/to/guidance.json
```

Add `--prune` to delete entries whose slug is not in the file. Without it, entries that
are no longer listed are left alone.

Entries can also be edited through the database admin, but bear in mind that a later
`loadguidance` run will overwrite changes to bundled entries. Give custom entries their
own slugs to keep them safe.

## API

Guidance is available through the REST API:

- `/api/guidance-entries/` - the content library, filterable by `scale`, `period`, `kind`
  and `is_active`
- `/api/pregnancies/` - due dates, including a computed `days_until_due`
- `/api/guidance-completions/` - which actions have been ticked off, for a `child` or a
  `pregnancy`

See [API](../api.md) for authentication details.
