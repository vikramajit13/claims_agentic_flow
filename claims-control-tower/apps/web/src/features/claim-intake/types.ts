export type ClaimFormState = {
  claimNumber: string;
  customerId: string;
  claimType: string;
  description: string;
  incidentDate: string;
  claimAmount: string;
};

export const initialClaimFormState: ClaimFormState = {
  claimNumber: "",
  customerId: "",
  claimType: "motor",
  description: "",
  incidentDate: "",
  claimAmount: ""
};
