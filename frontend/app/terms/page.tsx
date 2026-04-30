"use client";
import { Cpu, ArrowRight } from "lucide-react";
import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0F1117] text-[#E6EAF2] font-sans flex flex-col">
      <div className="flex-1 py-16 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12">
            <h1 className="text-4xl font-black tracking-tight mb-4">
              Terms of Service
            </h1>
            <p className="text-[#9AA3B2]">
              Last updated: April 30, 2026
            </p>
          </div>

          <div className="prose prose-invert max-w-none space-y-10">
            <section>
              <h2 className="text-xl font-bold mb-4">
                1. Acceptance of Terms
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  By accessing or using the ApiCortex platform
                  (&quot;Platform&quot;) at apicortex.ai, you agree to be
                  bound by these Terms of Service
                  (&quot;Terms&quot;). If you do not agree to these
                  Terms, do not use the Platform.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                2. Description of Service
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  ApiCortex provides API monitoring, anomaly
                  detection, contract validation, and telemetry
                  analytics (&quot;Service&quot;). We reserve the right to
                  modify, suspend, or discontinue any part of the Service
                  at any time without notice.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                3. Account &amp; Eligibility
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  You must be at least 16 years old to create an
                  account. You are responsible for maintaining the
                  security of your account credentials. ApiCortex is not
                  liable for any loss caused by unauthorized access.
                </p>
                <p>
                  One account per person. Sharing account access with
                  multiple users requires a team plan.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                4. Acceptable Use
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>You agree NOT to:</p>
                <ul className="space-y-2 list-disc pl-5">
                  <li>
                    Use the Platform for any illegal purpose
                  </li>
                  <li>
                    Attempt to gain unauthorized access to
                    other accounts or systems
                  </li>
                  <li>
                    Overload, damage, or impair the Platform
                    beyond intended use
                  </li>
                  <li>
                    Reverse engineer or extract the Platform&apos;s
                    proprietary models
                  </li>
                  <li>
                    Resell the Platform without written permission
                  </li>
                  <li>
                    Use the Platform to probe third-party APIs without
                    authorization
                  </li>
                </ul>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                5. API Content &amp; Ownership
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  You retain full ownership of all data you submit to the
                  Platform (&quot;Content&quot;). By using the Platform,
                  you grant ApiCortex a non-exclusive, worldwide
                  license to use your Content solely for the purpose of
                  providing the Service.
                </p>
                <p>
                  ApiCortex claims no ownership over your OpenAPI
                  specifications, API configurations, or
                  telemetry data.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                6. Fees &amp; Payment
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  Usage of paid plans is billed according to the
                  pricing page. All fees are non-refundable unless
                  required by law. We reserve the right to change
                  pricing with 30 days&apos; notice.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                7. Disclaimer of Warranties
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  THE PLATFORM IS PROVIDED &quot;AS IS&quot; AND
                  &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES OF
                  ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
                  LIMITED TO IMPLIED WARRANTIES OF
                  MERCHANTABILITY AND FITNESS FOR A PARTICULAR
                  PURPOSE. ApiCortex does not guarantee that
                  anomaly detection will catch every failure.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                8. Limitation of Liability
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW,
                  ApiCortex SHALL NOT BE LIABLE FOR ANY
                  INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL,
                  OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF
                  THE PLATFORM, REGARDLESS OF THE CAUSE OF
                  ACTION OR THE THEORY OF LIABILITY.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                9. Termination
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  Either party may terminate your account at any
                  time. Upon termination, your data is retained for 30
                  days before permanent deletion.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                10. Changes to Terms
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  ApiCortex may update these Terms at any time.
                  Material changes will be communicated via email.
                  Continued use of the Platform after changes
                  constitutes acceptance.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                11. Governing Law
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  These Terms are governed by the laws of the
                  State of Delaware, USA, without regard to
                  conflict of law principles. Disputes are resolved
                  in the courts of Delaware.
                </p>
              </div>
            </section>

            <section>
              <h2 className="text-xl font-bold mb-4">
                12. Contact
              </h2>
              <div className="text-[#9AA3B2] space-y-3">
                <p>
                  Questions about these Terms? Contact us at{" "}
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
          </div>
        </div>
      </div>

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
            <Link href="/privacy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}