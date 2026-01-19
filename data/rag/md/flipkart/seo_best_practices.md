# Flipkart SEO Best Practices (Fashion, Apparel, Footwear, Accessories)

This document covers search and discoverability best practices for Flipkart fashion categories.
It focuses on how to structure titles, bullets, descriptions, and attributes so listings rank better and convert more.

---

# 1. How Flipkart Search Works (Simplified)

Flipkart search and ranking consider:

1. **Relevance**
   - Match between customer query and:
     - title
     - key attributes
     - category
     - description

2. **Listing Quality Score (LQS)**
   - completeness of attributes
   - image quality and count
   - content clarity
   - historical return/defect rate

3. **Conversion Signals**
   - click-through rate (CTR)
   - add-to-cart rate
   - purchase rate

4. **Seller / Fulfilment Performance**
   - cancellations
   - late dispatch
   - return reasons (“not as described”)

SEO on Flipkart = maximizing relevance **and** listing quality without violating content rules.

---

# 2. Title SEO for Flipkart

A good Flipkart title should be:

- 60–120 characters  
- clear, non-promotional  
- contain 2–3 most important keywords  
- specific to product type and category  

## 2.1 Recommended Structure

Brand + Gender/Target + Product Type + Key Feature/Material + Color


Examples:
- “BrandA Men’s Running Shoes Lightweight Mesh Blue”
- “BrandD Women’s Silk Blend Saree with Zari Border Red”

## 2.2 Do’s
- Place the **main search term** near the beginning  
- Use standard category words:
  - running shoes
  - sports shoes
  - kurta, saree, jeans, hoodie  
- Include material if important for search:
  - cotton, silk blend, mesh, leather-textured  
- Use consistent wording across your catalog

## 2.3 Don’ts
- No ALL CAPS  
- No promotional text (“Best Price”, “Hot Deal”)  
- No competitor brands  
- No repeated keywords (“running shoes running shoes running shoes”)  
- No vague words only (“stylish”, “cool”, “awesome”) without details  

---

# 3. Bullet Points for SEO

Bullets are important for:

- relevance  
- clarity  
- conversion  

Flipkart prefers **4–6 bullets**.

## 3.1 SEO-Oriented Bullet Structure

Each bullet should describe one strong aspect:

- fabric / material  
- fit / comfort  
- use-case  
- care instructions  
- design details  

Example (Running Shoes):

- **MATERIAL:** Breathable mesh upper keeps feet cool during walks and runs.  
- **LIGHTWEIGHT SOLE:** EVA sole for comfortable daily wear.  
- **USE-CASE:** Ideal for jogging, gym workouts, and casual outings.  
- **CLOSURE:** Lace-up design for secure fit.  

Keywords (“running”, “mesh”, “lightweight”) appear naturally.

## 3.2 Things to Avoid

- Listing promises like “guaranteed comfort”, “run faster”  
- Medical claims (“reduces knee pain”)  
- Irrelevant SEO phrases for fashion (e.g., “mobile cover”, “phone case”)  

---

# 4. Product Description for SEO + Conversion

The description can include **secondary keywords** and give context.

## 4.1 Best Practices

- Length: 100–250 words  
- 1–3 short paragraphs  
- Use natural language with:
  - fabric + feel  
  - design + pattern  
  - fit + usage scenario  
  - care instructions  

Example (Saree):

- Mention “wedding”, “festive wear”, “party wear” naturally  
- Mention “silk blend”, “zari border”  
- Avoid claiming “pure silk” unless true

## 4.2 Avoid

- Copy-pasting bullets into description  
- Keyword dumping  
- Fake guarantees or certifications  

---

# 5. Attribute-Driven SEO (Very Important on Flipkart)

Unlike classic keyword SEO, Flipkart relies heavily on **structured attributes**:

- Fabric
- Fit
- Pattern
- Color
- Occasion
- Size
- Sole material
- Upper material
- Number of compartments (bags/wallets)

Listings with correct and complete attributes:

- rank better  
- appear in facet filters (e.g., “cotton”, “formal shirts”, “sports shoes”)  
- have lower return rates (fewer “not as described”)  

The copilot should always treat **attribute completeness** as **equal or more important** than text SEO.

---

# 6. Long-Tail & Semantic Keywords

Examples for common categories:

## 6.1 Running Shoes (Men)
- running shoes for men  
- lightweight sports shoes  
- breathable mesh sneakers  
- walking shoes daily use  

## 6.2 Kurta / Kurti
- cotton kurta for women  
- straight kurti office wear  
- printed kurta daily wear  

## 6.3 Wallets
- wallet for men  
- leather-textured wallet  
- slim card holder wallet  

These should be distributed:

- once in title (where relevant)  
- once or twice in bullets/description naturally  

---

# 7. Common SEO Mistakes on Flipkart

- Repeating the same word 10+ times  
- Using irrelevant categories / attributes  
- Using incorrect attributes just to get traffic  
- Misusing gender or age group  
- Using “combo” or “pack of” incorrectly  
- Over-optimized but misleading titles  

Flipkart penalizes **clickbait** that leads to high return rates.

---

# 8. How the Copilot Should Use This

When the seller asks for Flipkart-focused SEO improvements:

1. Detect marketplace = Flipkart.  
2. Retrieve both:
   - `listing_guidelines.md`
   - `seo_best_practices.md`  

3. Analyze current listing:
   - title  
   - bullets  
   - attributes  

4. Suggest improvements:
   - restructure title as per Flipkart format  
   - add missing attributes/keywords  
   - rephrase bullets to add useful keywords  
   - extend description with natural language, semantic terms  

5. Validate against restricted claims:
   - call `restricted_products.md` to avoid banned phrases.

The output should be:

- SEO-aware  
- compliant  
- category-appropriate  
- specific and actionable  
