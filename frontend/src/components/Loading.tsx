export default function Loading() {
  return (
    <div className="flex h-[70vh] items-center justify-center">
      <div className="text-center">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-line border-t-signal"></div>
        <p className="mt-4 text-sm text-muted">
          Loading...
        </p>
      </div>
    </div>
  )
}