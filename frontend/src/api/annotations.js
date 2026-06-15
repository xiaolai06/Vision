const API = '/api'

export async function fetchAnnotations(recordId) {
  const res = await fetch(`${API}/annotations/${recordId}`)
  if (!res.ok) throw new Error('获取标注失败')
  return res.json()
}

export async function saveAnnotations(recordId, annotations) {
  const res = await fetch(`${API}/annotations/${recordId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ annotations }),
  })
  if (!res.ok) throw new Error('保存标注失败')
  return res.json()
}

export async function updateAnnotation(annotationId, data) {
  const res = await fetch(`${API}/annotations/${annotationId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('更新标注失败')
  return res.json()
}

export async function deleteAnnotation(annotationId) {
  const res = await fetch(`${API}/annotations/${annotationId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除标注失败')
  return res.json()
}
