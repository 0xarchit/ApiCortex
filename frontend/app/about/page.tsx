"use client";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Brain,
  Shield,
  Zap,
  BarChart3,
  GitBranch,
  Lock,
  Cpu,
  Users,
  ArrowRight,
  Mail,
  Github,
} from "lucide-react";

const stats = [
  { value: "99.9%", label: "Uptime SLA" },
  { value: "<50ms", label: "Median Latency" },
  { value: "10+", label: "Integrations" },
  { value: "24/7", label: "Observability" },
];

const features = [
  {
    icon: Brain,
    title: "ML-Powered Detection",
    description:
      "Anomaly detection models trained on API traffic patterns identify failures before they impact users.",
  },
  {
    icon: Shield,
    title: "Contract Validation",
    description:
      "OpenAPI specification enforcement ensures your API and consumers stay in sync at all times.",
  },
  {
    icon: BarChart3,
    title: "Deep Telemetry",
    description:
      "P95, P99 latency, error rates, and traffic volume — everything you need to know.",
  },
  {
    icon: GitBranch,
    title: "Version Control",
    description:
      "Track every API change with a full history. Revert, compare, and audit with confidence.",
  },
  {
    icon: Zap,
    title: "Real-Time Alerts",
    description:
      "Slack, PagerDuty, and webhooks fire instantly when your APIs show signs of trouble.",
  },
  {
    icon: Lock,
    title: "SOC 2 Ready",
    description:
      "Enterprise-grade security with role-based access, audit logs, and encrypted data flows.",
  },
];

const timeline = [
  {
    year: "2025",
    event: "ApiCortex founded to solve the API reliability problem at scale.",
  },
  {
    year: "Early 2025",
    event: "Closed beta with 5 engineering teams. First production anomaly caught before launch.",
  },
  {
    year: "Mid 2025",
    event: "Public launch. OpenAPI import, Slack alerts, and Grafana dashboard shipped.",
  },
  {
    year: "2026",
    event:
      "10+ integrations, <50ms median latency, and 99.9% uptime across all customers.",
  },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[#0F1117] text-[#E6EAF2] font-sans">
      {/* Hero */}
      <section className="relative py-24 px-6 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#5B5DFF] rounded-full blur-[150px] opacity-15" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[#00C2A8] rounded-full blur-[150px] opacity-10" />
        </div>
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#5B5DFF]/10 border border-[#5B5DFF]/20 text-[#5B5DFF] text-xs font-semibold mb-6">
            <Cpu className="w-3 h-3" />
            Built for production API infrastructure
          </div>
          <h1 className="text-5xl lg:text-6xl font-black tracking-tight mb-6 text-transparent bg-clip-text bg-linear-to-r from-white via-[#E6EAF2] to-[#9AA3B2]">
            ApiCortex is the intelligence layer
            <br />
            for your API infrastructure.
          </h1>
          <p className="text-xl text-[#9AA3B2] max-w-2xl mx-auto leading-relaxed mb-10">
            We predict API failures before they happen, validate contracts in real-time,
            and give you deep telemetry — so your APIs stay reliable at any scale.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/login">
              <Button className="h-12 px-8 bg-[#5B5DFF] hover:bg-[#5B5DFF]/90 text-white rounded-full font-medium text-base shadow-[0_0_30px_rgba(91,93,255,0.4)]">
                Start for free
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
            <Link href="/docs">
              <Button
                variant="outline"
                className="h-12 px-8 rounded-full font-medium text-base"
              >
                Read the docs
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 px-6 border-t border-b border-[#242938] bg-[#161A23]/50">
        <div className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-3xl font-black text-white mb-1">{s.value}</div>
              <div className="text-sm text-[#9AA3B2]">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-6" id="features">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-black tracking-tight mb-4">
              Everything your API needs
            </h2>
            <p className="text-[#9AA3B2] text-lg max-w-xl mx-auto">
              From anomaly detection to contract validation — a complete observability stack for API-first teams.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="p-6 rounded-xl bg-[#161A23]/80 border border-[#242938] hover:border-[#5B5DFF]/30 transition-all group"
              >
                <div className="w-10 h-10 rounded-lg bg-[#5B5DFF]/10 flex items-center justify-center mb-4 group-hover:bg-[#5B5DFF]/20 transition-colors">
                  <f.icon className="w-5 h-5 text-[#5B5DFF]" />
                </div>
                <h3 className="text-base font-semibold text-[#E6EAF2] mb-2">
                  {f.title}
                </h3>
                <p className="text-sm text-[#9AA3B2] leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="py-24 px-6 border-t border-[#242938]">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-black tracking-tight mb-16 text-center">
            How we got here
          </h2>
          <div className="relative">
            <div className="absolute left-[4.5rem] top-0 bottom-0 w-px bg-[#242938]" />
            <div className="space-y-10">
              {timeline.map((t, i) => (
                <div key={i} className="flex gap-8">
                  <div className="shrink-0 w-32 text-right text-sm font-semibold text-[#5B5DFF] pt-0.5">
                    {t.year}
                  </div>
                  <div className="relative flex items-start gap-4">
                    <div className="shrink-0 w-3 h-3 rounded-full bg-[#5B5DFF] border-2 border-[#0F1117] mt-1.5 z-10" />
                    <p className="text-[#9AA3B2] text-base leading-relaxed">{t.event}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6 border-t border-[#242938]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-black tracking-tight mb-4">
            Ready to upgrade your API stack?
          </h2>
          <p className="text-[#9AA3B2] text-lg mb-10">
            Start with the free tier. No credit card required.
          </p>
          <Link href="/login">
            <Button className="h-12 px-8 bg-[#5B5DFF] hover:bg-[#5B5DFF]/90 text-white rounded-full font-medium text-base shadow-[0_0_30px_rgba(91,93,255,0.4)]">
              Get started for free
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-[#242938]">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
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
            <Link href="/contact" className="hover:text-white transition-colors">
              Contact
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