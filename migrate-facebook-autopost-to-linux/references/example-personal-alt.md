# Example: personal_alt

Project root:

```bash
/root/05_skill_facebook_zalo/skill_post_facebook_personal_alt
```

Foreground validation:

```bash
cd /root/05_skill_facebook_zalo/skill_post_facebook_personal_alt
rm -f facebook-chrome-profile/SingletonCookie facebook-chrome-profile/SingletonLock facebook-chrome-profile/SingletonSocket
/usr/bin/xvfb-run -a /usr/bin/python3 -u .agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py
```

Create wrapper:

```bash
python3 /root/.agents/skills/migrate-facebook-autopost-to-linux/scripts/create_cron_wrapper.py \
  --project-root /root/05_skill_facebook_zalo/skill_post_facebook_personal_alt \
  --log-name personal_alt_5min_post.log \
  --lock-name skill_post_facebook_personal_alt_5min.lock
```

Cron:

```cron
# skill_post_facebook_personal_alt: post 1 personal Facebook item every 5 minutes
*/5 * * * * /root/05_skill_facebook_zalo/skill_post_facebook_personal_alt/.agents/skills/fb-auto-poster/scripts/run_5min_post.sh
```
