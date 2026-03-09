"""
Quick-reference dictionary of the 50 most commonly queried sections of the
Income Tax Act, 1961 and related statutes.

Each entry maps a section number (str) to:
    title             – short official name
    brief_description – plain-English summary (2-3 sentences)
    key_points        – list of bullet points practitioners care about most
"""

TAX_SECTIONS: dict[str, dict] = {
    # ── Income Heads & Exemptions ───────────────────────────────────────────
    "10(13A)": {
        "title": "House Rent Allowance (HRA) Exemption",
        "brief_description": (
            "Provides exemption for HRA received by a salaried employee. "
            "The exempt amount is the least of actual HRA received, rent paid "
            "minus 10% of salary, or 50%/40% of salary (metro/non-metro)."
        ),
        "key_points": [
            "Available only to salaried employees receiving HRA component",
            "Exemption = min(HRA received, rent paid - 10% salary, 50%/40% salary)",
            "Metro cities: Delhi, Mumbai, Kolkata, Chennai (50% salary)",
            "Rent receipts mandatory if annual rent exceeds Rs. 1,00,000",
            "Landlord PAN required if annual rent exceeds Rs. 1,00,000",
            "Not available under new regime (Section 115BAC)",
        ],
    },
    "10(14)": {
        "title": "Special Allowances",
        "brief_description": (
            "Covers prescribed allowances like children education allowance, "
            "hostel expenditure, transport allowance for disabled employees, etc. "
            "Rule 2BB prescribes specific limits."
        ),
        "key_points": [
            "Children education allowance: Rs. 100/month/child (max 2 children)",
            "Hostel expenditure: Rs. 300/month/child (max 2 children)",
            "Transport allowance for disabled: Rs. 3,200/month",
            "Prescribed under Rule 2BB of IT Rules",
        ],
    },
    "10(10D)": {
        "title": "Life Insurance Maturity Proceeds",
        "brief_description": (
            "Exempts maturity proceeds from life insurance policies, subject "
            "to the premium not exceeding prescribed percentage of sum assured."
        ),
        "key_points": [
            "Premium must not exceed 10% of sum assured (policies post 01-Apr-2012)",
            "For policies pre 01-Apr-2012, limit is 20% of sum assured",
            "Keyman insurance proceeds are fully taxable",
            "ULIP proceeds taxable if annual premium exceeds Rs. 2.5 lakh (from AY 2022-23)",
        ],
    },
    "10(10)": {
        "title": "Gratuity Exemption",
        "brief_description": (
            "Provides exemption for gratuity received on retirement, death, "
            "or disablement. Limits differ for government and non-government employees."
        ),
        "key_points": [
            "Government employees: fully exempt",
            "Non-government (covered by Gratuity Act): exempt up to Rs. 20,00,000",
            "Non-government (not covered): lower of 15 days salary x years or Rs. 20,00,000",
            "Salary = last drawn salary (Gratuity Act) or avg of last 10 months",
        ],
    },
    "10(10AA)": {
        "title": "Leave Encashment Exemption",
        "brief_description": (
            "Exempts leave encashment received at the time of retirement or "
            "superannuation. Government employees get full exemption."
        ),
        "key_points": [
            "Government employees: fully exempt",
            "Others: exempt up to Rs. 25,00,000 (w.e.f. 01-Apr-2023)",
            "Based on average salary of last 10 months",
            "Maximum leave: 30 days per year of service",
        ],
    },
    # ── House Property ──────────────────────────────────────────────────────
    "24(b)": {
        "title": "Deduction for Interest on Home Loan",
        "brief_description": (
            "Allows deduction of interest paid on housing loan from income "
            "from house property. Limit of Rs. 2 lakh for self-occupied property."
        ),
        "key_points": [
            "Self-occupied: max Rs. 2,00,000 per year",
            "Let-out property: no upper limit on interest deduction",
            "Construction must be completed within 5 years from end of FY of loan",
            "Pre-construction interest deductible in 5 equal instalments",
            "Both co-owners can claim deduction on joint home loans",
            "Available under both old and new regimes for let-out property",
        ],
    },
    # ── Audit & Presumptive ─────────────────────────────────────────────────
    "44AB": {
        "title": "Tax Audit",
        "brief_description": (
            "Mandates audit of accounts for businesses with turnover exceeding "
            "prescribed threshold and professionals with gross receipts exceeding "
            "the limit. Form 3CA/3CB with 3CD."
        ),
        "key_points": [
            "Business: turnover > Rs. 1 crore (Rs. 10 crore if cash < 5%)",
            "Profession: gross receipts > Rs. 50 lakh",
            "Due date: 30th September of assessment year",
            "Penalty u/s 271B: 0.5% of turnover or Rs. 1,50,000 (lower)",
            "Not required if opting for presumptive taxation u/s 44AD (if income >= 8%/6%)",
            "Form 3CA for companies, Form 3CB for others",
        ],
    },
    "44AD": {
        "title": "Presumptive Taxation — Business",
        "brief_description": (
            "Allows eligible businesses to declare income at 8% of turnover "
            "(6% for digital receipts) without maintaining books. Available to "
            "resident individuals, HUFs, and partnership firms."
        ),
        "key_points": [
            "Turnover limit: Rs. 2 crore (Rs. 3 crore if cash < 5%)",
            "Presumptive income: 8% of turnover (6% for digital receipts)",
            "Can declare higher income but not lower (if lower, audit required)",
            "Not available to LLPs, companies, or professionals",
            "If opted out, cannot use 44AD for next 5 years",
            "No requirement to maintain books of account if income >= 8%/6%",
        ],
    },
    "44ADA": {
        "title": "Presumptive Taxation — Professionals",
        "brief_description": (
            "Allows specified professionals to declare 50% of gross receipts "
            "as income without maintaining books. Covers professions listed "
            "in Section 44AA(1)."
        ),
        "key_points": [
            "Gross receipts limit: Rs. 50 lakh (Rs. 75 lakh if cash < 5%)",
            "Presumptive income: 50% of gross receipts",
            "Covers: legal, medical, engineering, architecture, accountancy, etc.",
            "Available to resident individuals and partnership firms",
            "Advance tax: single instalment by 15th March",
        ],
    },
    "44AE": {
        "title": "Presumptive Taxation — Goods Carriers",
        "brief_description": (
            "Provides presumptive income scheme for taxpayers in the business "
            "of plying, hiring, or leasing goods carriages."
        ),
        "key_points": [
            "Max vehicles: 10 goods carriages at any time during the year",
            "Income per heavy vehicle: Rs. 1,000/ton/month",
            "Income per other vehicle: Rs. 7,500/month",
            "No requirement to maintain books",
        ],
    },
    # ── Capital Gains Exemptions ────────────────────────────────────────────
    "54": {
        "title": "Exemption on Sale of Residential House",
        "brief_description": (
            "Provides exemption from LTCG on sale of a residential house "
            "if net consideration is invested in another residential house."
        ),
        "key_points": [
            "Only for individuals and HUFs",
            "New house must be purchased within 1 year before or 2 years after sale",
            "Or constructed within 3 years of sale",
            "Lock-in: new house cannot be sold within 3 years",
            "If not invested by due date, deposit in Capital Gains Account Scheme",
            "Max exemption: Rs. 10 crore (w.e.f. AY 2024-25)",
        ],
    },
    "54EC": {
        "title": "Exemption on Investment in Specified Bonds",
        "brief_description": (
            "Exempts LTCG if invested in specified bonds (NHAI/RECL) within "
            "6 months of transfer. Lock-in period of 5 years."
        ),
        "key_points": [
            "Bonds: NHAI, RECL, PFC, IRFC",
            "Max investment: Rs. 50 lakh per financial year",
            "Lock-in: 5 years",
            "Investment must be within 6 months of date of transfer",
            "Interest on bonds is taxable",
        ],
    },
    "54F": {
        "title": "Exemption on Sale of Any Long-Term Capital Asset",
        "brief_description": (
            "Provides LTCG exemption on sale of any asset (other than "
            "residential house) if net consideration invested in a residential house."
        ),
        "key_points": [
            "Asset sold must NOT be a residential house",
            "Full exemption if entire net consideration invested",
            "Proportionate exemption if partial investment",
            "Must not own more than one residential house on date of transfer",
            "Same timelines as Section 54 for purchase/construction",
            "Lock-in: 3 years for new house",
        ],
    },
    "50C": {
        "title": "Deemed Consideration — Stamp Duty Value",
        "brief_description": (
            "For transfer of land/building, if actual consideration is less than "
            "stamp duty value, the stamp duty value is deemed to be the consideration."
        ),
        "key_points": [
            "Tolerance band: 10% (stamp value can exceed actual by up to 10%)",
            "Assessee can challenge stamp duty value before Valuation Officer",
            "Applicable to seller for computing capital gains",
            "Corresponding provision for buyer: Section 56(2)(x)",
        ],
    },
    "112A": {
        "title": "LTCG on Listed Equity Shares / Units",
        "brief_description": (
            "Levies 12.5% tax on LTCG exceeding Rs. 1.25 lakh from listed "
            "equity shares and equity-oriented mutual funds."
        ),
        "key_points": [
            "Tax rate: 12.5% (w.e.f. AY 2025-26, was 10%)",
            "Exemption threshold: Rs. 1,25,000 per year (was Rs. 1,00,000)",
            "STT must be paid on acquisition and transfer",
            "No indexation benefit available",
            "Grandfathering: cost of acquisition as on 31-Jan-2018",
        ],
    },
    "111A": {
        "title": "STCG on Listed Equity Shares / Units",
        "brief_description": (
            "Short-term capital gains on listed equity shares and equity-oriented "
            "mutual funds where STT is paid, taxed at 20%."
        ),
        "key_points": [
            "Tax rate: 20% (w.e.f. AY 2025-26, was 15%)",
            "STT must be paid on transfer",
            "No deduction under Chapter VI-A against such income",
            "Rebate u/s 87A not available on STCG 111A",
        ],
    },
    # ── Chapter VI-A Deductions ─────────────────────────────────────────────
    "80C": {
        "title": "Deduction for Investments & Payments",
        "brief_description": (
            "Allows deduction up to Rs. 1,50,000 for investments in specified "
            "instruments like PPF, ELSS, life insurance premium, tuition fees, "
            "home loan principal, etc."
        ),
        "key_points": [
            "Max deduction: Rs. 1,50,000 (combined with 80CCC and 80CCD(1))",
            "Eligible: PPF, ELSS, NSC, 5-year FD, life insurance premium",
            "Tuition fees: max 2 children, full-time education",
            "Home loan principal repayment included",
            "ELSS lock-in: 3 years",
            "Not available under new regime (Section 115BAC)",
        ],
    },
    "80CCD(1B)": {
        "title": "Additional NPS Deduction",
        "brief_description": (
            "Allows additional deduction of Rs. 50,000 for contributions "
            "to National Pension System, over and above Section 80C limit."
        ),
        "key_points": [
            "Additional deduction: Rs. 50,000",
            "Over and above Section 80C limit of Rs. 1,50,000",
            "Available to employees and self-employed",
            "Not available under new regime",
            "Tier-I NPS account only",
        ],
    },
    "80CCD(2)": {
        "title": "Employer NPS Contribution",
        "brief_description": (
            "Deduction for employer's contribution to NPS. Not subject to "
            "Rs. 1,50,000 limit of Section 80C."
        ),
        "key_points": [
            "Central/State Govt employees: up to 14% of salary",
            "Other employees: up to 10% of salary",
            "No overall cap — deduction independent of 80C/80CCD(1B)",
            "Available under both old and new regimes",
            "Salary = basic + DA for this purpose",
        ],
    },
    "80D": {
        "title": "Health Insurance Premium",
        "brief_description": (
            "Allows deduction for medical insurance premium paid for self, "
            "family, and parents. Includes preventive health check-up."
        ),
        "key_points": [
            "Self/family: Rs. 25,000 (Rs. 50,000 if senior citizen)",
            "Parents: Rs. 25,000 (Rs. 50,000 if senior citizen)",
            "Max total: Rs. 1,00,000 (both senior citizens)",
            "Preventive health check-up: Rs. 5,000 (within above limit)",
            "Payment must be by non-cash mode (except preventive check-up)",
            "Not available under new regime",
        ],
    },
    "80DD": {
        "title": "Maintenance of Disabled Dependent",
        "brief_description": (
            "Deduction for maintenance/medical treatment of a dependent "
            "with disability. Flat deduction irrespective of actual expenditure."
        ),
        "key_points": [
            "Disability (40-79%): Rs. 75,000",
            "Severe disability (80%+): Rs. 1,25,000",
            "Certificate from prescribed medical authority required",
            "Dependent: spouse, children, parents, siblings",
            "Not available under new regime",
        ],
    },
    "80DDB": {
        "title": "Medical Treatment of Specified Diseases",
        "brief_description": (
            "Deduction for medical treatment of specified diseases like "
            "cancer, neurological diseases, AIDS, etc."
        ),
        "key_points": [
            "General: up to Rs. 40,000",
            "Senior citizens: up to Rs. 1,00,000",
            "Specified diseases: cancer, AIDS, neurological, renal failure, etc.",
            "Prescription from specialist required (Form 10-I)",
            "Reduced by insurance reimbursement received",
        ],
    },
    "80E": {
        "title": "Interest on Education Loan",
        "brief_description": (
            "Deduction for interest on loan taken for higher education. "
            "No cap on amount. Available for 8 assessment years."
        ),
        "key_points": [
            "No upper limit on deduction amount",
            "Available for initial 8 years from start of interest repayment",
            "Higher education: after Senior Secondary / equivalent",
            "Loan must be from financial institution or approved charitable institution",
            "Available for self, spouse, children",
            "Only interest component, not principal",
        ],
    },
    "80EEA": {
        "title": "Interest on Housing Loan (Affordable Housing)",
        "brief_description": (
            "Additional deduction of Rs. 1,50,000 for interest on loan "
            "for affordable housing. Over and above Section 24(b)."
        ),
        "key_points": [
            "Additional deduction: Rs. 1,50,000",
            "Stamp duty value must not exceed Rs. 45 lakh",
            "Loan sanctioned between 01-Apr-2019 and 31-Mar-2022",
            "First-time homebuyer only",
            "Not available under new regime",
        ],
    },
    "80G": {
        "title": "Donations to Charitable Institutions",
        "brief_description": (
            "Deduction for donations to specified funds/institutions. "
            "Some qualify for 100% deduction, others for 50%."
        ),
        "key_points": [
            "100% deduction: PM Relief Fund, National Defence Fund, etc.",
            "50% deduction: other approved charities",
            "Some donations subject to 10% of adjusted total income cap",
            "Cash donations > Rs. 2,000 not allowed",
            "Section 80GGA for scientific research donations",
        ],
    },
    "80GG": {
        "title": "Rent Paid (No HRA)",
        "brief_description": (
            "Deduction for rent paid by individuals not receiving HRA. "
            "Applies to self-employed persons and employees without HRA."
        ),
        "key_points": [
            "Max deduction: Rs. 5,000/month (Rs. 60,000/year)",
            "Least of: rent - 10% total income, 25% total income, or actual rent",
            "Must not own residential property in city of employment",
            "Form 10BA declaration required",
            "Not available under new regime",
        ],
    },
    "80TTA": {
        "title": "Interest on Savings Account",
        "brief_description": (
            "Deduction up to Rs. 10,000 on interest earned from savings "
            "bank accounts. Not available for fixed/recurring deposits."
        ),
        "key_points": [
            "Max deduction: Rs. 10,000",
            "Only savings account interest (not FD/RD)",
            "Available to individuals and HUFs (non-senior citizens)",
            "For senior citizens: Section 80TTB (Rs. 50,000 on all deposits)",
            "Not available under new regime",
        ],
    },
    "80TTB": {
        "title": "Interest on Deposits — Senior Citizens",
        "brief_description": (
            "Deduction up to Rs. 50,000 for senior citizens on interest "
            "from deposits with banks, co-operative societies, or post office."
        ),
        "key_points": [
            "Max deduction: Rs. 50,000",
            "Covers savings, FD, RD, and post office deposits",
            "Only for senior citizens (60+ years)",
            "Replaces Section 80TTA for senior citizens",
            "Not available under new regime",
        ],
    },
    "80U": {
        "title": "Person with Disability",
        "brief_description": (
            "Flat deduction for resident individuals suffering from "
            "specified disability, certified by prescribed medical authority."
        ),
        "key_points": [
            "Disability (40-79%): Rs. 75,000",
            "Severe disability (80%+): Rs. 1,25,000",
            "Certificate from prescribed medical authority required",
            "Available only to the disabled person (not dependents — that is 80DD)",
            "Not available under new regime",
        ],
    },
    # ── Rebate ──────────────────────────────────────────────────────────────
    "87A": {
        "title": "Tax Rebate for Lower Income",
        "brief_description": (
            "Provides rebate to resident individuals with total income "
            "below prescribed threshold, effectively making income tax-free."
        ),
        "key_points": [
            "Old regime: income up to Rs. 5,00,000 — rebate up to Rs. 12,500",
            "New regime: income up to Rs. 12,00,000 — rebate up to Rs. 60,000 (Budget 2025)",
            "Marginal relief applicable at boundary",
            "Not available on STCG u/s 111A or LTCG u/s 112A",
            "Only for resident individuals",
        ],
    },
    # ── New Tax Regime ──────────────────────────────────────────────────────
    "115BAC": {
        "title": "New Tax Regime",
        "brief_description": (
            "Optional (default from AY 2024-25) concessional tax regime "
            "with lower slab rates but no major deductions/exemptions."
        ),
        "key_points": [
            "Default regime from AY 2024-25 — opt out if preferring old regime",
            "Slabs (AY 2026-27): 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%",
            "Standard deduction: Rs. 75,000 (salaried/pensioners)",
            "Most Chapter VI-A deductions NOT available",
            "80CCD(2) (employer NPS) IS available",
            "Section 24(b) available only for let-out property",
            "Family pension deduction: Rs. 25,000",
            "Salaried: can switch every year; business income: one-time choice",
        ],
    },
    # ── Filing Obligations ──────────────────────────────────────────────────
    "139(1)": {
        "title": "Filing of Return — Due Dates",
        "brief_description": (
            "Prescribes mandatory filing of income tax returns and the "
            "due dates for different categories of taxpayers."
        ),
        "key_points": [
            "Individuals (no audit): 31st July",
            "Audit cases (44AB, companies): 31st October",
            "Transfer pricing cases: 30th November",
            "Late filing allowed u/s 139(4) till 31st December",
            "Updated return u/s 139(8A) within 24 months from end of AY",
            "Mandatory if income exceeds basic exemption limit",
        ],
    },
    "139(4)": {
        "title": "Belated Return",
        "brief_description": (
            "Allows filing of return after the due date but before "
            "the end of the relevant assessment year (31st December)."
        ),
        "key_points": [
            "Can be filed till 31st December of the assessment year",
            "Late fee u/s 234F: Rs. 5,000 (Rs. 1,000 if income < Rs. 5 lakh)",
            "Cannot carry forward certain losses (house property loss can be carried forward)",
            "Can be revised u/s 139(5)",
        ],
    },
    "139(5)": {
        "title": "Revised Return",
        "brief_description": (
            "Allows correction of mistakes in original/belated return "
            "by filing a revised return before end of assessment year."
        ),
        "key_points": [
            "Can be filed before 31st December of assessment year",
            "No limit on number of revisions",
            "Original return is treated as withdrawn",
            "Can revise a belated return as well",
        ],
    },
    "139(8A)": {
        "title": "Updated Return",
        "brief_description": (
            "Allows filing of an updated return within 24 months from end "
            "of relevant assessment year, with additional tax of 25%/50%."
        ),
        "key_points": [
            "Window: within 24 months from end of assessment year",
            "Additional tax: 25% (within 12 months) / 50% (12-24 months)",
            "Cannot file if return results in refund or reduces tax liability",
            "Cannot file if search/survey/prosecution initiated",
            "Only one updated return per assessment year",
        ],
    },
    # ── Reassessment ────────────────────────────────────────────────────────
    "147": {
        "title": "Reopening of Assessment — Income Escaping",
        "brief_description": (
            "Empowers AO to reassess income if there is information suggesting "
            "income has escaped assessment. Requires prior approval."
        ),
        "key_points": [
            "Requires 'information' suggesting income has escaped assessment",
            "Approval: Principal Commissioner / Commissioner",
            "Time limit: 3 years (normal); 10 years if escaped income > Rs. 50 lakh",
            "Mandatory opportunity of hearing before reassessment",
            "New regime effective from AY 2021-22",
        ],
    },
    "148": {
        "title": "Notice Before Reassessment",
        "brief_description": (
            "AO must issue notice u/s 148 before making reassessment. "
            "Prior information and approval is required u/s 148A."
        ),
        "key_points": [
            "Mandatory prerequisite: enquiry u/s 148A and order",
            "Notice must specify reasons for reopening",
            "Assessee can challenge notice before High Court (writ)",
            "Return filed in response treated as u/s 139",
        ],
    },
    "148A": {
        "title": "Enquiry Before Issuing 148 Notice",
        "brief_description": (
            "Requires AO to conduct enquiry, provide opportunity to assessee, "
            "and pass order before issuing notice u/s 148."
        ),
        "key_points": [
            "Step 1: AO provides information to assessee",
            "Step 2: Assessee can reply within prescribed time",
            "Step 3: AO passes order deciding whether to issue 148 notice",
            "Order must be approved by specified authority",
            "Entire process introduced by Finance Act 2021",
        ],
    },
    # ── TDS/TCS ─────────────────────────────────────────────────────────────
    "192": {
        "title": "TDS on Salary",
        "brief_description": (
            "Requires employer to deduct TDS on salary at average rate of "
            "income tax based on estimated total income."
        ),
        "key_points": [
            "Deduct at average rate based on estimated salary for the year",
            "Employee must furnish declaration of other income/deductions",
            "Form 12BA for perquisites",
            "Monthly deposit by 7th of next month",
            "Form 24Q quarterly return",
        ],
    },
    "194A": {
        "title": "TDS on Interest (Other than Securities)",
        "brief_description": (
            "TDS on interest paid by banks, co-operative societies, "
            "and others. Rate 10%, threshold varies."
        ),
        "key_points": [
            "Rate: 10% (20% without PAN)",
            "Bank interest threshold: Rs. 40,000 (Rs. 50,000 for senior citizens)",
            "Other interest: Rs. 5,000 threshold",
            "Form 26Q quarterly return",
            "194A does not cover interest on securities (that is 193)",
        ],
    },
    "194C": {
        "title": "TDS on Contractor Payments",
        "brief_description": (
            "TDS on payments to contractors and sub-contractors for "
            "carrying out any work, including supply of labour."
        ),
        "key_points": [
            "Individual/HUF: 1%, Others: 2%",
            "Single payment threshold: Rs. 30,000",
            "Aggregate annual threshold: Rs. 1,00,000",
            "Includes manufacturing/supplying product per specifications",
            "Transport contractors exempt if PAN furnished and fewer than 10 vehicles",
        ],
    },
    "194H": {
        "title": "TDS on Commission/Brokerage",
        "brief_description": (
            "TDS on commission or brokerage paid, other than insurance "
            "commission which falls under 194D."
        ),
        "key_points": [
            "Rate: 5% (2% for certain cases)",
            "Threshold: Rs. 15,000 per year",
            "Covers: commission, brokerage, consultancy for sales",
            "Does not cover insurance commission (194D)",
        ],
    },
    "194I": {
        "title": "TDS on Rent",
        "brief_description": (
            "TDS on rent paid for land, building, machinery, plant, "
            "equipment, furniture, or fittings."
        ),
        "key_points": [
            "194I(a) — Plant/machinery/equipment: 2%",
            "194I(b) — Land/building/furniture: 10%",
            "Threshold: Rs. 2,40,000 per year",
            "Individual/HUF not liable if no audit in preceding year (194-IB for such cases)",
        ],
    },
    "194J": {
        "title": "TDS on Professional/Technical Services",
        "brief_description": (
            "TDS on fees for professional services, technical services, "
            "royalty, and non-compete fees."
        ),
        "key_points": [
            "Professional services: 10%",
            "Technical services / royalty: 2%",
            "Threshold: Rs. 30,000 per year",
            "Call center services treated as technical (2%)",
            "Directors fees also covered",
        ],
    },
    "194Q": {
        "title": "TDS on Purchase of Goods",
        "brief_description": (
            "TDS on purchase of goods from resident sellers, applicable "
            "to buyers with turnover exceeding Rs. 10 crore."
        ),
        "key_points": [
            "Buyer's turnover must exceed Rs. 10 crore in preceding year",
            "Rate: 0.1% on amount exceeding Rs. 50 lakh",
            "Does not apply if seller is liable for TCS u/s 206C(1H)",
            "194Q overrides 206C(1H) in case of conflict",
        ],
    },
    "206C(1H)": {
        "title": "TCS on Sale of Goods",
        "brief_description": (
            "TCS on sale of goods by sellers with turnover exceeding "
            "Rs. 10 crore, on receipt exceeding Rs. 50 lakh."
        ),
        "key_points": [
            "Seller's turnover must exceed Rs. 10 crore in preceding year",
            "Rate: 0.1% on amount exceeding Rs. 50 lakh",
            "Not applicable if buyer is liable to deduct TDS u/s 194Q",
            "Not applicable on exports or certain specified transactions",
        ],
    },
    # ── Interest & Penalties ────────────────────────────────────────────────
    "234A": {
        "title": "Interest for Delay in Filing Return",
        "brief_description": (
            "Levies interest at 1% per month on unpaid tax for delay "
            "in filing the income tax return."
        ),
        "key_points": [
            "Rate: 1% per month (part of month = full month)",
            "On: self-assessment tax payable (total tax minus advance tax/TDS)",
            "From: due date u/s 139(1) to actual date of filing",
            "Not applicable on refund cases",
        ],
    },
    "234B": {
        "title": "Interest for Default in Advance Tax",
        "brief_description": (
            "Interest at 1% per month if advance tax paid is less than "
            "90% of assessed tax."
        ),
        "key_points": [
            "Rate: 1% per month",
            "Default: advance tax paid < 90% of assessed tax",
            "Period: April to date of determination of income",
            "Senior citizens without business income exempt from advance tax",
            "Computed on assessed tax minus TDS/TCS",
        ],
    },
    "234C": {
        "title": "Interest for Deferment of Advance Tax",
        "brief_description": (
            "Interest at 1% per month for shortfall in quarterly advance "
            "tax instalments."
        ),
        "key_points": [
            "Rate: 1% per month for 3 months per instalment shortfall",
            "Q1 (15 Jun): 15% cumulative, Q2 (15 Sep): 45%, Q3 (15 Dec): 75%, Q4 (15 Mar): 100%",
            "Presumptive (44AD/ADA): single instalment by 15th March",
            "Interest on shortfall at each instalment date",
        ],
    },
    "234F": {
        "title": "Late Filing Fee",
        "brief_description": (
            "Mandatory fee for filing return after the due date prescribed "
            "under Section 139(1)."
        ),
        "key_points": [
            "Rs. 5,000 if return filed after due date",
            "Rs. 1,000 if total income does not exceed Rs. 5,00,000",
            "Nil if total income is below basic exemption limit",
            "In addition to interest u/s 234A",
        ],
    },
    "271B": {
        "title": "Penalty for Failure to Get Tax Audit",
        "brief_description": (
            "Penalty for failure to get accounts audited u/s 44AB. "
            "Equal to 0.5% of total sales/turnover or Rs. 1,50,000 (lower)."
        ),
        "key_points": [
            "Penalty: 0.5% of total sales/turnover/gross receipts",
            "Maximum: Rs. 1,50,000",
            "Lower of the two amounts",
            "Reasonable cause is a valid defence",
            "Order must be passed by Joint Commissioner or above",
        ],
    },
    "276CC": {
        "title": "Prosecution for Failure to File Return",
        "brief_description": (
            "Criminal prosecution for willful failure to file return of income "
            "where tax evaded exceeds prescribed threshold."
        ),
        "key_points": [
            "Imprisonment: 3 months to 2 years (tax evaded < Rs. 25 lakh)",
            "Imprisonment: 6 months to 7 years (tax evaded >= Rs. 25 lakh)",
            "With fine",
            "Reasonable cause is defence",
            "Prosecution at the instance of Commissioner",
        ],
    },
}
