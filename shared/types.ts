/**
 * PrivacyLens Shared Domain Types
 * Used across Extension (TypeScript) and aligned with Backend Pydantic Schemas.
 */

export type RequestCategory = 
  | 'analytics' 
  | 'advertising' 
  | 'social' 
  | 'cdn' 
  | 'essential' 
  | 'telemetry' 
  | 'unknown';

export type RiskTier = 'Very Low' | 'Low' | 'Moderate' | 'High' | 'Critical';

export type GapType = 
  | 'omission_advertising' 
  | 'omission_analytics' 
  | 'broad_language_concern' 
  | 'permission_mismatch' 
  | 'undisclosed_third_party' 
  | 'excessive_persistence';

export type FindingSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface NetworkSignal {
  requestId: string;
  url: string;
  targetDomain: string;
  initiator: string;
  isThirdParty: boolean;
  category: RequestCategory;
  method: string;
  timestamp: number;
}

export interface StorageSignal {
  type: 'cookie' | 'localStorage' | 'sessionStorage';
  name: string;
  isThirdParty: boolean;
  persistent: boolean;
  byteLength?: number;
}

export interface PermissionSignal {
  permission: string;
  state: 'granted' | 'prompt' | 'denied';
  timestamp: number;
}

export interface TabObservationBatch {
  domain: string;
  tabUrl: string;
  policyUrl?: string;
  timestamp: number;
  requests: NetworkSignal[];
  storage: StorageSignal[];
  permissions: PermissionSignal[];
}

export interface PolicyClaim {
  claimId: string;
  category: string;
  dataType: string;
  purpose: string;
  sharing: boolean;
  thirdParty?: string;
  retentionSpecified: boolean;
  retentionPeriod?: string;
  sectionName: string;
  exactQuote: string;
  confidence: number;
}

export interface EvidenceFinding {
  findingId: string;
  gapType: GapType;
  severity: FindingSeverity;
  confidence: number;
  title: string;
  rationale: string;
  evidence: {
    policyQuotes: string[];
    observedDomains: string[];
    observedStorageKeys?: string[];
    observedPermissions?: string[];
  };
}

export interface SiteAnalysisResult {
  domain: string;
  policyUrl?: string;
  inspectedAt: string;
  riskScore: number;
  riskTier: RiskTier;
  confidence: number;
  summary: string;
  claimsCount: number;
  observedThirdPartiesCount: number;
  findings: EvidenceFinding[];
  dataFlow: {
    firstParty: string;
    thirdParties: {
      domain: string;
      category: RequestCategory;
      requestCount: number;
      disclosedInPolicy: boolean;
    }[];
  };
  temporalChange?: {
    previousScore?: number;
    scoreDelta?: number;
    newThirdParties?: string[];
  };
}
