import { api } from '@/api/client'

export interface WorkbenchFocusMetrics {
  available: boolean
  error?: string | null
  pendingExceptions: number
  pendingCollections: number
  pendingTrackingReviews: number
  arrivingSoon: number
}

export type WorkbenchTodoKind = 'exception' | 'payment' | 'tracking_review'

export interface WorkbenchTodoItem {
  id: string
  kinds: WorkbenchTodoKind[]
  priority: number
  severity: string
  shipmentId?: string | null
  shipmentNo?: string | null
  customer: string
  title: string
  summary: string
  href: string
  overdueDays: number
  triggerTime?: string | null
  updatedTime?: string | null
}

export interface WorkbenchTodosModule {
  available: boolean
  error?: string | null
  items: WorkbenchTodoItem[]
}

export type WorkbenchArrivalDayGroup = 'today' | 'tomorrow' | 'later'

export interface WorkbenchArrivalItem {
  dayGroup: WorkbenchArrivalDayGroup
  vesselVoyage: string
  destinationPortCode: string
  eta: string | null
  shipmentCount: number
  isSubscribedPort: boolean
  href: string
}

export interface WorkbenchArrivalsModule {
  available: boolean
  error?: string | null
  items: WorkbenchArrivalItem[]
}

export interface WorkbenchTransportOverview {
  available: boolean
  error?: string | null
  inTransit: number
  inspection: number
  arrivedUnsigned: number
  deliveredThisWeek: number
}

export interface WorkbenchOverview {
  generatedAt: string
  focus: WorkbenchFocusMetrics
  todos: WorkbenchTodosModule
  arrivals: WorkbenchArrivalsModule
  overview: WorkbenchTransportOverview
}

export type WorkbenchOverviewParams = {
  todoLimit?: number
  arrivalLimit?: number
}

export function getWorkbenchOverview(params: WorkbenchOverviewParams = {}) {
  return api<WorkbenchOverview>('/api/v1/workbench/overview', {
    query: {
      todoLimit: params.todoLimit ?? 8,
      arrivalLimit: params.arrivalLimit ?? 6,
    },
  })
}
