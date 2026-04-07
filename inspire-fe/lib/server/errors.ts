export class AppError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(message: string, status = 400, code = "bad_request", details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function assert(condition: unknown, message: string, status = 400, code = "bad_request"): asserts condition {
  if (!condition) {
    throw new AppError(message, status, code);
  }
}

