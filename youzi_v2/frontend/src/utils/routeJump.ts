/** 同一次导航由多个缓存页面观察时，仅允许处理一次提示及路由清理。 */
const handledRoutes = new WeakSet<object>()

export function claimRouteJump(route: object): boolean {
  if (handledRoutes.has(route)) return false
  handledRoutes.add(route)
  return true
}
