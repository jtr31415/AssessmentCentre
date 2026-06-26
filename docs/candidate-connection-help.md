# Having trouble opening the assessment site?

If `https://assessment.kuhlinlabs.com` won't load and you see an error like
**"This site can't provide a secure connection"** or **"unsupported protocol"**
(`ERR_SSL_VERSION_OR_CIPHER_MISMATCH`), the site itself is up — the problem is
almost always your **work computer's security software / corporate network**
blocking or inspecting the connection. Here's how to get in.

---

## Quick fixes — try in this order

**1. Open it on a personal device.**
Use your phone or a personal laptop, ideally on **mobile data / home Wi-Fi**
(not the office network). If it loads there, the issue is your work machine or
network — keep reading.

**2. Try a different browser.**
If Chrome fails, try **Firefox** (or vice-versa). If one works, use that one.

**3. Turn off one Chrome/Edge setting (30 seconds).**
This is the single most common fix.

- **Chrome:** in the address bar, go to `chrome://flags`
- **Edge:** go to `edge://flags`
- In the **"Search flags"** box at the top, type: **`kyber`**
  (if nothing appears, try **`ml-kem`**, then **`post-quantum`**)
- Set the one result that appears (e.g. *"Use ML-KEM in TLS"* /
  *"TLS 1.3 hybridized Kyber support"*) to **Disabled**
- Click **Relaunch** at the bottom, then reload the site

Shortcut: paste `chrome://flags/#use-ml-kem` (or `chrome://flags/#enable-tls13-kyber`)
straight into the address bar — Chrome will highlight the setting for you.

If the setting is **greyed out / "managed by your organization,"** your IT
controls it — see the section below.

---

## If none of that works — for your IT team

The assessment is hosted at **`assessment.kuhlinlabs.com`** (a standard public
website with a valid Let's Encrypt TLS certificate, supporting TLS 1.2 and 1.3).
A corporate web-security proxy / TLS-inspection appliance is blocking it.
Please ask IT to do any of the following for this domain:

- **Allowlist `assessment.kuhlinlabs.com`** in the web-security / proxy policy,
  and **recategorize** it out of "newly registered / uncategorized."
- **Exclude it from TLS/SSL inspection** (or trust the public Let's Encrypt chain).
- If they run TLS inspection, ensure the appliance **supports post-quantum TLS
  (X25519MLKEM768)** — older versions choke on it. Updating the appliance, or
  setting the Chrome/Edge policy **`PostQuantumKeyAgreementEnabled = Disabled`**
  fleet-wide, resolves it.

---

## Still stuck?

Contact your assessor and include:
- the **exact error message / code** the browser shows,
- which **browser** and whether you tried a **personal device**,
- whether you're on a **work or personal network**.

We'll help you get connected.
