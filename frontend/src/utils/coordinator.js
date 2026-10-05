export const STAGE_OPTIONS = [
  ['placed', 'Placed'], ['in_process', 'In process'], ['applied', 'Applied'], ['rejected', 'Rejected'], ['not_applied', 'Not applied yet'],
]
export const STAGE_STYLE = {
  placed: 'bg-emerald-100 text-emerald-800', in_process: 'bg-indigo-100 text-indigo-800', applied: 'bg-sky-100 text-sky-800',
  rejected: 'bg-red-100 text-red-800', not_applied: 'bg-slate-100 text-slate-700',
}
export const STAGE_LABEL = Object.fromEntries(STAGE_OPTIONS)
