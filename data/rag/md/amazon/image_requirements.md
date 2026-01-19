# Amazon Image Requirements (Fashion, Footwear, Accessories)

These simplified guidelines are inspired by public Amazon image policies.
They are structured so that sections can be retrieved independently by a RAG system.

---

## 1. General Image Principles

- Images must **accurately represent** the product being sold.
- The product should be **clearly visible**, properly lit, and not obscured.
- Images should help customers:
  - understand color, fit, size, texture, and details,
  - make an informed purchase decision without surprises.

Poor images can lead to:

- lower click-through rate (CTR),
- higher return rate,
- and potential listing suppression for repeated violations.

---

## 2. Main (Primary) Image Requirements

The **main image** is the one shown in search results and as the first image on the detail page.

### 2.1 Background & Composition

- Must have a **pure white background**:
  - RGB (255, 255, 255).
- The product should fill **at least 85%** of the image frame.
- The product should be centered and **fully visible**:
  - no part of the product cut off at the edges,
  - no unnecessary empty space.

### 2.2 Allowed Content in Main Image

- The actual product being sold.
- For multi-pack items, it is acceptable to show:
  - the pack as a group (e.g., 3 pairs of socks together),
  - but not additional unrelated items.

### 2.3 Disallowed Content in Main Image

- No additional text overlays:
  - no discount banners,
  - no “Best Seller”, “Top Quality”, or star ratings.
- No logos or watermarks that are not part of the product.
- No lifestyle backgrounds (parks, rooms, models doing activities) for the main image.
- No offensive, adult, or violent content for non-adult categories.

For **fashion and footwear**:

- Mannequins may be allowed in some categories, but:
  - avoid overly stylized or distracting mannequins,
  - ghost mannequin style is generally acceptable.
- Models should not cover crucial details like neckline, print, or footwear design.

---

## 3. Additional (Secondary) Images

Secondary images provide more context and detail.

### 3.1 Recommended Types of Secondary Images

- Front, back, and side views of the product.
- Close-up shots:
  - fabric texture,
  - stitching detail,
  - embroidery/zari work,
  - sole pattern (for shoes).
- Lifestyle images:
  - model wearing the apparel,
  - product being used in a realistic scenario (e.g., running, office, party).
- Size charts or fit guides (especially for apparel and footwear).

### 3.2 Use of Text in Secondary Images

- Limited and relevant text overlays are allowed, for example:
  - “SIZE GUIDE” with a clear measurement chart,
  - “MATERIAL: 100% COTTON”.
- Text must not be misleading or promotional:
  - avoid “BEST QUALITY”, “NO.1 BRAND”, “GUARANTEED FIT”.
- Text should not cover the main product details.

### 3.3 Multi-pack and Variant Images

- For multi-pack items (e.g., socks, t-shirts):
  - show all included items clearly.
- For color variants:
  - show each color clearly and label them if needed.
- Do not show colors or variants that are **not actually available** for purchase.

---

## 4. Resolution & Technical Requirements

### 4.1 Image Size

- Recommended minimum resolution: **1000 x 1000 pixels**.
- This allows:
  - **zoom** functionality on desktop and mobile,
  - better clarity on high-density displays.

### 4.2 File Type & Quality

- Supported formats typically include: `JPEG`, `PNG`.
- Use high-quality images:
  - no pixelation,
  - no visible compression artifacts,
  - no heavy filters that distort actual colors.

### 4.3 Cropping & Aspect Ratio

- Maintain a consistent aspect ratio across images in a listing.
- Avoid:
  - overly tall or wide images where the product looks tiny,
  - awkward cropping that removes important product sections.

---

## 5. Fashion-Specific Notes

### 5.1 Apparel (Shirts, T-Shirts, Kurtis, Hoodies)

- Show the **full garment**:
  - front view,
  - back view,
  - close-up of pattern or print,
  - neckline, collar, sleeve details.
- For fitted garments (e.g., slim fit shirts, jeans):
  - include a model shot, if possible, to show how it sits on the body.
- Avoid:
  - overly styled outfits that hide the actual product,
  - accessories that are not included with the product (unless clearly shown as separate).

### 5.2 Ethnic Wear (Sarees, Kurtis, Dresses)

- Sarees:
  - show full drape and pallu design,
  - close-up of border and pallu work,
  - clarify blouse piece design if included.
- Kurtis and dresses:
  - show overall silhouette,
  - focus on neck design, print, and sleeves.
- Avoid:
  - using images from other brands or designers,
  - over-editing colors that makes product look significantly different.

### 5.3 Footwear (Running Shoes, Casual Shoes)

- Show:
  - side profile,
  - top view,
  - sole pattern,
  - back view.
- Include close-ups of:
  - mesh/upper material,
  - cushioning,
  - lacing or closure type.
- Lifestyle image examples:
  - shoes worn by a runner on a track,
  - person walking, but with focus on the footwear.

---

## 6. Accessories (Wallets, Handbags, Socks)

### 6.1 Wallets

- Show:
  - closed front view,
  - open view with card slots and compartments,
  - close-up of stitching and material texture.
- Avoid filling with branded cards or cash that may confuse customers.

### 6.2 Handbags

- Show:
  - full front view,
  - side view,
  - top view with open zipper showing compartments,
  - model carrying the bag to show size relative to body.
- Ensure the bag looks like it does in real life:
  - do not inflate or stuff excessively to misrepresent shape.

### 6.3 Socks

- For packs (e.g., 3-pack, 5-pack):
  - show all included pairs together,
  - highlight length (ankle, crew) clearly.
- Optional lifestyle shots:
  - socks worn with shoes,
  - close-ups of cushioning or knit pattern.

---

## 7. Disallowed or Risky Image Practices

### 7.1 Misleading Visuals

- Editing colors to make products appear brighter than they really are.
- Using stock images that do not represent the actual product.
- Adding certification logos (e.g., “ISO”, “FDA”) without legitimate certification.

### 7.2 Overly Promotional Designs

- Large discount stickers: “50% OFF”, “SALE”.
- Fake badges like “#1 Best Seller” on the image itself.
- Repeated phrases like “SUPER DEAL” or “HOT OFFER”.

### 7.3 Irrelevant or Distracting Elements

- Including other products not part of the sale.
- Busy or cluttered backgrounds that hide product details.
- Using models or props that shift focus away from the product.

---

## 8. How the Copilot Should Use These Guidelines

When analyzing a listing’s images for Amazon, the copilot should:

1. **Check primary image**:
   - white background,
   - product filling most of the frame,
   - no text overlays or extra graphics.
2. **Check number and variety of secondary images**:
   - angles, close-ups, lifestyle shots.
3. **Check category-specific expectations**:
   - sarees: full drape, border, blouse piece visibility,
   - shoes: sole, side profile, upper material,
   - wallets/handbags: interior compartments.
4. **Flag policy risks**:
   - promotional text,
   - misleading imagery,
   - missing key angles.
5. **Suggest improvements**:
   - add close-up of embroidery,
   - include model shot to show fit,
   - remove text overlay and move content to bullets/description instead.

The goal is to generate **concrete, rule-aware recommendations**, not generic “improve image quality” advice.
