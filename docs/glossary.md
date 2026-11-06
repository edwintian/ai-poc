# Glossary

- **Consistent**: the contract term is supported by retrieved official evidence and doesn't conflict with any rule. It's never given when the term wasn't found or there is no official evidence.
- **Needs Attention**: the term appears to fall short of a rule or guidance, or it's silent where the Act expects a provision (e.g. no overtime clause). Not a finding that the term is "illegal".
- **Unable to Assess**: the tool can't decide. The reason is one of the following: insufficient information/evidence, rule may not apply (e.g. managers), **out of scope** (see below), or service error.
- **Out-of-scope term**: a term the Employment Act and the indexed MOM guidance don't regulate (`confidentiality`, `non_compete`). It is always `Unable to Assess` with `OUT_OF_SCOPE_REASON`. See ADR 0001.
- **Part 4 coverage**: hours, overtime and rest-day rules in Part 4 of the Employment Act (s 35). These apply to workmen earning ≤ $4,500/month and to non-managerial, non-executive non-workmen earning ≤ $2,600/month. The ceilings can be changed by the Minister. The app doesn't ask for category or salary; it checks hours and overtime for everyone and notes the coverage limits on any shortfall (ADR 0013).
- **Annual leave entitlement (s 88A)**: 7 days in the first year of service, +1 day per year, up to 14 days from the 8th year. The tool treats only ≥ 14 days as `Consistent`. See ADR 0003.
- **Workman**: an employee doing mainly manual labour, as defined in the Act.
- **Verified quote**: extracted wording that, after normalisation, appears in the contract text, possibly across a page break. Only verified quotes are shown. An unverified quote means the term is treated as not found. See ADR 0002.
- **Evidence guard**: a no-rule finding can only be `Consistent` or `Needs Attention` if it cites a retrieved official passage. Otherwise it becomes `Unable to Assess`. See ADR 0005.
- **Official passage**: a knowledge-base passage of kind `law` (statute) or `guidance` (MOM). Only these can be cited as sources. Contract passages are evidence, not sources.
