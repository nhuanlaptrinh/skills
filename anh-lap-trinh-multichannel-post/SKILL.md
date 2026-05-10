---
name: anh-lap-trinh-multichannel-post
description: Create and save Vietnamese personal-brand content in the "Anh Lập Trình" voice for Nguyễn Văn Nhuần. Use when the user asks to write, rewrite, polish, summarize, or save a personal Facebook post, especially from raw notes, story drafts, career lessons, AI/automation observations, or đời sống cá nhân; by default save every post as Markdown. Facebook personal posts must be saved to the dedicated "02 - Facebook Cá Nhân" folder when working in the training vault. For short posts under 2000 words, create and save only one Facebook version unless the user asks for Zalo.
---

# Anh Lập Trình Multichannel Post

## Core Rule

Always save each requested post as a `.md` file by default. Only skip saving when the user explicitly asks to only draft, preview, or return the content in chat.

For **Facebook cá nhân** posts, save to this dedicated folder by default when available:

```text
C:\Users\nhuan\OneDrive\Ứng dụng\remotely-save\Anhlaptrinh_Vault\01Chuong_Trinh_Dao_Tao\02 - Facebook Cá Nhân
```

If that folder is not available in the current environment, save to the most relevant/current working directory and mention the fallback.

For short posts under 2000 words, create and save only one **Facebook cá nhân** version by default.

Create a separate **Zalo** version only when:
- The user explicitly asks for Zalo/multichannel content.
- The Facebook post is long enough that a shorter Zalo adaptation is useful.
- The user asks for both Facebook and Zalo.

If the `personal-brand-voice` skill is available in the session, use it together with this skill for tone. If not available, follow the style checklist below.

## Workflow

1. Extract the raw idea: chuyện gì xảy ra, nhân vật chính, mâu thuẫn, cảm xúc, bài học.
2. Turn it into the structure: câu nói/tình huống thật -> diễn biến -> nhận ra điều gì -> quan điểm cá nhân -> kết luận ngắn.
3. Draft the Facebook version first.
4. If the post is under 2000 words and the user did not ask for Zalo, do not create a Zalo version.
5. If a Zalo version is needed, create it by shortening, not by changing the core message.
6. Save the Facebook `.md` file in the dedicated Facebook personal folder by default:
   - Facebook: `<NN> - <Topic Title> - Facebook.md`
7. If a Zalo version is needed, save both `.md` files using paired filenames:
   - Facebook: `<NN> - <Topic Title> - Facebook.md`
   - Zalo: `<NN> - <Topic Title> - Zalo.md`
8. If a current working directory is not available, return the version(s) in chat and mention that no file was saved.

## Voice Checklist

- Xưng hô mặc định: `mình`, có thể dùng `tui` khi bài cần đời hơn.
- Với Facebook cá nhân, tránh xưng `tôi` trừ khi người dùng yêu cầu giọng nghiêm túc/trang trọng; ưu tiên đổi `tôi` thành `mình` để bài thân thiết hơn.
- Gọi người đọc: `anh em`, `các ông`, hoặc `bạn`.
- Giọng: thẳng, thật, thực dụng, có chút tự giễu, không làm màu.
- Không viết như coach/guru, không sáo rỗng, không lên lớp đạo lý.
- Ưu tiên câu ngắn, xuống dòng nhiều, mỗi ý 1-3 câu.
- Giữ trải nghiệm cá nhân làm gốc, rồi mới rút ra bài học.
- Có thể dùng `kaka`, `hồi đó`, `xin thưa`, `nghe cũng hơi ngứa`, `vướng đâu gỡ đó` khi hợp ngữ cảnh.
- Với mọi content Facebook/Zalo, luôn thêm đúng bộ hashtag cuối bài: `#anhlaptrinh #aiautomation #nguyenvannhuan #obsidian #antigravity #ai #python #openclaw #claude #codex`
- Không dùng biến thể khác của bộ hashtag mặc định, trừ khi người dùng yêu cầu rõ.

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

[Bộ hashtag mặc định]
```

## Zalo Version

Aim for 250-700 words by default, and always keep it under 2000 words.

Make the Zalo version:

- Ngắn hơn Facebook khoảng 30-50%.
- Ít nhánh phụ hơn, tập trung vào một bài học chính.
- Vẫn giữ câu mở đầu mạnh nếu có.
- Luôn giữ bộ hashtag mặc định ở cuối bài: `#anhlaptrinh #aiautomation #nguyenvannhuan #obsidian #antigravity #ai #python #openclaw #claude #codex`
- Dễ đọc khi copy vào Zalo, nhiều dòng ngắn.

## File Saving Conventions

When saving `.md` files:

- Use Vietnamese content inside the file.
- Use ASCII filenames for portability.
- For short posts under 2000 words, save only the Facebook file unless the user asks for Zalo.
- When saving both Facebook and Zalo, keep the filenames clearly paired.
- Use the same numeric prefix for paired files so they sort next to each other.
- For Facebook personal posts, choose `<NN>` as the next available 2-digit number in the dedicated `02 - Facebook Cá Nhân` folder. Inspect existing filenames matching `^\d\d - ` and increment the highest number.
- Use title case without Vietnamese accents for `<Topic Title>`, with spaces between words, not hyphen slugs.
- Use the exact suffix `- Facebook.md` for Facebook files, and `- Zalo.md` only when a Zalo version is created.
- Save Facebook personal posts in `C:\Users\nhuan\OneDrive\Ứng dụng\remotely-save\Anhlaptrinh_Vault\01Chuong_Trinh_Dao_Tao\02 - Facebook Cá Nhân`, not in the skill folder.
- Do not overwrite existing files unless the user asks for it. If a filename exists, choose a short variant such as `-2` or a more specific slug.

Example:

```text
09 - Cong viec chua toi noi bay dat sang tao - Facebook.md
09 - Cong viec chua toi noi bay dat sang tao - Zalo.md
```
