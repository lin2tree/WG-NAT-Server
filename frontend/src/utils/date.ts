export function formatDateTime(utcDateString: string | null | undefined): string {
  if (!utcDateString) return '-'
  
  const utcString = utcDateString.endsWith('Z') ? utcDateString : utcDateString + 'Z'
  
  const date = new Date(utcString)
  
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export function formatDateTimeShort(utcDateString: string | null | undefined): string {
  if (!utcDateString) return '-'
  
  const utcString = utcDateString.endsWith('Z') ? utcDateString : utcDateString + 'Z'
  
  const date = new Date(utcString)
  
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
