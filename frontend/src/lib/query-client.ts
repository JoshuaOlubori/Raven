import { QueryClient } from '@tanstack/react-query';

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000, // 30 seconds
        gcTime: 5 * 60_000, // 5 minutes
        retry: (failureCount, error) => {
          // Don't retry 4xx errors (except 401 which might be auth issue)
          if (error instanceof Response) {
            return error.status >= 500 || error.status === 401;
          }
          // For ApiError from our client
          if (error && typeof error === 'object' && 'status' in error) {
            const apiError = error as { status: number };
            return apiError.status >= 500 || apiError.status === 401;
          }
          return failureCount < 3;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Singleton for client-side
let browserQueryClient: QueryClient | undefined;

export function getQueryClient(): QueryClient {
  if (typeof window === 'undefined') {
    // Server: always make a new query client
    return makeQueryClient();
  }
  // Browser: make a new query client if we don't already have one
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}
