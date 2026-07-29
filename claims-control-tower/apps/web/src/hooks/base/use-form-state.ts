import { useState } from "react";

export function useFormState<TState extends Record<string, unknown>>(initialState: TState) {
  const [state, setState] = useState<TState>(initialState);

  function updateField<TKey extends keyof TState>(key: TKey, value: TState[TKey]) {
    setState((current) => ({ ...current, [key]: value }));
  }

  function reset(nextState: TState = initialState) {
    setState(nextState);
  }

  return {
    state,
    setState,
    updateField,
    reset
  };
}
