export interface Column {
  name: string;
  type: string; // TEXT, INTEGER, BOOLEAN, etc
  is_nullable: boolean;
  is_primary_key: boolean;
}

export interface Table {
  name: string;
  created_at: string;
  columns?: Column[];
}

export interface TableDataResponse {
  data: Record<string, any>[];
  total: number;
  limit: number;
  offset: number;
}
