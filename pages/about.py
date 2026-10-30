import streamlit as st

st.title("About Us")
st.caption("Singapore Employment Contract Checker (prototype)")

st.header("Project scope")
st.markdown(
    """
This tool is for employees and job seekers in Singapore who want a quick,
plain-English check of an employment contract against the Employment Act and
Ministry of Manpower (MOM) guidance.

**What it does**
- Reads an uploaded PDF contract and finds 11 common terms.
- Compares each term with official sources and a small set of rules.
- Answers questions about the contract, with citations.

**What it does not do**
- It does not compare contracts, have user accounts, or give legal advice.
- It is not a substitute for professional legal advice. A finding of
  "Needs Attention" is a prompt to look closer, not a finding that a clause
  is illegal.
- Confidentiality and non-compete terms are outside the Employment Act and
  the MOM sources used here. They are always reported as Unable to Assess,
  with a reason that says so.
"""
)

st.header("Objectives")
st.markdown(
    """
- Help people understand what their contract says about pay, hours, leave,
  notice and similar terms.
- Flag terms that appear to fall short of Employment Act rules or MOM guidance.
- Never invent findings or citations: every result is backed by a quote from
  the contract and, where a judgement is made, an official source.
- Be honest about uncertainty by using "Unable to Assess" rather than guessing.
"""
)

st.header("Data sources")
st.markdown(
    """
The knowledge base has 305 passages from the following sources.

- [Employment Act 1968](https://sso.agc.gov.sg/Act/EmA1968) (154 sections,
  converted from a saved Singapore Statutes Online page, because the site
  blocks automated fetching)
- [MOM: Key employment terms](https://www.mom.gov.sg/employment-practices/contract-of-service/key-employment-terms)
- [MOM: Who is covered by the Employment Act](https://www.mom.gov.sg/employment-practices/employment-act/who-is-covered)
- [MOM: Hours of work, overtime and rest days](https://www.mom.gov.sg/employment-practices/hours-of-work-overtime-and-rest-days)
- [MOM: Annual leave eligibility and entitlement](https://www.mom.gov.sg/employment-practices/leave/annual-leave/eligibility-and-entitlement)
- [MOM: Sick leave eligibility and entitlement](https://www.mom.gov.sg/employment-practices/leave/sick-leave/eligibility-and-entitlement)
- [MOM: Paying salary](https://www.mom.gov.sg/employment-practices/salary/paying-salary)
- [MOM: Salary deductions](https://www.mom.gov.sg/employment-practices/salary/salary-deductions)
- [MOM: Termination with notice](https://www.mom.gov.sg/employment-practices/termination-of-employment/termination-with-notice)
- [MOM: Termination without notice](https://www.mom.gov.sg/employment-practices/termination-of-employment/termination-without-notice)

MOM pages were fetched on 2026-10-30. Two MOM hub pages are kept as source
links only and are not indexed:
[Employment practices](https://www.mom.gov.sg/employment-practices) and
[Contract of service](https://www.mom.gov.sg/employment-practices/contract-of-service).
"""
)

st.header("Features")
st.markdown(
    """
- **Contract Health Check:** extracts 11 terms (salary payment, working hours,
  overtime, annual leave, sick leave, probation, notice period, deductions,
  termination, confidentiality, non-compete) and assesses each one.
- **Ask Your Contract:** ask a question and get an answer grounded in the
  contract and official sources, or a refusal when there is no evidence.
- **Three statuses only:** Consistent, Needs Attention, Unable to Assess.
- **Citations:** contract quotes are checked against the contract text, and
  official sources are shown for each finding.
- **Privacy controls:** a button clears the contract and results from the
  session.
"""
)

st.header("Privacy and limits")
st.info(
    "Contract text is sent to OpenAI to be analysed. It is kept for your "
    "session only and can be cleared at any time. This is a prototype, not "
    "production-grade security, and the results are not a substitute for "
    "professional legal advice."
)
