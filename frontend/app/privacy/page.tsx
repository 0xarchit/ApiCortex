"use client";
import { Cpu } from "lucide-react";
import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#0F1117] text-[#E6EAF2] font-sans flex flex-col">
      <div className="flex-1 py-16 px-6">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="mb-12">
            <h1 className="text-4xl font-black tracking-tight mb-4">
              Privacy Policy
            </h1>
            <p className="text-[#9AA3B2]">Last updated: April 30, 2026</p>
          </div>

          <div className="prose prose-invert max-w-none space-y-10">
            {/* Overview */}
            <section>
              <h2 className="text-xl font-bold mb-4">1. Overview</h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  ApiCortex, Inc. (&quot;ApiCortex,&quot; &quot;we,&quot; or
                  &quot;us&quot;) operates the website located at apicortex.ai
                  (the &quot;Site&quot;) and the ApiCortex platform (the
                  &quot;Platform&quot;). This Privacy Policy explains how
                  ApiCortex collects, uses, and protects information when you
                  use our Site and Platform.
                </p>
                <p>
                  By using ApiCortex, you agree to the collection and use of
                  information in accordance with this policy.
                </p>
              </div>
            </section>

            {/* Information */}
            <section>
              <h2 className="text-xl font-bold mb-4">
                2. Information We Collect
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  <strong className="text-[#E6EAF2]">
                    Account &amp; Authentication.
                  </strong>{" "}
                  When you sign up via Google or GitHub OAuth, we collect your
                  email address, name, and profile picture. We do not store your
                  OAuth tokens — authentication is handled entirely by the OAuth
                  provider.
                </p>
                <p>
                  <strong className="text-[#E6EAF2]">API Metadata.</strong> The
                  Platform stores your OpenAPI specifications, endpoint
                  configurations, and prediction settings. This data is
                  encrypted at rest and in transit.
                </p>
                <p>
                  <strong className="text-[#E6EAF2]">Telemetry Data.</strong>{" "}
                  ApiCortex may collect anonymized, aggregated API telemetry
                  (latency, error rates, traffic volume) solely for the purpose
                  of providing the Platform&apos;s anomaly detection and
                  monitoring features. This data is never shared with third
                  parties.
                </p>
                <p>
                  <strong className="text-[#E6EAF2]">Usage Logs.</strong> We
                  retain server-side request logs for up to 30 days for
                  debugging and security purposes.
                </p>
                <p>
                  <strong className="text-[#E6EAF2]">Cookies.</strong> We use
                  essential session cookies to maintain your login. No
                  advertising or tracking cookies are used.
                </p>
              </div>
            </section>

            {/* Use */}
            <section>
              <h2 className="text-xl font-bold mb-4">
                3. How We Use Information
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <ul className="space-y-2 list-disc pl-5">
                  <li>Provide and maintain the Platform</li>
                  <li>Detect and alert on API anomalies in real-time</li>
                  <li>Send you service-related notifications</li>
                  <li>Improve Platform performance and features</li>
                  <li>Enforce rate limits and prevent abuse</li>
                </ul>
              </div>
            </section>

            {/* Sharing */}
            <section>
              <h2 className="text-xl font-bold mb-4">4. Information Sharing</h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  ApiCortex does not sell, trade, or rent your personal data. We
                  share information only in these cases:
                </p>
                <ul className="space-y-2 list-disc pl-5">
                  <li>
                    <strong className="text-[#E6EAF2]">
                      Service providers.
                    </strong>{" "}
                    Trusted third-party services (hosting, analytics) that
                    process data under our instructions.
                  </li>
                  <li>
                    <strong className="text-[#E6EAF2]">
                      Legal requirements.
                    </strong>{" "}
                    When required by law, court order, or to prevent illegal
                    activity.
                  </li>
                  <li>
                    <strong className="text-[#E6EAF2]">
                      Business transfers.
                    </strong>{" "}
                    In the event of a merger or acquisition, information may be
                    transferred as part of the business assets.
                  </li>
                </ul>
              </div>
            </section>

            {/* Security */}
            <section>
              <h2 className="text-xl font-bold mb-4">5. Data Security</h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  We implement industry-standard measures to protect your data:
                  TLS encryption in transit, AES-256 encryption at rest,
                  role-based access controls, and regular security audits. No
                  security measure is 100% foolproof, and we cannot guarantee
                  absolute security of transmitted data.
                </p>
              </div>
            </section>

            {/* Retention */}
            <section>
              <h2 className="text-xl font-bold mb-4">
                6. Data Retention &amp; Deletion
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  Account data is retained until you delete your account. You
                  can delete your account at any time from the Settings page,
                  which permanently removes all personal data within 30 days.
                  API metadata is retained for 90 days after account deletion
                  for audit purposes.
                </p>
                <p>
                  To request data deletion, email{" "}
                  <a
                    href="mailto:mail@0xarchit.is-a.dev"
                    className="text-[#5B5DFF] hover:underline"
                  >
                    mail@0xarchit.is-a.dev
                  </a>
                  .
                </p>
              </div>
            </section>

            {/* Children's */}
            <section>
              <h2 className="text-xl font-bold mb-4">
                7. Children&apos;s Privacy
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  The ApiCortex Platform is not intended for users under the age
                  of 16. We do not knowingly collect data from minors. If you
                  believe a minor&apos;s data has been collected, contact us
                  immediately.
                </p>
              </div>
            </section>

            {/* Changes */}
            <section>
              <h2 className="text-xl font-bold mb-4">
                8. Changes to This Policy
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  We may update this Privacy Policy from time to time. Material
                  changes will be communicated via email or a notice on the
                  Platform. Continued use after changes constitutes acceptance
                  of the updated policy.
                </p>
              </div>
            </section>

            {/* Contact */}
            <section>
              <h2 className="text-xl font-bold mb-4">9. Contact</h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  For privacy-related questions or to submit a data request:
                </p>
                <p>
                  <strong className="text-[#E6EAF2]">Email:</strong>{" "}
                  <a
                    href="mailto:mail@0xarchit.is-a.dev"
                    className="text-[#5B5DFF] hover:underline"
                  >
                    mail@0xarchit.is-a.dev
                  </a>
                </p>
              </div>
            </section>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-[#242938]">
        <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-[#9AA3B2]">
            <div className="w-5 h-5 rounded bg-linear-to-br from-[#5B5DFF] to-[#00C2A8] flex items-center justify-center">
              <Cpu className="w-3 h-3 text-white" />
            </div>
            ApiCortex, Inc. &copy; 2026
          </div>
          <div className="flex gap-6 text-sm text-[#9AA3B2]">
            <Link href="/about" className="hover:text-white transition-colors">
              About
            </Link>
            <Link
              href="/contact"
              className="hover:text-white transition-colors"
            >
              Contact
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
