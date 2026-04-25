"use client";
import {
  Bell,
  Search,
  ChevronDown,
  User,
  Settings,
  LogOut,
  CircleCheck,
  TriangleAlert,
  Info,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type {
  AuthSession,
  DashboardNotification,
  Organization,
  User as AppUser,
} from "@/lib/api-types";

/**
 * Dashboard topbar that resolves session identity, displays tenant context,
 * and provides profile/settings/logout actions.
 */
export function Topbar() {
  const router = useRouter();

  const [profile, setProfile] = useState<AppUser | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [notifications, setNotifications] = useState<DashboardNotification[]>(
    [],
  );
  const [notificationsLoading, setNotificationsLoading] = useState(false);

  const loadNotifications = async () => {
    setNotificationsLoading(true);
    try {
      const res = await apiClient.get<DashboardNotification[]>(
        "/dashboard/notifications?limit=12",
      );
      setNotifications(res.data);
    } catch {
      setNotifications([]);
    } finally {
      setNotificationsLoading(false);
    }
  };

  useEffect(() => {
    let mounted = true;
    const loadIdentity = async () => {
      try {
        const [profileRes, orgRes, sessionRes] = await Promise.all([
          apiClient.get<AppUser>("/auth/profile"),
          apiClient.get<Organization>("/orgs/current"),
          apiClient.get<AuthSession>("/auth/me"),
        ]);
        if (!mounted) {
          return;
        }
        setProfile(profileRes.data);
        setOrganization(orgRes.data);
        setSession(sessionRes.data);
      } catch {
        if (!mounted) {
          return;
        }
        setProfile(null);
        setOrganization(null);
        setSession(null);
      }
    };
    void loadIdentity();
    void loadNotifications();
    const timer = window.setInterval(() => {
      void loadNotifications();
    }, 20000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const unreadCount = useMemo(
    () => notifications.filter((item) => !item.is_read).length,
    [notifications],
  );

  const markNotificationAsRead = async (id: string) => {
    const target = notifications.find((item) => item.id === id);
    if (!target || target.is_read) {
      return;
    }
    try {
      await apiClient.post(`/dashboard/notifications/${id}/read`);
      setNotifications((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, is_read: true, read_at: new Date().toISOString() }
            : item,
        ),
      );
    } catch {}
  };

  const markAllNotificationsRead = async () => {
    if (unreadCount === 0) {
      return;
    }
    try {
      await apiClient.post("/dashboard/notifications/read-all");
      setNotifications((prev) =>
        prev.map((item) => ({
          ...item,
          is_read: true,
          read_at: item.read_at ?? new Date().toISOString(),
        })),
      );
    } catch {}
  };

  const formatNotificationTime = (iso: string) => {
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) {
      return "now";
    }
    return dt.toLocaleString();
  };

  const severityIcon = (severity: DashboardNotification["severity"]) => {
    if (severity === "warning" || severity === "critical") {
      return <TriangleAlert className="w-4 h-4 text-[#F5B74F]" />;
    }
    if (severity === "success") {
      return <CircleCheck className="w-4 h-4 text-[#00C2A8]" />;
    }
    return <Info className="w-4 h-4 text-[#3A8DFF]" />;
  };

  const displayName = profile?.name?.trim() || "User";
  const displayEmail = profile?.email?.trim() || "No email";
  const displayOrg = organization?.name?.trim() || "No Organization";
  const roleLabel = session?.role
    ? `${session.role.charAt(0).toUpperCase()}${session.role.slice(1)}`
    : "Member";

  const userInitials = useMemo(() => {
    const seed = displayName.trim();
    const value = seed
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
    return value || "U";
  }, [displayName]);

  const orgInitials = useMemo(() => {
    const seed = displayOrg.trim();
    const value = seed
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
    return value || "OR";
  }, [displayOrg]);

  /**
   * Terminates the active session and clears client auth state before redirecting.
   */
  const handleLogout = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
    } finally {
      document.cookie =
        "acx_access=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      document.cookie =
        "acx_refresh=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      document.cookie =
        "acx_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      router.push("/login");
      router.refresh();
    }
  };

  return (
    <div className="h-16 border-b border-[#242938] bg-[#0F1117]/80 backdrop-blur-xl sticky top-0 z-40 flex items-center justify-between px-6">
      <div className="flex items-center gap-4 flex-1">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9AA3B2]" />
          <Input
            type="text"
            placeholder="Search APIs, endpoints, tests..."
            className="pl-9 bg-[#161A23] border-[#242938] text-[#E6EAF2] placeholder:text-[#9AA3B2] focus-visible:ring-[#5B5DFF] h-9 rounded-lg"
          />
        </div>
      </div>
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2 cursor-pointer hover:bg-[#161A23] px-3 py-1.5 rounded-lg transition-colors border border-transparent hover:border-[#242938]">
          <div className="w-5 h-5 rounded bg-linear-to-tr from-[#5B5DFF] to-[#3A8DFF] flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
            {orgInitials}
          </div>
          <span className="text-sm font-medium text-[#E6EAF2]">
            {displayOrg}
          </span>
          <ChevronDown className="w-4 h-4 text-[#9AA3B2]" />
        </div>
        <div className="flex items-center gap-4 border-l border-[#242938] pl-5">
          <DropdownMenu>
            <DropdownMenuTrigger className="relative text-[#9AA3B2] hover:text-[#E6EAF2] transition-colors rounded-full p-1 hover:bg-[#161A23] outline-none">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 ? (
                <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-[#FF5C5C] text-[10px] leading-4 text-white border border-[#0F1117]">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              ) : null}
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-95 max-w-[92vw] bg-[#161A23] border-[#242938] text-[#E6EAF2] rounded-xl shadow-[0_10px_40px_rgba(0,0,0,0.5)] p-0 overflow-hidden"
            >
              <div className="flex items-center justify-between px-3 py-2 border-b border-[#242938]">
                <span className="text-sm font-semibold">Notifications</span>
                <button
                  className="text-xs text-[#9AA3B2] hover:text-[#E6EAF2] disabled:opacity-50"
                  onClick={markAllNotificationsRead}
                  disabled={unreadCount === 0}
                >
                  Mark all read
                </button>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notificationsLoading ? (
                  <div className="px-3 py-6 text-center text-sm text-[#9AA3B2]">
                    Loading notifications...
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="px-3 py-6 text-center text-sm text-[#9AA3B2]">
                    No notifications yet.
                  </div>
                ) : (
                  notifications.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => markNotificationAsRead(item.id)}
                      className={`w-full text-left px-3 py-3 border-b border-[#242938] last:border-b-0 hover:bg-[#1B2030] transition-colors ${item.is_read ? "opacity-70" : ""}`}
                    >
                      <div className="flex items-start gap-2">
                        <div className="mt-0.5 shrink-0">
                          {severityIcon(item.severity)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium text-[#E6EAF2] truncate">
                              {item.title}
                            </p>
                            {!item.is_read ? (
                              <span className="w-2 h-2 rounded-full bg-[#5B5DFF] shrink-0" />
                            ) : null}
                          </div>
                          <p className="text-xs text-[#9AA3B2] mt-0.5 wrap-break-word whitespace-pre-wrap">
                            {item.message}
                          </p>
                          <p className="text-[10px] text-[#7B8497] mt-1">
                            {formatNotificationTime(item.created_at)}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger className="outline-none">
              <Avatar className="w-8 h-8 cursor-pointer ring-2 ring-transparent hover:ring-[#5B5DFF] transition-all">
                <AvatarImage src="" />
                <AvatarFallback>{userInitials}</AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="w-56 bg-[#161A23] border-[#242938] text-[#E6EAF2] rounded-xl shadow-[0_10px_40px_rgba(0,0,0,0.5)]"
              align="end"
            >
              <div className="px-2 py-1.5 text-sm font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none text-white">
                    {displayName}
                  </p>
                  <p className="text-xs leading-none text-[#9AA3B2]">
                    {displayEmail}
                  </p>
                  <p className="text-xs leading-none text-[#9AA3B2]">
                    {roleLabel}
                  </p>
                </div>
              </div>
              <DropdownMenuSeparator className="bg-[#242938]" />
              <DropdownMenuGroup>
                <Link href="/profile" prefetch>
                  <DropdownMenuItem className="cursor-pointer focus:bg-[#242938] focus:text-white group">
                    <User className="mr-2 h-4 w-4 text-[#9AA3B2] group-hover:text-white" />
                    <span>Profile</span>
                  </DropdownMenuItem>
                </Link>
                <Link href="/settings" prefetch>
                  <DropdownMenuItem className="cursor-pointer focus:bg-[#242938] focus:text-white group">
                    <Settings className="mr-2 h-4 w-4 text-[#9AA3B2] group-hover:text-white" />
                    <span>Settings</span>
                  </DropdownMenuItem>
                </Link>
              </DropdownMenuGroup>
              <DropdownMenuSeparator className="bg-[#242938]" />
              <DropdownMenuItem
                className="cursor-pointer focus:bg-[#242938] text-[#FF5C5C] focus:text-[#FF5C5C] group"
                onClick={handleLogout}
              >
                <LogOut className="mr-2 h-4 w-4 text-[#FF5C5C]" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </div>
  );
}
