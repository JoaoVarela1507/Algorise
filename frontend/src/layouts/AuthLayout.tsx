import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-beige">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-lg">
        <div className="mb-6 text-center text-3xl font-extrabold text-salmon">
          Algorise
        </div>
        <Outlet />
      </div>
    </div>
  )
}
