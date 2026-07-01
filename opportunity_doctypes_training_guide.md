# Opportunity DocTypes Training Guide

> Based on the active configuration on `testsite.local` as of 2026-07-01.

There are five main Opportunity DocTypes:

| Business stream | DocType | Approx. fields | Main distinction |
|---|---|---:|---|
| Dedicated | `Opportunity` | 140 | Full connectivity and service requirements |
| S&M | `Opportunity SM` | 113 | Small/Medium project-scale routing |
| Hotels | `Opportunity Hotels` | 138 | Hotel-specific sales roles and connectivity fields |
| ISP | `Opportunity ISP` | 136 | Almost identical fields to Hotels, with ISP type and links |
| Tenders | `Opportunity Tenders` | 110 | RFP and CXO team management |

`Hotspot` is also opportunity-like, but it is a separate operational process rather than another version of the standard Opportunity form.

## 1. Fields Shared by the Five Opportunity DocTypes

All five contain the standard commercial CRM information:

- Series, Opportunity From, Party and Status
- Opportunity Type, Source, Owner and Sales Stage
- Expected closing date and probability
- Customer organization, industry, market segment and territory
- Contact and address information
- Currency, exchange rate and opportunity amount
- Items, quantities, rates and totals
- Scope, deliverables, survey information and audit log
- Lost reasons and competitors
- Notes and activities
- Links to Quotation, Supplier Quotation, RFQ and Material Request

They all use the naming series `CRM-OPP-.YYYY.-`, so the document number alone does not identify the business stream.

None of them is submittable. Workflow approval, rather than document submission, controls their lifecycle.

## 2. Important Field Differences

### Dedicated — `Opportunity`

Dedicated has the broadest technical and service information:

- Contract start and end dates
- Working days/hours
- Enterprise/Individual
- Service active
- Speed, public IP and VLAN
- Main site
- AP and SM management IPs
- Link, equipment and fiber details
- P2P/P2MP details
- SSID, username and password
- Dedicated survey template

Its effective Opportunity Type default is `Dedicated`.

Important mandatory information includes:

- Standard party and company fields
- Surveyor Manager
- Request
- Expected Closing, Industry, Market Segment, City and Territory

### S&M — `Opportunity SM`

Its defining field is:

- **Project Scale:** `Small` or `Medium`

It does not contain the full connectivity, contract and service-activation field set found in Dedicated, Hotels and ISP.

It still has:

- Request and Requirements
- Scope and Deliverables
- QA Report
- Surveyor Manager
- Survey and item sections

Project Scale is mandatory because it determines which Scope and QA team handles the document.

Its Opportunity Type default is `SM`, while downstream Quotation documents identify the source as `S&M`.

### Hotels — `Opportunity Hotels`

Hotels is effectively a copy of the Dedicated technical data structure:

- Contract dates and working hours
- Service status and speed
- Public IP and VLAN
- Main site and management IPs
- Equipment and link information
- SSID and credentials

Its data fields are practically identical to ISP. The main differences are:

- Opportunity Type is `Hotels`
- Workflow roles are `Hotels RG`, `Hotels Scope`, `Hotels QA`, etc.
- Downstream documents use Hotels-specific link fields

Request and Surveyor Manager are mandatory.

### ISP — `Opportunity ISP`

ISP and Hotels have the same meaningful business fields. Their differences are mainly configuration:

- Opportunity Type is `ISP`
- ISP has its own source-link fields on downstream documents
- The workflow currently uses the `Dedicated ...` workflow roles
- ISP has built-in change tracking enabled; the other main Opportunity DocTypes do not

Unlike Dedicated, S&M, Hotels and Tenders, the site does not currently make Expected Closing, Industry, Market Segment, City and Territory mandatory through Property Setters.

### Tenders — `Opportunity Tenders`

Tenders removes much of the normal requirements-gathering structure and adds:

- RFP Document — mandatory
- CXO Team
- CXO Team Leader

It does not have:

- Request and Requirements
- Surveyor Manager
- QA Report
- Contract, connectivity and service-activation fields

Its Opportunity Type default is `Tenders`.

## 3. Workflow Comparison

### Dedicated

```text
Requirements Gathering
  → Scoping
  → Qualifying
  → Surveying
  → Surveyed
  → Approved
  → Accepted
```

Special paths:

- Scoping → `Converted` using **Convert to S&M**
- Qualifying or Surveyed → `Rejected`
- Converted updates Status to `Converted`

Roles:

- Dedicated RG
- Dedicated Scope
- Dedicated QA
- Dedicated Surveyor
- Dedicated TA
- Dedicated Sales

### S&M

```text
Requirements Gathering
  → Scoping
  → Qualifying
  → Surveying
  → Surveyed
  → Approved
  → Accepted
```

The route depends on Project Scale:

- Small → `S&M Scope Small` and `S&M QA Small`
- Medium → `S&M Scope Medium` and `S&M QA Medium`

This is the only Opportunity workflow with scale-dependent responsibility.

### Hotels

```text
Requirements Gathering
  → Scoping
  → Qualifying
  → Surveying
  → Surveyed
  → Approved
  → Accepted
```

Important difference:

- Rejecting during Qualifying produces `Rejected`
- Rejecting after Surveyed sends the document back to `Surveying`, rather than closing it as rejected

This behaves like technical rework.

### ISP

```text
Requirements Gathering
  → Scoping
  → Qualifying
  → Surveying
  → Surveyed
  → Approved
  → Accepted
```

ISP offers more rejection points than Dedicated:

- Requirements Gathering → Rejected
- Scoping → Rejected or Converted to S&M
- Qualifying → Rejected
- Surveying → Rejected
- Surveyed → Rejected

It uses Dedicated workflow roles despite being a separate ISP DocType.

### Tenders

```text
Scoping
  → Surveying
  → Surveyed
  → Approved
  → Accepted
```

There is no Requirements Gathering or Qualifying stage.

Scoping completes when the scope description, CXO Team and CXO Team Leader are populated. Rejection is available after the survey.

## 4. Workflow Side Effects

For all five main Opportunity DocTypes:

- Moving to `Accepted` automatically creates a Quotation.
- At least one item must exist before the Quote action can complete.
- Status becomes `Quotation` after quotation creation.
- Moving to `Rejected` sets Status to `Lost`.
- Workflow changes and deliverable changes are recorded in the Audit Log.
- Quotations, RFQs, Supplier Quotations and Material Requests receive a link back to the correct Opportunity DocType.
- Customer opportunities can create Issues.
- Prospect-based opportunities can create Customers.
- Warehouse selection retrieves item availability and valuation rates.

The shared automation is implemented in `ion_crm_sales/ion_crm_sales/doc_events/opportunity_handlers.py`.

## 5. Workflow-Driven Form Visibility

The forms progressively reveal their sections:

- Requirements Gathering: requirements are visible; scope is hidden
- Scoping: scope becomes available
- Qualifying: QA becomes available
- Surveying: technical survey tools become available
- Approved/Accepted: item and quotation-related work becomes relevant

Some client scripts also automatically change workflow state when required data is completed. For example:

- Requirements populated → Scoping
- Scope description and deliverables populated → Qualifying
- Tenders scope and CXO information populated → Surveying

Therefore, saving the document can sometimes advance its state even without selecting a workflow action.

## 6. Permissions

The business-stream sales roles generally have full document permissions:

- Dedicated Sales
- S&M Sales
- Hotels Sales
- ISP Sales
- Tenders Sales
- Sales Manager

Workflow states then limit editing to the department responsible for that stage, such as RG, Scope, QA, Surveyor or Technical Approval.

Surveyors generally receive read/write access but not creation or deletion rights.

## 7. Hotspot: Separate Process

`Hotspot` should be trained separately. It focuses on:

- Hotspot location and type
- Commercial proposal or customer-request origin
- Reseller and contact details
- Location and survey
- Materials and stock entry
- Installation
- Network setup, SSID, VLAN, access points and credentials
- Assets and maintenance history

Its workflow is:

```text
Qualifying
  → Proposed
  → Surveying
  → Surveyed
  → Requirements Gathering
  → Setup
  → Active
  → Closed
```

It also has commercial rejection, technical rejection and revision paths.

## 8. Training Summary

- Use **Dedicated** for normal enterprise connectivity projects.
- Use **S&M** when project handling depends on Small or Medium scale.
- Use **Hotels** for hotel-sector opportunities.
- Use **ISP** for ISP-sector opportunities.
- Use **Tenders** when the process begins with an RFP and CXO stakeholders.
- Use **Hotspot** for hotspot installation and ongoing operational management.

## Configuration Caveat

The client scripts contain legacy logic that changes an Opportunity Type of `Sales` to `Dedicated`, including in some specialized forms. Correct defaults currently prevent this in most new records, but legacy records should be checked.
