export type FindingSeverity="critical"|"warning"|"info"|"positive";
export interface Applicant{id:string;name:string;sector:string;location:string;requestedAmount:number;purpose:string;submitted:string;analyst:string;status:"Under review"|"Pending evidence"|"Ready for review";riskLevel:"Elevated"|"Moderate"|"Low";}
export interface FinancialMetrics{income:number;existingDebt:number;dti:number;lti:number;cashFlow:number;assets:number;liabilities:number;}
export interface Transaction{id:string;date:string;description:string;type:"Inflow"|"Outflow";amount:number;balance:number;flagged:boolean;reason?:string;}
export interface Finding{id:string;title:string;description:string;severity:FindingSeverity;source:string;}
export interface PolicyCheck{id:string;requirement:string;threshold:string;actual:string;status:"Satisfied"|"Exception"|"Unclear"|"Missing";evidence:string;}
