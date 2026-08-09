import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

interface FetchState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

export function useFetch<T>(path: string | null): FetchState<T> & { reload: () => void } {
  const [state, setState] = useState<FetchState<T>>({
    data: null, error: null, loading: path !== null,
  });

  const load = useCallback(() => {
    if (path === null) return;
    setState((s) => ({ ...s, loading: s.data === null }));
    api.get<T>(path)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((err) => setState({
        data: null,
        error: err instanceof ApiError ? err.message : "The server can't be reached.",
        loading: false,
      }));
  }, [path]);

  useEffect(load, [load]);
  return { ...state, reload: load };
}
