import client from './client'

/** Fetches a file with the login token and hands it to the browser as a download. Returns the file name. */
export async function downloadFile(path, fallbackName) {
  const res = await client.get(path, { responseType: 'blob' })
  const match = /filename="([^"]+)"/.exec(res.headers['content-disposition'] ?? '')
  const filename = match ? match[1] : fallbackName
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return filename
}
