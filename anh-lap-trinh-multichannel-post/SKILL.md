---
name: anh-lap-trinh-multichannel-post
description: Create and save Vietnamese personal-brand content in the "Anh Lập Trình" voice for Nguyễn Văn Nhuần. Use when the user asks to write, rewrite, polish, summarize, or save a personal Facebook post, especially from raw notes, story drafts, career lessons, AI/automation observations, or đời sống cá nhân; by default create both a Facebook personal post and a shorter Zalo post under 2000 words, and save both as Markdown files in the current working directory when filesystem access is available.
---

# Anh Lập Trình Multichannel Post

## Core Rule

Always create two versions unless the user explicitly asks for only one channel:

1. **Facebook cá nhân**: bản chính, giàu câu chuyện, giữ chất Anh Lập Trình.
2. **Zalo**: bản tóm tắt, gọn hơn, dễ đọc trên Zalo, luôn dưới 2000 từ.

When filesystem access is available, save both versions as `.md` files in the current working directory by default. Only skip saving when the user explicitly asks to only draft, preview, or return the content in chat.

If the `personal-brand-voice` skill is available in the session, use it together with this skill for tone. If not available, follow the style checklist below.

## Workflow

1. Extract the raw idea: chuyện gì xảy ra, nhân vật chính, mâu thuẫn, cảm xúc, bài học.
2. Turn it into the structure: câu nói/tình huống thật -> diễn biến -> nhận ra điều gì -> quan điểm cá nhân -> kết luận ngắn.
3. Draft the Facebook version first.
4. Create the Zalo version by shortening, not by changing the core message.
5. Save both `.md` files in the current working directory by default using paired filenames:
   - Facebook: `<NN> - <Topic Title> - Facebook.md`
   - Zalo: `<NN> - <Topic Title> - Zalo.md`
6. If a current working directory is not available, return both versions in chat and mention that no file was saved.

## Voice Checklist

- Xưng hô mặc định: `mình`, có thể dùng `tui` khi bài cần đời hơn.
- Gọi người đọc: `anh em`, `các ông`, hoặc `bạn`.
- Giọng: thẳng, thật, thực dụng, có chút tự giễu, không làm màu.
- Không viết như coach/guru, không sáo rỗng, không lên lớp đạo lý.
- Ưu tiên câu ngắn, xuống dòng nhiều, mỗi ý 1-3 câu.
- Giữ trải nghiệm cá nhân làm gốc, rồi mới rút ra bài học.
- Có thể dùng `kaka`, `hồi đó`, `xin thưa`, `nghe cũng hơi ngứa`, `vướng đâu gỡ đó` khi hợp ngữ cảnh.
- Với Facebook, thêm hashtag cuối bài nếu phù hợp: `#anhlaptrinh #antigravity #ai #nguyenvannhuan #pyan #python #openclaw #Obsidian #antigravity`
- Với Zalo, không bắt buộc hashtag; chỉ thêm nếu người dùng yêu cầu.

## Facebook Version

Aim for a complete personal post, usually 300-800 words unless the user asks otherwise.

Recommended shape:

```text
[Câu nói hoặc tình huống mở đầu gây chú ý]

[Kể lại bối cảnh thật]

[Mâu thuẫn / điều làm mình tự ái / điều mình nhận ra]

[Phân tích thực tế, không né điểm mình sai]

[Bài học chính]

[Kết lại bằng một câu đúc kết hoặc Ps]

[Hashtag nếu phù hợp]
```

## Zalo Version

Aim for 250-700 words by default, and always keep it under 2000 words.

Make the Zalo version:

- Ngắn hơn Facebook khoảng 30-50%.
- Ít nhánh phụ hơn, tập trung vào một bài học chính.
- Vẫn giữ câu mở đầu mạnh nếu có.
- Không quá nhiều hashtag.
- Dễ đọc khi copy vào Zalo, nhiều dòng ngắn.

## File Saving Conventions

When saving `.md` files:

- Use Vietnamese content inside the file.
- Use ASCII filenames for portability.
- Keep the Facebook and Zalo filenames clearly paired.
- Use the same numeric prefix for both files so they sort next to each other.
- Choose `<NN>` as the next available 2-digit number in the current working directory. Inspect existing filenames matching `^\d\d - ` and increment the highest number.
- Use title case without Vietnamese accents for `<Topic Title>`, with spaces between words, not hyphen slugs.
- Use the exact suffixes `- Facebook.md` and `- Zalo.md`.
- Save in the current working directory, not in the skill folder.
- Do not overwrite existing files unless the user asks for it. If a filename exists, choose a short variant such as `-2` or a more specific slug.

Example:

```text
09 - Cong viec chua toi noi bay dat sang tao - Facebook.md
09 - Cong viec chua toi noi bay dat sang tao - Zalo.md
```
