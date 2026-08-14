export interface OperationResponse {
  operation_id: string
  status: string
  completed_steps: string[]
  failures: string[]
}

export interface HealthResponse {
  project_id: string
  state: string
  status: string
  success: boolean
  message: string
}

export interface LogEventResponse {
  audit_id: string
  timestamp: string
  event_type: string
  severity: string
  message: string
}

export interface LogsResponse {
  project_id: string
  logs: LogEventResponse[]
}

export interface ProjectStatusResponse {
  project_id: string
  lifecycle_state: string
  deployment_status: string
  simulated: boolean
  message: string
}

export interface OperationHistoryEntry {
  operation_id: string
  status: string
  completed_steps: string[]
  failures: string[]
}

export interface OperationHistoryResponse {
  project_id: string
  total_returned: number
  history: OperationHistoryEntry[]
}

export interface DeployRequest {
  configuration?: Record<string, any>
}

export interface BackupRequest {
  backup_type?: string
}

export interface RestoreRequest {
  backup_id: string
}
