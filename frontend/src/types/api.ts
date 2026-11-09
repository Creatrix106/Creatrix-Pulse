/** Standard error body expected from the backend. */
export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

/**
 * Some analytics only make sense when the dataset contains certain columns
 * (customer ids, cost, ...). The backend answers with `available: false` and a
 * human-readable reason instead of fabricating numbers.
 */
export type Capability<T> = { available: true; data: T } | { available: false; reason: string };
