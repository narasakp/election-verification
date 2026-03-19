import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo })
    console.error('[ErrorBoundary]', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      const { fallback, compact } = this.props

      if (fallback) return fallback(this.state.error, this.handleReset)

      if (compact) {
        return (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <AlertTriangle size={16} className="flex-shrink-0" />
            <span className="flex-1">เกิดข้อผิดพลาด: {this.state.error?.message || 'Unknown error'}</span>
            <button
              onClick={this.handleReset}
              className="flex items-center gap-1 px-2 py-1 bg-red-100 hover:bg-red-200 rounded text-xs font-medium transition"
            >
              <RefreshCw size={12} /> ลองใหม่
            </button>
          </div>
        )
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[300px] p-8 bg-red-50 border border-red-200 rounded-xl">
          <AlertTriangle size={48} className="text-red-400 mb-4" />
          <h2 className="text-lg font-semibold text-red-800 mb-2">เกิดข้อผิดพลาด</h2>
          <p className="text-red-600 text-sm text-center mb-4 max-w-md">
            {this.state.error?.message || 'เกิดข้อผิดพลาดที่ไม่คาดคิด'}
          </p>
          {this.state.errorInfo && (
            <details className="mb-4 w-full max-w-lg">
              <summary className="text-xs text-red-500 cursor-pointer hover:text-red-700">
                รายละเอียดทางเทคนิค
              </summary>
              <pre className="mt-2 p-3 bg-red-100 rounded text-xs text-red-800 overflow-auto max-h-40">
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition"
          >
            <RefreshCw size={16} /> ลองใหม่อีกครั้ง
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
