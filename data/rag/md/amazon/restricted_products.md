# Amazon Restricted Products & Risky Claims (Fashion, Lifestyle, Accessories)

This document summarizes categories, keywords, and claims that are prohibited or high-risk for Amazon product listings.  
It is structured intentionally for RAG retrieval: clearly separated sections, headings, examples, and rule lists.

---

# 1. General Restricted Products Policy

Amazon prohibits or restricts listing products that:

- Mislead customers,
- Are unsafe,
- Are illegal to sell,
- Require certifications the seller does not have,
- Make unverified health or performance claims.

Fashion, apparel, footwear, and accessories occasionally trigger **policy violations** when sellers:
- Over-claim effects (“increases height”),
- Misrepresent materials (“genuine leather” when synthetic),
- Use medically regulated terms without approval.

---

# 2. Restricted / High-Risk Terms for Fashion & Apparel

The following **phrases or claims** must NOT appear unless the seller has verifiable certification or regulatory approval:

## 2.1 Medical / Health Claims (Not Allowed)
- “Improves posture”
- “Relieves back pain”
- “Cures knee pain”
- “Therapeutic effects”
- “Medical-grade”
- “Boosts blood circulation”
- “Corrects spine alignment”

Examples:
- ❌ “These shoes cure back pain”
- ❌ “Compression socks that guarantee medical-grade circulation improvement”

Safe alternative:
- ✔ “Designed for comfortable walking”  
- ✔ “Soft cushioning for daily use”

---

## 2.2 Performance Guarantees (Not Allowed)
Do NOT guarantee performance outcomes such as:

- “Guaranteed to make you run faster”
- “Doubles stamina”
- “100% sweat-proof”
- “Guaranteed colorfast fabric”
- “Shrink-proof guarantee”
- “Lifetime durability”

Reason: They cannot be objectively proven and expose the account to claims disputes.

---

## 2.3 Misleading Material Claims
The biggest violation area for fashion categories.

Never claim:

- **“100% leather”** if PU/faux leather is used  
- **“Pure silk”** when it's silk blend  
- **“100% cotton”** when it contains polyester blend  
- “Genuine branded fabric” for unbranded materials  
- “Organic cotton” unless certified

Examples:
- ❌ “This wallet is 100% genuine leather” (if not verifiable)
- ❌ “Pure silk saree” (if fabric composition is unclear)

Safe:
- ✔ “Silk blend fabric with zari work”

---

## 2.4 Unverified Sustainability / Eco Claims
Amazon often flags vague greenwashing language:

Do NOT say:
- “Eco-friendly”
- “Environmentally safe”
- “Plant-based material”
- “Biodegradable fabric”

Unless:
- Certifications are provided (e.g., GOTS, OEKO-TEX).

---

# 3. Restricted Imagery & Keywords

## 3.1 Prohibited Imagery
- Logos or branding that does not belong to you (copyright risk)
- Symbols that imply government endorsement
- Fake rating stars (“★★★★★” graphics)
- Fake badges: “Best Seller”, “Amazon’s Choice”, “Top Rated”
- Currency icons or discount icons in images

## 3.2 Prohibited Keywords in Titles, Bullets, Description
- “Best Deal”, “Hot Sale”, “Big Discount”
- “Free Shipping”
- Competitor brand names
- Irrelevant high-traffic search terms (“iPhone”, “Samsung”, “PS5”)

Reason: Amazon enforces strict keyword relevance policies.

---

# 4. Category-Specific Restricted Rules

## 4.1 Sarees, Kurtis, Ethnic Wear
Avoid:
- Misstating fabric origin (e.g., “Banarasi silk” when it’s printed poly-silk)
- Cultural/religious symbols incorrectly used
- Claiming handcrafted work when machine-made

High-risk claims:
- “Pure handloom guaranteed”
- “Real zari work”

Unless proof is provided.

---

## 4.2 Footwear (Running Shoes, Casual Shoes)
Restricted:
- “Shock absorption technology guaranteed”
- “Medical cushioning”
- “Increases height by 3 inches”
- “Therapeutic footwear”

You can safely say:
- “Soft cushioning”
- “Comfortable for long walks”
- “Lightweight mesh for breathability”

---

## 4.3 Accessories (Wallets, Handbags, Socks)
Avoid:
- “100% pure leather” without certification
- “Anti-theft guaranteed”
- “Waterproof” unless lab-tested
- “RFID protection guaranteed” unless documented

Amazon flags unclear functional guarantees unless validated.

---

# 5. Marketplace-Wide Prohibited Areas

These are *universal* and always unsafe:

## 5.1 Competitor Misuse
Do NOT include:
- competitor brand names,
- competitor model numbers,
- comparative claims (“better than XYZ brand”).

## 5.2 Logo, Brand Misuse
Do NOT include:
- images showing logos of well-known brands unless you're authorized,
- text describing association with brands unless licensed.

## 5.3 Fake Claims / Social Proof
Do NOT state:
- “5-star rated”
- “Most reviewed shirt on Amazon”
- “Amazon’s Choice”
- “Award-winning design”

These are automatic policy hits.

---

# 6. High-Risk Words to Use Carefully (Often Cause Suppression)

These words trigger human or automated checks:

- “Guarantee”
- “Warranty”
- “Certified”
- “Premium quality” (allowed but must be contextual)
- “Original branded”
- “Pure”
- “Medicinal”
- “Therapeutic”
- “Shockproof” / “Waterproof”

Use with caution:
- Provide context and factual support, or avoid entirely.

---

# 7. Examples: Safe vs Risky

## 7.1 Running Shoes

**Risky (Do Not Use):**
> “These shoes cure knee pain and guarantee faster running performance.”

**Safe:**
> “Lightweight mesh design with comfortable cushioning for daily runs.”

---

## 7.2 Saree

**Risky:**
> “Pure silk saree with real zari guaranteed.”

**Safe:**
> “Silk blend saree with zari-style border work.”

---

## 7.3 Wallet

**Risky:**
> “100% original leather wallet with lifetime durability.”

**Safe:**
> “Brown wallet with multiple card slots, crafted from leather-textured material.”

---

# 8. What the Copilot Must Do With This

When generating or checking listing content:

1. **Scan title and bullets** for restricted or risky terms.
2. Match content against:
   - medical/health claims,
   - unverified material claims,
   - misleading performance promises,
   - competitor references.
3. Detect prohibited imagery text if user uploads images later.
4. Provide **precise corrections**, for example:
   - “Remove ‘pure silk’ → replace with ‘silk blend’”
   - “Avoid 'guaranteed comfort’ → use ‘comfortable cushioning’”
5. Cite sections retrieved from this document in the compliance output.

This allows:
- clear explanations,
- strong interview defense (“our compliance agent retrieves section 2.3 and flags misrepresentation of material”).

