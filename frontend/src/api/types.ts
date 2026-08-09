export interface Profile {
  id: number;
  display_name: string;
  email: string;
}

export interface Institution {
  id: number;
  name: string;
  kind: string;
  status: string;
  closed_at: string | null;
  closed_reason: string | null;
}

export interface Account {
  id: number;
  institution_id: number;
  display_name: string;
  mask: string | null;
  type: string;
  currency: string;
  is_liquid: boolean;
  opened_at: string | null;
  closed_at: string | null;
}

export interface Transaction {
  id: number;
  account_id: number;
  posted_date: string;
  transaction_date: string | null;
  description_raw: string;
  description_clean: string | null;
  merchant: string | null;
  amount_minor: number;
  currency: string;
  type: string;
  pending: boolean;
  source: string;
  source_document_id: number | null;
  category_id: number | null;
  category_confidence: number | null;
  category_source: string | null;
  reviewed_at: string | null;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  is_system: boolean;
}

export interface DocumentRow {
  id: number;
  account_id: number | null;
  kind: string;
  filename: string;
  period_start: string | null;
  period_end: string | null;
  parse_status: string;
  parse_error: string | null;
  uploaded_at: string;
}

export interface BalanceRow {
  account_id: number;
  as_of: string;
  current_minor: number;
  available_minor: number | null;
  source: string;
}

export interface SyncStatus {
  provider: string;
  last_run: {
    run_id: number;
    status: string;
    started_at: string | null;
    finished_at: string | null;
    records_ingested: number;
    error: string | null;
  } | null;
}
