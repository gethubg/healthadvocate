// Mirrors the backend pydantic schemas (see backend/src/healthadvocate/models.py).

export type Direction = 'high' | 'low';

export interface LabValue {
  parameter: string;
  value: number;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  range_available: boolean;
}

export interface ReportMeta {
  report_id: string;
  filename: string;
  report_date: string;
  uploaded_at: string;
}

export interface UploadResponse {
  report_id: string;
  filename: string;
  report_date: string;
  uploaded_at: string;
  parsed_parameters: LabValue[];
  warnings: string[];
}

export interface AbnormalFinding {
  parameter: string;
  value: number;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  direction: Direction;
}

export interface Source {
  title: string;
  url: string;
}

export interface FoodAdvice {
  parameter: string;
  foods_to_avoid: string[];
  sources: Source[];
}

export interface AskResponse {
  answer: string;
  report_id: string | null;
  report_date: string | null;
  findings: AbnormalFinding[];
  advice: FoodAdvice[];
}

export interface TrendPoint {
  report_date: string;
  value: number;
  ref_low: number | null;
  ref_high: number | null;
  abnormal: boolean;
}

export interface TrendSeries {
  parameter: string;
  unit: string | null;
  points: TrendPoint[];
}
