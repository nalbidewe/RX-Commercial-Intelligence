# Version Tracking

This document tracks the version history of the AI Content Gen App

## v0.1 - Alpha Release
- **Release Date:** 2025-03-04
- **Notes:** Initial **alpha release**.

## v0.2 - Chat History, Refinement Tool
- **Release Date:** 2025-03-12
- **Notes:**
    - Introduced **chat history** feature to persist user data.
    - Added the **tools selection drop box**.
    - Introduced **refinement tool** to help tailor existing content to Riyadh Air's tone of voice and lexicon.
    - Added **content type** as part of the questions of the guided flow.
    - Added a **skip option** in the selections to remove redundancy.
    - Switched **font family** to Google's Roboto.

## v0.3 - Lifecycle Content Tool & UI Redesign
- **Release Date:** 2025-03-19
- **Notes:**
    - Added **lifecycle content creation tool** that targets emails, SMS and push notifications.
    - Redesigned the **guided flow** completely in the UI with a custom developed form-like structure, with dynamic sub-questions rendering upon selection of options.

## v0.4 - File Attachments
- **Release Date:** 2025-03-24
- **Notes:**
    - Implemented **file upload/attachment** feature across all tools allowing users to upload supporting documents (PDF or DOCX only) to enhance model context.

## v1.0 - Beta Release with Translation Tool
- **Release Date:** 2025-04-10
- **Notes:**
    - Added **content translation tool** as a standalone feature to translate English content to Modern Standard Arabic.
    - Integrated **translation capabilities** within existing tools for seamless multilingual content creation.
    - Ensured all translations adhere to Riyadh Air's **tone of voice guidelines**.
    - Incorporated approved **Arabic lexicon** to maintain brand consistency across languages.

## v1.1 - Model & Arabic Enhancements
- **Release Date:** 2025-04-16
- **Notes:**
    - Updated OpenAI models to the new **GPT-4.1** for improved performance and accuracy.
    - Implemented **right-to-left (RTL) direction flow** and **right alignment** for Arabic text in the UI.
    - Enhanced **Arabic translation quality** for more natural and contextually accurate outputs.

## v1.2 - RX Policy Tool, Production Rollout & SSO
- **Release Date:** 2025-04-30
- **Notes:**
    - Added **RX Policy Generation Tool** for automated policy content creation.
    - Rolled out the app to **production environment** with **private network integration**; access now requires **Zscaler**.
    - Authentication now fully uses **Microsoft Entra SSO**; **custom username and password** login removed.

## v1.3 - Home Landing Page, Dynamic Textarea & Info Tooltips
- **Release Date:** 2025-05-04
- **Notes:**
    - Added a new **home landing page** to improve user onboarding and navigation.
    - Introduced a **dynamic textarea** that automatically expands as users type, enhancing the content creation experience.
    - Added **info tooltips** to questions, providing users with helpful descriptions and guidance for each question.

## v1.4 - Tone of Voice Selection
- **Release Date:** 2025-05-08
- **Notes:**
    - Introduced **tone of voice selection** allowing users to choose between the default Riyadh Air corporate TOV or a new marketing/sales focused TOV aimed at upselling and enticing sales.