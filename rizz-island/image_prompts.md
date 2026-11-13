# Rizz Island — image prompts

Generated from `cast.json` by `python rizz_island.py --prompts` (re-run after adding a bombshell).

## How to get a consistent cast

1. **Start with each character's `neutral` image.** Regenerate until you love it: it becomes the reference for everything else.
2. **Make the other expressions *from* that neutral image**, using your generator's reference / image-edit feature (for example "edit image", "character reference" or "image prompt") together with the expression prompt. Fresh generations from text alone drift.
3. **`talking` must match `neutral` exactly except the mouth.** Use edit/inpaint mode and change only the mouth; it is swapped with neutral many times a second.
4. Keep the **same canvas shape for all images** (portrait 2:3 or 9:16 works best) and the whole body in frame. White backgrounds are fine: they are removed automatically.
5. Save as `characters/<id>/<expression>.png`, then run `python rizz_island.py --art` and check `review/cast_sheet.jpg`. Anything missing keeps using the placeholder set until `neutral.png` exists.

**Shared style line** (already included at the end of every prompt below):

> Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.

Content guardrails: PG only, original characters, no real people, no logos or brand names.

## Characters

### 🥖 Baguettini Croccantelli — save to `characters/baguettini/`

**neutral.png**

```text
Baguettini Croccantelli, an original cartoon character for a reality show: a tall golden-brown baguette standing upright, diagonal score marks across his crust, a tiny red beret tilted on top, a thin curly black mustache, big expressive eyes, stubby arms and little brown loafers. Signature colour #E8A33D. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Baguettini Croccantelli, an original cartoon character for a reality show: a tall golden-brown baguette standing upright, diagonal score marks across his crust, a tiny red beret tilted on top, a thin curly black mustache, big expressive eyes, stubby arms and little brown loafers. Signature colour #E8A33D. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Baguettini Croccantelli, an original cartoon character for a reality show: a tall golden-brown baguette standing upright, diagonal score marks across his crust, a tiny red beret tilted on top, a thin curly black mustache, big expressive eyes, stubby arms and little brown loafers. Signature colour #E8A33D. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Baguettini Croccantelli, an original cartoon character for a reality show: a tall golden-brown baguette standing upright, diagonal score marks across his crust, a tiny red beret tilted on top, a thin curly black mustache, big expressive eyes, stubby arms and little brown loafers. Signature colour #E8A33D. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Baguettini Croccantelli, an original cartoon character for a reality show: a tall golden-brown baguette standing upright, diagonal score marks across his crust, a tiny red beret tilted on top, a thin curly black mustache, big expressive eyes, stubby arms and little brown loafers. Signature colour #E8A33D. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Baguettini Croccantelli, an original cartoon character for a reality show: a tall golden-brown baguette standing upright, diagonal score marks across his crust, a tiny red beret tilted on top, a thin curly black mustache, big expressive eyes, stubby arms and little brown loafers. Signature colour #E8A33D. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Baguettini Croccantelli: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Baguettini Croccantelli: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Baguettini Croccantelli: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Baguettini Croccantelli: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Baguettini Croccantelli: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🚧 Conetta Arancioni — save to `characters/conetta/`

**neutral.png**

```text
Conetta Arancioni, an original cartoon character for a reality show: a glossy bright-orange traffic cone with two white reflective stripes, huge fluttery eyelashes, glossy pink lips, little arms holding a phone on a selfie stick. Signature colour #FF6A13. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Conetta Arancioni, an original cartoon character for a reality show: a glossy bright-orange traffic cone with two white reflective stripes, huge fluttery eyelashes, glossy pink lips, little arms holding a phone on a selfie stick. Signature colour #FF6A13. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Conetta Arancioni, an original cartoon character for a reality show: a glossy bright-orange traffic cone with two white reflective stripes, huge fluttery eyelashes, glossy pink lips, little arms holding a phone on a selfie stick. Signature colour #FF6A13. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Conetta Arancioni, an original cartoon character for a reality show: a glossy bright-orange traffic cone with two white reflective stripes, huge fluttery eyelashes, glossy pink lips, little arms holding a phone on a selfie stick. Signature colour #FF6A13. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Conetta Arancioni, an original cartoon character for a reality show: a glossy bright-orange traffic cone with two white reflective stripes, huge fluttery eyelashes, glossy pink lips, little arms holding a phone on a selfie stick. Signature colour #FF6A13. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Conetta Arancioni, an original cartoon character for a reality show: a glossy bright-orange traffic cone with two white reflective stripes, huge fluttery eyelashes, glossy pink lips, little arms holding a phone on a selfie stick. Signature colour #FF6A13. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Conetta Arancioni: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Conetta Arancioni: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Conetta Arancioni: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Conetta Arancioni: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Conetta Arancioni: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🐸 Ranocchio Addominalli — save to `characters/ranocchio/`

**neutral.png**

```text
Ranocchio Addominalli, an original cartoon character for a reality show: a bright lime-green frog with ridiculously chiselled six-pack abs, bulging cartoon eyes on top of his head, a red sweatband, tiny gym shorts and a protein shaker in one hand. Signature colour #5BD13B. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Ranocchio Addominalli, an original cartoon character for a reality show: a bright lime-green frog with ridiculously chiselled six-pack abs, bulging cartoon eyes on top of his head, a red sweatband, tiny gym shorts and a protein shaker in one hand. Signature colour #5BD13B. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Ranocchio Addominalli, an original cartoon character for a reality show: a bright lime-green frog with ridiculously chiselled six-pack abs, bulging cartoon eyes on top of his head, a red sweatband, tiny gym shorts and a protein shaker in one hand. Signature colour #5BD13B. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Ranocchio Addominalli, an original cartoon character for a reality show: a bright lime-green frog with ridiculously chiselled six-pack abs, bulging cartoon eyes on top of his head, a red sweatband, tiny gym shorts and a protein shaker in one hand. Signature colour #5BD13B. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Ranocchio Addominalli, an original cartoon character for a reality show: a bright lime-green frog with ridiculously chiselled six-pack abs, bulging cartoon eyes on top of his head, a red sweatband, tiny gym shorts and a protein shaker in one hand. Signature colour #5BD13B. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Ranocchio Addominalli, an original cartoon character for a reality show: a bright lime-green frog with ridiculously chiselled six-pack abs, bulging cartoon eyes on top of his head, a red sweatband, tiny gym shorts and a protein shaker in one hand. Signature colour #5BD13B. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Ranocchio Addominalli: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Ranocchio Addominalli: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Ranocchio Addominalli: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Ranocchio Addominalli: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Ranocchio Addominalli: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🍦 Lumachina Gelatella — save to `characters/lumachina/`

**neutral.png**

```text
Lumachina Gelatella, an original cartoon character for a reality show: a cute pastel-pink snail whose shell is a waffle cone topped with strawberry and pistachio gelato scoops and sprinkles, two little antennae, rosy cheeks and big sparkly eyes. Signature colour #FF9ECF. No arms or hands. Showing a friendly, relaxed expression with the mouth closed in a small smile, relaxed upright posture. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Lumachina Gelatella, an original cartoon character for a reality show: a cute pastel-pink snail whose shell is a waffle cone topped with strawberry and pistachio gelato scoops and sprinkles, two little antennae, rosy cheeks and big sparkly eyes. Signature colour #FF9ECF. No arms or hands. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, posture exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Lumachina Gelatella, an original cartoon character for a reality show: a cute pastel-pink snail whose shell is a waffle cone topped with strawberry and pistachio gelato scoops and sprinkles, two little antennae, rosy cheeks and big sparkly eyes. Signature colour #FF9ECF. No arms or hands. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', body leaning back in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Lumachina Gelatella, an original cartoon character for a reality show: a cute pastel-pink snail whose shell is a waffle cone topped with strawberry and pistachio gelato scoops and sprinkles, two little antennae, rosy cheeks and big sparkly eyes. Signature colour #FF9ECF. No arms or hands. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, body puffed up and tense. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Lumachina Gelatella, an original cartoon character for a reality show: a cute pastel-pink snail whose shell is a waffle cone topped with strawberry and pistachio gelato scoops and sprinkles, two little antennae, rosy cheeks and big sparkly eyes. Signature colour #FF9ECF. No arms or hands. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, head tilted slightly, chin up. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Lumachina Gelatella, an original cartoon character for a reality show: a cute pastel-pink snail whose shell is a waffle cone topped with strawberry and pistachio gelato scoops and sprinkles, two little antennae, rosy cheeks and big sparkly eyes. Signature colour #FF9ECF. No arms or hands. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, swaying dreamily to one side. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Lumachina Gelatella: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Lumachina Gelatella: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Lumachina Gelatella: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Lumachina Gelatella: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Lumachina Gelatella: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🍄 Gnometta Sussurrina — save to `characters/gnometta/`

**neutral.png**

```text
Gnometta Sussurrina, an original cartoon character for a reality show: a small garden gnome grandma with a tall droopy red pointy hat, white curly hair buns, round spectacles, rosy cheeks, a blue dress with a brown belt, holding a tiny notebook and pencil. Signature colour #D62839. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Gnometta Sussurrina, an original cartoon character for a reality show: a small garden gnome grandma with a tall droopy red pointy hat, white curly hair buns, round spectacles, rosy cheeks, a blue dress with a brown belt, holding a tiny notebook and pencil. Signature colour #D62839. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Gnometta Sussurrina, an original cartoon character for a reality show: a small garden gnome grandma with a tall droopy red pointy hat, white curly hair buns, round spectacles, rosy cheeks, a blue dress with a brown belt, holding a tiny notebook and pencil. Signature colour #D62839. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Gnometta Sussurrina, an original cartoon character for a reality show: a small garden gnome grandma with a tall droopy red pointy hat, white curly hair buns, round spectacles, rosy cheeks, a blue dress with a brown belt, holding a tiny notebook and pencil. Signature colour #D62839. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Gnometta Sussurrina, an original cartoon character for a reality show: a small garden gnome grandma with a tall droopy red pointy hat, white curly hair buns, round spectacles, rosy cheeks, a blue dress with a brown belt, holding a tiny notebook and pencil. Signature colour #D62839. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Gnometta Sussurrina, an original cartoon character for a reality show: a small garden gnome grandma with a tall droopy red pointy hat, white curly hair buns, round spectacles, rosy cheeks, a blue dress with a brown belt, holding a tiny notebook and pencil. Signature colour #D62839. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Gnometta Sussurrina: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Gnometta Sussurrina: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Gnometta Sussurrina: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Gnometta Sussurrina: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Gnometta Sussurrina: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🪩 Discotto Brillantelli — save to `characters/discotto/`

**neutral.png**

```text
Discotto Brillantelli, an original cartoon character for a reality show: a round mirrored silver disco ball with sparkling reflections as his whole head and body, big eyes, skinny legs in purple flared trousers and chunky platform shoes. Signature colour #B48CFF. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Discotto Brillantelli, an original cartoon character for a reality show: a round mirrored silver disco ball with sparkling reflections as his whole head and body, big eyes, skinny legs in purple flared trousers and chunky platform shoes. Signature colour #B48CFF. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Discotto Brillantelli, an original cartoon character for a reality show: a round mirrored silver disco ball with sparkling reflections as his whole head and body, big eyes, skinny legs in purple flared trousers and chunky platform shoes. Signature colour #B48CFF. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Discotto Brillantelli, an original cartoon character for a reality show: a round mirrored silver disco ball with sparkling reflections as his whole head and body, big eyes, skinny legs in purple flared trousers and chunky platform shoes. Signature colour #B48CFF. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Discotto Brillantelli, an original cartoon character for a reality show: a round mirrored silver disco ball with sparkling reflections as his whole head and body, big eyes, skinny legs in purple flared trousers and chunky platform shoes. Signature colour #B48CFF. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Discotto Brillantelli, an original cartoon character for a reality show: a round mirrored silver disco ball with sparkling reflections as his whole head and body, big eyes, skinny legs in purple flared trousers and chunky platform shoes. Signature colour #B48CFF. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Discotto Brillantelli: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Discotto Brillantelli: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Discotto Brillantelli: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Discotto Brillantelli: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Discotto Brillantelli: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🌶️ Polpetta Piccantina — save to `characters/polpetta/`

**neutral.png**

```text
Polpetta Piccantina, an original cartoon character for a reality show: a round glossy meatball with a drizzle of tomato sauce on top, a basil leaf like a hair bow, heart-shaped sunglasses pushed up on her head, gold hoop earrings and little sneakers. Signature colour #C1440E. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Polpetta Piccantina, an original cartoon character for a reality show: a round glossy meatball with a drizzle of tomato sauce on top, a basil leaf like a hair bow, heart-shaped sunglasses pushed up on her head, gold hoop earrings and little sneakers. Signature colour #C1440E. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Polpetta Piccantina, an original cartoon character for a reality show: a round glossy meatball with a drizzle of tomato sauce on top, a basil leaf like a hair bow, heart-shaped sunglasses pushed up on her head, gold hoop earrings and little sneakers. Signature colour #C1440E. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Polpetta Piccantina, an original cartoon character for a reality show: a round glossy meatball with a drizzle of tomato sauce on top, a basil leaf like a hair bow, heart-shaped sunglasses pushed up on her head, gold hoop earrings and little sneakers. Signature colour #C1440E. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Polpetta Piccantina, an original cartoon character for a reality show: a round glossy meatball with a drizzle of tomato sauce on top, a basil leaf like a hair bow, heart-shaped sunglasses pushed up on her head, gold hoop earrings and little sneakers. Signature colour #C1440E. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Polpetta Piccantina, an original cartoon character for a reality show: a round glossy meatball with a drizzle of tomato sauce on top, a basil leaf like a hair bow, heart-shaped sunglasses pushed up on her head, gold hoop earrings and little sneakers. Signature colour #C1440E. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Polpetta Piccantina: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Polpetta Piccantina: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Polpetta Piccantina: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Polpetta Piccantina: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Polpetta Piccantina: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

### 🥦 Broccolo Mullettini — save to `characters/broccolo/`

**neutral.png**

```text
Broccolo Mullettini, an original cartoon character for a reality show: a broccoli with a lush floret mullet (business in the front, party in the back), sunglasses pushed up into his florets, a shell necklace, teal board shorts and flip-flops, a little surfboard beside him. Signature colour #17B6A7. Showing a friendly, relaxed expression with the mouth closed in a small smile, arms relaxed at the sides. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**talking.png**

```text
Broccolo Mullettini, an original cartoon character for a reality show: a broccoli with a lush floret mullet (business in the front, party in the back), sunglasses pushed up into his florets, a shell necklace, teal board shorts and flip-flops, a little surfboard beside him. Signature colour #17B6A7. Showing the mouth wide open mid-word as if talking, otherwise the IDENTICAL expression, pose, framing and size as the neutral image, arms relaxed at the sides exactly as in the neutral image. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked.png**

```text
Broccolo Mullettini, an original cartoon character for a reality show: a broccoli with a lush floret mullet (business in the front, party in the back), sunglasses pushed up into his florets, a shell necklace, teal board shorts and flip-flops, a little surfboard beside him. Signature colour #17B6A7. Showing a shocked expression: eyes huge and wide, eyebrows raised high, mouth open in a round 'O', both hands raised up beside the face in surprise. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry.png**

```text
Broccolo Mullettini, an original cartoon character for a reality show: a broccoli with a lush floret mullet (business in the front, party in the back), sunglasses pushed up into his florets, a shell necklace, teal board shorts and flip-flops, a little surfboard beside him. Signature colour #17B6A7. Showing an angry expression: eyebrows angled sharply down, gritted teeth, slightly flushed, fists planted on the hips. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug.png**

```text
Broccolo Mullettini, an original cartoon character for a reality show: a broccoli with a lush floret mullet (business in the front, party in the back), sunglasses pushed up into his florets, a shell necklace, teal board shorts and flip-flops, a little surfboard beside him. Signature colour #17B6A7. Showing a smug expression: half-closed eyes, one eyebrow raised, a sly sideways smirk, arms crossed. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love.png**

```text
Broccolo Mullettini, an original cartoon character for a reality show: a broccoli with a lush floret mullet (business in the front, party in the back), sunglasses pushed up into his florets, a shell necklace, teal board shorts and flip-flops, a little surfboard beside him. Signature colour #17B6A7. Showing in love: big glossy heart-shaped eyes, rosy blushing cheeks, a dreamy smile, hands clasped together beside one cheek. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

<details><summary>Optional extras (blink + mouth-open reactions), for image-edit mode</summary>

**blink.png** (edit `neutral.png`)

```text
Edit this image of Broccolo Mullettini: change only the face to show eyes fully closed (a calm blink), mouth closed in a small smile. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**shocked_talking.png** (edit `shocked.png`)

```text
Edit this image of Broccolo Mullettini: change only the face to show the shocked expression but with the mouth open even wider mid-word. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**angry_talking.png** (edit `angry.png`)

```text
Edit this image of Broccolo Mullettini: change only the face to show the angry expression but shouting, mouth open showing teeth. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**smug_talking.png** (edit `smug.png`)

```text
Edit this image of Broccolo Mullettini: change only the face to show the smug expression but with the mouth half open mid-word, still smirking. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

**in_love_talking.png** (edit `in_love.png`)

```text
Edit this image of Broccolo Mullettini: change only the face to show the in-love expression but with the mouth open mid-word, still heart-eyed. Keep the character, pose, framing, size, colours, lighting and white background exactly the same. Glossy 3D cartoon render, like a frame from a modern animated movie, soft studio lighting, smooth shiny surfaces, bold saturated colours, big expressive cartoon eyes, full body visible from head to toe with space around it, front-facing, centred, plain pure white background, no ground shadow, no text, no watermark, same art style as the rest of the Rizz Island cast.
```

</details>

## Backgrounds

Save to `backgrounds/<location>.png`. Portrait, ideally 1440x2560 or larger (the extra room is used for camera moves). Leave the lower middle open: characters stand there.

**Shared background style line** (included below):

> Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.

**pool.png** — The infinity pool and loungers. Where couples flirt and Discotto falls in.

```text
A sunny luxury villa pool deck: a turquoise infinity pool with sparkling water, pink-and-white striped sun loungers, a giant inflatable flamingo, tall palm trees, white villa walls with pastel accents, bright blue sky with puffy clouds. Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.
```

**firepit.png** — The fire pit at night. Recouplings, dumpings and big announcements happen here.

```text
The villa fire pit at night: a round stone fire pit with glowing orange flames, curved cushioned benches with pink and teal pillows, string lights and tiki torches, a deep purple starry sky, dramatic warm firelight. Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.
```

**lounge.png** — The bright villa lounge with neon signs and bean bags. Group chats and arguments.

```text
A bright villa lounge: pastel pink and teal bean bags, a curved velvet sofa, a glowing neon heart shape on the wall (no words), tropical plants, a shiny floor, colourful cushions. Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.
```

**beach.png** — The private beach with a little pier. Dates and dramatic walks.

```text
A private tropical beach at golden hour: soft pale sand, a small wooden pier, calm turquoise sea, leaning palm trees, a heart-shaped arch of pink flowers, warm sunset sky. Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.
```

**hideout.png** — The hideout: a dim secret room behind the kitchen for whispered plotting.

```text
The hideout: a small, dim secret room behind the villa kitchen, shelves of jars and snacks, one hanging lamp casting a warm pool of light, a lumpy beanbag, cosy teal and purple shadows, a sneaky gossip-den feeling. Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.
```

**confessional.png** — The pink confessional chair. A character alone, spilling the tea to camera.

```text
The reality-show confessional booth: a single plush pink egg-shaped chair in the centre against glossy wallpaper of pink and gold tropical leaves, soft spotlight from the front, symmetrical, front-facing camera. Glossy 3D cartoon render, same art style as a modern animated movie, vertical 9:16 composition, empty scene with no characters and no text or signs with words, eye-level camera, an open clear floor area in the lower middle of the frame where characters will stand, slightly soft focus in the far background, vibrant saturated colours, bright and fun reality-TV villa vibe.
```
