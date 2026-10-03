import assert from 'node:assert/strict'
import test from 'node:test'
import {reportExportMetadata,reportUrl,type ReportFilters} from '../src/reporting.ts'

const filters:ReportFilters={account:'12',project:'7',service:'EC2',resource_type:'aws.ec2.instance',active:'true',status:'open',severity:'high',priority:'high',category:'cost',simulation:'false',start_date:'2026-09-01',end_date:'2026-09-30',action:'report.export',object_type:'Organization'}

test('reportUrl sends only filters supported by the selected report',()=>{
 const cost=new URL(reportUrl('cost-detail','https://example.test/api/reports/cost-detail.csv',filters))
 assert.deepEqual([...cost.searchParams.keys()],['account','project','service','start_date','end_date'])
 assert.equal(cost.searchParams.get('status'),null)
 const remediation=new URL(reportUrl('remediation-history','https://example.test/api/reports/remediation-history.csv',filters))
 assert.deepEqual([...remediation.searchParams.keys()].sort(),['account','simulation','status'])
 assert.equal(remediation.searchParams.get('category'),null)
})

test('reportUrl omits empty supported filters',()=>{
 const empty={...filters,account:' ',severity:''}
 const url=new URL(reportUrl('compliance-findings','https://example.test/report.csv',empty))
 assert.equal(url.searchParams.has('account'),false)
 assert.equal(url.searchParams.has('severity'),false)
 assert.equal(url.searchParams.get('status'),'open')
})

test('reportExportMetadata parses existing response headers',()=>{
 const headers=new Headers({'X-Finopser-Report':'cost-detail','X-Finopser-Generated-At':'2026-10-03T03:00:00Z','X-Finopser-Row-Count':'42','X-Finopser-Truncated':'true'})
 assert.deepEqual(reportExportMetadata(headers,'fallback'),{report:'cost-detail',generatedAt:'2026-10-03T03:00:00Z',rowCount:'42',truncated:true})
})
