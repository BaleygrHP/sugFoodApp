MESSAGE_SEGMENTATION_PROMPT_TEMPLATE = """You are an expert at splitting customer support messages into optimal segments for progressive streaming.
Your goal: Create natural, complete reading segments that flow smoothly.

⚠️ CRITICAL RULES:
1. **Complete Sentences Only**: NEVER split in the middle of a sentence
2. **Preserve Everything**: Keep all text exactly as written - no rewrites
3. **Group Related Info**: Keep related details together in one segment
4. **Minimum Length**: Each segment should be substantial (2-3+ complete sentences)
5. **No Orphan Text**: Avoid tiny fragments like single titles, prices, or incomplete phrases
6. **Product Details Stay Together**: Product name + description + price + details = ONE segment

📋 WHEN TO SPLIT:
✅ SPLIT when message has clearly SEPARATE topics/sections (>300 chars)
✅ SPLIT before closing questions ("Bạn muốn...?", "Interested?")
✅ SPLIT detailed product lists where EACH item has multiple lines of info

❌ DON'T SPLIT when:
- Message is short (<200 chars total)
- Only 1 product mentioned (keep name + price + details together)
- List items are simple (just names/titles without details)
- Content is a cohesive paragraph

📋 SPLITTING STRATEGIES:

**SHORT MESSAGES** (<200 chars):
→ Keep as 1 segment

**SINGLE PRODUCT** (name + prices + details + image):
→ Group ALL info together in 1 segment:
  ✓ GOOD: "Greeting + product intro.\\n\\n**Product Name**\\n* Price: X\\n* Details: Y\\n[Image](url)"
  ✗ BAD: Splitting into "Greeting" + "Product name" + "Details"

**MULTIPLE PRODUCTS WITH DETAILS** (each has description/price/features):
→ Split strategy:
  • Segment 1: Greeting + intro
  • Segment 2+: Each COMPLETE product (title + ALL details + image)
  • Last segment: Closing question
→ Each product segment MUST include COMPLETE info:
  ✓ "**1. Product A**\\nPrice: $50\\nFeatures: X\\n[Image](url)"
  ✗ "**1. Product A**" (incomplete - missing details!)

**SIMPLE PRODUCT LISTS** (just names, no details):
→ Keep ALL in 1-2 segments maximum:
  ✓ "We have: 1. Product A, 2. Product B, 3. Product C"
  ✗ Don't split into separate segments for each name

**LONG PARAGRAPHS** (>200 chars):
→ Split at natural topic changes or after 2-3 sentences
→ Each segment should be standalone readable

**IMAGES/LINKS**:
→ Images will be auto-extracted from markdown format [text](url), so:
  ✗ AVOID: "You can see the image here: [link]" (incomplete sentence after extraction)
  ✓ BETTER: Keep product name with image: "**Product Name**\\n[Product Name](image_url)"
→ IMPORTANT: Only real image URLs should be in the message (no placeholders or fake URLs)

**MESSAGE STRUCTURE**:
→ Greeting/intro: 1 segment
→ Main content: 1-3 segments (depending on length)
→ Closing question: 1 segment

⏱️ TIMING:
- First segment: delay_ms = 0
- Other segments: delay_ms = 500

📤 OUTPUT (STRICT JSON):
{{"segments": [{{"content": "...", "delay_ms": 0}}, {{"content": "...", "delay_ms": 500}}]}}

💡 EXAMPLES:

Input: "Hi! Product X costs $100. Buy now!"
Output: {{"segments": [{{"content": "Hi! Product X costs $100. Buy now!", "delay_ms": 0}}]}}

Input: "Hello! Product details:\\n**Name**: ABC\\n* Price: $50\\n* Discount: 10%\\n\\nInterested?"
Output: {{"segments": [
  {{"content": "Hello! Product details:\\n**Name**: ABC\\n* Price: $50\\n* Discount: 10%", "delay_ms": 0}},
  {{"content": "Interested?", "delay_ms": 500}}
]}}

Input: "We have 3 options: 1. Basic plan 2. Pro plan 3. Enterprise plan"
Output: {{"segments": [{{"content": "We have 3 options: 1. Basic plan 2. Pro plan 3. Enterprise plan", "delay_ms": 0}}]}}

Input: "Here are our products:\\n\\n**1. Product A** - $50, great quality\\n**2. Product B** - $80, premium\\n\\nWhich one interests you?"
Output: {{"segments": [
  {{"content": "Here are our products:\\n\\n**1. Product A** - $50, great quality\\n**2. Product B** - $80, premium", "delay_ms": 0}},
  {{"content": "Which one interests you?", "delay_ms": 500}}
]}}

Input: "We have 2 detailed products:\\n\\n**1. Product A**\\nPrice: $50\\nFeatures: X, Y, Z\\n\\n**2. Product B**\\nPrice: $80\\nFeatures: A, B, C\\n\\nInterested?"
Output: {{"segments": [
  {{"content": "We have 2 detailed products:", "delay_ms": 0}},
  {{"content": "**1. Product A**\\nPrice: $50\\nFeatures: X, Y, Z", "delay_ms": 500}},
  {{"content": "**2. Product B**\\nPrice: $80\\nFeatures: A, B, C", "delay_ms": 500}},
  {{"content": "Interested?", "delay_ms": 500}}
]}}

📝 NOW SPLIT THIS MESSAGE:
{message}"""
