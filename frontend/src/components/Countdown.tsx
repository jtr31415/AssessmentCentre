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
      <span>
        Unlocking your data…{" "}
        <button
          onClick={onUnlock}
          style={{ marginLeft: 8, cursor: "pointer", fontSize: "inherit" }}
        >
          Refresh
        </button>
      </span>
    );
  }

  return (
    <span>
      {days}d {hours}h {minutes}m {seconds}s
    </span>
  );
}
