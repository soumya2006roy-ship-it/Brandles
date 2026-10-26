# BRANDLENS

AI-Driven Brand Governance | First Round Solution Proposal

Inkloom Problem Statement - AI • Evaluation-based submission

### OUR CENTRAL IDEA

Shift focus from examining individual posts to safeguarding an entire campaign: a source-based AI reviewer that detects inconsistencies in all channels, elucidates all flags, and retains ultimate decision making power with humans.

BrandLens: "One brand. Every channel. One voice you can trust."

## 1  Introduction and Problem Understanding

### The problem

These days a brand rarely speaks through one person. Employees, agencies, freelancers and AI writing tools all publish on its behalf, across social media, email, websites and ads. Keeping one consistent voice through all of that has become genuinely hard. A discount that changed last week, a claim nobody approved, or a logo from two years ago can slip into public view, and each slip chips away at the trust a company has spent years building.

### Who faces the problem?

The people who feel this most are marketing teams, content creators, brand managers, advertising agencies, compliance and legal reviewers, and any organisation that publishes in more than one place. Creators can break a guideline without realising it, simply because the rule sits in a PDF they have not opened in months. Reviewers then spend their time hunting for mistakes and sending work back for fixes. And without a dependable review step, something misleading or inconsistent can reach the public before anyone notices.

### What breaks today?

- Knowledge about the brand is dispersed among PDFs, old campaign presentations, product sheets, and individuals in the team; creators may be unwittingly using incorrect information.

- While individually the contents can be acceptable, they may contradict each other; for instance, one Instagram post offers 30% discount whereas an email offers 20% discount.

- Manual reviews are time-consuming, inconsistent, and auditable; unfounded claims, misuse of terms, and difficult designs could pass unnoticed.

- AI proofreading can boldly create its own rules or rewrite the author’s message without offering any evidence.

### Our focused problem definition

How should a group of people ensure before launching their campaign that their message is correct and consistent with their brand knowledge before launch, while every decision made is explainable and accountable?

We focus on sourcing based content and campaign consistency, with visual imagery testing. We do not have an automated publishing engine, nor do we believe AI can certify compliance on its own.

### Our understanding and approach

We are proposing an AI-assisted brand governance platform that checks content before it goes out. It reads each submission against the brand’s approved guidelines, verified facts, terminology and visual assets. When something looks inconsistent, it flags it, explains why, and suggests a correction that keeps what the creator was trying to say.

It also gives creators, managers and authorised reviewers one shared place to work together: scan, revise, comment and approve. The AI does the tiring comparison work, and people keep the judgement. Our aim is simple: fewer avoidable slips, faster reviews, and a brand that audiences can keep trusting.

## 2  Proposed Solution

### The idea in plain words

Think about how a campaign actually gets made. A designer finishes a poster on Monday, a copywriter writes the Instagram caption on Tuesday, and someone else drafts the email on Thursday. Each of them is working from a slightly different memory of what the brand guide says. By the time a reviewer sees any of it, they are checking one piece at a time, often late, and often without the original source open beside them. That is how “20% off” quietly turns into “30% off”.

BrandLens sits between the people making the content and the moment it goes live. The brand team gives it the material they already trust: the brand guide, product sheets, approved claims, banned phrases, offer dates and the current logo. BrandLens treats that material as the only truth it is allowed to use. When a creator uploads a caption, an email or a poster, BrandLens compares it with the approved material and with the other pieces in the same campaign, then shows exactly what looks wrong, why, and which document says so.

Everything it does follows three promises:

- It only judges against approved sources. If a statement cannot be backed by something the brand team has signed off, BrandLens says so instead of guessing.

- It shows its working. Every flag carries the exact text, the rule or source behind it, a confidence level and a suggested fix, so the creator sees why instead of just being told no.

- People decide. BrandLens advises. A named reviewer approves, and that decision is stored with the version and the time.

### How BrandLens thinks: two kinds of checks

Not every problem needs AI, and the ones that do should not be left to AI alone. So the work is split in two.

Exact checks. These are plain rules written in code. Is this offer still valid on the planned posting date? Does the discount match the approved number? Is a banned phrase present? Is the logo file the current version? Is the caption within the channel’s length limit? They give the same answer every time and can be explained in a single sentence.

Judgement checks. These are the fuzzier questions. Is “cures acne in 24 hours” supported by anything in the product sheet? Does this caption sound like the brand? Here an AI model helps, but only after the system has fetched the relevant approved passages and handed them over. The model must answer in a fixed structure that includes the source ID and the quoted excerpt. If it cannot point to one, the finding is labelled “Needs human verification” instead of being stated as fact.

Campaign comparison. On top of both, BrandLens pulls the key facts out of each asset (product, price, discount, dates, claim, call to action) into the same simple format and lines them up side by side. Any mismatch becomes a finding, even when every asset looks fine on its own.

Keeping these apart is deliberate. We do not ask AI to do what a few lines of code can do reliably, and we do not let it invent policy where the brand’s own documents are silent.

### Core workflow — from brand knowledge to approval

### Walking through the workflow

Set up. An admin loads the brand’s trusted material once: guidelines, product facts, approved and banned wording, offer dates and logos. BrandLens splits it into searchable passages and keeps every version, so a finding can always point to the exact document that was current at the time. The admin confirms what was extracted before it is used, so a badly read PDF cannot quietly turn into “truth”.

Create. A creator adds a caption, an email, a poster or a whole multi-channel campaign. Text is pulled out of the files and attached to the right brand and campaign, so BrandLens knows which assets belong together.

Analyse. With one click the creator starts a pre-publication scan. Exact rule checks run first, then the evidence-based AI checks, then the comparison across channels.

Explain. Findings come back ranked by severity. Each one shows the highlighted text, what is wrong, the source it relies on, how confident the system is, and a suggested rewrite that stays close to the creator’s own message.

Resolve. The creator can accept a suggestion, edit it, or dismiss it with a short reason. Dismissing is allowed because the creator may know something the documents do not, but the reason is recorded. After each change only the affected content is rechecked, so the process stays fast.

Approve. A reviewer sees the content, the findings and how each was handled, then approves, comments or requests changes. The reviewer’s identity, decision, version and timestamp are saved, which gives the team an audit trail most teams do not have today.

### What the user actually sees

The main screen is a campaign workspace, not a list of files. At the top is a short summary: how many findings there are, how serious they are and how many are still open. Below it, each asset shows the original text beside the suggested text, with the problem phrases highlighted. Click a highlight and the approved passage behind that flag opens alongside it. A separate conflict panel lists contradictions between assets, such as two different discounts, and shows where each one appears. Reviewer comments and an approval timeline sit on the side.

When the system has no approved evidence either way, it says “Insufficient approved evidence” instead of calling the content a breach. Not being able to confirm something is not the same as it being wrong, and we want the tool to be honest about that difference.

### Who does what

- Admin: sets up and maintains the approved sources, manages users, and reviews any guideline updates the system suggests.

- Creator: uploads content, runs scans, and resolves each finding by accepting, editing or dismissing it.

- Reviewer: gives the final decision. Only reviewers can approve a campaign.

### What BrandLens deliberately does not do

- It does not publish anything or connect to posting platforms.

- It does not claim to certify legal or regulatory compliance. It flags and explains; people decide.

- It does not rewrite a creator’s message without showing why.

- It does not change brand rules on its own.

### Skincare scenario

To make this concrete, consider an imaginary skincare brand. Its approved material says two things: the moisturiser “helps to keep the skin hydrated”, and the current offer is 20% off until 30 November. A creator then prepares three assets: an Instagram post that says the product “cures acne in 24 hours”, a promotional email offering 30% off, and a poster that still uses the old logo. When the creator runs the scan, BrandLens raises these flags:

- Unsupported claim. Nothing in the approved product sheet says the product cures acne. The flag shows the sheet’s approved wording next to the creator’s line.

- Conflicting discount. The email offers 30% while the approved offer is 20%.

- Mismatched offer across the campaign. The conflict panel places the assets side by side so the disagreement is visible at once.

- Wrong logo version. The poster uses a logo that has since been replaced.

If the planned send date falls after 30 November, an expiry flag appears as well. The creator fixes the claim and the discount, swaps in the current logo, rescans, and sends the campaign to a reviewer, who approves it. This scenario describes the intended workflow: evidence, consistency, explanation and human sign-off.

## 3  Technical Plan

### Proposed stack and why

### Architecture

Upload → parsing to secure store → approved-source database (document versions + embeddings) → retrieval → hybrid processing (rule-based exact + LLM + referenced passages + cross-channel comparison) → structured results → review by creator → review by approver → audit log and metrics. For multilingual checks: extract structured facts from both English and Hindi text and compare to the same approved facts; flag dubious translation for review. For platform previews: use responsive preview templates and channel rules, not social-media posting APIs.

### Hardest technical challenge: trustworthy, explainable findings

The LLM may create policies or believe that a marketing line is true. This problem is avoided via ensuring that only approved and versioned documents are accessed, that every flagged factual issue must contain the ID number of the source and an excerpt, that structured outputs in JSON are validated, that deterministic evaluations and AI decisions are separated, and that low-confidence results are marked as “Needs human verification.”

### Security and reliability

Personalized workspaces for each private brand; authentication and least-privilege access control; server-side API keys; encryption in transit; allowed file formats and size limits; access-controlled source fetching; limited logging of private data; explicit notification of AI vendor involvement in processing of content. Handling settings of sensitive sources and providers should be verified before production use.

## 4  Originality of Approach

### The differentiator: Campaign Consistency Graph

Most review tools, human or automated, look at one asset at a time: this caption, this email, this poster. Each one can pass on its own and the campaign can still be a mess, because the problem sits between the assets, not inside any one of them.

BrandLens treats the whole campaign as the thing being checked. When assets are uploaded, we pull out the small facts a customer would actually notice: product, price, discount, validity dates, claims, call to action and key terms. Each fact becomes a point in a graph, linked to the asset it came from and to the approved source it should match. Facts of the same kind, for example the discount, are then compared across the entire campaign. When two points that should agree do not, the graph shows a conflict and marks both places.

A simple way to picture it is a shared notebook of everything the campaign says about itself. A single asset cannot tell you that the Instagram post and the email disagree, but the notebook can. And since every fact also points back to an approved source, the same structure answers two questions at once: is the campaign consistent, and is it true?

### What exists today, and where it stops

- Grammar and writing assistants polish the language, but they know nothing about this brand’s approved facts, offers or dates.

- General-purpose chatbots can critique and rewrite, but they may invent rules and rarely show a source you can check.

- Manual review catches subtle problems, but it is slow, differs from reviewer to reviewer, and leaves little record of why something was approved.

BrandLens is built for the gap between these: quick like software, grounded like a careful reviewer, and accountable like a proper process.

### Seven ideas that make the graph useful

Around the core idea sit seven features. Each is small on its own, and each was chosen because it contributes to the first product workflow.

### Why we consider this approach original

We are not claiming to have invented retrieval, rule engines or language models. Those are well-known tools. What we believe is new is the way they are combined and pointed at one specific, everyday problem: keeping a whole campaign truthful and consistent.

- The campaign is the unit of checking. Most tools stop at the single asset. BrandLens looks at what the assets say together, which is where the costly mistakes tend to hide.

- Evidence comes before opinion. Every factual finding has to point to an approved, versioned source. Where no source exists, the system says so openly instead of guessing.

- Learning is proposed, never imposed. When reviewers keep overriding the same flag, BrandLens suggests a guideline update to the admin. It never rewrites the rules by itself.

- The human decision is part of the design. Reviewer identity, decision, version and timestamp are saved, so approval is something the team can trace, not just a message in a chat.

### What we are honest about

The English/Hindi consistency checker and the Instagram/LinkedIn preview are deliberately simple, rule-based prototypes. They help a creator spot likely problems early. They do not promise a perfect translation, and they do not promise that a post will look exactly like this on a real platform. What does not change is the principle underneath: flags backed by evidence, and a person who gives the final approval.

## 5  Feasibility and Scope

### Must-have MVP vs. stretch goals

### Execution plan (adaptable to the event duration)

### Measurable success criteria

- End-to-end workflow: a source file is uploaded by Admin → two assets are created → results are shown → revision → approval by Reviewer.

- Each factual discovery comes with an accurate source citation or is marked as “unverified.”

- The first example identifies an unsupportable statement, inconsistent offer, and expired promotion, whereas the second highlights a discrepancy between English and Hindi offers and channel captions.

- Original content is still retrievable; only authorized reviewers can approve.

### Risks and mitigation

False positives in models → override by reviewer and labelling for confidence/evidence. Bad extraction from PDF → revert to text editing. Short build times → focus on text extraction, two-asset comparison and static preview for platforms; extend languages only when core review functionality is working. API unavailable → deterministic rules remain available and evaluation cases are clearly marked.

## Closing pitch

BrandLens changes the practice of brand governance from a tedious, subjective quality check process to an efficient workflow among the team members. Its key differentiation is the consistency of the campaign based on the approved evidence and not just another grammar correction tool using AI.

## Source table 1

| Step | User action | System response |
| --- | --- | --- |
| 01 · Set up | Upload brand guide, facts, unacceptable phrases, date ranges, and logos by admin. | The extracts, versions, and indexes authorize sources; administrator verifies guidelines. |
| 02 · Create | Caption, e-mail, poster, or multi-channel campaigns are uploaded by the creator. | Extracts text; associates content with a brand and campaign. |
| 03 · Analyse | Creator starts a pre-publication scan. | Runs deterministic rules and evidence-grounded AI checks; compares claims across channels. |
| 04 · Explain | Creator opens findings. | Shows severity, exact text, rule/source citation, confidence and suggested edit. |
| 05 · Resolve | Creator accepts/edits/dismisses a suggestion with a reason. | Saves revision and rechecks affected content. |
| 06 · Approve | Reviewer comments, requests changes or approves. | Records reviewer identity, decision, version and timestamp. |

## Source table 2

| Layer | Technology | Reason |
| --- | --- | --- |
| Frontend | Next.js / React + Tailwind CSS | Responsive dashboard, annotation UI and fast product iteration. |
| Backend | Python FastAPI | Simple API design; strong document and AI tooling. |
| Data & access | PostgreSQL + role-based permissions | Campaigns, versions, comments, approvals and audit history. |
| Document processing | PyMuPDF / python-docx; OCR as needed | Extracts text from PDF/DOCX and selected image assets. |
| AI & retrieval | LLM API + embeddings + pgvector | Retrieves approved evidence before evaluating claims and tone. |
| Visual rules | Pillow / OpenCV | Checks dominant colours and basic image properties; logo matching is a stretch goal. |

## Source table 3

| Innovation | Why it matters | First product workflow |
| --- | --- | --- |
| Cross-channel contradiction detection | Prevents Instagram, email and poster from communicating conflicting offers. | 20% versus 30% discount highlighted across two assets. |
| Evidence Map | Every factual finding links to a specific approved source and version. | Click a claim to see the relevant approved passage. |
| Brand Twin (bounded) | Brand voice profile derived from explicit tone examples and guidelines—not a vague AI personality. | Compare an off-tone caption with a source-aligned rewrite. |
| Expiry-aware checks | Catches promotions or facts that are invalid on planned publication dates. | Expired campaign offer flagged automatically. |
| Feedback-to-guideline loop | Repeated overrides become suggestions for admin review, never automatic policy changes. | Dashboard lists recurring ambiguity and reviewer overrides. |
| Multilingual Brand Consistency Checker | Checks whether key claims, prices and brand terminology retain the same meaning in English and Hindi; avoids relying on literal translation alone. | Show an English offer and a Hindi version with a changed discount; flag the mismatch and display the approved wording. |
| Platform-specific content preview | Previews content in Instagram and LinkedIn-style layouts and checks channel rules such as caption length, tone, CTA and hashtag usage. | Switch between two channel previews; see a formal LinkedIn alternative without changing the approved facts. |

## Source table 4

| Build in the hackathon | Only if time permits |
| --- | --- |
| Brand guideline/fact upload with basic parsing | Advanced logo similarity and typography detection |
| Text input + PDF/DOCX text extraction | Broad image OCR and complex layout understanding |
| Rule-based checks + cited AI suggestions | Advanced language-specific tone evaluation beyond English and Hindi |
| Two-asset campaign contradiction check | Automated integrations with publishing platforms |
| Creator/reviewer roles, comments, status and history | Full enterprise SSO and advanced analytics |
| Findings dashboard, expiry checks and simple platform previews | Adaptive learning from reviewer decisions |

## Source table 5

| Phase | Deliverable / acceptance check |
| --- | --- |
| Foundation · first 25% | Working authentication/roles, brand setup, approved source documents and content submission. |
| Intelligence · next 35% | Structured findings for tone, terminology, claims and offers with source references; two-asset contradiction detection. |
| Workflow · next 25% | Revision history, comments, reviewer decision and re-scan; end-to-end happy path. |
| Polish · final 15% | Labelled evaluation cases, edge-case tests, UX cleanup and final review. |
