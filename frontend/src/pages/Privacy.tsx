import { Link } from "react-router-dom";

export default function Privacy() {
  return (
    <div className="max-w-3xl mx-auto my-12 animate-fade-in">
      <div className="border border-brand-hair rounded-lg p-8 bg-white space-y-6 shadow-xs">
        <div className="border-b border-brand-hair pb-4">
          <span className="text-[10px] uppercase tracking-widest text-brand-muted font-bold block mb-1">
            Candidate Security &amp; Trust
          </span>
          <h2 className="text-2xl font-bold text-brand-blue">Privacy Notice</h2>
        </div>

        <div className="space-y-4 text-xs text-brand-ink leading-relaxed">
          <p>
            This assessment platform deliberately holds the minimum personal data. About you we store
            only your <strong className="font-semibold text-brand-blue">first name</strong> and a
            system-generated ID (e.g.{" "}
            <code className="font-mono bg-brand-codebg px-1">cand-07</code>), together with your
            assessment booking, file downloads, questions you ask, and an Anthropic API key stored{" "}
            <strong className="font-semibold text-brand-blue">encrypted</strong>.
          </p>
          <p>
            We do <strong className="font-bold">not</strong> store your email, surname, phone number,
            IP-based analytics, or any marketing data. We use a single essential session cookie to
            keep you logged in; it is removed when you log out or it expires. Because it is strictly
            necessary, no cookie-consent banner is required.
          </p>
          <p>
            Your data is held only for the duration of the assessment process and is then permanently
            deleted. You may ask the assessor to erase your data at any time.
          </p>
        </div>

        <div className="border-t border-brand-hair pt-5 flex items-center justify-between">
          <div className="text-[10px] text-brand-muted">
            Document Version: <span className="font-mono">v1.1 (June 2026)</span>
          </div>
          <Link
            to="/dashboard"
            className="px-4 py-2 bg-brand-blue hover:bg-opacity-90 text-white text-xs font-semibold rounded transition"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
