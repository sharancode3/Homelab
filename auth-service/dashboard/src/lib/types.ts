export interface Project {
  project_id: string;
  name: string;
  created_at: string;
}

export interface ProjectMember {
  user_id: string;
  username: string;
  role: "owner" | "admin" | "developer" | "viewer";
}
