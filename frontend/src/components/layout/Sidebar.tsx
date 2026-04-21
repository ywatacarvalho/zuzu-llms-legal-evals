import { BarChart2, BookOpen, ClipboardList, FileText, Info, LayoutDashboard } from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";

import { branding } from "@/config/branding";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  labelKey: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.dashboard", icon: <LayoutDashboard className="h-4 w-4" /> },
  { to: "/cases", labelKey: "nav.cases", icon: <FileText className="h-4 w-4" /> },
  { to: "/rubrics", labelKey: "nav.rubrics", icon: <ClipboardList className="h-4 w-4" /> },
  { to: "/evaluations", labelKey: "nav.evaluations", icon: <BookOpen className="h-4 w-4" /> },
  { to: "/results", labelKey: "nav.results", icon: <BarChart2 className="h-4 w-4" /> },
  { to: "/description", labelKey: "nav.methodology", icon: <Info className="h-4 w-4" /> },
];

export function Sidebar() {
  const { t } = useTranslation();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-56 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-14 items-center border-b border-sidebar-border px-5">
        <span className="text-base font-bold tracking-tight text-sidebar-foreground">
          {branding.logoText}
        </span>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        <ul className="space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )
                }
              >
                {item.icon}
                {t(item.labelKey)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
