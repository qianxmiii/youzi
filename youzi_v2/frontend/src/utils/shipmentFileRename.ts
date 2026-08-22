/** 本地文件夹重命名（Chrome / Edge File System Access API） */

export type RenamePlanItem = {
  oldName: string
  /** 目标文件名（不含目录） */
  newName: string
  /** 子文件夹名；空表示仍在所选根目录 */
  folderName: string
  /** 预览用相对路径，如 `A组/xxx.pdf` 或 `xxx.pdf` */
  targetPath: string
  shipmentNo: string
  status: 'ready' | 'skip-same' | 'conflict' | 'missing-excel'
}

export type ShipmentRenameMapItem = {
  shipmentNo: string
  country: string
  addressCode: string
  ctns: string
  folderName?: string
  targetStem: string
}

function stemAndExt(filename: string): { stem: string; ext: string } {
  const i = filename.lastIndexOf('.')
  if (i <= 0) return { stem: filename, ext: '' }
  return { stem: filename.slice(0, i), ext: filename.slice(i) }
}

function targetPathOf(folderName: string, newName: string): string {
  return folderName ? `${folderName}/${newName}` : newName
}

export function buildRenamePlans(
  fileNames: string[],
  items: ShipmentRenameMapItem[],
): { plans: RenamePlanItem[]; unmatchedExcel: string[] } {
  const byNo = new Map(items.map((it) => [it.shipmentNo.trim().toUpperCase(), it]))
  const usedTargets = new Set<string>()
  const plans: RenamePlanItem[] = []
  const matched = new Set<string>()

  for (const oldName of fileNames) {
    const { stem, ext } = stemAndExt(oldName)
    const key = stem.trim().toUpperCase()
    const hit = byNo.get(key)
    if (!hit) {
      plans.push({
        oldName,
        newName: oldName,
        folderName: '',
        targetPath: oldName,
        shipmentNo: stem,
        status: 'missing-excel',
      })
      continue
    }
    matched.add(key)
    const folderName = (hit.folderName || '').trim()
    const newName = `${hit.targetStem}${ext}`
    const targetPath = targetPathOf(folderName, newName)
    // 无子目录且文件名未变 → 跳过
    if (!folderName && newName === oldName) {
      plans.push({
        oldName,
        newName,
        folderName: '',
        targetPath,
        shipmentNo: hit.shipmentNo,
        status: 'skip-same',
      })
      continue
    }
    const pathKey = targetPath.toUpperCase()
    const conflict = usedTargets.has(pathKey)
    usedTargets.add(pathKey)
    plans.push({
      oldName,
      newName,
      folderName,
      targetPath,
      shipmentNo: hit.shipmentNo,
      status: conflict ? 'conflict' : 'ready',
    })
  }

  const unmatchedExcel = items
    .filter((it) => !matched.has(it.shipmentNo.trim().toUpperCase()))
    .map((it) => it.shipmentNo)

  return { plans, unmatchedExcel }
}

type DirHandle = FileSystemDirectoryHandle

export async function listDirectoryFileNames(dir: DirHandle): Promise<string[]> {
  const names: string[] = []
  const anyDir = dir as DirHandle & {
    entries: () => AsyncIterableIterator<[string, FileSystemHandle]>
  }
  for await (const [name, handle] of anyDir.entries()) {
    if (handle.kind === 'file') names.push(name)
  }
  return names.sort((a, b) => a.localeCompare(b))
}

async function ensureSubdir(dir: DirHandle, folderName: string): Promise<DirHandle> {
  if (!folderName) return dir
  return dir.getDirectoryHandle(folderName, { create: true })
}

async function targetExists(dir: DirHandle, folderName: string, newName: string): Promise<boolean> {
  try {
    const parent = folderName ? await dir.getDirectoryHandle(folderName) : dir
    await parent.getFileHandle(newName)
    return true
  } catch {
    return false
  }
}

async function moveFileToTarget(
  root: DirHandle,
  oldName: string,
  folderName: string,
  newName: string,
): Promise<void> {
  const fileHandle = await root.getFileHandle(oldName)
  const destDir = await ensureSubdir(root, folderName)

  if (await targetExists(root, folderName, newName)) {
    throw new Error(`目标已存在：${targetPathOf(folderName, newName)}`)
  }

  const movable = fileHandle as FileSystemFileHandle & {
    move?: (destination: DirHandle | string, name?: string) => Promise<void>
  }
  if (typeof movable.move === 'function') {
    try {
      if (folderName) {
        await movable.move(destDir, newName)
      } else {
        await movable.move(newName)
      }
      return
    } catch {
      // fall through to copy
    }
  }

  const file = await fileHandle.getFile()
  const newHandle = await destDir.getFileHandle(newName, { create: true })
  const writable = await newHandle.createWritable()
  await writable.write(await file.arrayBuffer())
  await writable.close()
  await root.removeEntry(oldName)
}

export async function applyRenamePlans(
  dir: DirHandle,
  plans: RenamePlanItem[],
): Promise<{ ok: number; failed: { oldName: string; message: string }[] }> {
  let ok = 0
  const failed: { oldName: string; message: string }[] = []
  for (const plan of plans) {
    if (plan.status !== 'ready') continue
    try {
      await moveFileToTarget(dir, plan.oldName, plan.folderName, plan.newName)
      ok += 1
    } catch (e) {
      failed.push({
        oldName: plan.oldName,
        message: e instanceof Error ? e.message : String(e),
      })
    }
  }
  return { ok, failed }
}

export function supportsDirectoryPicker(): boolean {
  return typeof window !== 'undefined' && typeof (window as Window & {
    showDirectoryPicker?: unknown
  }).showDirectoryPicker === 'function'
}
