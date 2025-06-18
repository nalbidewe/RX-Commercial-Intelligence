CRM_Document_Collection = """
[Subject] We need some documents to complete your request  
[Preview Text] Submit them here | Reference ID: {ReferenceID}

[Column - Main Content]  
Hi {FirstName},  

We’re almost there! Please use the button below to share the documents we need to complete your request.

{{Submit Documents}}

[Column - Support]  
Need help?  
Live chat is available 24/7  
{{Chat with Us}}

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

CRM_Survey_Notification = """
[Subject] Please take a minute to share your feedback  
[Preview Text] Let us know how we did, {FirstName}  

[Column - Main Content]  
**Reference Number**: {ReferenceID}  

Hi {FirstName},  

You recently spoke to {AgentFirstName} from our inflight hospitality team.  

Please take a moment to let us know how we did, so we can keep improving your experience.

{{Share Feedback}}

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

Tax_Invoice = """
[Subject] Your tax invoice for Order {OrderID}  
[Preview Text] Your invoice is attached for reference  

[Column - Main Content]  
Hi {FirstName},  

Your tax invoice for Order ID: {OrderID} is now available.  

[Table Start]  
| Item | Quantity | Unit Price | VAT Rate | VAT | Amount (Excl. VAT) |  
|------|---------|-----------|-----------|-----|-------------------|  
| Flight: {DepartureAirport} to {ArrivalAirport} | {Quantity} | SAR {UnitPrice} | 15% | SAR {VATAmount} | SAR {TotalAmountExclVAT} |  
| Seat Fees | {Quantity} | SAR {SeatFee} | 15% | SAR {SeatVAT} | SAR {SeatAmountExclVAT} |  
| Security Charges | {Quantity} | SAR {SecurityCharge} | 15% | SAR {SecurityVAT} | SAR {SecurityAmountExclVAT} |  
| Airport Building Charge | {Quantity} | SAR {AirportCharge} | 15% | SAR {AirportVAT} | SAR {AirportAmountExclVAT} |  
[Table End]  

**Total Amount (Including VAT):** SAR {TotalAmountInclVAT}  

{{Download PDF Invoice}}  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

Order_Cancellation = """
[Subject] Your order cancellation, {FirstName}  
[Preview Text] Here are the details | Order ID: {OrderID}

[Column - Main Content]  
**Order ID**: {OrderID}  

## Your order has been cancelled  

Hi {FirstName},  

Here’s a summary of your cancelled order.  

[Table Start]  
| Flight Number | Departure | Arrival | Date | Time | Seat |  
|--------------|------------|--------|------|------|------|  
| {FlightNumber} | {DepartureAirport} | {ArrivalAirport} | {FlightDate} | {FlightTime} | {SeatNumber} |  
[Table End]  

### **Refund Information**  

{If Refund Applicable}  
Based on the fare rules and terms & conditions, your order qualifies for a refund of **SAR {RefundAmount}**.  
A refund request has automatically been submitted and may take up to **14 business days** to process.  

{{View Refund Status}}  

{If No Refund}  
Unfortunately, your order does not qualify for a refund under the fare rules and terms & conditions.  

{{Manage Order}}  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

Order_Change_Flight = """
[Subject] Your flight change request is confirmed  
[Preview Text] Here are your updated flight details | Order ID: {OrderID}

[Column - Main Content]  
Hi {FirstName},  

Your flight change request has been successfully processed. Below are your updated details:  

[Table Start]  
| Flight Number | Departure | Arrival | Date | Time |  
|--------------|------------|--------|------|------|  
| {FlightNumber} | {DepartureAirport} | {ArrivalAirport} | {FlightDate} | {FlightTime} |  
[Table End]  

{{View Updated Itinerary}}

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh

"""

Order_Confirmation = """
[Subject] Your booking is confirmed!  
[Preview Text] Your journey with Riyadh Air starts soon | Order ID: {OrderID}

[Column - Main Content]  
Hi {FirstName},  

Thank you for booking with Riyadh Air! Your reservation is confirmed.  

[Table Start]  
| Flight Number | Departure | Arrival | Date | Time | Seat |  
|--------------|------------|--------|------|------|------|  
| {FlightNumber} | {DepartureAirport} | {ArrivalAirport} | {FlightDate} | {FlightTime} | {SeatNumber} |  
[Table End]  

{{View Your Booking}}

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

Order_Change_Non_Flight = """
[Subject] Your order’s been updated, {FirstName}  
[Preview Text] Here’s a confirmation of the details  

[Column - Main Content]  
**Order ID**: {OrderID}  

## Your changes have been confirmed  

Hi {FirstName},  

Your order change request has been successfully processed. Below are your updated details:  

[Table Start]  
| Flight Number | Route | Date | Time | Passenger Name |  
|--------------|---------|------|------|---------------|  
| {FlightNumber} | {Route} | {FlightDate} | {FlightTime} | {PassengerName} |  
[Table End]  

### **Add-ons**  
[Table Start]  
| Item | Quantity | Paid (SAR) |  
|------|---------|------------|  
| Extra Baggage (15 kg) | {BaggageQty} | {BaggageFee} |  
| Premium Window Seat | {SeatQty} | {SeatFee} |  
| Meal Preference | {MealType} | {MealFee} |  
[Table End]  

**Total Amount Paid (Including Taxes):** SAR {TotalPaid}  

{{Manage Order}}  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.

"""

Refund_Request_Processed = """
[Subject] Your refund has been processed  
[Preview Text] Please expect up to 14 business days for payment to arrive in your account  

[Column - Main Content]  
**Order ID**: {OrderID}  

## Your refund is on the way  

Hi {FirstName},  

Your refund has been processed and will be returned to your original payment method.  
This could take up to **14 business days**.  

If you need to contact your bank about this refund, use the Acquirer Reference Number (ARN): **{ARNNumber}**.  

[Column - Support]  
Need help?  
Live chat is available 24/7  
{{Chat with Us}}  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.

"""

OTP = """
[Subject] Your OTP has arrived  
[Preview Text] This one-time password will expire in {OTPTTL} minutes  

[Column - Main Content]  
Hi {FirstName},  

Here’s your one-time password (OTP):  

**{OTPCode}**  

It will expire in {OTPTTL} minutes and can only be used once.  

If this wasn’t you, please {{Contact Us}}.  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

Payment_Link_No_Link = """
[Subject] Let’s complete your order, {FirstName}  
[Preview Text] Your payment link will be valid for 20 minutes  

[Column - Main Content]  
**Order ID**: {OrderID}  

Hi {FirstName},  

Thanks for choosing Riyadh Air. Use the **Pay Now** button to complete your order.

We’ll hold your order for **20 minutes**. This link can only be used once and should **not** be shared with anyone else.

{{Pay Now}}  

[Column - Support]  
Need help?  
Live chat is available 24/7  
{{Chat with Us}}  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

CRM_CASE_OPEN = """
[Subject] You recently contacted us, {FirstName}  
[Preview Text] Your reference ID is {ReferenceID}

[Column - Main Content]  
**Reference ID**: {ReferenceID}  

Hi {FirstName},  

Thank you for reaching out. A member of our team will be in touch with you as soon as possible.  

If you need to contact us, please use the reference ID at the top of this email.  

[Column - Support]  
Need help?  
Live chat is available 24/7  
{{Chat with Us}}  

[Footer]  
[Column - Left]  
To avoid missing important updates, add us to your contacts.  
Your privacy is our priority. Read our {{Privacy Policy}} to learn more.  

[Column - Right]  
**Riyadh Air** | General Authority of Civil Aviation Building 4075, P.O. Box 8427, Riyadh 13443, Kingdom of Saudi Arabia  
© 2022-24 Aviation Services Company. All Rights Reserved.
"""

