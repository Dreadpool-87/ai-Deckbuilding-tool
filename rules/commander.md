# Commander: Official Sources and Validation Checklist

**Format rules:** https://magic.wizards.com/en/formats/commander

**Current banned list:** https://magic.wizards.com/en/banned-restricted-list

**Comprehensive Rules:** https://magic.wizards.com/en/rules

## Checklist for future validator development

- Verify deck size and eligible commander(s) against the current official format rules.
- Derive color identity from complete Oracle card information, not just the printed mana cost.
- Check singleton restrictions and documented card-specific exceptions.
- Validate commander eligibility and exceptions such as partner mechanics separately.
- Check banned lists by **format and effective date**. Model exceptions such as `banned as companion` separately.
- Report unsupported or unresolved mechanics as `NOT_CHECKED` or `UNVERIFIED`, never `PASS`.
- A banned-list update does **not** mean the local validator automatically enforces it.

This is a specification/checklist, **not an implemented or tested enhancement** to MTG Deck Validator v1.1.
