/**
 * 垃圾分类预测 API
 * 连接 FastAPI 后端进行图片识别
 */

const API_BASE = '/api'

/**
 * 上传图片并获取分类结果
 * @param {Blob|File} imageFile - 图片文件
 * @param {string|null} modelId - 模型 ID
 * @returns {Promise<object>}
 */
export async function predictImage(imageFile, modelId = null) {
  const formData = new FormData()
  formData.append('file', imageFile)
  if (modelId) formData.append('model_id', modelId)

  const response = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `服务器错误 (${response.status})`)
  }

  return response.json()
}

/**
 * 发送 base64 图片并获取分类结果
 * @param {string} base64 - base64 编码的图片数据
 * @param {string|null} modelId - 模型 ID
 * @returns {Promise<object>}
 */
export async function predictBase64(base64, modelId = null) {
  const body = { image: base64 }
  if (modelId) body.model_id = modelId

  const response = await fetch(`${API_BASE}/predict_base64`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `服务器错误 (${response.status})`)
  }

  return response.json()
}

/**
 * 检查后端服务是否可用
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`)
    return res.ok
  } catch {
    return false
  }
}
