const API = '/api'

export async function fetchModels() {
  const res = await fetch(`${API}/models`)
  if (!res.ok) throw new Error('获取模型列表失败')
  return res.json()
}

export async function activateModel(modelId) {
  const res = await fetch(`${API}/models/${modelId}/activate`, { method: 'PUT' })
  if (!res.ok) throw new Error('切换模型失败')
  return res.json()
}
