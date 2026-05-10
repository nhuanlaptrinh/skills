---
name: viet-chia-se-app-social
description: Write and save Vietnamese Facebook personal or Zalo posts in the "Anh Lap Trinh" voice about apps, tools, AI products, automation workflows, or software experiences. Use when the user asks to share the benefits of an application in short bullet points with an attractive title, or to tell a personal/third-person usage story with lessons learned for Facebook ca nhan or Zalo.
---

# Viet Chia Se App Social

## Core Rule

Create content in the "Anh Lap Trinh" voice: thang, that, thuc dung, doi thuong, co chut hai huoc, uu tien ung dung vao viec that. Avoid guru/coach tone, exaggerated promises, and glossy marketing copy.

Save each requested post as a `.md` file by default. Only skip saving when the user explicitly asks to preview only.

When working in the training vault, save Facebook personal and Zalo post files to:

```text
C:\Users\nhuan\OneDrive\Ứng dụng\remotely-save\Anhlaptrinh_Vault\01Chuong_Trinh_Dao_Tao\02 - Facebook Cá Nhân
```

If that exact folder is not visible because of environment encoding, use the existing `02 - Facebook Cá Nhân` folder under the current training vault. Use ASCII filenames:

```text
<NN> - <Topic Title> - Facebook.md
<NN> - <Topic Title> - Zalo.md
```

Inspect existing `^\d\d - ` filenames and increment the highest number. Do not overwrite files unless the user asks.

## Workflow

1. Identify the channel: Facebook, Zalo, or both. If unclear, create the Facebook version only.
2. Identify the post type:
   - **Loi ich ung dung**: app/tool benefits, short bullet points, attractive title.
   - **Cau chuyen trai nghiem**: a real or plausible usage story from the author or another person, ending with lessons learned.
3. Extract the raw material: app name, who uses it, problem before using it, what changed after using it, concrete benefits, caveats, and intended reader.
4. If factual details about a current app are uncertain, avoid inventing exact features, prices, dates, or official claims. Ask briefly or frame as "neu dung theo huong..." based on the user's notes.
5. Draft Facebook first. Create a Zalo version only when the user asks for Zalo/both, or the request explicitly says "Facebook hoac Zalo" and the context benefits from a shorter adaptation.
6. Save the file(s), then report the path(s) and the post type created.

## Voice Checklist

- Use `minh` by default; use `tui` when the post needs a more casual, punchy feel.
- Address readers as `anh em`, `cac ong`, `ban`, or `moi nguoi`.
- Keep lines short. Break paragraphs often.
- Prefer concrete work examples over abstract claims.
- Use mild self-deprecation when natural: "hoi do minh cung bi z", "nghe hoi que nhung dung la z".
- End with practical action: try it on one real task first, then improve later.
- Signature ideas: `cu ung dung vao cong viec di, vuong thi go`, `ung dung truoc, toi uu sau`, `xai vao viec that roi moi biet`.
- Facebook may include relevant hashtags at the end, for example: `#anhlaptrinh #ai #automation #python #openclaw #antigravity`
- Zalo should usually avoid hashtags unless the user asks.

## Type 1: Loi Ich Ung Dung

Use this when the user asks to share the benefits of an app/tool, make a short bullet post, review why an app is useful, or create a concise Facebook/Zalo share.

Recommended structure:

```text
[Tieu de thu hut]

[1-2 cau mo dau noi thang vao van de]

- [Loi ich 1: ket qua ro rang trong cong viec]
- [Loi ich 2: tiet kiem thoi gian/cong suc/tien]
- [Loi ich 3: giam loi/giam thao tac lap lai]
- [Loi ich 4: phu hop voi ai/ngu canh nao]
- [Luu y nho: dung cho viec gi thi hop, dung qua da thi de lech]

[Ket: thu tren mot viec nho truoc]

Ps: [mot cau goc nhin doi thuong neu hop]
```

Title patterns:

- `Dung <app> dung cach, no tiet kiem cho minh kha nhieu viec vat`
- `<app> khong than thanh, nhung co may diem rat dang xai`
- `Neu anh em dang lam <cong viec>, thu <app> theo cach nay`
- `May loi ich cua <app> ma minh thay dung duoc vao viec that`

Keep it concise:

- Facebook: usually 120-350 words.
- Zalo: usually 80-220 words.
- Use bullet points for benefits. Each bullet should be one clear idea, not a paragraph disguised as a bullet.

## Type 2: Cau Chuyen Trai Nghiem

Use this when the user asks to tell a story about personal experience, another person's experience, a before/after situation, a mistake while using an app, or lessons learned after applying a tool.

Recommended structure:

```text
[Hook: cau noi/tinh huong that, co chut gay chu y]

[Boi canh: ai dang gap van de gi]

[Va cham: luc dau dung app/tool bi vuong, nghi no vo dung, hoac dung sai cach]

[Cach ap dung: dem vao mot viec that, nho va cu the]

[Ket qua: thay doi nao xay ra, noi vua du, khong phong dai]

[Bai hoc rut ra: 2-4 y ngan, co the bullet neu can]

[Ket: quan diem Anh Lap Trinh, ung dung truoc/toi uu sau]
```

Story angles:

- "Luc dau minh cung nghi app nay binh thuong..."
- "Co ban hoc vien bao app nay khong hieu y em..."
- "Mot nguoi quen dung tool nay sai cach nen thay no vo dung..."
- "Minh thu no vao mot viec nho truoc, ai ngo no go duoc dung cai viec minh dang met..."

Keep it grounded:

- Do not claim dramatic life change unless the user provides that detail.
- Mention both benefit and limitation so the post sounds honest.
- The lesson should come from the story, not be pasted on like a motivational quote.

Length:

- Facebook: usually 300-800 words.
- Zalo: usually 180-450 words.

## Channel Adaptation

Facebook ca nhan:

- More personal context, more voice, can include a short `Ps:`.
- Add hashtags only when they fit the topic.
- Use a title only when the post type is benefit/list style or the user asks for one.

Zalo:

- Shorter, more direct, fewer side stories.
- Keep the same core point but remove extra jokes, long context, and most hashtags.
- Make it easy to copy into chat: short lines, clear conclusion.

## Quality Check

Before saving or returning the post, verify:

- The first line is strong enough to stop scrolling.
- Type 1 has a clear title and bullet benefits.
- Type 2 has a real story arc and lessons learned.
- The post sounds like a person sharing usage experience, not an ad.
- The final idea pushes practical action: try it on one real task, then refine.
