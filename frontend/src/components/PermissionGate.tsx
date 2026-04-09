"use client";

import { usePermissions } from "@/hooks/usePermissions";

type Props = {
  permission?: string;
  feature?: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
};

export function PermissionGate({ permission, feature, fallback = null, children }: Props) {
  const { hasPermission, hasFeature } = usePermissions();

  if (permission && !hasPermission(permission as Parameters<typeof hasPermission>[0])) {
    return <>{fallback}</>;
  }

  if (feature && !hasFeature(feature)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
