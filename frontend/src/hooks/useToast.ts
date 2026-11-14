/**
 * src/hooks/useToast.ts
 *
 * Lightweight toast state manager inspired by the shadcn/ui toast hook.
 * Uses a module-level store (not Zustand) so it's usable outside React trees.
 *
 * Usage:
 *   const { toast } = useToast();
 *   toast({ title: 'Saved!', description: 'Your changes were saved.' });
 */

import * as React from 'react';
import type { ToastProps, ToastActionElement } from '@/components/ui/toast';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

const TOAST_LIMIT = 3;
const TOAST_REMOVE_DELAY_MS = 4000;

type ToastVariant = 'default' | 'destructive' | 'success';

interface ToasterToast extends Omit<ToastProps, 'variant'> {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: ToastActionElement;
  variant?: ToastVariant;
}

type Action =
  | { type: 'ADD_TOAST'; toast: ToasterToast }
  | { type: 'UPDATE_TOAST'; toast: Partial<ToasterToast> & { id: string } }
  | { type: 'DISMISS_TOAST'; toastId?: string }
  | { type: 'REMOVE_TOAST'; toastId?: string };

interface State {
  toasts: ToasterToast[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Module-level state (singleton — survives re-renders)
// ─────────────────────────────────────────────────────────────────────────────

let count = 0;
function genId(): string {
  count = (count + 1) % Number.MAX_SAFE_INTEGER;
  return String(count);
}

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

function addToRemoveQueue(toastId: string) {
  if (toastTimeouts.has(toastId)) return;
  const timeout = setTimeout(() => {
    toastTimeouts.delete(toastId);
    dispatch({ type: 'REMOVE_TOAST', toastId });
  }, TOAST_REMOVE_DELAY_MS);
  toastTimeouts.set(toastId, timeout);
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'ADD_TOAST':
      return {
        ...state,
        toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
      };
    case 'UPDATE_TOAST':
      return {
        ...state,
        toasts: state.toasts.map((t) =>
          t.id === action.toast.id ? { ...t, ...action.toast } : t,
        ),
      };
    case 'DISMISS_TOAST': {
      const { toastId } = action;
      if (toastId) {
        addToRemoveQueue(toastId);
      } else {
        state.toasts.forEach((t) => addToRemoveQueue(t.id));
      }
      return {
        ...state,
        toasts: state.toasts.map((t) =>
          !toastId || t.id === toastId ? { ...t, open: false } : t,
        ),
      };
    }
    case 'REMOVE_TOAST':
      return {
        ...state,
        toasts: action.toastId
          ? state.toasts.filter((t) => t.id !== action.toastId)
          : [],
      };
  }
}

// Listeners subscribed by useToast() calls
const listeners: Array<(state: State) => void> = [];
let memoryState: State = { toasts: [] };

function dispatch(action: Action) {
  memoryState = reducer(memoryState, action);
  listeners.forEach((listener) => listener(memoryState));
}

// ─────────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────────

type ToastOptions = Omit<ToasterToast, 'id'>;

function toast(options: ToastOptions) {
  const id = genId();
  const dismiss = () => dispatch({ type: 'DISMISS_TOAST', toastId: id });
  dispatch({
    type: 'ADD_TOAST',
    toast: { ...options, id, open: true, onOpenChange: (open) => { if (!open) dismiss(); } },
  });
  return { id, dismiss, update: (props: ToastOptions) => dispatch({ type: 'UPDATE_TOAST', toast: { ...props, id } }) };
}

export function useToast() {
  const [state, setState] = React.useState<State>(memoryState);

  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const index = listeners.indexOf(setState);
      if (index > -1) listeners.splice(index, 1);
    };
  }, []);

  return {
    ...state,
    toast,
    dismiss: (toastId?: string) => dispatch({ type: 'DISMISS_TOAST', toastId }),
  };
}

// Also export the imperative toast() for use outside React components
export { toast };
