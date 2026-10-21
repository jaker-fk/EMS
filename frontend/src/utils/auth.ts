const PERM_KEY = 'perms'

export function setPerms(perms: string[]): void {
  localStorage.setItem(PERM_KEY, JSON.stringify(perms || []))
}

export function getPerms(): string[] {
  try {
    return JSON.parse(localStorage.getItem(PERM_KEY) || '[]')
  } catch {
    return []
  }
}

/** 按钮级权限判断：拥有通配符 * 或指定权限标识即可见 */
export function hasPerm(perm?: string): boolean {
  if (!perm) return true
  const perms = getPerms()
  return perms.includes('*') || perms.includes(perm)
}
