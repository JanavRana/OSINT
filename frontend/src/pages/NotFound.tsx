export default function NotFound() {
  return (
    <div className="flex h-[70vh] items-center justify-center">
      <div className="text-center">
        <h1 className="font-mono text-6xl font-bold text-signal">404</h1>
        <p className="mt-4 text-lg text-text">Page Not Found</p>
        <p className="mt-2 text-sm text-muted">
          The page you are looking for does not exist.
        </p>
      </div>
    </div>
  )
}