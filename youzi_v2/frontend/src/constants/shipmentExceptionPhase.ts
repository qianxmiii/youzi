/** 运单异常类型大类（码表 shipment_exception_codes.phase_category） */

export type ShipmentExceptionPhase = 'pre_port' | 'post_port'

export const SHIPMENT_EXCEPTION_PHASE_PRE_PORT: ShipmentExceptionPhase = 'pre_port'
export const SHIPMENT_EXCEPTION_PHASE_POST_PORT: ShipmentExceptionPhase = 'post_port'

export const SHIPMENT_EXCEPTION_PHASE_LABEL: Record<ShipmentExceptionPhase, string> = {
  pre_port: '港前',
  post_port: '港后',
}

export function shipmentExceptionPhaseLabel(
  phase: string | null | undefined,
): string {
  const key = (phase || SHIPMENT_EXCEPTION_PHASE_POST_PORT) as ShipmentExceptionPhase
  return SHIPMENT_EXCEPTION_PHASE_LABEL[key] ?? SHIPMENT_EXCEPTION_PHASE_LABEL.post_port
}

export const shipmentExceptionPhaseFilterOptions = [
  { label: '全部大类', value: '' },
  { label: '港前', value: SHIPMENT_EXCEPTION_PHASE_PRE_PORT },
  { label: '港后', value: SHIPMENT_EXCEPTION_PHASE_POST_PORT },
] as const
