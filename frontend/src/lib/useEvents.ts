import { useEffect, useRef } from "react";

export type MeridianEvent =
  | "sync.started"
  | "sync.account_done"
  | "sync.completed"
  | "sync.failed"
  | "transactions.new";

// One SSE subscription per mounted hook; reconnects are the browser's job.
export function useEvents(handlers: Partial<Record<MeridianEvent, (data: unknown) => void>>) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const source = new EventSource("/api/events");
    const names: MeridianEvent[] = [
      "sync.started", "sync.account_done", "sync.completed", "sync.failed",
      "transactions.new",
    ];
    const listeners = names.map((name) => {
      const listener = (event: MessageEvent) => {
        const handler = handlersRef.current[name];
        if (handler) handler(JSON.parse(event.data));
      };
      source.addEventListener(name, listener);
      return [name, listener] as const;
    });
    return () => {
      listeners.forEach(([name, listener]) => source.removeEventListener(name, listener));
      source.close();
    };
  }, []);
}
