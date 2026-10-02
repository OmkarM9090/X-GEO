export interface User {
  id: string;
  name: string;
  email: string;
  workspaceName: string;
  avatarUrl?: string;
}

export interface AppNotification {
  id: string;
  title: string;
  description: string;
  time: string;
  unread: boolean;
  kind: "audit" | "alert" | "report";
}
