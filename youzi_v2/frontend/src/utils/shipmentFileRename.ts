/** 本地文件夹重命名（Chrome / Edge File System Access API） */

export type RenamePlanItem = {
  /** 相对所选根目录的当前路径，如 `子目录/运单号.pdf` */
  sourcePath: string
  /** 目标文件名（不含目录） */
  newName: string
  /**
   * 目标子目录（相对根）：Excel「文件夹名」优先；
   * 无则保留源文件所在目录（原地改名）。
   */
  folderName: string
  /** 预览用相对路径，如 `A组/xxx.pdf` 或 `子目录/xxx.pdf` */
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

export type ListedFile = {
  /** 相对根目录路径，使用 `/` */
  relativePath: string
  fileName: string
}

function stemAndExt(filename: string): { stem: string; ext: string } {
  const i = filename.lastIndexOf('.')
  if (i <= 0) return { stem: filename, ext: '' }
  return { stem: filename.slice(0, i), ext: filename.slice(i) }
}

function dirnameRel(relativePath: string): string {
  const i = relativePath.lastIndexOf('/')
  return i < 0 ? '' : relativePath.slice(0, i)
}

function joinRel(dir: string, name: string): string {
  return dir ? `${dir}/${name}` : name
}

function targetPathOf(folderName: string, newName: string): string {
  return joinRel(folderName, newName)
}

export function buildRenamePlans(
  files: ListedFile[],
  items: ShipmentRenameMapItem[],
): { plans: RenamePlanItem[]; unmatchedExcel: string[] } {
  const byNo = new Map(items.map((it) => [it.shipmentNo.trim().toUpperCase(), it]))
  const usedTargets = new Set<string>()
  const plans: RenamePlanItem[] = []
  const matched = new Set<string>()

  for (const file of files) {
    const { stem, ext } = stemAndExt(file.fileName)
    const key = stem.trim().toUpperCase()
    const hit = byNo.get(key)
    if (!hit) {
      plans.push({
        sourcePath: file.relativePath,
        newName: file.fileName,
        folderName: dirnameRel(file.relativePath),
        targetPath: file.relativePath,
        shipmentNo: stem,
        status: 'missing-excel',
      })
      continue
    }
    matched.add(key)
    const excelFolder = (hit.folderName || '').trim()
    const sourceDir = dirnameRel(file.relativePath)
    // Excel 指定文件夹名则归入该子目录；否则在原目录改名
    const destDir = excelFolder || sourceDir
    const newName = `${hit.targetStem}${ext}`
    const targetPath = targetPathOf(destDir, newName)
    if (targetPath === file.relativePath) {
      plans.push({
        sourcePath: file.relativePath,
        newName,
        folderName: destDir,
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
      sourcePath: file.relativePath,
      newName,
      folderName: destDir,
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

type DirWithEntries = DirHandle & {
  entries: () => AsyncIterableIterator<[string, FileSystemHandle]>
}

/** 递归列出根目录下全部文件（含子文件夹）。 */
export async function listDirectoryFiles(
  dir: DirHandle,
  prefix = '',
): Promise<ListedFile[]> {
  const out: ListedFile[] = []
  const anyDir = dir as DirWithEntries
  for await (const [name, handle] of anyDir.entries()) {
    const relativePath = joinRel(prefix, name)
    if (handle.kind === 'file') {
      out.push({ relativePath, fileName: name })
    } else if (handle.kind === 'directory') {
      const nested = await listDirectoryFiles(handle as DirHandle, relativePath)
      out.push(...nested)
    }
  }
  return out.sort((a, b) => a.relativePath.localeCompare(b.relativePath, 'zh'))
}

/** @deprecated 使用 listDirectoryFiles；仅根目录文件名（兼容旧调用） */
export async function listDirectoryFileNames(dir: DirHandle): Promise<string[]> {
  const files = await listDirectoryFiles(dir)
  return files.filter((f) => !f.relativePath.includes('/')).map((f) => f.fileName)
}

async function resolveDir(
  root: DirHandle,
  relativeDir: string,
  options: { create: boolean },
): Promise<DirHandle> {
  if (!relativeDir) return root
  let cur = root
  for (const part of relativeDir.split('/').filter(Boolean)) {
    cur = await cur.getDirectoryHandle(
      part,
      options.create ? { create: true } : undefined,
    )
  }
  return cur
}

async function getSourceFile(
  root: DirHandle,
  sourcePath: string,
): Promise<{ parent: DirHandle; fileName: string; handle: FileSystemFileHandle }> {
  const parts = sourcePath.split('/').filter(Boolean)
  if (!parts.length) throw new Error('空路径')
  const fileName = parts.pop()!
  const parent = await resolveDir(root, parts.join('/'), { create: false })
  const handle = await parent.getFileHandle(fileName)
  return { parent, fileName, handle }
}

async function targetExists(dir: DirHandle, folderName: string, newName: string): Promise<boolean> {
  try {
    const parent = await resolveDir(dir, folderName, { create: false })
    await parent.getFileHandle(newName)
    return true
  } catch {
    return false
  }
}

async function moveFileToTarget(
  root: DirHandle,
  sourcePath: string,
  destDir: string,
  newName: string,
): Promise<void> {
  const { parent: sourceParent, fileName: oldName, handle } = await getSourceFile(root, sourcePath)
  const destParent = await resolveDir(root, destDir, { create: true })

  if (await targetExists(root, destDir, newName)) {
    throw new Error(`目标已存在：${targetPathOf(destDir, newName)}`)
  }

  const sameDir = dirnameRel(sourcePath) === destDir
  const movable = handle as FileSystemFileHandle & {
    move?: (destination: DirHandle | string, name?: string) => Promise<void>
  }
  if (typeof movable.move === 'function') {
    try {
      if (sameDir) {
        await movable.move(newName)
      } else {
        await movable.move(destParent, newName)
      }
      return
    } catch {
      // fall through to copy
    }
  }

  const file = await handle.getFile()
  const newHandle = await destParent.getFileHandle(newName, { create: true })
  const writable = await newHandle.createWritable()
  await writable.write(await file.arrayBuffer())
  await writable.close()
  await sourceParent.removeEntry(oldName)
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
      await moveFileToTarget(dir, plan.sourcePath, plan.folderName, plan.newName)
      ok += 1
    } catch (e) {
      failed.push({
        oldName: plan.sourcePath,
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
