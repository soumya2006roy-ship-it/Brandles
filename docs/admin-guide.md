# Organisation administrator guide

## Onboard an organisation

1. A user signs up with an email address, password, and account recovery question/answer. They can sign in immediately; email verification is disabled for this hackathon build. The recovery answer is normalized and stored as an Argon2 hash. Users can reset by email or through the recovery question; existing users without a recovery answer can use email reset. They then submit the organisation name, official email, website and contact details.
2. A platform administrator reviews the organisation and records an approve, reject or more-information decision in the Platform Admin verification screen. The submitter cannot decide their own verification.
3. After approval, the organisation administrator can invite admins, creators and reviewers. Invite codes are single-use or usage-limited, expire, and are stored as hashes.
4. Upload brand-approved sources, review parsed passages/page references and effective dates, then approve the source. Build exact rules from a specific approved passage.
5. Create a campaign, add channel assets, review content-based validation and scan findings. Resolve or dismiss high/critical findings with a reason and rescan after changes.
6. Submit the campaign for review. A reviewer other than the submitter approves, rejects or requests changes. Approval binds to the exact asset version and becomes invalid when an asset changes.

## Evidence and prototype status

The source passage, page and version shown in a finding are the evidence trail. Deterministic checks are exact code. LLM judgement is disabled by default; without a configured, consented provider, the UI asks for human verification. Embeddings are lexical-hash vectors rather than semantic embeddings. Hindi checking and platform previews are simple rule-based prototypes. Optional OCR and malware scanning only work when their tools/services are configured. No finding or approval should be represented as legal or regulatory assurance.
