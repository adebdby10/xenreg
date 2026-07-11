"""Add /fb command to reg_bot.py"""
with open("/root/scripts/reg_bot.py") as f:
    c = f.read()

# 1. Add fb_flow import
c = c.replace(
    "from telethon import TelegramClient, events",
    "from telethon import TelegramClient, events\nfrom fb_flow import fb_check, fb_register"
)

# 2. Add /fb and /status handler updates
# Find /status handler
old_status = """@client.on(events.NewMessage(pattern="/status"))
async def status_handler(event):
    if not is_allowed(event): return
    statuses = []
    for p in ADB_PORTS:
        r = subprocess.run(f"adb -s 127.0.0.1:{p} shell echo OK", shell=True, capture_output=True, text=True, timeout=3)
        ok = r.stdout.strip() == "OK"
        statuses.append(f"{'✅' if ok else '❌'} Container {p}")
    await event.reply(
        "🔄 *Bot Status*\n" + "\n".join(statuses) +
        f"\n\n⚡ Paralel: {CONCURRENCY} container\n📧 Email: {TEMP_EMAIL}",
        parse_mode="markdown"
    )"""

new_status = """@client.on(events.NewMessage(pattern="/status"))
async def status_handler(event):
    if not is_allowed(event): return
    statuses = []
    for p in ADB_PORTS:
        r = subprocess.run(f"adb -s 127.0.0.1:{p} shell echo OK", shell=True, capture_output=True, text=True, timeout=3)
        ok = r.stdout.strip() == "OK"
        statuses.append(f"{'✅' if ok else '❌'} Container {p}")
    await event.reply(
        "🔄 *Bot Status*\n" + "\n".join(statuses) +
        f"\n\n⚡ Paralel: {CONCURRENCY} container\n📧 Email: {TEMP_EMAIL}\n📱 FB: ✅ fb_flow terinstall",
        parse_mode="markdown"
    )"""

c = c.replace(old_status, new_status)

# 3. Add /fb command handler AFTER the last handler (before run_until_disconnected)
# Find where /cancel handler ends
old_end_handlers = """client.run_until_disconnected()"""

fb_handler = '''
@client.on(events.NewMessage(pattern="/fb"))
async def fb_handler(event):
    if not is_allowed(event): return
    args = event.text.strip().split()
    if len(args) < 2:
        await event.reply(
            "Cara pakai: `/fb +62812xxxxxx`\\n\\n"
            "Bot akan:\\n"
            "1. Buka Facebook.com/reg\\n"
            "2. Isi form dengan data random\\n"
            "3. Detect OTP_SENT / INVALID / BLOCKED\\n"
            "4. Kalo OTP_SENT, lo reply kode OTP-nya",
            parse_mode="markdown"
        )
        return
    
    phone = args[1]
    if not phone.startswith("+"):
        phone = "+" + phone
    if not re.match(r'^\\+\\d{7,15}$', phone):
        await event.reply(f"\\u274c Format nomor salah: `{phone}`")
        return
    
    status_msg = await event.reply(f"\\ud83c\\udf10 Cek Facebook untuk `{phone}`...\\n\\n"
                                    f"Langkah:\\n1. Buka fb.com/reg\\n2. Isi form\\n3. Submit\\n4. Detect screen",
                                    parse_mode="markdown")
    
    try:
        result, profile = await fb_check(phone)
        
        if result == "OTP_SENT":
            # Send reply-able message
            m = await status_msg.edit(
                f"\\ud83d\\udcf2 `{phone}` \\u2192 **OTP_SENT**\\n\\n"
                f"\\u2139\ufe0f Facebook kirim kode verifikasi via SMS.\\n"
                f"Balas pesan ini dengan kode OTP untuk registrasi.\\n\\n"
                f"*Profile:* `{profile['first_name']} {profile['last_name']}`",
                parse_mode="markdown"
            )
            pending_otp[m.id] = {"phone": phone, "chat_id": event.chat_id, "type": "fb", "profile": profile}
            
        elif result == "INVALID_NUMBER":
            await status_msg.edit(f"\\u274c `{phone}` \\u2192 **INVALID_NUMBER**\\n\\nNomor tidak valid / ditolak Facebook.")
        elif result == "CHECKPOINT":
            await status_msg.edit(f"\\u26a0\ufe0f `{phone}` \\u2192 **CHECKPOINT**\\n\\nFacebook minta verifikasi tambahan (captcha/identity).")
        elif result == "EMAIL_VERIFICATION":
            await status_msg.edit(f"\\ud83d\\udce7 `{phone}` \\u2192 **EMAIL_VERIFICATION**\\n\\nFacebook minta verifikasi email.")
        elif result == "SUCCESS":
            await status_msg.edit(f"\\u2705 `{phone}` \\u2192 **AKUN JADI!** (tanpa OTP)")
        else:
            await status_msg.edit(f"\\u2753 `{phone}` \\u2192 **{result}**\\n\\nGagal mendeteksi status. Coba manual.")
            
    except Exception as e:
        await status_msg.edit(f"\\u274c Error: `{e}`")
        import traceback
        traceback.print_exc()

'''

c = c.replace(old_end_handlers, fb_handler + "\n" + old_end_handlers)

# 4. Modify otp_reply_handler to handle fb type
old_otp = """    info = pending_otp[replied.id]
    phone = info["phone"]
    otp = event.text.strip()

    if not re.match(r'^\\d{4,10}$', otp):
        await event.reply("\\u274c Kode OTP harus 4-10 digit angka.")
        return

    status_msg = await event.reply(f"\\u23f3 Registrasi `{phone}`...")

    mail_token = ensure_temp_mail()
    port = await pool.acquire()
    try:
        result = await register_number(phone, otp, port, mail_token)
        del pending_otp[replied.id]  # clean up

        if result == "SUCCESS":
            await status_msg.edit(f"\\u2705 REGISTRASI BERHASIL!\\n\\n`{phone}` \\u2192 Akun Telegram berhasil dibuat!")
        elif result == "WRONG_CODE":
            # Keep pending so user can retry
            await status_msg.edit(f"\\u274c Kode Salah\\n\\n`{phone}` \\u2192 OTP tidak valid. Coba kirim ulang kode dengan reply lagi.")
        elif result == "ADD_EMAIL":
            await status_msg.edit(f"\\u2709\ufe0f Perlu Email\\n\\n`{phone}` \\u2192 Nomor ini minta alamat email dulu.")
        elif result == "TIMEOUT":
            await status_msg.edit(f"\\u23f0 Timeout\\n\\n`{phone}` \\u2192 Waktu habis menunggu OTP, coba ulang.")
        else:
            await status_msg.edit(f"\\u2753 Unknown\\n\\n`{phone}` \\u2192 {result}\\n\\nCoba manual.")
    finally:
        pool.release(port)"""

new_otp = """    info = pending_otp[replied.id]
    phone = info["phone"]
    otp = event.text.strip()
    ptype = info.get("type", "telegram")

    if not re.match(r'^\\d{4,10}$', otp):
        await event.reply("\\u274c Kode OTP harus 4-10 digit angka.")
        return

    status_msg = await event.reply(f"\\u23f3 Registrasi `{phone}` ({ptype})...")

    if ptype == "fb":
        # Facebook registration
        profile = info.get("profile")
        try:
            result = await fb_register(phone, otp, profile)
            del pending_otp[replied.id]
            
            if result == "SUCCESS":
                await status_msg.edit(f"\\u2705 **FB REGISTRASI BERHASIL!**\\n\\n`{phone}` \\u2192 Akun Facebook berhasil dibuat!\\nNama: `{profile['first_name']} {profile['last_name']}`\\nPass: `{profile['password']}`",
                                      parse_mode="markdown")
            elif result == "WRONG_CODE":
                await status_msg.edit(f"\\u274c Kode Salah\\n\\n`{phone}` \\u2192 OTP tidak valid. Coba kirim ulang kode.")
            elif result == "ADD_EMAIL":
                await status_msg.edit(f"\\u2709\ufe0f Perlu Email\\n\\n`{phone}` \\u2192 Facebook minta email dulu.")
            elif result == "CHECKPOINT":
                await status_msg.edit(f"\\u26a0\ufe0f Checkpoint\\n\\n`{phone}` \\u2192 Facebook minta verifikasi identitas.")
            else:
                await status_msg.edit(f"\\u2753 Unknown\\n\\n`{phone}` \\u2192 {result}")
        except Exception as e:
            await status_msg.edit(f"\\u274c FB Error: `{e}`")
            import traceback
            traceback.print_exc()
    else:
        # Telegram registration
        mail_token = ensure_temp_mail()
        port = await pool.acquire()
        try:
            result = await register_number(phone, otp, port, mail_token)
            del pending_otp[replied.id]

            if result == "SUCCESS":
                await status_msg.edit(f"\\u2705 **TG REGISTRASI BERHASIL!**\\n\\n`{phone}` \\u2192 Akun Telegram berhasil dibuat!")
            elif result == "WRONG_CODE":
                await status_msg.edit(f"\\u274c Kode Salah\\n\\n`{phone}` \\u2192 OTP tidak valid. Coba kirim ulang kode dengan reply lagi.")
            elif result == "ADD_EMAIL":
                await status_msg.edit(f"\\u2709\ufe0f Perlu Email\\n\\n`{phone}` \\u2192 Nomor ini minta alamat email dulu.")
            elif result == "TIMEOUT":
                await status_msg.edit(f"\\u23f0 Timeout\\n\\n`{phone}` \\u2192 Waktu habis menunggu OTP, coba ulang.")
            else:
                await status_msg.edit(f"\\u2753 Unknown\\n\\n`{phone}` \\u2192 {result}\\n\\nCoba manual.")
        finally:
            pool.release(port)"""

c = c.replace(old_otp, new_otp)

with open("/root/scripts/reg_bot.py", "w") as f:
    f.write(c)
print("Done - reg_bot.py patched with FB integration")
