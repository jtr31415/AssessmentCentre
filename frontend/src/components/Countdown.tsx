import { useEffect, useRef, useState } from "react";

interface Props {
  unlockAt: string;
  onUnlock: () => void;
}

function getRemaining(unlockAt: string): number {
  return Math.max(0, new Date(unlockAt).getTime() - Date.now());
}

export default function Countdown({ unlockAt, onUnlock }: Props) {
  const [msLeft, setMsLeft] = useState(() => getRemaining(unlockAt));
  const firedRef = useRef(false);

  // Reset state when unlockAt changes so a new deadline can fire again
  useEffect(() => {
    firedRef.current = false;
    setMsLeft(getRemaining(unlockAt));
  }, [unlockAt]);

  // Single interval created once per unlockAt+onUnlock; computes fresh time each tick
  useEffect(() => {
    // Fire immediately if already past the unlock time
    if (getRemaining(unlockAt) <= 0 && !firedRef.current) {
      firedRef.current = true;
      onUnlock();
      return;
    }

    const id = setInterval(() => {
      const rem = getRemaining(unlockAt);
      setMsLeft(rem);
      if (rem <= 0 && !firedRef.current) {
        firedRef.current = true;
        onUnlock();
      }
    }, 1000);

    return () => clearInterval(id);
  }, [unlockAt, onUnlock]);

  const totalSec = Math.floor(msLeft / 1000);
  const days = Math.floor(totalSec / 86400);
  const hours = Math.floor((totalSec % 86400) / 3600);
  const minutes = Math.floor((totalSec % 3600) / 60);
  const seconds = totalSec % 60;

  if (msLeft <= 0) {
    return (
      <span className="text-sm text-brand-muted">
        Unlocking your data…{" "}
        <button
          onClick={onUnlock}
          className="ml-2 text-brand-blue underline hover:no-underline cursor-pointer text-sm"
        >
          Refresh
        </button>
      </span>
    );
  }

  return (
    <div className="bg-white border border-brand-hair p-4 rounded text-center">
      <p className="text-[10px] uppercase tracking-wider text-brand-muted font-bold mb-1">
        Materials unlock in
      </p>
      <div className="text-2xl md:text-3xl font-extrabold font-mono text-brand-red tracking-tight tabular-numbers flex justify-center items-center gap-1.5">
        <span>{days}</span>
        <span className="text-xs text-brand-muted font-sans font-medium uppercase">d</span>
        <span className="text-brand-hair">:</span>
        <span>{String(hours).padStart(2, "0")}</span>
        <span className="text-xs text-brand-muted font-sans font-medium uppercase">h</span>
        <span className="text-brand-hair">:</span>
        <span>{String(minutes).padStart(2, "0")}</span>
        <span className="text-xs text-brand-muted font-sans font-medium uppercase">m</span>
        <span className="text-brand-hair">:</span>
        <span className="text-brand-red bg-red-50 px-1 rounded animate-pulse">
          {String(seconds).padStart(2, "0")}
        </span>
        <span className="text-xs text-brand-muted font-sans font-medium uppercase">s</span>
      </div>
    </div>
  );
}
