import client from './client'
import { downloadFile } from './download'

export const getMyReport = () => client.get('/reports/me').then((r) => r.data)
export const downloadMyReport = () => downloadFile('/reports/me.csv', 'placegenie-my-report.csv')
