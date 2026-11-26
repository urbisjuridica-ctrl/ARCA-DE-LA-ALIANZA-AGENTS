export interface VerificationResult {
  status: "PASS" | "REJECTED";
  reason: string;
  domains: string[];
  action?: string;
  fields: Record<string, string>;
}
export function verifySyntaxAndPolicy(message: string): VerificationResult;
