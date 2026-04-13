import json

PRODUCT_KNOWLEDGE: dict = {
    "company": "Gesture",
    "tagline": "Emotionally intelligent gifting and experiences that connect brands with consumers",

    "what_we_do": "Gesture is a B2B platform that helps brands send curated physical gifts and experiences to consumers, employees, and partners. We handle product curation, logistics, personalization, and measurement — all from one platform. Brands use Gesture to create memorable tangible moments that drive loyalty, recognition, and engagement.",

    "verticals": {
        "gifting": {
            "description": "Curated consumer gifting for personal and occasion-based moments",
            "products": [
                "Gift Finder — AI-powered quiz that matches a gift to the recipient's profile and preferences",
                "Occasion Engine — automated gifting triggered by birthdays, anniversaries, purchase milestones, and custom events",
                "Gift-with-Purchase — add a curated gift at checkout to lift average order value and delight customers"
            ],
            "pricing": "Starts at $15 per gift with no minimum order. Volume pricing available above 500 gifts per month. White-label storefronts included.",
            "ideal_customer": "D2C brands, subscription companies, e-commerce retailers with repeat purchase goals",
            "typical_results": "30% lift in repeat purchase rate, 40% improvement in NPS among gifted customers",
            "time_to_launch": "2 weeks for standard setup, 4 weeks for full CRM integration"
        },
        "loyalty": {
            "description": "Tangible rewards that make loyalty programs feel real and valuable",
            "products": [
                "Points-to-Gift — let loyalty members redeem existing points for curated physical gifts they choose themselves",
                "VIP Early Access Box — exclusive curated product drops for top-tier loyalty members before public release",
                "Re-engagement Kit — personalised gift sent automatically to lapsed customers at the 60 or 90 day mark"
            ],
            "pricing": "Platform fee from $2,000 per month plus per-gift cost. Custom enterprise pricing for programs above 10,000 active members.",
            "ideal_customer": "Retail brands, hospitality groups, subscription boxes, any brand with an existing loyalty or points program",
            "typical_results": "Redemption rates increase from under 20% to over 85%. Churn reduction of 25-40% among gifted segments.",
            "time_to_launch": "3-4 weeks including points system integration"
        },
        "brand_engagement": {
            "description": "Experiential marketing and brand activation through tangible touchpoints",
            "products": [
                "Launch Kit — premium branded physical kit sent to influencers, press, and key customers at a product launch",
                "Pop-up Experience Box — curated kit that drives foot traffic and social sharing around in-person events",
                "Community Appreciation Drop — surprise and delight gift to brand advocates and community members"
            ],
            "pricing": "Project-based pricing typically $10,000 to $50,000 per campaign depending on volume, customization, and fulfillment complexity.",
            "ideal_customer": "CPG brands, fashion and beauty companies, tech companies running product launches or seasonal campaigns",
            "typical_results": "Average 4.2x social amplification on launch kits. 60% increase in event attendance with pre-event experience boxes.",
            "time_to_launch": "4-6 weeks for custom campaign design and production"
        },
        "enterprise_rewards": {
            "description": "Employee recognition and B2B incentive programs that feel personal at scale",
            "products": [
                "Milestone Recognition — curated gift automatically sent at 1yr, 3yr, 5yr employee tenure milestones",
                "Sales Performance Reward — real-time gift triggered by quota attainment via Salesforce or HubSpot integration",
                "Executive Gifting — bespoke, premium gifting for key accounts, board members, and C-suite relationships"
            ],
            "pricing": "Enterprise contracts from $5,000 per month. Per-gift cost varies by tier: $25 to $150 for standard, $150 to $500 for executive tier.",
            "ideal_customer": "Mid-market and enterprise companies with HR or sales teams, professional services firms, financial services",
            "typical_results": "35% improvement in employee retention scores. 28% increase in sales quota attainment when performance gifts are in place.",
            "time_to_launch": "2-3 weeks for standard HR integration, 4-6 weeks for custom Salesforce workflow setup"
        }
    },

    "how_it_works": [
        "Step 1 — Connect: Brand connects their CRM, HRIS, or e-commerce platform, or simply uploads a recipient list as a CSV",
        "Step 2 — Curate: Gesture curates gift options from 500+ vetted products across 40+ categories, all quality-checked and brand-appropriate",
        "Step 3 — Choose: Recipients receive a branded digital card and choose their preferred gift from a white-label storefront",
        "Step 4 — Deliver: Gesture handles all fulfillment, packaging, and delivery to 50+ countries with real-time tracking",
        "Step 5 — Measure: Brand gets a dashboard with open rates, gift selection rates, delivery confirmation, and downstream revenue impact"
    ],

    "integrations": [
        "Salesforce — native connector, trigger gifts from any workflow or opportunity stage",
        "HubSpot — native connector, automate gifts based on deal stage or lifecycle event",
        "Shopify — trigger post-purchase gifts based on order value or product type",
        "Custom API — REST API available for any other platform"
    ],

    "differentiators": [
        "Recipient choice — recipients pick their own gift from a curated selection, which drives 90% selection rates vs 20-30% for pre-selected items",
        "White-label experience — every touchpoint including the storefront, packaging, and delivery note is branded to the client",
        "Global fulfillment — ships to 50+ countries with local warehousing in US, UK, EU, and Australia",
        "Real measurement — tracks not just delivery but gift selection, sentiment, and downstream revenue impact",
        "Zero inventory risk — Gesture holds all inventory, brands pay only for gifts that are selected and shipped"
    ],

    "common_objections": {
        "too_expensive": "We offer tiered pricing starting at $15 per gift with no minimum order for pilots. Most clients see 3-5x ROI within 90 days through improved retention or revenue metrics. We can model your expected ROI before you commit.",
        "already_have_swag": "Unlike generic swag that sits in a drawer, Gesture gifts are chosen by the recipient — which means they actually want them. Our clients see 90% selection rates vs 20-30% for pre-selected items. The ROI difference is significant.",
        "logistics_complexity": "We handle everything end to end — curation, warehousing, fulfillment, packaging, and returns. Your team uploads a CSV or connects your CRM and we handle the rest. Most clients are fully operational within 2-4 weeks.",
        "integration_concerns": "We have native connectors for Salesforce, HubSpot, and Shopify. For everything else we have a REST API. Most integrations take 1-2 weeks. We provide a dedicated integration engineer at no extra cost.",
        "scale_concerns": "We currently serve programs ranging from 50 recipients to 500,000. Our infrastructure is built to scale and per-gift cost decreases significantly at volume."
    },

    "pilot_program": "Gesture offers a 90-day pilot for qualified prospects. Minimum 100 gifts. Full platform access. Dedicated customer success manager. ROI measurement report at the end of the pilot. No long-term commitment required to start."
}


def get_knowledge_as_string() -> str:
    return json.dumps(PRODUCT_KNOWLEDGE, indent=2)
