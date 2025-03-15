CRM_Document_Collection = """
**Subject Line**: We need some documents to complete your request  
**Preview Text**: Submit them here | Reference ID: {{ReferenceID}}

---

Hi {{FirstName}},

We’re almost there! Please use the button below to share the documents we need to complete your request.

[Submit documents]

Need help?  
Live chat is available 24/7  
[Chat with us Link]

You’ve received this email because you recently interacted with Riyadh Air.  
Not you? [Contact us Link]

To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our [Privacy Policy Link] to learn more.

Riyadh Air | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022‑24 Aviation Services Company. All Rights Reserved.

"""

CRM_Survey_Notification = """
**Subject Line**: Please take a minute to share your feedback  
**Preview Text**: Let us know how we did, {{FirstName}}

---

**Reference Number**: {{ReferenceID}}

Hi {{FirstName}},

You recently spoke to {{AgentFirstName}}.

Please take a moment to let us know how we did, so we can keep improving your experience.

[Share feedback Link]

You’ve received this email because you recently interacted with Riyadh Air.  
Not you? [Contact us Link]

To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our [Privacy Policy Link] to learn more.

Riyadh Air | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022‑24 Aviation Services Company. All Rights Reserved.
"""

Order_Cancellation = """
**Subject Line**: Your order cancellation, {{FirstName}}  
**Preview Text**: Here are the details | Order ID: {{OrderID}}

---

**Order ID**: {{OrderID}}

## Your order’s been canceled

Hi {{FirstName}},

Below is a summary of your canceled order.

Based on the fare rules and terms & conditions, your order qualifies for a refund of {{RefundAmount}}.  
A refund request has automatically been submitted, which can take up to 14 business days to process.

(*OR if no refund is due*)  
Unfortunately, your order does not qualify for a refund under the fare rules and terms & conditions.

[Right Column - Refund Summary or Additional Info]

---

### Full trip canceled
(*Insert multi-city or single itinerary details if needed.*)

**Example Itinerary Display (Update as needed)**  
- {{DepartureAirport}} to {{ArrivalAirport}}  
- {{FlightDate}} at {{FlightTime}}  

Guests (e.g., “7 Guests”)  
- **Adult**: {{GuestName}}  
  - Cabin class: **Business Class**  
  - Seat: {{SeatNumber}}  
  - Personal item: 5 kg • hand baggage: 7 kg • Checked bags: 35 kg  
- (Repeat for all guests)

> **Note**: Each individual bag must weigh less than 32 kg. If you’re flying with a partner airline, some fare benefits may not apply.  
> [See fare details Link] | [More about this flight Link]

---

### Refund Summary
Name: {{Name}}  
Order ID: {{OrderID}}  
Original payment method: {{PaymentMethod}}

**Order summary**  
- Original fare paid: SAR {{OriginalFare}}  
- (List other fees/taxes if relevant)  
- **Total refund**: SAR {{TotalRefund}}

---

Need help?  
Support is available no matter the time or timezone.  
[Chat with us Link]

You’ve received this email because you recently interacted with Riyadh Air.  
Not you? [Contact us Link]

To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our [Privacy Policy Link] to learn more.

Riyadh Air | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022‑24 Aviation Services Company. All Rights Reserved.
"""
