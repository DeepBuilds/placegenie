import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="mx-auto max-w-2xl px-4 py-12 text-center">
      <h1 className="text-2xl font-bold text-slate-900">Page not found</h1>
      <Link to="/" className="mt-4 inline-block text-indigo-600 hover:underline">
        Back to home
      </Link>
    </section>
  )
}
