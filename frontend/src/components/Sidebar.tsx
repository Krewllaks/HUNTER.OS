"use client";

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, Users, Zap,
  BarChart3, Settings, LogOut, Globe, Plus,
} from "lucide-react";
import { useI18n } from "@/hooks/useI18n";

const NAV_ITEMS = [
  { labelKey: "nav.dashboard", href: "/dashboard", icon: LayoutDashboard },
  { labelKey: "nav.leads", href: "/leads", icon: Users },
  { labelKey: "nav.campaigns", href: "/campaigns", icon: Zap },
  { labelKey: "nav.analytics", href: "/analytics", icon: BarChart3 },
  { labelKey: "nav.settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { locale, t, toggleLanguage } = useI18n();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const userPlan = (user as any)?.plan || "trial";

  return (
    <aside className="fixed left-0 top-0 h-screen w-sidebar bg-[#1A1A1A] border-r border-[#2A2A2A] flex flex-col z-50">
      {/* Logo */}
      <div className="px-grid-3 py-grid-3 border-b border-[#2A2A2A]">
        <h1 className="font-display text-display-sm tracking-tight text-white">
          HUNTER<span className="text-primary">.OS</span>
        </h1>
        <p className="text-label text-[#8B6B5A] mt-0.5">PRECISION GROWTH</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-grid-2 py-grid-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-grid-2 px-grid-2 py-grid-1 rounded-sm text-body-md transition-all duration-100 cursor-pointer ${
                isActive
                  ? "text-primary bg-primary/10 font-medium"
                  : "text-[#9E9E9E] hover:text-white hover:bg-[#2A2A2A]"
              }`}
            >
              <item.icon size={18} strokeWidth={isActive ? 2.5 : 1.5} />
              <span>{t(item.labelKey)}</span>
            </Link>
          );
        })}
      </nav>

      {/* New Campaign Button */}
      <div className="px-grid-2 py-grid-2">
        <button
          onClick={() => router.push("/campaigns")}
          className="w-full flex items-center justify-center gap-2 px-grid-2 py-grid-1 bg-primary text-white rounded-sm font-medium text-body-md hover:bg-primary-hover active:scale-[0.98] transition-all"
        >
          <Plus size={18} />
          <span>{t("campaigns.new")}</span>
        </button>
      </div>

      {/* Footer */}
      <div className="px-grid-2 py-grid-2 border-t border-[#2A2A2A] space-y-1">
        {/* Language Toggle */}
        <button
          onClick={toggleLanguage}
          className="flex items-center gap-grid-2 px-grid-2 py-grid-1 rounded-sm text-body-md text-[#9E9E9E] hover:text-white hover:bg-[#2A2A2A] w-full transition-all duration-100 cursor-pointer"
        >
          <Globe size={18} strokeWidth={1.5} />
          <span>{locale === "tr" ? "TR → EN" : "EN → TR"}</span>
        </button>

        {user && (
          <div className="px-grid-2 py-grid-1">
            <p className="text-body-sm font-medium text-white truncate">{user.full_name}</p>
            <p className="text-label text-[#9E9E9E] truncate">{user.email}</p>
            <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded capitalize mt-0.5 inline-block">
              {userPlan}
            </span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-grid-2 px-grid-2 py-grid-1 rounded-sm text-body-md text-[#9E9E9E] hover:text-red-400 hover:bg-[#2A2A2A] w-full transition-all duration-100 cursor-pointer"
        >
          <LogOut size={18} strokeWidth={1.5} />
          <span>{t("common.logout")}</span>
        </button>
      </div>
    </aside>
  );
}
