import {Applicant,FinancialMetrics,Finding,PolicyCheck,Transaction} from "./types";
export const applicants:Applicant[]=[
{id:"CR-2026-001",name:"Acme Manufacturing Ltd",sector:"Manufacturing",location:"Lagos, Nigeria",requestedAmount:18500000,purpose:"Working capital",submitted:"28 Sep 2026",analyst:"A. Okafor",status:"Under review",riskLevel:"Elevated"},
{id:"CR-2026-002",name:"Greenfield Logistics Ltd",sector:"Logistics",location:"Abuja, Nigeria",requestedAmount:9200000,purpose:"Fleet expansion",submitted:"29 Sep 2026",analyst:"M. Yusuf",status:"Pending evidence",riskLevel:"Moderate"},
{id:"CR-2026-003",name:"Nova Retail Services Ltd",sector:"Retail",location:"Port Harcourt, Nigeria",requestedAmount:6400000,purpose:"Inventory financing",submitted:"30 Sep 2026",analyst:"S. Bello",status:"Ready for review",riskLevel:"Low"}];
export const financialMetrics:FinancialMetrics={income:4200000,existingDebt:2180000,dti:51.9,lti:44,cashFlow:860000,assets:31800000,liabilities:12400000};
export const transactions:Transaction[]=[
{id:"TX-9012",date:"02 Oct 2026",description:"Payroll & operations",type:"Outflow",amount:840000,balance:5820000,flagged:false},
{id:"TX-9008",date:"30 Sep 2026",description:"Customer settlement",type:"Inflow",amount:2100000,balance:6660000,flagged:false},
{id:"TX-8991",date:"28 Sep 2026",description:"Large third-party transfer",type:"Inflow",amount:4800000,balance:4560000,flagged:true,reason:"Unusually large inflow relative to recent activity"},
{id:"TX-8975",date:"26 Sep 2026",description:"Supplier payment",type:"Outflow",amount:1250000,balance:-240000,flagged:true,reason:"Material balance movement"},
{id:"TX-8958",date:"22 Sep 2026",description:"Customer settlement",type:"Inflow",amount:1780000,balance:1010000,flagged:false},
{id:"TX-8932",date:"18 Sep 2026",description:"Utilities & services",type:"Outflow",amount:330000,balance:-770000,flagged:true,reason:"Account moved sharply into negative balance"}];
export const policyChecks:PolicyCheck[]=[
{id:"P-01",requirement:"Debt-to-income ratio",threshold:"≤ 40%",actual:"51.9%",status:"Exception",evidence:"Calculated from stated income and existing debt obligations."},
{id:"P-02",requirement:"Loan-to-income ratio",threshold:"≤ 50%",actual:"44.0%",status:"Satisfied",evidence:"Requested facility compared with annualised income."},
{id:"P-03",requirement:"Positive operating cash flow",threshold:"> ₦0",actual:"₦860K",status:"Satisfied",evidence:"Latest available reporting period."},
{id:"P-04",requirement:"Recent bank statements",threshold:"6 months",actual:"4 months",status:"Missing",evidence:"Only four months of statements were supplied."},
{id:"P-05",requirement:"Large unexplained inflows",threshold:"Must be explained",actual:"₦4.8M inflow",status:"Unclear",evidence:"Transaction description does not establish business purpose."}];
export const findings:Finding[]=[
{id:"F-01",title:"Debt-to-income exception",description:"The calculated DTI of 51.9% is above the configured 40% policy threshold.",severity:"critical",source:"Financial analysis • Policy P-01"},
{id:"F-02",title:"Unusual inflow detected",description:"A ₦4.8M third-party inflow is materially larger than recent account activity and has no clear business-purpose evidence.",severity:"warning",source:"Transaction TX-8991"},
{id:"F-03",title:"Statement history incomplete",description:"Available statements cover four months rather than the six months required by policy.",severity:"warning",source:"Policy P-04"},
{id:"F-04",title:"Positive operating cash flow",description:"The latest available period shows positive operating cash flow of ₦860K.",severity:"positive",source:"Financial analysis"}];
export const monthlyCashFlow=[{month:"May",inflow:3.1,outflow:2.6},{month:"Jun",inflow:3.6,outflow:2.9},{month:"Jul",inflow:3.3,outflow:3.1},{month:"Aug",inflow:4.1,outflow:3.0},{month:"Sep",inflow:4.8,outflow:3.9},{month:"Oct",inflow:4.2,outflow:3.3}];