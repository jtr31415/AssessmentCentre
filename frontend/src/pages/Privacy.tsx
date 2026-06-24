export default function Privacy() {
  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", lineHeight: 1.5 }}>
      <h1>Privacy notice</h1>
      <p>
        This assessment platform deliberately holds the minimum personal data. About you we store
        only your <strong>first name</strong> and a system-generated ID (e.g. <code>cand-07</code>),
        together with your assessment booking, file downloads, questions you ask, and an Anthropic
        API key stored <strong>encrypted</strong>.
      </p>
      <p>
        We do <strong>not</strong> store your email, surname, phone number, IP-based analytics, or
        any marketing data. We use a single essential session cookie to keep you logged in; it is
        removed when you log out or it expires. Because it is strictly necessary, no cookie-consent
        banner is required.
      </p>
      <p>
        Your data is held only for the duration of the assessment process and is then permanently
        deleted. You may ask the assessor to erase your data at any time.
      </p>
    </main>
  );
}
