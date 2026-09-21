import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-8">
        <div className="mb-6 text-center font-display text-3xl font-extrabold text-primary">
          Algorise
        </div>
        <Outlet />
      </div>
    </div>
  )
}
