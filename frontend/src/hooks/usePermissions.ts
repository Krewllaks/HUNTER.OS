"use client";

import { useAuth } from "@/context/AuthContext";

type Permission =
  | "manage_team"
  | "view_audit_logs"
  | "manage_billing"
  | "manage_campaigns"
  | "send_messages"
  | "view_leads"
  | "export_data"
  | "manage_accounts"
  | "view_analytics"
  | "manage_settings";

const ROLE_PERMISSIONS: Record<string, Permission[]> = {
  admin: [
    "manage_team", "view_audit_logs", "manage_billing", "manage_campaigns",
    "send_messages", "view_leads", "export_data", "manage_accounts",
    "view_analytics", "manage_settings",
  ],
  manager: [
    "manage_campaigns", "send_messages", "view_leads", "export_data",
    "manage_accounts", "view_analytics",
  ],
  member: [
    "manage_campaigns", "send_messages", "view_leads", "view_analytics",
  ],
  viewer: [
    "view_leads", "view_analytics",
  ],
};

const PLAN_FEATURES: Record<string, string[]> = {
  trial: ["basic_discovery", "basic_messaging"],
  pro: ["basic_discovery", "basic_messaging", "linkedin_automation", "advanced_analytics", "ab_testing"],
  enterprise: [
    "basic_discovery", "basic_messaging", "linkedin_automation", "advanced_analytics",
    "ab_testing", "team_management", "audit_logs", "api_access", "custom_integrations",
  ],
};

export function usePermissions() {
  const { user } = useAuth();

  const hasPermission = (permission: Permission): boolean => {
    if (!user) return false;
    const rolePerms = ROLE_PERMISSIONS[user.role] || [];
    return rolePerms.includes(permission);
  };

  const hasFeature = (feature: string): boolean => {
    if (!user) return false;
    const planFeatures = PLAN_FEATURES[user.plan || "trial"] || [];
    return planFeatures.includes(feature);
  };

  const isAdmin = user?.role === "admin";
  const isManager = user?.role === "admin" || user?.role === "manager";
  const canManageTeam = hasPermission("manage_team");
  const canViewAuditLogs = hasPermission("view_audit_logs");
  const canManageBilling = hasPermission("manage_billing");

  return {
    hasPermission,
    hasFeature,
    isAdmin,
    isManager,
    canManageTeam,
    canViewAuditLogs,
    canManageBilling,
    user,
  };
}
