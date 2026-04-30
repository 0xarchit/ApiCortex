"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Cpu, Mail, Github, ArrowRight, CheckCircle2 } from "lucide-react";
import Link from "next/link";

type FormState = "idle" | "submitting" | "success" | "error";

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [formState, setFormState] = useState<FormState>("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !message.trim()) return;
    setFormState("submitting");
    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          message: message.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(
          `Contact request failed with status ${response.status}`,
        );
      }

      setFormState("success");
    } catch (error) {
      console.error("Failed to send contact message", error);
      setFormState("error");
    }
  };

  return (
    <div className="min-h-screen bg-[#0F1117] text-[#E6EAF2] font-sans flex flex-col">
      <div className="flex-1 py-24 px-6">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#5B5DFF]/10 border border-[#5B5DFF]/20 text-[#5B5DFF] text-xs font-semibold mb-6">
              <Mail className="w-3 h-3" />
              We typically reply within 24 hours
            </div>
            <h1 className="text-5xl font-black tracking-tight mb-4 text-transparent bg-clip-text bg-linear-to-r from-white via-[#E6EAF2] to-[#9AA3B2]">
              Get in touch
            </h1>
            <p className="text-xl text-[#9AA3B2] max-w-xl mx-auto leading-relaxed">
              Questions, feedback, bug reports, or partnership ideas — we&apos;d
              love to hear from you.
            </p>
          </div>

          <div className="grid lg:grid-cols-5 gap-16">
            {/* Contact Methods */}
            <div className="lg:col-span-2 space-y-8">
              <div>
                <h2 className="text-lg font-semibold mb-4 text-[#E6EAF2]">
                  Contact directly
                </h2>
                <div className="space-y-4">
                  <a
                    href="mailto:mail@0xarchit.is-a.dev"
                    className="flex items-center gap-3 p-4 rounded-xl bg-[#161A23] border border-[#242938] hover:border-[#5B5DFF]/30 transition-all group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-[#5B5DFF]/10 flex items-center justify-center shrink-0">
                      <Mail className="w-5 h-5 text-[#5B5DFF]" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-[#E6EAF2]">
                        Email us
                      </div>
                      <div className="text-sm text-[#9AA3B2]">
                        mail@0xarchit.is-a.dev
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-[#9AA3B2] ml-auto group-hover:text-[#5B5DFF] transition-colors" />
                  </a>
                  <a
                    href="https://github.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-4 rounded-xl bg-[#161A23] border border-[#242938] hover:border-[#5B5DFF]/30 transition-all group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-[#161A23] border border-[#242938] flex items-center justify-center shrink-0">
                      <Github className="w-5 h-5 text-[#E6EAF2]" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-[#E6EAF2]">
                        GitHub
                      </div>
                      <div className="text-sm text-[#9AA3B2]">
                        Open an issue or PR
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-[#9AA3B2] ml-auto group-hover:text-[#5B5DFF] transition-colors" />
                  </a>
                </div>
              </div>

              <div>
                <h2 className="text-lg font-semibold mb-4 text-[#E6EAF2]">
                  What we help with
                </h2>
                <ul className="space-y-3">
                  {[
                    "API integration and onboarding support",
                    "Enterprise pricing and custom contracts",
                    "Bug reports and feature requests",
                    "Security disclosures",
                    "Partnership and API access",
                  ].map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-2 text-sm text-[#9AA3B2]"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-[#5B5DFF] mt-1.5 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Contact Form */}
            <div className="lg:col-span-3">
              <div className="p-6 rounded-2xl bg-[#161A23]/80 border border-[#242938]">
                {formState === "success" ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-16 h-16 rounded-full bg-[#00C2A8]/10 flex items-center justify-center mb-6">
                      <CheckCircle2 className="w-8 h-8 text-[#00C2A8]" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">Message sent!</h3>
                    <p className="text-[#9AA3B2] mb-6">
                      We&apos;ll get back to you at {email} within 24 hours.
                    </p>
                    <Button
                      onClick={() => setFormState("idle")}
                      variant="outline"
                      className="rounded-full"
                    >
                      Send another
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                      <label
                        htmlFor="contact-name"
                        className="block text-sm font-medium text-[#9AA3B2] mb-1.5"
                      >
                        Your name
                      </label>
                      <Input
                        id="contact-name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Alex Chen"
                        required
                        className="bg-[#0F1117] border-[#242938]"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="contact-email"
                        className="block text-sm font-medium text-[#9AA3B2] mb-1.5"
                      >
                        Email address
                      </label>
                      <Input
                        id="contact-email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="alex@company.com"
                        required
                        className="bg-[#0F1117] border-[#242938]"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="contact-message"
                        className="block text-sm font-medium text-[#9AA3B2] mb-1.5"
                      >
                        How can we help?
                      </label>
                      <textarea
                        id="contact-message"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Tell us what's on your mind..."
                        rows={5}
                        required
                        className="w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1.5 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                      />
                    </div>
                    {formState === "error" && (
                      <p className="text-sm text-[#FF5C5C]">
                        Something went wrong. Please try again or email us
                        directly.
                      </p>
                    )}
                    <Button
                      type="submit"
                      disabled={formState === "submitting"}
                      className="w-full h-11 bg-[#5B5DFF] hover:bg-[#5B5DFF]/90 text-white rounded-full font-medium shadow-[0_0_20px_rgba(91,93,255,0.3)]"
                    >
                      {formState === "submitting" ? (
                        "Sending..."
                      ) : (
                        <>
                          Send message
                          <ArrowRight className="w-4 h-4 ml-2" />
                        </>
                      )}
                    </Button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-[#242938]">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
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
              href="/privacy"
              className="hover:text-white transition-colors"
            >
              Privacy Policy
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
