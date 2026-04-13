# Gesture Decision Engine — Product Overview

---

## What is this?

The Gesture Decision Engine is an AI chatbot that helps businesses figure out which Gesture product is right for them — without filling out a form or waiting for a sales call.

You open the app, describe your situation in plain English, and an AI called **Maya** has a short conversation with you. By the end of that conversation, Maya tells you exactly which Gesture product fits your needs, why it fits, what it costs, and how quickly you could get started.

---

## Who is it for?

**Primary audience — potential Gesture customers.** Anyone from a business who wants to explore what Gesture offers. For example:

- A retail brand manager who wants to improve customer loyalty
- An HR leader who wants to reward employees at scale
- A marketing team launching a new product and looking for an experiential campaign
- A sales director who wants to incentivise their team

You do not need to know anything about Gesture before you start. Maya guides the entire conversation.

**Secondary audience — the Gesture sales team.** The Sales Dashboard (accessible from the top bar) shows every active conversation in real time — who is chatting, what their situation is, how interested they seem, and what recommendation Maya gave them. This helps the sales team prioritise which leads to follow up with.

---

## The three views

When you open the app, you'll see three buttons at the top: **Demo**, **Customer View**, and **Sales Dashboard**.

### Demo Mode
This is the default view. The screen is split in two:
- **Left side** — the chat, exactly as a customer would see it
- **Right side** — a live data panel showing what the system is producing behind the scenes (vertical, confidence score, intent level, suggested next questions)

This is the best view for understanding how the whole thing works — you can watch the AI make decisions in real time as the conversation unfolds.

### Customer View
This is what a real customer would see if the chatbot were embedded on Gesture's website. The data panel is completely hidden. Just a clean chat — nothing internal, nothing technical visible to the user.

### Sales Dashboard
The internal tool for the Gesture sales team. Shows a live list of every active chat session. Click any session to see the full picture — what the customer said, what Maya recommended, how likely they are to buy, and a one-line CRM summary.

---

## How a conversation works

Here is exactly what happens from start to finish.

### Step 1 — Maya says hello
The moment you open the app, Maya sends a greeting automatically. You don't need to type anything first.

### Step 2 — You describe your situation
Just type naturally. No specific format needed. For example:

> "We have about 50,000 loyalty members and our redemption rates are terrible."

Maya understands conversational language and picks up as much information as she can from what you write.

### Step 3 — Maya asks focused follow-up questions
Maya needs to understand four things before she can give you a recommendation:

| What Maya is figuring out | Example answers |
|---|---|
| Who are you trying to reach? | Customers, employees, partners |
| How many people? | 500, 5,000, 50,000+ |
| What outcome do you want? | Reduce churn, reward performance, drive engagement |
| How soon do you want to move? | This quarter, next quarter, just exploring |

She figures these out one natural question at a time — not a form. If you give her multiple pieces of information at once she picks them all up and moves on. Most people reach a recommendation in 3–4 messages.

### Step 4 — Maya gives you a recommendation
Once she has enough information, Maya switches from asking questions to giving expert advice. She tells you:

- **Which Gesture product line fits your situation** — Gifting, Loyalty, Brand Engagement, or Enterprise Rewards
- **Which specific product** — for example "Points-to-Gift" for a loyalty programme with low redemption
- **Real pricing** — actual numbers, not "contact us for a quote"
- **How long it takes to get started** — realistic timelines for your situation
- **A result you can expect** — for example "clients like yours have seen redemption rates jump from 20% to 85%"
- **One specific next question** to move you toward getting started

### Step 5 — You can keep asking questions
After the recommendation, the conversation stays open. You can ask anything — about pricing, how integration works, the pilot programme, or anything else. Maya answers based on real Gesture product information.

---

## The preset buttons

At the top of the chat there are four shortcut buttons: **Gifting**, **Loyalty**, **Brand**, and **Enterprise**. Clicking one sends a pre-written opening message that matches a typical customer in that category. It's the fastest way to see a full conversation — you'll get a recommendation in 2–3 messages without having to think of what to type.

---

## The decision panel (Demo Mode only)

In Demo Mode, the right side of the screen updates live as the conversation progresses.

**Vertical badge** — which of Gesture's four product lines fits best. Colour-coded: purple for Gifting, blue for Loyalty, orange for Brand Engagement, green for Enterprise Rewards.

**Recommended campaign** — the specific product Maya picked and a one-line description of what it does.

**Confidence score** — how confident the AI is in its recommendation, shown as a percentage bar that animates when it updates. Higher means the customer's situation mapped very clearly to one vertical.

**Intent level** — how likely this person is to actually buy, based on the language they use and how deep into the conversation they are:
- **Browsing** (grey) — early stage, just looking around
- **Engaged** (amber) — showing real interest, worth a follow-up
- **High Intent** (green) — active buying signals, should be contacted by a sales rep soon

**Suggested next questions** — three clickable buttons with follow-up questions that would move the conversation forward. Click any of them and it sends automatically.

**Intent timeline** — a row of coloured dots at the bottom, one per message, showing how the customer's intent level has shifted across the conversation.

---

## The Sales Dashboard

Built for the Gesture sales team to monitor conversations in real time.

**Session list (left panel)** — each card shows:
- A short session ID
- Which product vertical was recommended
- The intent level (browsing / engaged / high intent)
- How many messages have been exchanged
- How long ago the last message was sent

**Session detail (right panel)** — click any session card to see:
- The customer's pain point in their own words
- Their audience, scale, goal, and timeline
- The recommended vertical and confidence score
- Verbatim quotes pulled from the conversation
- A one-sentence CRM summary ready to paste into Salesforce (e.g. "Enterprise retail brand with 50K loyalty members seeking to fix sub-20% redemption rates — immediate Q1 timeline, high intent")
- The intent score history across all turns
- A **Push to CRM → Salesforce** button — in a production system this would automatically create a lead record and notify the account executive

---

## The four product verticals

Maya always recommends one of four Gesture product areas.

### Gifting
For brands that want to send physical gifts to customers at specific moments — a birthday, a milestone purchase, a thank-you after a big order. The AI helps match the right gift to the right person. Best for D2C brands and subscription companies that want customers to come back.

### Loyalty
For brands that already have a loyalty or points programme but aren't seeing people actually use it. Gesture turns abstract points into physical gifts that people genuinely want. Best for retail brands with low redemption rates or rising churn.

### Brand Engagement
For brands running a campaign, a product launch, or an event who want a tangible physical moment to go alongside it — a premium kit sent to influencers before a launch, or a curated box that drives people to show up at an in-person event. Best for CPG, fashion, and tech companies.

### Enterprise Rewards
For companies that want to recognise and reward their own employees or sales team — automatic gifts sent at work anniversaries, or a reward triggered when a salesperson hits their quota. Best for HR teams and sales organisations at mid-size to large companies.

---

## Other buttons in the app

**New Conversation** — clears the chat and starts fresh. Maya greets you again as if it's the first time. Useful for trying different scenarios back to back.

**View Summary** — appears after Maya has given a recommendation and a few messages have been exchanged. Opens a panel showing the complete structured data from your session — the full profile Maya built, the intent score history, and the CRM note. This is what would be sent automatically to a CRM system in a production version of this tool.

**Refresh** (in Sales Dashboard) — reloads the session list to show the latest activity.
