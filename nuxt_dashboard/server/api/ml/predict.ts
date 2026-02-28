/**
 * Server API endpoint for ML model predictions
 * Uses python-runner to invoke ml_integration_api.py as a CLI tool
 */

import { execPython } from '../../utils/python-runner'

export default defineEventHandler(async (event) => {
  const method = getMethod(event)

  if (method === "POST") {
    try {
      const body = await readBody(event)
      const args = ["--action", "get_recommendation", "--format", "json"]
      if (body?.battery_soc !== undefined) args.push("--battery_soc", String(body.battery_soc))
      if (body?.strategy) args.push("--strategy", body.strategy)
      const raw = await execPython("ml_integration", args)
      return JSON.parse(raw)
    } catch (error: any) {
      console.error("ML prediction error:", error)
      throw createError({ statusCode: 500, statusMessage: String(error?.message ?? "Prediction failed") })
    }
  }

  if (method === "GET") {
    try {
      const raw = await execPython("ml_integration", ["--action", "get_status", "--format", "json"])
      return JSON.parse(raw)
    } catch (error: any) {
      console.error("ML status error:", error)
      return {
        success: false,
        status: "unavailable",
        message: "ML pipeline unavailable. Ensure Python environment is set up.",
        timestamp: new Date().toISOString()
      }
    }
  }

  throw createError({ statusCode: 405, statusMessage: "Method not allowed" })
})
