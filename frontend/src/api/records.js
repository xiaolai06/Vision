const API = '/api'

export async function fetchRecords(params = {}) {
  const query = new URLSearchParams()
  if (params.category) query.set('category', params.category)
  if (params.corrected !== undefined) query.set('corrected', params.corrected)
  if (params.offset) query.set('offset', params.offset)
  if (params.limit) query.set('limit', params.limit)
  if (params.start_date) query.set('start_date', params.start_date)
  if (params.end_date) query.set('end_date', params.end_date)
  if (params.keyword) query.set('keyword', params.keyword)
  if (params.model_type) query.set('model_type', params.model_type)

  const res = await fetch(`${API}/records?${query}`)
  if (!res.ok) throw new Error('获取记录失败')
  return res.json()
}

export async function deleteRecord(id) {
  const res = await fetch(`${API}/records/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('删除失败')
  return res.json()
}

export async function batchDeleteRecords(ids) {
  const res = await fetch(`${API}/records/batch/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
  if (!res.ok) throw new Error('批量删除失败')
  return res.json()
}

export async function correctRecord(id, category, label, confidence) {
  const res = await fetch(`${API}/records/${id}/correct`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category, label, confidence }),
  })
  if (!res.ok) throw new Error('修正失败')
  return res.json()
}

export async function batchCorrectRecords(ids, category, label, confidence) {
  const res = await fetch(`${API}/records/batch/correct`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids, category, label, confidence }),
  })
  if (!res.ok) throw new Error('批量修正失败')
  return res.json()
}

export async function fetchStats() {
  const res = await fetch(`${API}/records/stats`)
  if (!res.ok) throw new Error('获取统计失败')
  return res.json()
}

export function exportUrl(format, category) {
  const params = new URLSearchParams({ format })
  if (category) params.set('category', category)
  return `${API}/export?${params}`
}

export async function fetchChartData(params = {}) {
  const query = new URLSearchParams()
  if (params.category) query.set('category', params.category)
  if (params.days) query.set('days', params.days)
  const res = await fetch(`${API}/records/chart-data?${query}`)
  if (!res.ok) throw new Error('获取图表数据失败')
  return res.json()
}

export function splitExportUrl(trainRatio, valRatio, testRatio, category) {
  const params = new URLSearchParams({
    train_ratio: trainRatio,
    val_ratio: valRatio,
    test_ratio: testRatio,
  })
  if (category) params.set('category', category)
  return `${API}/export/split?${params}`
}
