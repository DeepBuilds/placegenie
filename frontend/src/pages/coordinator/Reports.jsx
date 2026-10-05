import { useState } from 'react'
import { downloadReport, getReports } from '../../api/admin'
import { ErrorNote, PageHeader } from '../../components/coordinator/Parts'
import { primaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { getErrorMessage } from '../../utils/errors'

const TITLES = { students: 'Students', applications: 'Applications', placements: 'Placements', companies: 'Companies', skills: 'Skills' }

export default function Reports() {
  const { data, error, loading } = useLoad(getReports, 'reports')
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState({ ok: '', error: '' })

  const download = async (kind) => {
    setBusy(kind)
    setMessage({ ok: '', error: '' })
    try {
      const name = await downloadReport(kind)
      setMessage({ ok: `Downloaded ${name}`, error: '' })
    } catch (err) {
      setMessage({ ok: '', error: getErrorMessage(err) })
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <PageHeader title="Reports" subtitle="Download CSV files that open in Excel or Google Sheets. They always contain the latest data." />
      <div className="mt-4 space-y-3" aria-live="polite">
        <ErrorNote>{error}</ErrorNote>
        <ErrorNote>{message.error}</ErrorNote>
        {message.ok && <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{message.ok}</p>}
      </div>
      {loading && !data && <p className="py-10 text-center text-slate-500">Loading reports…</p>}
      {data && (
        <ul className="mt-4 space-y-3">
          {data.map((r) => (
            <li key={r.kind} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div>
                <h2 className="font-semibold text-slate-900">{TITLES[r.kind] ?? r.kind}</h2>
                <p className="text-sm text-slate-600">{r.description}</p>
              </div>
              <button type="button" className={primaryButton} disabled={busy !== ''} onClick={() => download(r.kind)} aria-label={`Download ${TITLES[r.kind] ?? r.kind} report`}>
                {busy === r.kind ? 'Preparing…' : 'Download CSV'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
