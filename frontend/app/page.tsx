"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useScroll,
  useInView,
} from "framer-motion";
import type { SVGProps } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Terminal,
  Activity,
  Database,
  Lock,
  Cpu,
  Zap,
  CheckCircle2,
  ChevronRight,
  Code2,
  Network,
} from "lucide-react";

function useCountUp(target: number, duration = 1200, trigger = true) {
  const [value, setValue] = useState(0);
  const frameRef = useRef<number>(0);
  useEffect(() => {
    if (!trigger) return;
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) frameRef.current = requestAnimationFrame(animate);
    };
    frameRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration, trigger]);
  return value;
}

function WaveDivider() {
  return (
    <div className="relative h-12 -mt-px overflow-hidden">
      <svg
        className="absolute bottom-0 w-full h-12"
        viewBox="0 0 1440 48"
        preserveAspectRatio="none"
      >
        <path
          d="M0,48 C240,0 480,48 720,24 C960,0 1200,48 1440,24 L1440,48 Z"
          fill="#0F1117"
        />
      </svg>
    </div>
  );
}

function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);
  return (
    <motion.div
      className="fixed top-0 left-0 right-0 h-0.5 bg-linear-to-r from-[#5B5DFF] to-[#00C2A8] z-100 origin-left"
      style={{ scaleX }}
    />
  );
}

const typedWords = ["Production.", "Deployment.", "Scale."];

function TypewriterHeadline() {
  const [wordIndex, setWordIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const word = typedWords[wordIndex];
    const timeout = setTimeout(
      () => {
        if (!deleting) {
          if (charIndex < word.length) {
            setCharIndex((c) => c + 1);
          } else {
            setTimeout(() => setDeleting(true), 2000);
          }
        } else {
          if (charIndex > 0) {
            setCharIndex((c) => c - 1);
          } else {
            setDeleting(false);
            setWordIndex((w) => (w + 1) % typedWords.length);
          }
        }
      },
      deleting ? 40 : 80,
    );
    return () => clearTimeout(timeout);
  }, [charIndex, deleting, wordIndex]);

  return (
    <span className="text-transparent bg-clip-text bg-linear-to-r from-[#5B5DFF] to-[#00C2A8] inline-block min-w-45">
      {typedWords[wordIndex].slice(0, charIndex)}
      <span className="animate-pulse text-[#5B5DFF]">|</span>
    </span>
  );
}

function CursorGlow() {
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 100, damping: 30 });
  const springY = useSpring(mouseY, { stiffness: 100, damping: 30 });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, [mouseX, mouseY]);

  return (
    <motion.div
      className="fixed pointer-events-none z-99 w-75 h-75 rounded-full"
      style={{
        left: springX,
        top: springY,
        translateX: "-50%",
        translateY: "-50%",
        background:
          "radial-gradient(circle, rgba(91,93,255,0.12) 0%, transparent 70%)",
      }}
    />
  );
}

function TiltCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const rotateX = useMotionValue(0);
  const rotateY = useMotionValue(0);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rx = useTransform(rotateX, [-1, 1], [-8, 8]);
  const ry = useTransform(rotateY, [-1, 1], [8, -8]);

  const handleMouse = useCallback(
    (e: React.MouseEvent) => {
      if (!ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const cx = e.clientX - rect.left - rect.width / 2;
      const cy = e.clientY - rect.top - rect.height / 2;
      rotateX.set(cy / (rect.height / 2));
      rotateY.set(cx / (rect.width / 2));
      x.set(cx);
      y.set(cy);
    },
    [rotateX, rotateY, x, y],
  );

  return (
    <motion.div
      ref={ref}
      className={`relative perspective-midrange ${className}`}
      onMouseMove={handleMouse}
      onMouseLeave={() => {
        rotateX.set(0);
        rotateY.set(0);
        x.set(0);
        y.set(0);
      }}
      style={{ rotateX: rx, rotateY: ry }}
      transition={{ type: "spring", stiffness: 200, damping: 20 }}
    >
      <motion.div
        className="absolute inset-0 rounded-3xl pointer-events-none opacity-0 transition-opacity duration-300"
        style={{
          background: `radial-gradient(circle at ${x.get()}% ${y.get()}%, rgba(91,93,255,0.15) 0%, transparent 60%)`,
        }}
      />
      {children}
    </motion.div>
  );
}

export default function LandingPage() {
  const statsRef = useRef<HTMLDivElement>(null);
  const statsInView = useInView(statsRef, { once: true, margin: "-100px" });
  const featuresRef = useRef<HTMLDivElement>(null);
  const featuresInView = useInView(featuresRef, {
    once: true,
    margin: "-50px",
  });

  const stats = {
    integrations: useCountUp(10, 1500, statsInView),
    uptime: useCountUp(99.9, 1000, statsInView),
    inference: useCountUp(500, 1200, statsInView),
    endpoints: useCountUp(50000, 1500, statsInView),
  };

  return (
    <div className="min-h-screen bg-[#0F1117] text-[#E6EAF2] font-sans selection:bg-[#5B5DFF]/30 overflow-x-hidden">
      <ScrollProgress />
      <CursorGlow />

      {/* Background */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[#5B5DFF] rounded-full blur-[150px] opacity-20" />
        <div className="absolute top-[20%] right-[-10%] w-[40%] h-[40%] bg-[#00C2A8] rounded-full blur-[150px] opacity-15" />
        <div className="absolute bottom-[-10%] left-[20%] w-[60%] h-[40%] bg-[#3A8DFF] rounded-full blur-[150px] opacity-10" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(to right, #E6EAF2 1px, transparent 1px), linear-gradient(to bottom, #E6EAF2 1px, transparent 1px)`,
            backgroundSize: "40px 40px",
            maskImage:
              "radial-gradient(ellipse at center, black 40%, transparent 80%)",
            WebkitMaskImage:
              "radial-gradient(ellipse at center, black 40%, transparent 80%)",
          }}
        />
      </div>

      {/* Nav */}
      <nav className="relative z-50 border-b border-[#242938]/50 bg-[#0F1117]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-linear-to-br from-[#5B5DFF] to-[#00C2A8] flex items-center justify-center shadow-[0_0_15px_rgba(91,93,255,0.4)]">
              <Network className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-white">
              ApiCortex
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-[#9AA3B2]">
            <Link
              href="#features"
              className="hover:text-white transition-colors"
            >
              Features
            </Link>
            <Link
              href="#how-it-works"
              className="hover:text-white transition-colors"
            >
              How it Works
            </Link>
            <Link
              href="#terminal-demo"
              className="hover:text-white transition-colors"
            >
              Demo
            </Link>
            <Link
              href="#dev-experience"
              className="hover:text-white transition-colors"
            >
              Developers
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-[#9AA3B2] hover:text-white transition-colors"
            >
              Sign In
            </Link>
            <Link href="/login">
              <Button className="bg-[#5B5DFF]/10 text-[#5B5DFF] border border-[#5B5DFF]/30 hover:bg-[#5B5DFF]/20 backdrop-blur-md rounded-full px-6 transition-all">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        {/* Hero */}
        <section className="relative min-h-[calc(100vh-4rem)] flex items-center py-14 lg:py-20 px-6">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            >
              <div className="inline-flex flex-row items-center justify-center p-1 rounded-full bg-[#161A23] border border-[#242938] mb-8 pr-4">
                <span className="px-3 py-1 text-xs font-semibold bg-[#5B5DFF] text-white rounded-full mr-3 shadow-[0_0_10px_rgba(91,93,255,0.5)]">
                  New
                </span>
                <span className="text-sm text-[#9AA3B2]">
                  ML Anomaly Detection is live
                </span>
              </div>
              <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 text-transparent bg-clip-text bg-linear-to-r from-white via-[#E6EAF2] to-[#9AA3B2]">
                Predict API Failures
                <br />
                Before They Break
                <br className="hidden lg:block" />
                <TypewriterHeadline />
              </h1>
              <p className="text-lg text-[#9AA3B2] mb-10 max-w-xl leading-relaxed">
                ApiCortex continuously analyzes API traffic, detects anomalies,
                and validates contracts — so your APIs stay reliable at scale.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/login">
                  <Button className="h-14 px-8 bg-[#5B5DFF] hover:bg-[#5B5DFF]/90 text-white rounded-full font-medium text-lg w-full sm:w-auto shadow-[0_0_30px_rgba(91,93,255,0.4)] transition-all hover:scale-105">
                    Start Testing APIs
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link href="#terminal-demo">
                  <Button
                    variant="outline"
                    className="h-14 px-8 border-[#242938] bg-[#161A23]/50 backdrop-blur-xl hover:bg-[#242938] text-white rounded-full font-medium text-lg w-full sm:w-auto transition-all"
                  >
                    View Demo
                  </Button>
                </Link>
              </div>
            </motion.div>

            {/* Parallax Hero Mockups */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
              className="relative lg:h-150 flex items-center justify-center"
            >
              <ParallaxCard
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-sm bg-[#161A23]/90 backdrop-blur-xl border border-[#242938] rounded-2xl p-6 shadow-2xl z-20"
                strength={-5}
              >
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#5B5DFF]/20 flex items-center justify-center">
                      <Activity className="w-5 h-5 text-[#5B5DFF]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">
                        Live Traffic Analysis
                      </h3>
                      <p className="text-xs text-[#00C2A8]">
                        Processing 42.1k req/s
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-[#0F1117] rounded-xl p-4 font-mono text-xs text-[#9AA3B2] space-y-2 relative overflow-hidden">
                  <div className="flex justify-between">
                    <span className="text-[#3A8DFF]">GET /api/v1/users</span>
                    <span className="text-[#2ED573]">200 OK</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#3A8DFF]">POST /api/v1/orders</span>
                    <span className="text-[#F5B74F]">Latency Warning</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#3A8DFF]">
                      PATCH /api/v1/profile
                    </span>
                    <span className="text-[#FF5C5C]">Schema Mismatch</span>
                  </div>
                  <motion.div
                    className="absolute inset-0 bg-linear-to-b from-transparent via-[#5B5DFF]/10 to-transparent"
                    animate={{ top: ["-100%", "200%"] }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  />
                </div>
              </ParallaxCard>
              <ParallaxCard
                className="absolute top-10 right-0 lg:-right-10 w-48 bg-[#161A23]/80 backdrop-blur-xl border border-[#242938] rounded-xl p-4 shadow-xl z-30"
                strength={-10}
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-[#FF5C5C] animate-pulse" />
                  <span className="text-xs font-semibold text-white">
                    Anomaly Detected
                  </span>
                </div>
                <div className="h-10 w-full bg-linear-to-r from-[#242938] via-[#FF5C5C]/20 to-[#242938] rounded opacity-50 relative overflow-hidden">
                  <svg
                    className="w-full h-full"
                    viewBox="0 0 100 20"
                    preserveAspectRatio="none"
                  >
                    <path
                      d="M0,10 L20,10 L30,5 L40,15 L50,10 L60,10 L70,18 L80,2 L90,10 L100,10"
                      fill="none"
                      stroke="#FF5C5C"
                      strokeWidth="2"
                    />
                  </svg>
                </div>
              </ParallaxCard>
              <ParallaxCard
                className="absolute -bottom-10 left-0 lg:-left-10 w-56 bg-[#161A23]/80 backdrop-blur-xl border border-[#00C2A8]/30 rounded-xl p-4 shadow-xl z-30"
                strength={-7}
              >
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-[#00C2A8]" />
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-white">
                      Contract Verified
                    </span>
                    <span className="text-xs text-[#9AA3B2]">
                      No breaking changes
                    </span>
                  </div>
                </div>
              </ParallaxCard>
              <svg
                className="absolute inset-0 w-full h-full z-0 opacity-40"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
              >
                <motion.path
                  d="M10,50 Q40,10 70,50 T90,80"
                  fill="none"
                  stroke="#5B5DFF"
                  strokeWidth="0.5"
                  strokeDasharray="2 2"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                />
                <motion.path
                  d="M10,80 Q30,60 60,80 T90,20"
                  fill="none"
                  stroke="#00C2A8"
                  strokeWidth="0.5"
                  strokeDasharray="2 2"
                  initial={{ pathLength: 0, opacity: 0.5 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                />
              </svg>
            </motion.div>
          </div>
        </section>

        {/* Stats Bar */}
        <section
          ref={statsRef}
          className="relative z-10 border-y border-[#242938] bg-[#161A23]/50 backdrop-blur-sm py-10"
        >
          <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              {
                label: "Native Integrations",
                value: stats.integrations,
                suffix: "+",
                color: "text-[#5B5DFF]",
              },
              {
                label: "Uptime Guarantee",
                value: stats.uptime,
                suffix: "%",
                color: "text-[#00C2A8]",
                decimals: 1,
              },
              {
                label: "Inference Speed",
                value: stats.inference,
                suffix: "ms",
                color: "text-[#3A8DFF]",
              },
              {
                label: "Endpoints Monitored",
                value: stats.endpoints,
                suffix: "+",
                color: "text-[#F5B74F]",
              },
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <p
                  className={`text-3xl md:text-4xl font-extrabold tabular-nums ${stat.color}`}
                >
                  {stat.decimals !== undefined
                    ? stat.value.toFixed(stat.decimals)
                    : Math.round(stat.value).toLocaleString()}
                  {stat.suffix}
                </p>
                <p className="text-[#9AA3B2] text-sm mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Features */}
        <section
          id="features"
          ref={featuresRef}
          className="py-24 relative z-10 bg-[#0F1117]/50 backdrop-blur-3xl"
        >
          <WaveDivider />
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl md:text-5xl font-bold mb-6 text-white">
                Everything Your APIs Need <br className="hidden sm:block" />
                To Stay Reliable
              </h2>
              <p className="text-[#9AA3B2] text-lg">
                Purpose-built tools for modern engineering teams to proactively
                monitor, test, and validate their API infrastructure.
              </p>
            </div>
            <div className="grid md:grid-cols-2 gap-6">
              {[
                {
                  title: "Predict Failures Early",
                  desc: "Machine learning detects abnormal latency and error patterns before incidents occur.",
                  icon: <Activity className="w-6 h-6 text-[#5B5DFF]" />,
                  color: "from-[#5B5DFF]",
                  visual: (
                    <div className="h-full w-full bg-[#161A23] rounded-lg border border-[#242938] overflow-hidden relative p-4 flex items-end">
                      <div className="absolute top-4 left-4 text-xs font-mono text-[#9AA3B2]">
                        Failure Probability:{" "}
                        <span className="text-[#FF5C5C]">84%</span>
                      </div>
                      <div className="w-full flex items-end gap-1 h-20">
                        {[20, 30, 25, 40, 35, 60, 85, 90, 40].map((h, i) => (
                          <motion.div
                            key={i}
                            className={`w-full rounded-t-sm ${h > 70 ? "bg-[#FF5C5C]" : "bg-[#5B5DFF]"}`}
                            initial={{ height: 0 }}
                            animate={
                              featuresInView
                                ? { height: `${h}%` }
                                : { height: 0 }
                            }
                            transition={{
                              duration: 0.6,
                              delay: i * 0.07,
                              ease: "easeOut",
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  ),
                },
                {
                  title: "Test APIs Like Postman",
                  desc: "Built-in API testing kit with request builder, response viewer, and contract validation.",
                  icon: <Terminal className="w-6 h-6 text-[#3A8DFF]" />,
                  color: "from-[#3A8DFF]",
                  visual: (
                    <div className="h-full w-full bg-[#161A23] rounded-lg border border-[#242938] p-4 flex flex-col gap-2 font-mono text-xs">
                      <div className="flex gap-2">
                        <span className="bg-[#242938] text-[#3A8DFF] px-2 py-1 rounded">
                          GET
                        </span>
                        <span className="bg-[#0F1117] border border-[#242938] text-[#E6EAF2] px-2 py-1 rounded flex-1 truncate">
                          api.acme.com/users
                        </span>
                      </div>
                      <div className="flex-1 bg-[#0F1117] border border-[#242938] rounded p-2 text-[#00C2A8]">{`{ "status": 200, "data": [] }`}</div>
                    </div>
                  ),
                },
                {
                  title: "Contract Intelligence",
                  desc: "Automatically detect schema mismatches, missing fields, and breaking changes.",
                  icon: <Code2 className="w-6 h-6 text-[#00C2A8]" />,
                  color: "from-[#00C2A8]",
                  visual: (
                    <div className="h-full w-full bg-[#161A23] rounded-lg border border-[#242938] p-4 font-mono text-[10px] sm:text-xs">
                      <div className="flex justify-between mb-2">
                        <span className="text-[#9AA3B2]">
                          Expected (OpenAPI)
                        </span>
                        <span className="text-[#9AA3B2]">Actual (Traffic)</span>
                      </div>
                      <div className="flex gap-2">
                        <div className="flex-1 bg-[#0F1117] p-2 rounded border border-[#242938] text-[#9AA3B2]">
                          age: number
                        </div>
                        <div className="flex-1 bg-[#FF5C5C]/10 p-2 rounded border border-[#FF5C5C]/30 text-[#FF5C5C] relative overflow-hidden">
                          age: string
                          <div className="absolute right-2 top-2 w-2 h-2 rounded-full bg-[#FF5C5C] animate-pulse" />
                        </div>
                      </div>
                    </div>
                  ),
                },
                {
                  title: "Telemetry Insights",
                  desc: "Track latency, error rates, and request patterns across all endpoints globally.",
                  icon: <Globe2Icon className="w-6 h-6 text-[#F5B74F]" />,
                  color: "from-[#F5B74F]",
                  visual: (
                    <div className="h-full w-full bg-[#161A23] rounded-lg border border-[#242938] p-4 relative overflow-hidden group">
                      <svg
                        className="w-full h-full"
                        viewBox="0 0 100 40"
                        preserveAspectRatio="none"
                      >
                        <path
                          d="M0,30 Q25,10 50,20 T100,5"
                          fill="none"
                          stroke="#F5B74F"
                          strokeWidth="2"
                          className="opacity-50 group-hover:opacity-100 transition-opacity"
                        />
                        <path
                          d="M0,40 L0,30 Q25,10 50,20 T100,5 L100,40 Z"
                          fill="url(#gradient-orange)"
                          stroke="none"
                          className="opacity-20"
                        />
                        <defs>
                          <linearGradient
                            id="gradient-orange"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop offset="0%" stopColor="#F5B74F" />
                            <stop
                              offset="100%"
                              stopColor="#161A23"
                              stopOpacity={0}
                            />
                          </linearGradient>
                        </defs>
                      </svg>
                    </div>
                  ),
                },
              ].map((feature, i) => (
                <TiltCard key={i}>
                  <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: i * 0.1 }}
                    className="group relative bg-[#161A23] border border-[#242938] rounded-3xl p-8 hover:border-[#5B5DFF]/50 transition-colors overflow-hidden flex flex-col h-87.5"
                  >
                    <div
                      className={`absolute top-0 right-0 w-64 h-64 bg-linear-to-bl ${feature.color} to-transparent opacity-5 rounded-full blur-3xl group-hover:opacity-20 transition-opacity`}
                    />
                    <div className="w-12 h-12 rounded-xl bg-[#0F1117] border border-[#242938] flex items-center justify-center mb-6 relative z-10 group-hover:scale-110 transition-transform">
                      {feature.icon}
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-3 relative z-10">
                      {feature.title}
                    </h3>
                    <p className="text-[#9AA3B2] mb-8 relative z-10 flex-1">
                      {feature.desc}
                    </p>
                    <div className="h-32 mt-auto relative z-10">
                      {feature.visual}
                    </div>
                  </motion.div>
                </TiltCard>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="py-24 relative z-10">
          <div className="max-w-7xl mx-auto px-6">
            <h2 className="text-3xl md:text-5xl font-bold mb-16 text-center text-white">
              From Traffic to Insights
            </h2>
            <div className="flex flex-col md:flex-row items-start justify-between relative">
              <div className="hidden md:block absolute top-11.25 left-[10%] right-[10%] h-px bg-linear-to-r from-[#242938] via-[#5B5DFF] to-[#242938] z-0" />
              {[
                {
                  step: "01",
                  title: "Connect APIs",
                  desc: "Upload OpenAPI specs or integrate live telemetry feeds.",
                  icon: <Database className="w-6 h-6" />,
                },
                {
                  step: "02",
                  title: "Analyze Traffic",
                  desc: "ApiCortex processes telemetry and extracts patterns.",
                  icon: <Activity className="w-6 h-6" />,
                },
                {
                  step: "03",
                  title: "Predict Risk",
                  desc: "ML models detect anomalies and forecast failures.",
                  icon: <Cpu className="w-6 h-6" />,
                },
                {
                  step: "04",
                  title: "Act Promptly",
                  desc: "Get alerts and fix issues before users notice.",
                  icon: <Zap className="w-6 h-6" />,
                },
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.15 }}
                  className="relative z-10 flex flex-col items-center text-center w-full md:w-1/4 px-4 mb-12 md:mb-0"
                >
                  <div className="w-24 h-24 rounded-full bg-[#0F1117] border-2 border-[#242938] flex flex-col items-center justify-center mb-6 shadow-xl relative overflow-hidden group">
                    <div className="absolute inset-0 bg-[#5B5DFF]/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="text-[#5B5DFF] mb-1 relative z-10">
                      {item.icon}
                    </div>
                    <span className="text-[#9AA3B2] font-mono text-xs relative z-10">
                      Step {item.step}
                    </span>
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">
                    {item.title}
                  </h3>
                  <p className="text-[#9AA3B2] text-sm">{item.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Interactive Terminal Demo */}
        <section
          id="terminal-demo"
          className="py-24 relative z-10 bg-[#161A23]/50 border-t border-[#242938]"
        >
          <div className="max-w-4xl mx-auto px-6">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-5xl font-bold mb-4 text-white">
                See It In Action
              </h2>
              <p className="text-[#9AA3B2] text-lg">
                Try the interactive terminal below. No signup required.
              </p>
            </div>
            <TerminalDemo />
          </div>
        </section>

        {/* Before/After Code Diff */}
        <section className="py-24 relative z-10">
          <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold mb-4 text-white">
                Stop Guessing.{" "}
                <span className="text-transparent bg-clip-text bg-linear-to-r from-[#5B5DFF] to-[#00C2A8]">
                  Start Knowing.
                </span>
              </h2>
              <p className="text-[#9AA3B2] text-lg max-w-2xl mx-auto">
                The difference between traditional API monitoring and ApiCortex
                is night and day.
              </p>
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
                className="bg-[#161A23] border border-[#242938] rounded-2xl overflow-hidden"
              >
                <div className="px-4 py-2 border-b border-[#242938] bg-[#FF5C5C]/10 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#FF5C5C]" />
                  <span className="text-xs font-mono text-[#FF5C5C] font-semibold">
                    Without ApiCortex
                  </span>
                </div>
                <div className="p-4 font-mono text-xs leading-relaxed text-[#9AA3B2] space-y-1">
                  <div>
                    <span className="text-[#3A8DFF]">$ </span>curl
                    https://api.acme.com/v1/users
                  </div>
                  <div className="text-[#FF5C5C]">{`{"error": "Internal Server Error"}`}</div>
                  <div className="mt-2">
                    <span className="text-[#3A8DFF]">$ </span>curl
                    https://api.acme.com/v1/orders
                  </div>
                  <div className="text-[#F5B74F]">{`Request timeout after 30s`}</div>
                  <div className="mt-2 text-[#9AA3B2]/50">
                    # Wait... was that a schema change?
                  </div>
                  <div className="text-[#9AA3B2]/50">
                    # Check logs manually at 3am...
                  </div>
                  <div className="text-[#9AA3B2]/50">
                    # Customers already reported outage
                  </div>
                </div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="bg-[#161A23] border border-[#00C2A8]/30 rounded-2xl overflow-hidden"
              >
                <div className="px-4 py-2 border-b border-[#00C2A8]/20 bg-[#00C2A8]/10 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#00C2A8]" />
                  <span className="text-xs font-mono text-[#00C2A8] font-semibold">
                    With ApiCortex
                  </span>
                </div>
                <div className="p-4 font-mono text-xs leading-relaxed space-y-1">
                  <div>
                    <span className="text-[#3A8DFF]">$ </span>apicortex monitor
                    users-service
                  </div>
                  <div className="text-[#00C2A8]">
                    [OK] Contract validated against OpenAPI spec
                  </div>
                  <div className="text-[#F5B74F]">
                    [WARN] Latency spike detected on GET /users
                  </div>
                  <div className="text-[#5B5DFF]">
                    [INFO] ML prediction: 84% risk of failure
                  </div>
                  <div className="mt-2">
                    <span className="text-[#3A8DFF]">$ </span>apicortex test
                    --contract orders-service
                  </div>
                  <div className="text-[#00C2A8]">{`[PASS] 42/42 endpoints validated`}</div>
                  <div className="text-[#00C2A8]">{`[PASS] 0 breaking changes detected`}</div>
                  <div className="text-[#00C2A8]">{`[PASS] CI/CD gate: deploy approved`}</div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Dev Experience */}
        <section
          id="dev-experience"
          className="py-24 relative z-10 bg-linear-to-b from-[#0F1117] to-[#161A23] border-t border-[#242938]"
        >
          <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="relative shadow-2xl rounded-2xl border border-[#242938] bg-[#0F1117] overflow-hidden"
            >
              <div className="h-10 border-b border-[#242938] bg-[#161A23] flex items-center px-4 gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-[#FF5C5C]" />
                  <div className="w-3 h-3 rounded-full bg-[#F5B74F]" />
                  <div className="w-3 h-3 rounded-full bg-[#2ED573]" />
                </div>
                <div className="ml-4 flex-1 text-center text-xs font-mono text-[#9AA3B2]">
                  ApiCortex Testing Kit
                </div>
              </div>
              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 h-100">
                <div className="bg-[#161A23] border border-[#242938] rounded-xl flex flex-col">
                  <div className="p-3 border-b border-[#242938] flex gap-2">
                    <span className="bg-[#5B5DFF] text-white px-2 py-1 rounded text-xs font-bold">
                      POST
                    </span>
                    <span className="bg-[#0F1117] border border-[#242938] text-white px-2 py-1 rounded text-xs font-mono flex-1 truncate">
                      /api/v2/charge
                    </span>
                  </div>
                  <div className="flex-1 p-3">
                    <pre className="font-mono text-[10px] text-[#00C2A8]">{`{
  "amount": 2000,
  "currency": "usd",
  "source": "tok_visa"
}`}</pre>
                  </div>
                  <div className="p-3 border-t border-[#242938]">
                    <Button className="w-full bg-[#5B5DFF] text-white h-8 text-xs relative overflow-hidden group">
                      <span className="relative z-10">Send Request</span>
                      <div className="absolute inset-0 bg-white/20 -translate-x-full group-hover:translate-x-full transition-transform duration-500" />
                    </Button>
                  </div>
                </div>
                <div className="bg-[#161A23] border border-[#242938] border-r-4 border-r-[#2ED573] rounded-xl flex flex-col relative overflow-hidden">
                  <div className="p-3 border-b border-[#242938] flex justify-between items-center bg-[#2ED573]/5">
                    <span className="text-[#2ED573] font-bold text-xs">
                      200 OK
                    </span>
                    <span className="text-[#9AA3B2] text-[10px] font-mono">
                      142ms
                    </span>
                  </div>
                  <div className="flex-1 p-3">
                    <pre className="font-mono text-[10px] text-[#E6EAF2]">{`{
  "id": "ch_12345",
  "object": "charge",
  "amount": 2000,
  "paid": true,
  "status": "succeeded"
}`}</pre>
                  </div>
                  <div className="absolute bottom-3 right-3 bg-[#0F1117] border border-[#242938] px-2 py-1 rounded text-[10px] flex items-center gap-1 text-[#00C2A8]">
                    <CheckCircle2 className="w-3 h-3" /> Contract Matches
                  </div>
                </div>
              </div>
            </motion.div>
            <div className="space-y-8">
              <h2 className="text-3xl md:text-5xl font-bold text-white">
                Built for Developers
              </h2>
              <p className="text-[#9AA3B2] text-lg">
                No more guessing why your endpoint failed in production.
                ApiCortex gives you the tools to test, monitor, and enforce
                schema contracts seamlessly.
              </p>
              <ul className="space-y-4">
                {[
                  "OpenAPI & Swagger natively supported",
                  "Real-time telemetry ingestion via SDK or proxy",
                  "CI/CD integration for contract testing before merging",
                  "Fast, Postman-style API testing interface built-in",
                  "Developer-first layout with zero clutter",
                ].map((item, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: 10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.3, delay: i * 0.1 }}
                    className="flex items-center gap-3 text-white"
                  >
                    <div className="w-6 h-6 rounded-full bg-[#5B5DFF]/20 flex shrink-0 items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-[#5B5DFF]" />
                    </div>
                    {item}
                  </motion.li>
                ))}
              </ul>
              <Button className="mt-4 bg-transparent border border-[#5B5DFF] text-[#5B5DFF] hover:bg-[#5B5DFF]/10 h-12 px-6 rounded-full group">
                Explore the Docs{" "}
                <ChevronRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            </div>
          </div>
        </section>

        {/* Trusted By */}
        <section className="py-20 border-t border-[#242938] bg-[#0F1117]">
          <div className="max-w-7xl mx-auto px-6 text-center">
            <p className="text-sm font-semibold text-[#9AA3B2] tracking-widest uppercase mb-10">
              Trusted by Engineering Teams at
            </p>
            <div className="flex flex-wrap justify-center gap-12 sm:gap-24 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
              <div className="text-2xl font-bold text-white flex items-center gap-2">
                <div className="w-6 h-6 bg-white rounded-sm drop-shadow-md" />{" "}
                Acme Corp
              </div>
              <div className="text-2xl font-bold text-white flex items-center gap-2">
                <div className="w-6 h-6 rounded-full border-4 border-white" />{" "}
                GlobalNet
              </div>
              <div className="text-2xl font-bold text-white flex items-center gap-2">
                <Network className="w-6 h-6" /> DataSystem
              </div>
              <div className="text-2xl font-bold text-white flex items-center gap-2">
                <Lock className="w-6 h-6" /> SecureAPI
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-32 relative overflow-hidden">
          <div className="absolute inset-0 bg-[#5B5DFF] opacity-[0.03] z-0" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[radial-gradient(circle_at_center,var(--tw-gradient-stops))] from-[#5B5DFF]/20 via-[#0F1117]/0 to-transparent z-0" />
          <div className="max-w-4xl mx-auto px-6 relative z-10 text-center">
            <h2 className="text-4xl md:text-6xl font-black text-white leading-tight mb-6">
              Stop Guessing.
              <br />
              <span className="text-transparent bg-clip-text bg-linear-to-r from-[#5B5DFF] to-[#00C2A8]">
                Start Predicting API Failures.
              </span>
            </h2>
            <p className="text-[#9AA3B2] text-xl mb-10 max-w-2xl mx-auto">
              Join the future of API observability. Get machine-learning driven
              insights and contract validation in seconds.
            </p>
            <div className="flex flex-col items-center gap-4">
              <Link href="/login">
                <Button className="h-16 px-10 bg-white text-[#0F1117] hover:bg-[#F8F9FA] rounded-full font-bold text-lg shadow-[0_0_40px_rgba(255,255,255,0.2)] hover:scale-105 transition-all">
                  Start Using ApiCortex
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
              <p className="text-sm text-[#9AA3B2]">
                Free tier available. No credit card required.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer with Wave */}
      <footer className="relative bg-[#0F1117] pt-16 pb-10">
        <div className="absolute top-0 left-0 right-0 h-16 -translate-y-full">
          <svg
            className="w-full h-16"
            viewBox="0 0 1440 64"
            preserveAspectRatio="none"
          >
            <path
              d="M0,64 C240,0 480,64 720,32 C960,0 1200,64 1440,32 L1440,64 Z"
              fill="#0F1117"
            />
          </svg>
        </div>
        <div className="max-w-7xl mx-auto px-6 border-t border-[#242938] pt-16">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 mb-16">
            <div className="col-span-2 lg:col-span-2">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-6 h-6 rounded-md bg-linear-to-br from-[#5B5DFF] to-[#00C2A8] flex items-center justify-center">
                  <Network className="w-3 h-3 text-white" />
                </div>
                <span className="font-bold text-xl tracking-tight text-white">
                  ApiCortex
                </span>
              </div>
              <p className="text-[#9AA3B2] text-sm max-w-xs leading-relaxed">
                The intelligence layer for your API infrastructure. Predicting
                failures, testing contracts, and analyzing telemetry at scale.
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-6">Product</h4>
              <ul className="space-y-4 text-sm text-[#9AA3B2]">
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    API Testing
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Telemetry
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Predictions
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Pricing
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-6">Developers</h4>
              <ul className="space-y-4 text-sm text-[#9AA3B2]">
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Documentation
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    API Reference
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    SDKs
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Status
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-6">Company</h4>
              <ul className="space-y-4 text-sm text-[#9AA3B2]">
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    About
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Blog
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    GitHub
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white transition-colors">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-[#242938] pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-[#9AA3B2] text-sm">
              © 2026 ApiCortex, Inc. All rights reserved.
            </p>
            <div className="flex gap-6 text-sm text-[#9AA3B2]">
              <Link href="#" className="hover:text-white transition-colors">
                Privacy Policy
              </Link>
              <Link href="#" className="hover:text-white transition-colors">
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* ---------- Sub-components ---------- */

function ParallaxCard({
  children,
  className = "",
  strength = -5,
}: {
  children: React.ReactNode;
  className?: string;
  strength?: number;
}) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 80, damping: 40 });
  const springY = useSpring(y, { stiffness: 80, damping: 40 });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const cx = (e.clientX - window.innerWidth / 2) / window.innerWidth;
      const cy = (e.clientY - window.innerHeight / 2) / window.innerHeight;
      x.set(cx * strength * 20);
      y.set(cy * strength * 20);
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, [x, y, strength]);

  return (
    <motion.div className={className} style={{ x: springX, y: springY }}>
      {children}
    </motion.div>
  );
}

function TerminalDemo() {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<
    { type: "input" | "output"; text: string }[]
  >([]);
  const [step, setStep] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = [
    {
      cmd: "apicortex monitor users-service",
      output: [
        "[OK]  Contract validated against OpenAPI v3 spec",
        "[OK]  24 endpoints discovered via SDK telemetry",
        "[INFO] P95 latency: 142ms | Error rate: 0.3%",
      ],
    },
    {
      cmd: "apicortex predict --risk users-service",
      output: [
        "[INFO] Running anomaly detection model...",
        "[WARN] GET /users/{id}: 84% probability of latency spike",
        "[INFO] top feature: request_size_variance = 0.76",
        "[INFO] recommendation: scale replicas before peak",
      ],
    },
    {
      cmd: "apicortex test --contract orders-service",
      output: [
        "[PASS] 42/42 endpoints schema-validated",
        "[PASS] 0 breaking changes in last 24h",
        "[PASS] CI gate: deployment approved",
      ],
    },
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "Enter" || step >= commands.length) return;
    const trimmed = input.trim();
    if (trimmed.toLowerCase() === commands[step].cmd) {
      setHistory((h) => [
        ...h,
        { type: "input", text: commands[step].cmd },
        ...commands[step].output.map((line) => ({
          type: "output" as const,
          text: line,
        })),
      ]);
      setInput("");
      setStep((s) => s + 1);
    }
  };

  const focusInput = () => inputRef.current?.focus();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="bg-[#0F1117] border border-[#242938] rounded-2xl overflow-hidden shadow-2xl cursor-text"
      onClick={focusInput}
    >
      <div className="h-10 border-b border-[#242938] bg-[#161A23] flex items-center px-4 gap-2">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#FF5C5C]" />
          <div className="w-3 h-3 rounded-full bg-[#F5B74F]" />
          <div className="w-3 h-3 rounded-full bg-[#2ED573]" />
        </div>
        <div className="ml-4 text-xs font-mono text-[#9AA3B2]">
          Terminal — ApiCortex CLI
        </div>
      </div>
      <div className="p-4 font-mono text-sm leading-relaxed min-h-80 max-h-100 overflow-y-auto">
        <div className="text-[#9AA3B2]/60 text-xs mb-3">
          # Type the prompted commands and press Enter. Try it!
        </div>
        {history.map((line, i) => (
          <div
            key={i}
            className={`${line.type === "input" ? "text-[#3A8DFF]" : line.text.startsWith("[OK]") ? "text-[#00C2A8]" : line.text.startsWith("[WARN]") ? "text-[#F5B74F]" : line.text.startsWith("[INFO]") ? "text-[#5B5DFF]" : "text-[#9AA3B2]"}`}
          >
            {line.type === "input" && (
              <span className="text-[#5B5DFF]">$ </span>
            )}
            {line.text}
          </div>
        ))}
        {step < commands.length && (
          <div className="flex items-center mt-1">
            <span className="text-[#5B5DFF]">$ </span>
            <span className="text-[#9AA3B2]/50 text-xs mr-2">
              (type: {commands[step].cmd})
            </span>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent border-none outline-none text-[#E6EAF2] font-mono text-sm"
              spellCheck={false}
            />
          </div>
        )}
        {step >= commands.length && (
          <div className="text-[#00C2A8] mt-2">
            All commands executed. Your APIs are now protected!
            <Link
              href="/login"
              className="text-[#5B5DFF] hover:text-[#3A8DFF] ml-2 underline transition-colors"
            >
              Get started →
            </Link>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function Globe2Icon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
      <path d="M2 12h20" />
    </svg>
  );
}
