"""Fields extracted from a commercial real estate loan term sheet."""

# field name -> value type (drives normalization and comparison)
FIELDS = {
    "borrower": "text",
    "property_address": "text",
    "loan_amount": "money",
    "interest_rate": "percent",
    "maturity_date": "date",
    "ltv": "percent",
    "noi": "money",
    "units": "int",
}

DESCRIPTIONS = {
    "borrower": "Legal name of the borrowing entity",
    "property_address": "Full street address of the collateral property",
    "loan_amount": "Principal amount of the senior loan, in USD",
    "interest_rate": "Annual interest rate as a percent (e.g. 6.25)",
    "maturity_date": "Loan maturity date, ISO format YYYY-MM-DD",
    "ltv": "Loan-to-value ratio as a percent (e.g. 65.0)",
    "noi": "In-place annual net operating income, in USD",
    "units": "Number of residential units in the property",
}
