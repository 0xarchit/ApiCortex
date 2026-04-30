"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight, Home } from "lucide-react";

const routeLabels: Record<string, string> = {
  dashboard: "Dashboard",
  testing: "API Testing",
  apis: "API Domains",
  telemetry: "Telemetry",
  predictions: "Predictions",
  profile: "Profile",
  settings: "Settings",
};

function titleCase(str: string): string {
  return str.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Breadcrumb() {
  const pathname = usePathname();
  if (!pathname || pathname === "/dashboard") return null;

  const segments = pathname.split("/").filter(Boolean);
  const items = segments.map((seg, i) => {
    const href = "/" + segments.slice(0, i + 1).join("/");
    const label = routeLabels[seg] || titleCase(seg);
    const isLast = i === segments.length - 1;
    return { href, label, isLast };
  });

  if (items.length <= 1) return null;

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs mb-4 text-[#9AA3B2] overflow-x-auto">
      <Link href="/dashboard" className="hover:text-[#E6EAF2] transition-colors shrink-0" title="Dashboard">
        <Home className="w-3.5 h-3.5" />
      </Link>
      {items.map((item) => (
        <span key={item.href} className="flex items-center gap-1.5">
          <ChevronRight className="w-3 h-3 shrink-0" />
          {item.isLast ? (
            <span
              aria-current="page"
              className="text-[#E6EAF2] font-medium truncate"
            >
              {item.label}
            </span>
          ) : (
            <Link
              href={item.href}
              className="hover:text-[#E6EAF2] transition-colors truncate"
            >
              {item.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}