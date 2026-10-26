export const siteConfig = {
  name: "BrandLens",
  tagline: "One brand. Every channel. One voice you can trust.",
  description:
    "An AI-assisted brand governance workspace that checks campaign content against approved sources and helps people review it together.",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "https://brandlens.example",
  navigation: [
    { label: "The problem", href: "/problem" },
    { label: "How it works", href: "/how-it-works" },
    { label: "Innovations", href: "/features" },
    { label: "Roles", href: "/roles" },
  ],
  pages: {
    problem: {
      title: "When every channel speaks, consistency gets harder",
      description:
        "Brand knowledge is scattered, manual reviews take time, and campaign assets can contradict one another.",
      eyebrow: "The problem",
      intro:
        "A brand rarely speaks through one person. Employees, agencies, freelancers and AI tools all publish on its behalf across social, email, websites and ads.",
      sections: [
        { title: "Knowledge is spread across the team", body: "Guidelines, product sheets, campaign decks and the people who remember them do not always meet at the point of creation. A creator can miss a rule simply because it is buried in a document they have not opened in months." },
        { title: "Assets can disagree with each other", body: "A caption, email and poster may each look acceptable on their own while the offer changes from one channel to another. The mismatch often sits between the pieces, where an asset-by-asset review can miss it." },
        { title: "Review needs evidence and a record", body: "Manual checks are time-consuming and inconsistent. AI proofreading can invent rules or rewrite the author’s message without showing evidence. BrandLens focuses on source-based content and campaign consistency; it does not publish content or certify compliance." },
      ],
      related: ["how-it-works", "campaign-consistency-graph", "security"],
    },
    "how-it-works": {
      title: "From trusted sources to a human decision",
      description:
        "See how BrandLens uses approved material, exact rules, evidence-backed findings and reviewer approval.",
      eyebrow: "How it works",
      intro:
        "BrandLens sits between content creation and publication. It checks campaign assets against trusted brand material and against one another, then gives the team a shared place to resolve findings.",
      sections: [
        { title: "01 · Set up trusted material", body: "An admin adds guidelines, product facts, approved and banned wording, offer dates and logos. Extracted material is checked before use, and versions remain available so findings can refer to the source that was current at the time." },
        { title: "02 · Create a campaign", body: "A creator adds a caption, email, poster or multi-channel campaign. The assets are attached to the same brand and campaign so their facts can be compared together." },
        { title: "03 · Analyse and explain", body: "Exact rule checks run alongside evidence-based judgement checks and cross-channel comparison. Each finding shows severity, highlighted text, its rule or source, confidence and a suggested edit." },
        { title: "04 · Resolve and approve", body: "The creator can accept, edit or dismiss a suggestion with a reason. A named reviewer makes the final decision. Identity, decision, version and timestamp are saved in the audit trail." },
      ],
      related: ["demo", "features", "roles"],
    },
    "campaign-consistency-graph": {
      title: "Check the campaign as a whole",
      description:
        "The Campaign Consistency Graph compares facts across assets and connects them to the approved source they should match.",
      eyebrow: "Campaign Consistency Graph",
      intro:
        "Most review tools look at one caption, email or poster at a time. BrandLens treats the campaign as the unit of checking, because a problem can sit between assets rather than inside a single one.",
      sections: [
        { title: "Facts become connected points", body: "BrandLens pulls out product, price, discount, dates, claims, calls to action and key terms. Each fact connects to the asset it came from and the approved source it should match." },
        { title: "Mismatches become visible", body: "Facts of the same kind are compared across the campaign. When two discounts do not agree, the graph marks both places so the reviewer can see the conflict and its source." },
        { title: "Consistency and evidence together", body: "The same structure helps answer two questions: do the campaign assets agree with each other, and do their claims agree with approved material? Where the material cannot confirm a claim, the system says so." },
      ],
      related: ["problem", "demo", "features"],
    },
    features: {
      title: "Seven ideas that make the graph useful",
      description:
        "Explore the seven BrandLens innovations proposed for the first-round demonstration.",
      eyebrow: "Seven innovations",
      intro:
        "Each idea adds a practical part to campaign review. The first-round demonstration focuses on showing the principle clearly, with prototypes labelled where they are rule-based.",
      sections: [],
      related: ["campaign-consistency-graph", "demo", "roadmap"],
    },
    roles: {
      title: "One shared workflow, clear responsibilities",
      description:
        "Admins maintain approved sources, creators resolve findings and reviewers make the final decision.",
      eyebrow: "Roles",
      intro:
        "BrandLens gives the people who create and review content one shared place to scan, revise, comment and approve.",
      sections: [
        { title: "Admin", body: "Sets up and maintains approved sources, manages users, confirms extracted guidance and reviews proposed guideline updates." },
        { title: "Creator", body: "Uploads content, starts scans and resolves each finding by accepting a suggestion, editing the text or dismissing it with a recorded reason." },
        { title: "Reviewer", body: "Reviews the content and its findings, then approves, comments or requests changes. Only reviewers can approve a campaign." },
      ],
      related: ["how-it-works", "demo", "security"],
    },
    security: {
      title: "Evidence, access and accountability by design",
      description:
        "BrandLens is designed around approved, versioned sources, least-privilege access and a human decision record.",
      eyebrow: "Security & trust",
      intro:
        "A useful review system must make its evidence inspectable and its decisions traceable. The proposal describes a private workspace for each brand, role-based permissions and careful handling of source material.",
      sections: [
        { title: "Evidence and access checks", body: "The API checks organisation membership and role on workspace requests, scopes product queries by organisation, validates private-file downloads and rejects untrusted browser origins. These application controls do not replace deployment-level network security or a production security review." },
        { title: "Files and operational limits", body: "Uploads are type-checked, size-limited and stored under random private object keys. File downloads require membership and a short-lived signed URL. Redis-backed limits protect account, invite, upload and scan endpoints; production deployments must configure Redis and trusted proxy CIDRs." },
        { title: "Audit and retention", body: "Audit records are append-only at the application and database layers and omit invite codes, secrets and document text. Admins can export workspace records and files, configure completed scan and finding history retention, or delete a workspace. Minimal audit history remains after workspace deletion." },
        { title: "AI and prototype boundaries", body: "No live LLM adapter is included, and the mock judgement client does not send workspace content to an external model. Lexical-hash retrieval, Hindi checks and platform previews are prototypes. OCR and malware scanning require optional configuration." },
        { title: "Deployment responsibility", body: "The API applies security headers and requires a strong secret and secure session cookies in production. Operators must provide TLS, private database and storage networking, Redis, secrets management, backups and a trusted proxy configuration. This page is not a security certification." },
      ],
      related: ["how-it-works", "roles", "privacy"],
    },
    roadmap: {
      title: "A focused path from a demo to a broader system",
      description:
        "The proposal prioritises source setup, evidence-backed findings, campaign comparison and reviewer sign-off before stretch goals.",
      eyebrow: "Roadmap & scope",
      intro:
        "The first build prioritises a complete review story over broad integrations: trusted sources, submitted content, explainable findings, revision and approval.",
      sections: [
        { title: "Build in the hackathon", body: "Basic source parsing, text input and PDF/DOCX extraction, rule-based checks with cited suggestions, a two-asset contradiction check, creator/reviewer roles, revision history and simple previews." },
        { title: "Stretch goals", body: "Advanced logo similarity, broad image OCR, deeper multilingual tone evaluation, publishing integrations and adaptive learning from reviewer decisions are listed as work for only if time permits." },
        { title: "Honest prototype boundaries", body: "The English/Hindi consistency checker and Instagram/LinkedIn preview are simple, rule-based prototypes. They do not promise perfect translation or exact platform rendering. The platform does not connect to publishing APIs." },
      ],
      related: ["features", "demo", "security"],
    },
    privacy: {
      title: "Privacy principles for campaign review",
      description:
        "How the BrandLens proposal approaches private brand workspaces, limited logging and AI processing transparency.",
      eyebrow: "Privacy",
      intro:
        "This page describes the data controls implemented in this repository. A deployment operator still configures the infrastructure, TLS, backups, email and storage services.",
      sections: [
        { title: "Workspace data and files", body: "Workspace API reads and writes require membership and role checks, and queries are scoped by organisation. Source and asset files use random private storage keys, allow-listed formats, size limits, membership checks and short-lived signed downloads. Configure HTTPS and private networking in deployment." },
        { title: "AI processing", body: "This repository has no live LLM provider adapter. The mock judgement client returns insufficient evidence, and Brand Twin uses local lexical retrieval over approved sources. External OCR and malware scanning are optional and remain unavailable until configured." },
        { title: "Export and deletion", body: "An organisation Admin can download a JSON export containing workspace records and uploaded originals up to a 100 MB total file limit. Admins can delete workspace content after typing the exact organisation name. The minimal append-only audit history is retained." },
        { title: "Retention", body: "Admins can set completed scan and finding history retention from 30 to 3,650 days. The worker checks the policy hourly and removes expired scan details. Current assets and approved sources remain until the organisation is deleted; append-only audit history is retained." },
        { title: "Audit and cookies", body: "Audit records retain action metadata and omit invite codes, secrets and full document text. Necessary site storage remembers preferences and core features. Optional analytics and marketing tracking stay disabled until consent." },
        { title: "Human review", body: "BrandLens does not autonomously certify legal or regulatory compliance or publish content. Reviewer decisions are stored against the exact asset version. Prototype checks may be inaccurate and require human review." },
      ],
      related: ["security", "cookies", "contact"],
    },
    cookies: {
      title: "Cookie choices",
      description:
        "Manage optional analytics and marketing cookies. Necessary storage keeps your preferences and core site features working.",
      eyebrow: "Cookie preferences",
      intro:
        "BrandLens keeps optional analytics and marketing storage off until you choose to allow it. You can review or change your choice from the footer at any time.",
      sections: [
        { title: "Necessary", body: "Used for core site features and to remember your privacy choice. These cannot be switched off in the preference panel." },
        { title: "Analytics", body: "Optional measurement that helps understand how the site is used. It remains off unless you allow it." },
        { title: "Marketing", body: "Optional marketing measurement. It remains off unless you allow it." },
      ],
      related: ["privacy", "contact"],
    },
    contact: {
      title: "Start a conversation about brand governance",
      description:
        "Get in touch with the BrandLens team to discuss source-based campaign review and the demonstration.",
      eyebrow: "Contact",
      intro:
        "BrandLens is an AI-assisted review concept for teams working across channels. Use the form to share what you would like to discuss.",
      sections: [
        { title: "What the demo covers", body: "The seeded skincare scenario shows an unsupported claim, a 20% versus 30% offer conflict, an old logo finding and a human approval record." },
        { title: "What it does not do", body: "The demo is a local simulation. It does not publish to social platforms, certify compliance or connect to customer accounts." },
      ],
      related: ["demo", "how-it-works", "privacy"],
    },
  },
  innovations: [
    { id: "cross-channel", title: "Cross-channel contradiction detection", summary: "Finds conflicting offers across Instagram, email and poster assets.", demo: "20% versus 30% discount highlighted across two assets.", status: "Core concept" },
    { id: "evidence-map", title: "Evidence Map", summary: "Connects every factual finding to an approved source and version.", demo: "Open a claim to inspect its approved passage.", status: "Core concept" },
    { id: "brand-twin", title: "Brand Twin (bounded)", summary: "A brand voice profile derived from explicit tone examples and guidelines.", demo: "Compare an off-tone caption with a source-aligned rewrite.", status: "Proposed" },
    { id: "expiry-aware", title: "Expiry-aware checks", summary: "Checks whether an offer or fact is valid on the planned publishing date.", demo: "Flag an offer after its approved end date.", status: "Rule-based" },
    { id: "feedback-loop", title: "Feedback-to-guideline loop", summary: "Surfaces repeated overrides for admin review; it never changes policy automatically.", demo: "Review recurring ambiguity and reviewer overrides.", status: "Proposed" },
    { id: "multilingual", title: "Multilingual Brand Consistency Checker", summary: "Checks whether key claims, prices and terms retain the same meaning in English and Hindi.", demo: "A simple rule-based prototype flags a changed offer and displays approved wording.", status: "Rule-based prototype" },
    { id: "platform-simulator", title: "Platform-Specific Content Simulator", summary: "Previews content in Instagram and LinkedIn-style layouts with channel rules.", demo: "A simple rule-based prototype switches previews and suggests a formal LinkedIn alternative.", status: "Rule-based prototype" },
  ],
  footerLinks: [
    { label: "Campaign graph", href: "/campaign-consistency-graph" },
    { label: "Demo", href: "/demo" },
    { label: "Roadmap", href: "/roadmap" },
    { label: "Security", href: "/security" },
    { label: "Privacy", href: "/privacy" },
    { label: "Cookies", href: "/cookies" },
    { label: "Contact", href: "/contact" },
  ],
  faqs: [
    { question: "What does BrandLens check?", answer: "It checks campaign content against approved brand guidelines, verified facts, terminology and visual assets, and compares facts across the campaign’s channels." },
    { question: "What happens when approved evidence is missing?", answer: "BrandLens says “Insufficient approved evidence” or “Needs human verification” instead of calling the content a breach or guessing." },
    { question: "Does BrandLens publish content or certify compliance?", answer: "No. BrandLens flags and explains; people decide. It does not publish content or claim to certify legal or regulatory compliance." },
    { question: "Who can approve a campaign?", answer: "Only a reviewer can approve a campaign. The reviewer’s identity, decision, version and timestamp are saved." },
  ],
} as const;

export type ContentPageSlug = keyof typeof siteConfig.pages;
